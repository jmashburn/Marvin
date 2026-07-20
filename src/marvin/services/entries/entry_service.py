"""Entry domain service — mutation + event emission in one place.

Marvin had no service layer for entries: the create/update/publish/archive rules and *which events
each transition emits* lived in the entry controller, and the automation write-back
(`runner._apply_writeback`) re-implemented a thinner copy — mutating the entry and emitting a bare
`entry_updated`, but NOT the status-transition events. So an AI write-back (or any future caller)
that flipped an entry to published silently skipped `entry_published`, and chained automations that
key on publish quietly stopped firing.

This service is the single seam. Every entry write goes through it, and it owns the emit — so status
transitions (`entry_published` / `entry_unpublished` / `entry_archived` / `entry_restored`) fire
*by construction*, from any caller, and chaining becomes reliable. It's also the natural home for
`changed_fields` / `before` / `after` (added next).

The event shape is preserved exactly from the controller (same integration_id, document data,
messages, and — importantly — the `entry_updated`-before-`entry_published` ordering the embedding
reaction depends on). `reaction_depth` is threaded so an automation's write-back re-emits at
`depth + 1`, keeping the loop-guard intact.
"""

from marvin.core.root_logger import get_logger
from marvin.repos.repository_factory import AllRepositories
from marvin.services.event_bus_service.event_types import EventEntryData, EventOperation, EventTypes

logger = get_logger("entry_service")

# Scalar entry fields we diff for `changed_fields`/`before`/`after` on update events. Deliberately
# small and scalar — never body/content/metadata (large, and by-value content shouldn't land in the
# audit log) or relationships. These are exactly the fields automation conditions key on.
_TRACKED_FIELDS = ("status", "title", "slug")


def _is_uuid(value: str) -> bool:
    import uuid as _uuid

    try:
        _uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _diff(old, new) -> tuple[list[str], dict, dict]:
    """(changed_fields, before, after) over the tracked scalar fields. before/after carry ONLY the
    changed fields, so `event.after.status == X` reads as "status changed to X"."""
    changed = [f for f in _TRACKED_FIELDS if getattr(old, f, None) != getattr(new, f, None)]
    before = {f: getattr(old, f, None) for f in changed}
    after = {f: getattr(new, f, None) for f in changed}
    return changed, before, after


class EntryService:
    """Own entry mutations and the events they emit. Construct per request/run with the actor + bus.

    Args:
        session:   an active SQLAlchemy session.
        group_id:  the workspace scope.
        event_bus: the EventBusService to dispatch through (the controller passes its request-scoped
                   one so events publish in the background; automation write-back passes a synchronous
                   one). Created synchronous if omitted.
        actor_id:  the user performing the action (goes on the event's `user_id`).
        integration_id: source tag on emitted events ("entry_management" for user actions,
                   "automation" for write-back).
    """

    def __init__(self, session, group_id, *, event_bus=None, actor_id=None,
                 integration_id: str = "entry_management") -> None:
        self.session = session
        self.group_id = group_id
        self.actor_id = actor_id
        self.integration_id = integration_id
        self._event_bus = event_bus
        self.repos = AllRepositories(session, group_id=group_id)

    @property
    def event_bus(self):
        if self._event_bus is None:
            from marvin.services.event_bus_service.event_bus_service import EventBusService
            self._event_bus = EventBusService(bg_tasks=None)  # synchronous fan-out
        return self._event_bus

    # ── Writes ────────────────────────────────────────────────────────────────
    def create(self, data_dict: dict):
        """Create an entry and emit `entry_created`. `data_dict` should already carry created_by."""
        entry = self.repos.entries.create(data_dict)
        names = self._names(entry)
        self._emit(entry, EventTypes.entry_created, EventOperation.create,
                   f"Entry '{entry.title}' created", names)
        return entry

    def update(self, entry_id, data, *, reaction_depth: int = 0):
        """Update an entry, emit `entry_updated`, then any status-transition events. Returns the
        updated entry, or None if it doesn't exist."""
        old = self.repos.entries.get_one(entry_id)
        if not old:
            return None
        entry = self.repos.entries.update(entry_id, data)
        self._emit_updated_and_transitions(old, entry, "updated", reaction_depth)
        return entry

    def apply_fields(self, entry_id, fields: dict, *, reaction_depth: int = 0):
        """Apply a dict of fields to an entry (the automation write-back path) — same mutation the AI
        write-back used, but now emitting `entry_updated` AND status transitions, so a write-back that
        changes status fires the right events and chains reliably. Returns the entry or None."""
        old = self.repos.entries.get_one(entry_id)
        if not old:
            return None
        self.repos.entries.apply_fields(entry_id, fields)
        entry = self.repos.entries.get_one(entry_id)
        self._emit_updated_and_transitions(old, entry, "updated by automation write-back", reaction_depth)
        return entry

    def apply_suggestion(self, entry_id):
        """Commit an entry's staged AI suggestion (suggestion_json) and emit `entry_updated`."""
        entry = self.repos.entries.apply_suggestion(entry_id)
        names = self._names(entry)
        self._emit(entry, EventTypes.entry_updated, EventOperation.update,
                   f"AI suggestion applied to '{entry.title}'", names)
        return entry

    def delete(self, entry_id) -> bool:
        """Emit `entry_deleted` (before the row is gone) then delete. Returns False if not found."""
        entry = self.repos.entries.get_one(entry_id)
        if not entry:
            return False
        names = self._names(entry)
        self._emit(entry, EventTypes.entry_deleted, EventOperation.delete,
                   f"Entry '{entry.title}' deleted", names)
        self.repos.entries.delete(entry_id)
        return True

    def set_status(self, entry_id, new_status: str, *, reaction_depth: int = 0):
        """Convenience for the entry status actions (publish/unpublish/archive/restore) — an update
        that only changes status, emitting `entry_updated` + the transition event."""
        from marvin.schemas.platform import EntryUpdate

        return self.update(entry_id, EntryUpdate(status=new_status), reaction_depth=reaction_depth)

    # ── Collection membership ──────────────────────────────────────────────────
    def _resolve_collection(self, collection_ref):
        """Resolve a collection within this workspace by id, slug, or name (same vocabulary the
        target selector uses). Returns the Collections row or None."""
        import uuid as _uuid

        from marvin.db.models.platform.collections import Collections

        ref = collection_ref
        if isinstance(ref, _uuid.UUID) or (isinstance(ref, str) and _is_uuid(ref)):
            coll = self.session.get(Collections, ref if isinstance(ref, _uuid.UUID) else _uuid.UUID(str(ref)))
            return coll if coll and coll.group_id == self.group_id else None
        return (
            self.session.query(Collections)
            .filter(Collections.group_id == self.group_id)
            .filter((Collections.slug == str(ref)) | (Collections.name == str(ref)))
            .first()
        )

    def add_to_collection(self, entry_id, collection_ref, *, reaction_depth: int = 0) -> str | None:
        """Add an entry to a collection (idempotent). Returns ``"added"`` (newly added, emits
        `entry_added_to_collection`), ``"exists"`` (already a member — no-op, no event), or ``None``
        (entry or collection not found in this workspace)."""
        import sqlalchemy as sa

        from marvin.db.models.platform.entry_collections import EntryCollections

        entry = self.repos.entries.get_one(entry_id)
        if not entry or entry.group_id != self.group_id:
            return None
        collection = self._resolve_collection(collection_ref)
        if not collection:
            return None

        existing = (
            self.session.query(EntryCollections)
            .filter(EntryCollections.entry_id == entry.id, EntryCollections.collection_id == collection.id)
            .first()
        )
        if existing:
            return "exists"

        max_sort = (
            self.session.query(sa.func.max(EntryCollections.sort_order))
            .filter(EntryCollections.collection_id == collection.id)
            .scalar()
        )
        self.session.add(EntryCollections(entry_id=entry.id, collection_id=collection.id, sort_order=(max_sort or -1) + 1))
        self.session.commit()
        self._emit(entry, EventTypes.entry_added_to_collection, EventOperation.update,
                   f"Entry '{entry.title}' added to collection '{collection.name}'", self._names(entry),
                   reaction_depth=reaction_depth)
        return "added"

    def remove_from_collection(self, entry_id, collection_ref, *, reaction_depth: int = 0) -> str | None:
        """Remove an entry from a collection (idempotent). Returns ``"removed"`` (emits
        `entry_removed_from_collection`), ``"absent"`` (wasn't a member — no-op, no event), or ``None``
        (entry or collection not found in this workspace)."""
        from marvin.db.models.platform.entry_collections import EntryCollections

        entry = self.repos.entries.get_one(entry_id)
        if not entry or entry.group_id != self.group_id:
            return None
        collection = self._resolve_collection(collection_ref)
        if not collection:
            return None

        deleted = (
            self.session.query(EntryCollections)
            .filter(EntryCollections.entry_id == entry.id, EntryCollections.collection_id == collection.id)
            .delete()
        )
        if not deleted:
            return "absent"
        self.session.commit()
        self._emit(entry, EventTypes.entry_removed_from_collection, EventOperation.update,
                   f"Entry '{entry.title}' removed from collection '{collection.name}'", self._names(entry),
                   reaction_depth=reaction_depth)
        return "removed"

    # ── Emission ──────────────────────────────────────────────────────────────
    def _emit_updated_and_transitions(self, old, entry, verb: str, reaction_depth: int) -> None:
        """Emit `entry_updated` first, then any status-transition events (published/unpublished/
        archived/restored). Each carries the scalar diff (changed_fields/before/after). The
        updated-then-published ordering is relied on by the embedding reaction — keep it.

        Wrapped in one correlation scope so `entry_updated` and its transition event share a chain id
        (inheriting the ambient id when this runs inside an automation, minting one from the controller).
        """
        from marvin.services.event_bus_service.correlation import correlation_scope

        names = self._names(entry)
        diff = _diff(old, entry)
        old_status = getattr(old, "status", None)
        with correlation_scope():
            self._emit(entry, EventTypes.entry_updated, EventOperation.update,
                       f"Entry '{entry.title}' {verb}", names, reaction_depth=reaction_depth, diff=diff)
            if old_status == entry.status:
                return
            if entry.status == "published":
                self._emit(entry, EventTypes.entry_published, EventOperation.update,
                           f"Entry '{entry.title}' published", names, reaction_depth=reaction_depth, diff=diff)
            elif old_status == "published":
                self._emit(entry, EventTypes.entry_unpublished, EventOperation.update,
                           f"Entry '{entry.title}' unpublished", names, reaction_depth=reaction_depth, diff=diff)
            if entry.status == "archived":
                self._emit(entry, EventTypes.entry_archived, EventOperation.update,
                           f"Entry '{entry.title}' archived", names, reaction_depth=reaction_depth, diff=diff)
            elif old_status == "archived":
                self._emit(entry, EventTypes.entry_restored, EventOperation.update,
                           f"Entry '{entry.title}' restored from archive", names, reaction_depth=reaction_depth, diff=diff)

    def _names(self, entry) -> tuple[str | None, str | None, str | None]:
        """(entry_type_slug, workspace_name, author_name) for the event payload."""
        entry_type_slug = None
        if getattr(entry, "entry_type_id", None):
            etype = self.repos.entry_types.get_one(entry.entry_type_id)
            if etype:
                entry_type_slug = etype.slug

        group = self.repos.groups.get_one(self.group_id)
        workspace_name = group.name if group else None

        author_name = None
        if getattr(entry, "created_by", None):
            author = self.repos.users.get_one(entry.created_by)
            if author:
                author_name = author.full_name
        return entry_type_slug, workspace_name, author_name

    def _emit(self, entry, event_type, operation, message: str,
              names: tuple[str | None, str | None, str | None], *, reaction_depth: int = 0,
              diff: tuple[list[str], dict, dict] | None = None) -> None:
        """Dispatch one entry event. Best-effort — a dispatch failure never breaks the write."""
        entry_type_slug, workspace_name, author_name = names
        changed_fields, before, after = diff or ([], {}, {})
        try:
            self.event_bus.dispatch(
                integration_id=self.integration_id,
                group_id=self.group_id,
                event_type=event_type,
                document_data=EventEntryData(
                    operation=operation,
                    entry_id=entry.id,
                    entry_title=entry.title,
                    entry_type=entry_type_slug,
                    workspace_id=entry.group_id,
                    workspace_name=workspace_name,
                    author_id=getattr(entry, "created_by", None),
                    author_name=author_name,
                    changed_fields=changed_fields,
                    before=before,
                    after=after,
                ),
                message=message,
                user_id=self.actor_id,
                entity_id=entry.id,
                entity_type="entry",
                reaction_depth=reaction_depth,
            )
        except Exception as e:  # noqa: BLE001 — event dispatch is best-effort
            logger.error(f"Failed to dispatch {getattr(event_type, 'name', event_type)} event: {e}", exc_info=True)

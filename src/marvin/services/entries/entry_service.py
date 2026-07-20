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

# Status → the event a *transition into* that status emits, and the event a transition *out of* it
# emits. Order matters: entry_updated is always emitted first, then these, then archive events.


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
        self._emit_updated_and_transitions(old.status, entry, "updated", reaction_depth)
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
        self._emit_updated_and_transitions(old.status, entry, "updated by automation write-back", reaction_depth)
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

    # ── Emission ──────────────────────────────────────────────────────────────
    def _emit_updated_and_transitions(self, old_status: str, entry, verb: str, reaction_depth: int) -> None:
        """Emit `entry_updated` first, then any status-transition events (published/unpublished/
        archived/restored). The updated-then-published ordering is relied on by the embedding
        reaction — keep it."""
        names = self._names(entry)
        self._emit(entry, EventTypes.entry_updated, EventOperation.update,
                   f"Entry '{entry.title}' {verb}", names, reaction_depth=reaction_depth)
        if old_status == entry.status:
            return
        if entry.status == "published":
            self._emit(entry, EventTypes.entry_published, EventOperation.update,
                       f"Entry '{entry.title}' published", names, reaction_depth=reaction_depth)
        elif old_status == "published":
            self._emit(entry, EventTypes.entry_unpublished, EventOperation.update,
                       f"Entry '{entry.title}' unpublished", names, reaction_depth=reaction_depth)
        if entry.status == "archived":
            self._emit(entry, EventTypes.entry_archived, EventOperation.update,
                       f"Entry '{entry.title}' archived", names, reaction_depth=reaction_depth)
        elif old_status == "archived":
            self._emit(entry, EventTypes.entry_restored, EventOperation.update,
                       f"Entry '{entry.title}' restored from archive", names, reaction_depth=reaction_depth)

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
              names: tuple[str | None, str | None, str | None], *, reaction_depth: int = 0) -> None:
        """Dispatch one entry event. Best-effort — a dispatch failure never breaks the write."""
        entry_type_slug, workspace_name, author_name = names
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
                ),
                message=message,
                user_id=self.actor_id,
                entity_id=entry.id,
                entity_type="entry",
                reaction_depth=reaction_depth,
            )
        except Exception as e:  # noqa: BLE001 — event dispatch is best-effort
            logger.error(f"Failed to dispatch {getattr(event_type, 'name', event_type)} event: {e}", exc_info=True)

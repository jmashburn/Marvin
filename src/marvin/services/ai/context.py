"""
ContextBuilder — assembles structured context from Marvin objects before prompt construction.

Usage:
    ctx = (
        ContextBuilder(session, group_id)
        .with_site_settings()
        .with_variables()
        .with_entry(entry_id)
        .with_assets(entry_id)
        .inject("current_date", "2026-07-17")
        .build()
    )
"""

from datetime import datetime, UTC
from pydantic import UUID4
from sqlalchemy.orm import Session

from .operations.base import OperationContext


class ContextBuilder:
    def __init__(self, session: Session, group_id: UUID4) -> None:
        self._session = session
        self._group_id = group_id
        self._ctx = OperationContext()
        self._runtime: dict = {}

    # ── Fluent builders ────────────────────────────────────────────────

    def with_site_settings(self) -> "ContextBuilder":
        """Load workspace name and site preferences."""
        from marvin.db.models.groups.groups import Groups
        from marvin.db.models.groups.preferences import GroupPreferencesModel

        group = self._session.get(Groups, self._group_id)
        if group:
            self._ctx.workspace_name = group.name

        prefs = self._session.query(GroupPreferencesModel).filter_by(group_id=self._group_id).first()
        if prefs:
            self._ctx.site_title = prefs.site_title or ""
            self._ctx.site_locale = prefs.site_locale or "en-US"
            # Pull ai-specific config from site_metadata_json.ai
            ai_cfg = (prefs.site_metadata_json or {}).get("ai", {})
            for key, val in ai_cfg.items():
                self._ctx.variables[f"AI_{key.upper()}"] = str(val)

        return self

    def with_variables(self, slugs: list[str] | None = None) -> "ContextBuilder":
        """Load workspace variables (and secrets slugs) into context for {{SLUG}} resolution."""
        from marvin.db.models.groups.variables import WorkspaceVariable
        q = self._session.query(WorkspaceVariable).filter_by(group_id=self._group_id)
        if slugs:
            q = q.filter(WorkspaceVariable.slug.in_(slugs))
        for var in q.all():
            self._ctx.variables[var.slug] = var.value
        return self

    def with_entry(self, entry_id: UUID4) -> "ContextBuilder":
        """Load a single entry as the primary context object."""
        from marvin.db.models.platform.entries import EntryModel
        from marvin.db.models.platform.entry_types import EntryTypeModel
        entry = self._session.get(EntryModel, entry_id)
        if not entry:
            return self
        entry_type = self._session.get(EntryTypeModel, entry.entry_type_id) if entry.entry_type_id else None
        self._ctx.entry = {
            "id": str(entry.id),
            "title": entry.title or "",
            "summary": entry.summary or "",
            "description": entry.description or "",
            "status": entry.status or "",
            "content": str(entry.data_json or ""),
            "entry_type": entry_type.name if entry_type else "",
        }
        # Inject entry fields as runtime variables for {{SLUG}} resolution
        self._runtime["entry_title"] = entry.title or ""
        self._runtime["entry_type"] = entry_type.name if entry_type else ""
        return self

    def with_related_entries(self, entry_id: UUID4, limit: int = 5) -> "ContextBuilder":
        """Load entries that share a collection with the given entry."""
        from marvin.db.models.platform.entries import EntryModel, entry_collections
        from sqlalchemy import select, and_

        collection_ids = self._session.execute(
            select(entry_collections.c.collection_id).where(entry_collections.c.entry_id == entry_id)
        ).scalars().all()

        if not collection_ids:
            return self

        related = self._session.execute(
            select(EntryModel)
            .join(entry_collections, EntryModel.id == entry_collections.c.entry_id)
            .where(
                and_(
                    entry_collections.c.collection_id.in_(collection_ids),
                    EntryModel.id != entry_id,
                    EntryModel.group_id == self._group_id,
                )
            )
            .limit(limit)
        ).scalars().all()

        self._ctx.variables["related_entries"] = "; ".join(e.title or "" for e in related)
        return self

    def with_assets(self, entry_id: UUID4 | None = None) -> "ContextBuilder":
        """Load assets — either entry-linked or all workspace assets."""
        from marvin.db.models.platform.assets import AssetModel
        if entry_id:
            from marvin.db.models.platform.entries import entry_assets
            from sqlalchemy import select
            asset_ids = self._session.execute(
                select(entry_assets.c.asset_id).where(entry_assets.c.entry_id == entry_id)
            ).scalars().all()
            assets = [self._session.get(AssetModel, aid) for aid in asset_ids]
            assets = [a for a in assets if a]
        else:
            assets = self._session.query(AssetModel).filter_by(group_id=self._group_id).limit(10).all()

        self._ctx.assets = [{"id": str(a.id), "name": a.name, "mime_type": a.mime_type} for a in assets]
        return self

    def with_resources(self, entry_id: UUID4 | None = None) -> "ContextBuilder":
        """Load resources linked to an entry, or all workspace resources."""
        from marvin.db.models.platform.resources import ResourceModel
        if entry_id:
            from marvin.db.models.platform.entries import entry_resources
            from sqlalchemy import select
            resource_ids = self._session.execute(
                select(entry_resources.c.resource_id).where(entry_resources.c.entry_id == entry_id)
            ).scalars().all()
            resources = [self._session.get(ResourceModel, rid) for rid in resource_ids]
            resources = [r for r in resources if r]
        else:
            resources = self._session.query(ResourceModel).filter_by(group_id=self._group_id).limit(10).all()

        self._ctx.resources = [
            {"id": str(r.id), "name": r.name, "type": r.resource_type, "description": r.description or ""}
            for r in resources
        ]
        return self

    def with_form_submission(self, submission_id: UUID4) -> "ContextBuilder":
        from marvin.db.models.platform.form_submissions import FormSubmissionModel
        sub = self._session.get(FormSubmissionModel, submission_id)
        if sub:
            self._ctx.form_submission = {
                "id": str(sub.id),
                "data": sub.data_json or {},
                "status": sub.status or "",
                "submitted_at": str(sub.submitted_at or ""),
            }
        return self

    def inject(self, key: str, value: str) -> "ContextBuilder":
        """Inject a runtime variable (e.g. current_date) for {{SLUG}} resolution."""
        self._runtime[key] = value
        return self

    def build(self) -> OperationContext:
        """Finalise context with runtime injections."""
        self._runtime.setdefault("current_date", datetime.now(UTC).strftime("%Y-%m-%d"))
        self._runtime.setdefault("workspace_name", self._ctx.workspace_name)
        self._runtime.setdefault("site_title", self._ctx.site_title)
        # Make runtime values available as variables for resolve()
        self._ctx.variables.update(self._runtime)
        return self._ctx


def resolve_prompt_messages(messages, group_id: UUID4, runtime: dict | None = None) -> list:
    """
    Run resolve() over every message's string content to interpolate {{SLUG}} references.
    Secrets, workspace variables, and runtime context all resolve in one pass.
    """
    from marvin.services.secrets.resolver import resolve
    resolved = []
    for msg in messages:
        if isinstance(msg.content, str):
            content = resolve(msg.content, group_id=group_id, context=runtime or {})
        else:
            content = msg.content  # multimodal list — skip interpolation
        from marvin.services.ai.base import Message
        resolved.append(Message(role=msg.role, content=content))
    return resolved

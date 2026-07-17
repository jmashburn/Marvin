"""API routes for per-workspace AI workflow policy settings."""

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.db.models.groups.ai_settings import WorkspaceAISettingsModel
from marvin.routes._base import MarvinCrudRoute
from marvin.routes._base.base_controllers import BaseUserController
from marvin.routes._base.controller import controller
from marvin.schemas.group.ai_settings import (
    WorkspaceAISettingsRead,
    WorkspaceAISettingsUpdate,
)

router = APIRouter(prefix="/groups/{group_id}/ai-settings", route_class=MarvinCrudRoute)


@controller(router)
class AISettingsController(BaseUserController):
    """Manage per-workspace AI workflow policy."""

    def _require_access(self, group_id: UUID4) -> None:
        if self.user.admin:
            return
        if not any(m.group_id == group_id for m in self.user.workspace_memberships):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this workspace.")

    def _require_admin(self, group_id: UUID4) -> None:
        if self.user.admin:
            return
        for m in self.user.workspace_memberships:
            if m.group_id == group_id and m.workspace_role.value >= 4:
                return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ADMIN or OWNER role required.")

    @router.get("", response_model=WorkspaceAISettingsRead, summary="Get AI Workflow Settings")
    def get_ai_settings(self, group_id: UUID4) -> WorkspaceAISettingsRead:
        """Return current AI workflow settings; synthesises defaults if none saved yet."""
        self._require_access(group_id)

        row = self.session.query(WorkspaceAISettingsModel).filter_by(group_id=group_id).first()
        if not row:
            # Return defaults without persisting — first PATCH will create the row.
            return WorkspaceAISettingsRead(
                id="00000000-0000-0000-0000-000000000000",
                group_id=group_id,
                enabled=True,
                credential_mode="platform",
                approval_mode="suggest-only",
            )
        return WorkspaceAISettingsRead.model_validate(row)

    @router.patch("", response_model=WorkspaceAISettingsRead, summary="Update AI Workflow Settings")
    def update_ai_settings(self, group_id: UUID4, data: WorkspaceAISettingsUpdate) -> WorkspaceAISettingsRead:
        """Upsert AI workflow settings. Creates the row on first write."""
        self._require_admin(group_id)

        # Soft-validate: if workspace credential mode, warn if secret_ref slug missing
        warnings = []
        if data.credential_mode == "workspace" and data.secret_ref:
            from marvin.db.models.groups.secrets import WorkspaceSecret
            exists = self.session.query(WorkspaceSecret).filter_by(
                group_id=group_id, slug=data.secret_ref
            ).first()
            if not exists:
                warnings.append(f"Secret slug '{data.secret_ref}' not found in this workspace.")

        row = self.session.query(WorkspaceAISettingsModel).filter_by(group_id=group_id).first()
        if not row:
            row = WorkspaceAISettingsModel(session=self.session, group_id=group_id)
            self.session.add(row)

        for field, value in data.model_dump(exclude_unset=True).items():
            if hasattr(row, field):
                setattr(row, field, value)

        # Clear secret_ref when switching away from workspace mode
        if data.credential_mode is not None and data.credential_mode != "workspace":
            row.secret_ref = None

        self.session.commit()
        self.session.refresh(row)

        result = WorkspaceAISettingsRead.model_validate(row)
        if warnings:
            self.logger.warning("AI settings saved with warnings: %s", "; ".join(warnings))
        return result

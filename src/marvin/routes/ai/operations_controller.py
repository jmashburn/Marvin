"""Routes for AI operations — list, execute, and execution history."""

import time
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.db.models.groups.ai_executions import AIExecutionModel
from marvin.db.models.groups.ai_settings import WorkspaceAISettingsModel
from marvin.routes._base import MarvinCrudRoute
from marvin.routes._base.base_controllers import BaseUserController
from marvin.routes._base.controller import controller
from marvin.schemas.group.ai_execution import AIExecutionRead, AIOperationExecuteRequest

router = APIRouter(prefix="/ai", route_class=MarvinCrudRoute)


@controller(router)
class AIOperationsController(BaseUserController):

    # ── Operations catalogue ───────────────────────────────────────────

    @router.get("/operations", summary="List AI Operations")
    def list_operations(self) -> list[dict]:
        """Return all registered system operations and their schemas."""
        from marvin.services.ai.operations import list_operations
        return [op.info() for op in list_operations()]

    @router.get("/operations/{slug}", summary="Get AI Operation")
    def get_operation(self, slug: str) -> dict:
        from marvin.services.ai.operations import get_operation
        try:
            return get_operation(slug).info()
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Operation '{slug}' not found.")

    # ── Execute ────────────────────────────────────────────────────────

    @router.post("/operations/{slug}/execute", response_model=AIExecutionRead, summary="Execute AI Operation")
    def execute_operation(self, slug: str, body: AIOperationExecuteRequest) -> AIExecutionRead:
        from marvin.services.ai.factory import AIDisabledError, get_workspace_ai_provider
        from marvin.services.ai.operations import get_operation

        # Load and validate operation
        try:
            operation = get_operation(slug)
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Operation '{slug}' not found.")

        # Permission check
        if not self.user.admin:
            role = 0
            for m in self.user.workspace_memberships:
                if m.group_id == self.group_id:
                    role = m.workspace_role.value
                    break
            if role < operation.min_role:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for this operation.")

        # Budget check from workspace settings
        self._check_budget()

        # Resolve provider
        try:
            provider = get_workspace_ai_provider(self.session, self.group_id)
        except AIDisabledError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"AI provider error: {e}")

        # Determine model
        model = body.model_override or self._default_model()
        if not model:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No model configured. Set a default model on the provider.")

        # Build context
        ctx = self._build_context(body)

        # Create execution record (pending)
        execution = AIExecutionModel(
            session=self.session,
            group_id=self.group_id,
            operation_slug=slug,
            provider_type=provider.provider_type,
            model_id=model,
            status="pending",
            triggered_by=self.user.id,
            trigger_type="api",
            entity_type=body.entity_type,
            entity_id=body.entity_id,
        )
        self.session.add(execution)
        self.session.commit()

        # Run the operation
        start = time.monotonic()
        try:
            execution.status = "running"
            execution.started_at = datetime.now(UTC)
            self.session.commit()

            messages = operation.build_prompt(body.input, ctx)
            result = provider.complete_structured(messages, model, operation.output_schema)

            elapsed_ms = int((time.monotonic() - start) * 1000)
            execution.status = "completed"
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = elapsed_ms
            execution.output_json = result
            self.session.commit()

        except Exception as e:
            execution.status = "failed"
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = int((time.monotonic() - start) * 1000)
            execution.error_message = str(e)
            self.session.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI call failed: {e}")

        self.session.refresh(execution)
        return AIExecutionRead.model_validate(execution)

    # ── Execution history ──────────────────────────────────────────────

    @router.get("/executions", response_model=list[AIExecutionRead], summary="List Executions")
    def list_executions(
        self,
        operation_slug: str | None = None,
        status: str | None = None,
        entity_id: UUID4 | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AIExecutionRead]:
        q = self.session.query(AIExecutionModel).filter_by(group_id=self.group_id)
        if operation_slug:
            q = q.filter(AIExecutionModel.operation_slug == operation_slug)
        if status:
            q = q.filter(AIExecutionModel.status == status)
        if entity_id:
            q = q.filter(AIExecutionModel.entity_id == entity_id)
        rows = q.order_by(AIExecutionModel.created_at.desc()).offset(offset).limit(limit).all()
        return [AIExecutionRead.model_validate(r) for r in rows]

    @router.get("/executions/{execution_id}", response_model=AIExecutionRead, summary="Get Execution")
    def get_execution(self, execution_id: UUID4) -> AIExecutionRead:
        row = self.session.get(AIExecutionModel, execution_id)
        if not row or row.group_id != self.group_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found.")
        return AIExecutionRead.model_validate(row)

    @router.delete("/executions/{execution_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Execution")
    def delete_execution(self, execution_id: UUID4) -> None:
        if not self.user.admin:
            for m in self.user.workspace_memberships:
                if m.group_id == self.group_id and m.workspace_role.value >= 4:
                    break
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ADMIN or OWNER role required.")
        row = self.session.get(AIExecutionModel, execution_id)
        if not row or row.group_id != self.group_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found.")
        self.session.delete(row)
        self.session.commit()

    # ── Helpers ────────────────────────────────────────────────────────

    def _check_budget(self) -> None:
        settings = self.session.query(WorkspaceAISettingsModel).filter_by(group_id=self.group_id).first()
        if not settings or not settings.budget_config:
            return
        budget = settings.budget_config
        max_per_day = budget.get("max_requests_per_day")
        if max_per_day:
            from sqlalchemy import func
            today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            count = self.session.query(func.count(AIExecutionModel.id)).filter(
                AIExecutionModel.group_id == self.group_id,
                AIExecutionModel.created_at >= today_start,
            ).scalar() or 0
            if count >= max_per_day:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Daily AI request limit ({max_per_day}) reached.")

    def _default_model(self) -> str | None:
        settings = self.session.query(WorkspaceAISettingsModel).filter_by(group_id=self.group_id).first()
        if settings and settings.model:
            return settings.model
        from marvin.db.models.groups.ai_providers import AIModelModel, AIProviderModel
        provider = self.session.query(AIProviderModel).filter_by(group_id=self.group_id, is_default=True, enabled=True).first()
        if provider:
            model = self.session.query(AIModelModel).filter_by(provider_id=provider.id, is_default=True, enabled=True).first()
            if model:
                return model.model_id
        return None

    def _build_context(self, body: AIOperationExecuteRequest):
        from marvin.db.models.groups.preferences import GroupPreferencesModel
        from marvin.services.ai.operations.base import OperationContext

        prefs = self.session.query(GroupPreferencesModel).filter_by(group_id=self.group_id).first()
        ai_cfg = (prefs.site_metadata_json or {}).get("ai", {}) if prefs else {}

        ctx = OperationContext(
            workspace_name=self.group.name if hasattr(self, "_group") else "",
            site_title=prefs.site_title or "" if prefs else "",
            site_locale=prefs.site_locale or "en-US" if prefs else "en-US",
            current_date=datetime.now(UTC).strftime("%Y-%m-%d"),
            variables={k: v for k, v in ai_cfg.items()},
        )

        if body.entity_type == "entry" and body.entity_id:
            from marvin.db.models.platform.entries import EntryModel
            entry = self.session.get(EntryModel, body.entity_id)
            if entry:
                ctx.entry = {"title": entry.title, "content": str(entry.data_json or ""), "status": entry.status}

        if body.entity_type == "form_submission" and body.entity_id:
            from marvin.db.models.platform.form_submissions import FormSubmissionModel
            sub = self.session.get(FormSubmissionModel, body.entity_id)
            if sub:
                ctx.form_submission = {"data": sub.data_json or {}}

        return ctx

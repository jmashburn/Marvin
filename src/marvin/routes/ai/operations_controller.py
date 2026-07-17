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

        # Validate the selected model can satisfy the operation's capability requirements (§7)
        self._validate_model_capabilities(operation, model)

        # Build context via ContextBuilder
        from marvin.services.ai.context import ContextBuilder, resolve_prompt_messages
        builder = ContextBuilder(self.session, self.group_id).with_site_settings().with_variables()
        if body.entity_type == "entry" and body.entity_id:
            builder.with_entry(body.entity_id).with_assets(body.entity_id).with_resources(body.entity_id)
        elif body.entity_type == "asset" and body.entity_id:
            builder.with_asset(body.entity_id)
        elif body.entity_type == "resource" and body.entity_id:
            builder.with_resource(body.entity_id)
        elif body.entity_type == "form_submission" and body.entity_id:
            builder.with_form_submission(body.entity_id)
        # Vision operations need the raw image bytes loaded into context.
        if operation.requires_vision:
            builder.with_asset_images()
        ctx = builder.build()

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

            # Build prompt then resolve {{SLUG}} references
            messages = operation.build_prompt(body.input, ctx)
            messages = resolve_prompt_messages(messages, self.group_id, ctx.variables)

            # execute_operation returns (parsed_dict, CompletionResult with token counts)
            parsed, completion = provider.execute_operation(messages, model, operation.output_schema)

            from marvin.services.ai.pricing import estimate_cost
            elapsed_ms = int((time.monotonic() - start) * 1000)
            execution.status = "completed"
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = elapsed_ms
            execution.output_json = parsed
            execution.prompt_tokens = completion.prompt_tokens
            execution.completion_tokens = completion.completion_tokens
            execution.total_tokens = completion.total_tokens
            execution.estimated_cost_usd = estimate_cost(
                provider.provider_type, model,
                completion.prompt_tokens, completion.completion_tokens,
            )
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
        from sqlalchemy import func
        settings = self.session.query(WorkspaceAISettingsModel).filter_by(group_id=self.group_id).first()
        if not settings or not settings.budget_config:
            return
        budget = settings.budget_config

        max_per_day = budget.get("max_requests_per_day")
        if max_per_day:
            today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            count = self.session.query(func.count(AIExecutionModel.id)).filter(
                AIExecutionModel.group_id == self.group_id,
                AIExecutionModel.created_at >= today_start,
            ).scalar() or 0
            if count >= max_per_day:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Daily request limit ({max_per_day}) reached.")

        max_cost = budget.get("max_cost_per_month_usd")
        if max_cost:
            month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            spent = self.session.query(func.sum(AIExecutionModel.estimated_cost_usd)).filter(
                AIExecutionModel.group_id == self.group_id,
                AIExecutionModel.created_at >= month_start,
                AIExecutionModel.status == "completed",
            ).scalar() or 0.0
            if spent >= max_cost:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Monthly cost limit (${max_cost:.2f}) reached.")

    def _validate_model_capabilities(self, operation, model: str) -> None:
        """Reject the call up front if the operation needs a capability the model lacks (§7).

        ``ai_models`` rows are the capability source of truth. When no row exists for the
        model (platform credential mode or an ad-hoc override) we cannot assert incompatibility,
        so the call is allowed through. Extend with further capability flags (e.g. tools) as
        operations declare them.
        """
        if not getattr(operation, "requires_vision", False):
            return
        from marvin.db.models.groups.ai_providers import AIModelModel
        row = (
            self.session.query(AIModelModel)
            .filter_by(group_id=self.group_id, model_id=model)
            .first()
        )
        if row and not row.supports_vision:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Operation '{operation.slug}' requires a vision-capable model; '{model}' does not support vision.",
            )

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


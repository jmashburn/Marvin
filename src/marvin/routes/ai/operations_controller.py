"""Routes for AI operations — list, execute, and execution history."""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.db.models.groups.ai_executions import AIExecutionModel
from marvin.db.models.groups.ai_settings import WorkspaceAISettingsModel
from marvin.routes._base import MarvinCrudRoute
from marvin.routes._base.base_controllers import BaseUserController
from marvin.routes._base.controller import controller
from marvin.schemas.group.ai_execution import (
    AIComposeEntryRequest,
    AIExecutionRead,
    AIOperationExecuteRequest,
    AIReindexRequest,
)

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

        # Invocation-source gate: operation's declared sources ∩ workspace policy.
        self._check_invocation_source(body.source, operation.invocation_sources)

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
        # RAG operations retrieve semantically-similar workspace chunks for the question.
        if getattr(operation, "requires_retrieval", False):
            from marvin.core.config import get_app_settings
            from marvin.services.ai.embeddings import default_embedding_model
            emb_model = default_embedding_model(provider.provider_type)
            query = body.input.get("question") or body.input.get("query") or ""
            if emb_model:
                top_k = getattr(get_app_settings(), "AI_RAG_TOP_K", 5)
                builder.with_semantic_search(query, provider, emb_model, limit=top_k, entity_types=["entry", "resource"])
        ctx = builder.build()

        # Workspace logging policy: whether to persist inputs/outputs on the execution.
        log_inputs, log_outputs = self._logging_policy()

        # Create execution record (pending)
        execution = AIExecutionModel(
            session=self.session,
            group_id=self.group_id,
            operation_slug=slug,
            provider_type=provider.provider_type,
            model_id=model,
            status="pending",
            triggered_by=self.user.id,
            trigger_type=body.source,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            input_json=body.input if log_inputs else None,
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
            from marvin.core.config import get_app_settings
            from marvin.services.ai.base import CompletionOptions
            _app = get_app_settings()
            opts = CompletionOptions(
                temperature=getattr(_app, "AI_DEFAULT_TEMPERATURE", 0.7),
                max_tokens=getattr(_app, "AI_DEFAULT_MAX_TOKENS", None),
            )
            parsed, completion = provider.execute_operation(messages, model, operation.output_schema, opts)

            # For retrieval ops, attach the actual sources (index → entity + title) so the UI can
            # render clickable citations. IDs come from context, not the model, so they're authoritative.
            if getattr(operation, "requires_retrieval", False) and ctx.retrieved:
                parsed = {**(parsed or {}), "retrieved_sources": self._resolve_retrieved_sources(ctx.retrieved)}

            from marvin.services.ai.pricing import estimate_cost
            elapsed_ms = int((time.monotonic() - start) * 1000)
            execution.status = "completed"
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = elapsed_ms
            execution.output_json = parsed if log_outputs else None
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
            self._emit_ai_event(execution, "failed", str(e))
            self._maybe_emit_quota(execution, str(e))
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI call failed: {e}")

        self.session.refresh(execution)
        self._emit_ai_event(execution, "completed", None)
        self._emit_budget_thresholds(execution)
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

    # ── Embeddings (RAG) ───────────────────────────────────────────────

    @router.post("/embeddings/reindex", summary="Reindex embeddings for semantic search / RAG")
    def reindex_embeddings(self, body: AIReindexRequest) -> dict:
        from marvin.services.ai.embeddings import default_embedding_model, index_entity
        from marvin.services.ai.factory import AIDisabledError, get_workspace_ai_provider
        from marvin.services.ai.operations.base import ROLE_EDITOR

        # Workspace maintenance — require EDITOR or higher.
        if not self.user.admin:
            role = 0
            for m in self.user.workspace_memberships:
                if m.group_id == self.group_id:
                    role = m.workspace_role.value
                    break
            if role < ROLE_EDITOR:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="EDITOR role or higher required.")

        try:
            provider = get_workspace_ai_provider(self.session, self.group_id)
        except AIDisabledError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        if not getattr(provider, "supports_embeddings", False):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Provider '{provider.provider_type}' does not support embeddings.",
            )
        model = default_embedding_model(provider.provider_type)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No default embedding model for this provider.",
            )

        entities = chunks = 0
        for entity_type, entity_id, text in self._reindex_targets(body):
            try:
                chunks += index_entity(self.session, self.group_id, entity_type, entity_id, text, provider, model)
                entities += 1
            except Exception as e:
                self.logger.warning("reindex failed for %s %s: %s", entity_type, entity_id, e)
        self._emit_reindex_event(model, entities, chunks)
        return {"model": model, "entities_indexed": entities, "chunks_indexed": chunks}

    # ── Compose (schema-driven draft generation) ───────────────────────

    @router.post("/compose-entry", summary="Compose a draft entry from a brief")
    def compose_entry(self, body: AIComposeEntryRequest) -> dict:
        """Generate a DRAFT entry of `entry_type` from a brief (+ optional images).

        The entry type's field schema IS the LLM output schema, so the model returns exactly
        the fields a valid entry needs. The result lands as status='inbox' for review — the
        caller (Marvin / MCP / UI) decides whether to publish, which fires the usual pipeline.
        """
        import time
        import uuid
        from datetime import UTC, datetime

        from marvin.core.config import get_app_settings
        from marvin.db.models.platform.entry_types import EntryTypes
        from marvin.schemas.platform.entry_type_recipe import EntryTypeRecipe
        from marvin.schemas.platform.entry_type_schema import EntryTypeSchemaDefinition
        from marvin.services.ai.base import CompletionOptions, ImagePart, Message
        from marvin.services.ai.compose import entry_type_to_output_schema
        from marvin.services.ai.context import ContextBuilder, resolve_prompt_messages
        from marvin.services.ai.factory import get_workspace_ai_provider
        from marvin.services.ai.operations.base import ROLE_AUTHOR
        from marvin.services.ai.pricing import estimate_cost

        # AUTHOR or higher — composing creates content.
        if not self.user.admin:
            role = 0
            for m in self.user.workspace_memberships:
                if m.group_id == self.group_id:
                    role = m.workspace_role.value
                    break
            if role < ROLE_AUTHOR:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AUTHOR role or higher required.")

        # Compose is an authoring verb: reachable from the editor, MCP, the agent, and the API
        # (not forms/scheduled). Gated against the workspace invocation_sources policy.
        self._check_invocation_source(body.source, ("editor", "mcp", "agent", "api"))

        # Resolve entry type by slug (workspace or system), then by id.
        entry_type = (
            self.session.query(EntryTypes)
            .filter(EntryTypes.slug == body.entry_type)
            .filter((EntryTypes.group_id == self.group_id) | (EntryTypes.group_id.is_(None)))
            .first()
        )
        if not entry_type:
            try:
                et = self.session.get(EntryTypes, uuid.UUID(str(body.entry_type)))
                if et and et.group_id in (None, self.group_id):
                    entry_type = et
            except (ValueError, TypeError):
                entry_type = None
        if not entry_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Entry type '{body.entry_type}' not found.")

        schema_def = EntryTypeSchemaDefinition.model_validate(entry_type.schema_json or {})
        recipe = EntryTypeRecipe.model_validate(entry_type.recipe_json or {})
        output_schema = entry_type_to_output_schema(schema_def, entry_type.name)

        # Assign asset roles from the recipe (hero → first) so rendering (getFeaturedAsset) lights up.
        asset_attachments = self._recipe_asset_attachments(body.asset_ids or [], recipe)

        # Degrade gracefully: if AI is off / unconfigured / erroring, still create a blank
        # skeleton draft of this type so the flow works "at a very dumb level".
        provider = None
        try:
            provider = get_workspace_ai_provider(self.session, self.group_id)
        except Exception:
            provider = None
        model = (body.model_override or self._default_model()) if provider else None
        if not provider or not model:
            return self._compose_skeleton(body, entry_type, schema_def, asset_attachments)

        self._check_budget()

        # Context + vision images.
        builder = ContextBuilder(self.session, self.group_id).with_site_settings().with_variables()
        for aid in body.asset_ids or []:
            builder.with_asset(aid)
        if body.asset_ids:
            builder.with_asset_images()
        ctx = builder.build()

        instruction = (
            f"Compose a new '{entry_type.name}' for {ctx.workspace_name or 'this workspace'} from the brief below. "
            f"Fill every field you reasonably can"
            + (", using the attached image(s) as the subject." if body.asset_ids else ".")
            + f"\n\nBrief:\n{body.brief}"
        )
        parts: list = [instruction]
        for a in ctx.assets or []:
            img = a.get("image_data")
            if img:
                parts.append(ImagePart(data=img, mime_type=a.get("mime_type") or "image/png"))
        voice = recipe.enrichment.get("voice") if isinstance(recipe.enrichment, dict) else None
        system_content = (
            f"You are a content author. Produce a complete, publish-ready '{entry_type.name}'. "
            f"Return ONLY the requested fields."
        )
        if voice:
            system_content += f" Voice/tone: {voice}"
        messages = [
            Message(role="system", content=system_content),
            Message(role="user", content=parts if len(parts) > 1 else instruction),
        ]
        messages = resolve_prompt_messages(messages, self.group_id, ctx.variables)

        log_inputs, log_outputs = self._logging_policy()
        execution = AIExecutionModel(
            session=self.session, group_id=self.group_id, operation_slug="compose-entry",
            provider_type=provider.provider_type, model_id=model, status="pending",
            triggered_by=self.user.id, trigger_type=body.source, entity_type="entry_type", entity_id=entry_type.id,
            input_json={"entry_type": body.entry_type, "brief": body.brief} if log_inputs else None,
        )
        self.session.add(execution)
        self.session.commit()

        start = time.monotonic()
        try:
            execution.status = "running"
            execution.started_at = datetime.now(UTC)
            self.session.commit()

            _app = get_app_settings()
            opts = CompletionOptions(
                temperature=getattr(_app, "AI_DEFAULT_TEMPERATURE", 0.7),
                max_tokens=getattr(_app, "AI_DEFAULT_MAX_TOKENS", None),
            )
            parsed, completion = provider.execute_operation(messages, model, output_schema, opts)

            fields = dict(parsed or {})
            title = fields.pop("title", None) or f"Untitled {entry_type.name}"
            summary = fields.pop("summary", None)
            allowed = schema_def.get_field_keys()
            data_json = {k: v for k, v in fields.items() if k in allowed}

            entry = self.repos.entries.create({
                "title": title,
                "summary": summary,
                "entry_type_id": entry_type.id,
                "status": "inbox",  # draft — review before publishing
                "data_json": data_json,
                "asset_attachments": asset_attachments or None,
                "created_by": self.user.id,
            })
            self.session.commit()

            elapsed_ms = int((time.monotonic() - start) * 1000)
            execution.status = "completed"
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = elapsed_ms
            execution.entity_type = "entry"
            execution.entity_id = entry.id
            execution.output_json = (
                {"entry_id": str(entry.id), "title": title, "status": entry.status, "fields": data_json}
                if log_outputs else {"entry_id": str(entry.id), "status": entry.status}
            )
            execution.prompt_tokens = completion.prompt_tokens
            execution.completion_tokens = completion.completion_tokens
            execution.total_tokens = completion.total_tokens
            execution.estimated_cost_usd = estimate_cost(
                provider.provider_type, model, completion.prompt_tokens, completion.completion_tokens,
            )
            self.session.commit()

        except HTTPException as he:
            # e.g. the repo rejecting AI output that fails schema validation.
            self._fail_execution(execution, str(he.detail), start)
            self._emit_ai_event(execution, "failed", str(he.detail))
            raise
        except Exception as e:
            self._fail_execution(execution, str(e), start)
            self._emit_ai_event(execution, "failed", str(e))
            self._maybe_emit_quota(execution, str(e))
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Compose failed: {e}")

        self.session.refresh(execution)
        self._emit_ai_event(execution, "completed", None)
        self._emit_budget_thresholds(execution)
        return {
            "entryId": str(entry.id),
            "status": entry.status,
            "title": title,
            "editUrl": f"/workspace/entries/{entry.id}",
            "executionId": str(execution.id),
            "totalTokens": execution.total_tokens,
            "estimatedCostUsd": execution.estimated_cost_usd,
            "generated": data_json,
        }

    # ── Compose helpers ────────────────────────────────────────────────

    def _recipe_asset_attachments(self, asset_ids: list, recipe) -> list[dict]:
        """Map provided assets to the recipe's roles (first → hero, then declared order)."""
        roles = [r.role for r in recipe.assets.roles] if (recipe.assets and recipe.assets.roles) else []
        out: list[dict] = []
        for i, aid in enumerate(asset_ids):
            role = roles[i] if i < len(roles) else (roles[-1] if roles else None)
            out.append({"asset_id": str(aid), "role": role, "position": i})
        return out

    def _skeleton_data(self, schema_def, brief: str) -> dict:
        """Minimal valid data_json for a no-AI draft: required fields filled with type-appropriate
        placeholders, and the brief stashed into the first free-text field so it isn't lost."""
        from datetime import UTC, datetime

        def placeholder(f):
            t = f.type
            if t == "number":
                return 0
            if t == "boolean":
                return False
            if t == "select":
                opts = getattr(f, "options", []) or []
                return opts[0] if opts else ""
            if t == "date":
                return datetime.now(UTC).date().isoformat()
            if t == "datetime":
                return datetime.now(UTC).isoformat()
            if t == "json":
                return {}
            return ""  # text / textarea / markdown

        data: dict = {f.key: placeholder(f) for f in schema_def.get_required_fields()}
        for f in schema_def.fields:
            if f.type in ("markdown", "textarea", "text"):
                data[f.key] = brief
                break
        return data

    def _compose_skeleton(self, body, entry_type, schema_def, asset_attachments) -> dict:
        """No-AI fallback: create a blank draft of the type so /compose still works when AI is off."""
        brief = (body.brief or "").strip()
        first_line = brief.splitlines()[0].strip() if brief else ""
        title = (first_line[:120] or f"New {entry_type.name}")
        entry = self.repos.entries.create({
            "title": title,
            "entry_type_id": entry_type.id,
            "status": "inbox",
            "data_json": self._skeleton_data(schema_def, brief),
            "asset_attachments": asset_attachments or None,
            "created_by": self.user.id,
        })
        self.session.commit()
        return {
            "entryId": str(entry.id),
            "status": entry.status,
            "title": title,
            "editUrl": f"/workspace/entries/{entry.id}",
            "executionId": None,
            "totalTokens": None,
            "estimatedCostUsd": None,
            "generated": entry.data_json,
            "aiSkipped": True,
        }

    # ── Helpers ────────────────────────────────────────────────────────

    def _fail_execution(self, execution, error: str, start: float) -> None:
        """Mark an execution failed. Rolls back first so a poisoned transaction (e.g. an
        IntegrityError during create) can't block writing the failure record."""
        import time
        from datetime import UTC, datetime

        self.session.rollback()
        row = self.session.get(AIExecutionModel, execution.id) or execution
        row.status = "failed"
        row.completed_at = datetime.now(UTC)
        row.duration_ms = int((time.monotonic() - start) * 1000)
        row.error_message = (error or "")[:2000]
        self.session.commit()

    def _resolve_retrieved_sources(self, retrieved: list[dict]) -> list[dict]:
        """Map retrieved chunks (in citation order) to their entity + resolved title.

        The LLM cites sources by their 1-based [n] index, which aligns with this ordered list,
        so the UI can turn each citation into a link. Titles are looked up in bulk per type.
        """
        from marvin.db.models.platform.entries import Entries
        from marvin.db.models.platform.resources import Resources

        entry_ids = {c["entity_id"] for c in retrieved if c.get("entity_type") == "entry"}
        resource_ids = {c["entity_id"] for c in retrieved if c.get("entity_type") == "resource"}
        titles: dict[tuple[str, str], str] = {}
        if entry_ids:
            for e in self.session.query(Entries).filter(Entries.id.in_(entry_ids)).all():
                titles[("entry", str(e.id))] = e.title or "Untitled entry"
        if resource_ids:
            for r in self.session.query(Resources).filter(Resources.id.in_(resource_ids)).all():
                titles[("resource", str(r.id))] = r.name or "Untitled resource"

        sources: list[dict] = []
        for i, c in enumerate(retrieved):
            et = c.get("entity_type")
            eid = str(c.get("entity_id"))
            sources.append({
                "index": i + 1,
                "entity_type": et,
                "entity_id": eid,
                "title": titles.get((et, eid), f"{et} {eid[:8]}"),
                "score": c.get("score"),
            })
        return sources

    def _reindex_targets(self, body: AIReindexRequest) -> list[tuple[str, object, str]]:
        from marvin.db.models.platform.entries import Entries
        from marvin.db.models.platform.resources import Resources

        def entry_text(e) -> str:
            return "\n".join(filter(None, [e.title, e.summary, e.description, str(e.data_json or "")]))

        def resource_text(r) -> str:
            return "\n".join(filter(None, [r.name, r.description, r.url]))

        targets: list[tuple[str, object, str]] = []
        if body.scope == "workspace":
            for e in self.session.query(Entries).filter_by(group_id=self.group_id).all():
                targets.append(("entry", e.id, entry_text(e)))
            for r in self.session.query(Resources).filter_by(group_id=self.group_id).all():
                targets.append(("resource", r.id, resource_text(r)))
        elif body.entity_type == "entry" and body.entity_id:
            e = self.session.get(Entries, body.entity_id)
            if e and e.group_id == self.group_id:
                targets.append(("entry", e.id, entry_text(e)))
        elif body.entity_type == "resource" and body.entity_id:
            r = self.session.get(Resources, body.entity_id)
            if r and r.group_id == self.group_id:
                targets.append(("resource", r.id, resource_text(r)))
        return targets

    def _logging_policy(self) -> tuple[bool, bool]:
        """(log_inputs, log_outputs) from the workspace logging_config.

        Defaults preserve prior behavior: outputs are logged, inputs are not. A workspace can
        opt into input logging or out of output logging via ai_settings.logging_config.
        """
        settings = self.session.query(WorkspaceAISettingsModel).filter_by(group_id=self.group_id).first()
        cfg = (settings.logging_config if settings else None) or {}
        return bool(cfg.get("log_inputs", False)), bool(cfg.get("log_outputs", True))

    def _check_invocation_source(self, source: str, operation_sources) -> None:
        """Gate a call by its invocation surface.

        Effective allow-list = the operation's declared sources ∩ the workspace's
        invocation_sources policy. `source` is set by the calling infrastructure (the admin
        editor sends "editor", MarvinMCP sends "mcp", the agent endpoint sends "agent", …), so
        this is surface/feature gating — the per-user authorization wall is min_role. The
        workspace policy is an override map: a source is enabled unless explicitly set false,
        so an unset/None policy allows everything (back-compat).
        """
        from marvin.services.ai.operations.base import INVOCATION_SOURCES

        if source not in INVOCATION_SOURCES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown invocation source '{source}'. Valid: {', '.join(INVOCATION_SOURCES)}.",
            )
        if source not in operation_sources:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This operation cannot be invoked from the '{source}' source.",
            )
        settings = self.session.query(WorkspaceAISettingsModel).filter_by(group_id=self.group_id).first()
        policy = settings.invocation_sources if settings else None
        if isinstance(policy, dict) and policy.get(source, True) is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This workspace has disabled AI from the '{source}' source.",
            )

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
        # Workspace mode: default model from the default provider's models.
        from marvin.db.models.groups.ai_providers import AIModelModel, AIProviderModel
        provider = self.session.query(AIProviderModel).filter_by(group_id=self.group_id, is_default=True, enabled=True).first()
        if provider:
            model = self.session.query(AIModelModel).filter_by(provider_id=provider.id, is_default=True, enabled=True).first()
            if model:
                return model.model_id
        # Platform mode: fall back to the admin-configured AppSettings model (e.g. OPENAI_MODEL),
        # so platform credentials work with env vars alone — no per-workspace model needed.
        if settings and settings.credential_mode == "platform":
            from marvin.core.config import get_app_settings
            app = get_app_settings()
            provider_type = settings.provider or getattr(app, "AI_DEFAULT_PROVIDER", "openai")
            return getattr(app, f"{provider_type.upper()}_MODEL", None)
        return None

    # ── Event emission ─────────────────────────────────────────────────

    def _emit_ai_event(self, execution, status: str, error_message: str | None) -> None:
        """Dispatch ai_operation_executed / ai_operation_failed to the event bus."""
        from marvin.services.event_bus_service.event_types import EventAIOperationData, EventTypes
        try:
            self.event_bus.dispatch(
                integration_id="ai_operations",
                group_id=self.group_id,
                event_type=EventTypes.ai_operation_executed if status == "completed" else EventTypes.ai_operation_failed,
                document_data=EventAIOperationData(
                    operation_slug=execution.operation_slug,
                    provider_type=execution.provider_type,
                    model_id=execution.model_id,
                    status=status,
                    execution_id=execution.id,
                    entity_type=execution.entity_type,
                    entity_id=execution.entity_id,
                    total_tokens=execution.total_tokens,
                    estimated_cost_usd=execution.estimated_cost_usd,
                    error_message=error_message,
                    workspace_id=self.group_id,
                    workspace_name=self.group.name if self.group else None,
                ),
                message=f"AI operation '{execution.operation_slug}' {status}",
                user_id=self.user.id if self.user else None,
                entity_id=execution.entity_id,
                entity_type=execution.entity_type,
            )
        except Exception as e:
            self.logger.error(f"Failed to dispatch ai operation event: {e}", exc_info=True)

    def _emit_reindex_event(self, model: str, entities: int, chunks: int) -> None:
        """Dispatch ai_embeddings_reindexed to the event bus."""
        from marvin.services.event_bus_service.event_types import EventAIEmbeddingsData, EventTypes
        try:
            self.event_bus.dispatch(
                integration_id="ai_operations",
                group_id=self.group_id,
                event_type=EventTypes.ai_embeddings_reindexed,
                document_data=EventAIEmbeddingsData(
                    model_id=model,
                    entities_indexed=entities,
                    chunks_indexed=chunks,
                    workspace_id=self.group_id,
                    workspace_name=self.group.name if self.group else None,
                ),
                message=f"Reindexed {entities} entities ({chunks} chunks)",
                user_id=self.user.id if self.user else None,
            )
        except Exception as e:
            self.logger.error(f"Failed to dispatch ai_embeddings_reindexed event: {e}", exc_info=True)

    def _emit_budget_thresholds(self, execution) -> None:
        """Emit budget threshold/exceeded events on the call that crosses the line (once)."""
        from sqlalchemy import func
        settings = self.session.query(WorkspaceAISettingsModel).filter_by(group_id=self.group_id).first()
        budget = (settings.budget_config if settings else None) or {}
        max_cost = budget.get("max_cost_per_month_usd")
        if not max_cost:
            return
        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        spent = self.session.query(func.sum(AIExecutionModel.estimated_cost_usd)).filter(
            AIExecutionModel.group_id == self.group_id,
            AIExecutionModel.created_at >= month_start,
            AIExecutionModel.status == "completed",
        ).scalar() or 0.0
        prev = spent - (execution.estimated_cost_usd or 0.0)
        from marvin.core.config import get_app_settings
        from marvin.services.event_bus_service.event_types import EventTypes
        warn_frac = getattr(get_app_settings(), "AI_BUDGET_WARNING_PERCENT", 80.0) / 100.0
        if prev < max_cost <= spent:
            self._emit_budget_event(
                EventTypes.ai_budget_exceeded, "monthly_cost", spent, max_cost, 100.0,
                f"Monthly AI cost limit of ${max_cost:.2f} reached (spent ${spent:.2f})",
            )
        elif warn_frac > 0 and prev < warn_frac * max_cost <= spent:
            self._emit_budget_event(
                EventTypes.ai_budget_threshold_reached, "monthly_cost", spent, max_cost,
                round(spent / max_cost * 100, 1),
                f"AI spend reached {round(spent / max_cost * 100)}% of the ${max_cost:.2f} monthly limit",
            )

    def _maybe_emit_quota(self, execution, error: str) -> None:
        """Emit ai_provider_quota_exceeded when a provider rejects the call for lack of quota/credits."""
        low = error.lower()
        if "insufficient_quota" in low or "quota" in low or "insufficient" in low or "429" in low:
            from marvin.services.event_bus_service.event_types import EventTypes
            self._emit_budget_event(
                EventTypes.ai_provider_quota_exceeded, "provider_quota", None, None, None,
                error[:300], provider_type=execution.provider_type, operation_slug=execution.operation_slug,
            )

    def _emit_budget_event(self, event_type, reason: str, current, limit, percent, detail: str,
                           provider_type: str | None = None, operation_slug: str | None = None) -> None:
        from marvin.services.event_bus_service.event_types import EventAIBudgetData
        try:
            self.event_bus.dispatch(
                integration_id="ai_operations",
                group_id=self.group_id,
                event_type=event_type,
                document_data=EventAIBudgetData(
                    reason=reason,
                    current_value=current,
                    limit_value=limit,
                    percent=percent,
                    provider_type=provider_type,
                    operation_slug=operation_slug,
                    detail=detail,
                    workspace_id=self.group_id,
                    workspace_name=self.group.name if self.group else None,
                ),
                message=detail or f"AI {reason} event",
                user_id=self.user.id if self.user else None,
            )
        except Exception as e:
            self.logger.error(f"Failed to dispatch AI budget event: {e}", exc_info=True)


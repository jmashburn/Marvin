"""Shared AI authoring service — the one "brain" behind composing and revising entries.

Both entry points call this:
  - the ``POST /ai/compose-entry`` (and, later, ``/ai/revise-entry``) endpoints, and
  - the agent's ``compose_entry`` / ``revise_entry`` tools.

So "create such-and-such entry" from chat and the Compose button do the *same* thing, grounded the
same way. The service owns the authoring flow — grounding, the structured LLM call, the entry
write, the execution record, cost, and lifecycle events — decoupled from FastAPI (plain deps:
session, group_id, user, provider, model). The calling surface still owns request concerns
(role/source/budget gating, response shaping).

Stage 1 moves the compose flow here behavior-preservingly; grounding + revise layer on next.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from marvin.core.root_logger import get_logger


class AuthoringService:
    """Composes and revises entries. Construct with the request's session/user/provider/model."""

    def __init__(self, session, group_id, user, provider, model, event_bus=None, logger=None):
        from marvin.repos.all_repositories import get_repositories

        self.session = session
        self.group_id = group_id
        self.user = user
        self.provider = provider
        self.model = model
        self.repos = get_repositories(session, group_id=group_id)
        self._event_bus = event_bus
        self.logger = logger or get_logger(__name__)
        # The execution record for the most recent call — the caller reads it to emit the
        # ai_operation lifecycle + budget-threshold events it owns (success and failure paths).
        self.last_execution = None

    # ── Public API ─────────────────────────────────────────────────────────

    def compose(
        self,
        *,
        entry_type,
        brief: str,
        asset_ids: list | None = None,
        asset_attachments: list | None = None,
        source: str = "api",
        assistant_name: str = "Marvin",
        persona_prompt: str = "",
        register: str = "auto",
        log_inputs: bool = False,
        log_outputs: bool = True,
        max_tokens: int | None = None,
        ground: bool = True,
    ) -> dict:
        """Compose a DRAFT entry of ``entry_type`` from a brief (+ optional images).

        The entry type's field schema IS the LLM output schema, so the model returns exactly the
        fields a valid entry needs. Lands as status='inbox' for review. Requires a provider — the
        no-AI skeleton fallback stays with the caller.
        """
        from marvin.db.models.groups.ai_executions import AIExecutionModel
        from marvin.schemas.platform.entry_type_recipe import EntryTypeRecipe
        from marvin.schemas.platform.entry_type_schema import EntryTypeSchemaDefinition
        from marvin.services.ai.base import CompletionOptions, ImagePart, Message
        from marvin.services.ai.compose import entry_type_to_output_schema
        from marvin.services.ai.context import ContextBuilder, resolve_prompt_messages

        asset_ids = asset_ids or []
        schema_def = EntryTypeSchemaDefinition.model_validate(entry_type.schema_json or {})
        recipe = EntryTypeRecipe.model_validate(entry_type.recipe_json or {})
        output_schema = entry_type_to_output_schema(schema_def, entry_type.name)
        # Let the model return tags so it can REUSE the existing vocabulary (grounded below).
        if isinstance(output_schema, dict) and isinstance(output_schema.get("properties"), dict):
            output_schema["properties"]["tags"] = {
                "type": "array", "items": {"type": "string"},
                "description": "Relevant tags. Reuse the existing tag names listed in the prompt where they fit; only add a new tag when none match.",
            }

        # Context + vision images.
        builder = ContextBuilder(self.session, self.group_id).with_site_settings().with_variables()
        for aid in asset_ids:
            builder.with_asset(aid)
        if asset_ids:
            builder.with_asset_images()
        ctx = builder.build()

        grounding = self._grounding_block(brief) if ground else ""
        instruction = (
            f"Compose a new '{entry_type.name}' for {ctx.workspace_name or 'this workspace'} from the brief below. "
            f"Fill every field you reasonably can"
            + (", using the attached image(s) as the subject." if asset_ids else ".")
            + f"\n\nBrief:\n{brief}"
            + grounding
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

        execution = AIExecutionModel(
            session=self.session, group_id=self.group_id, operation_slug="compose-entry",
            provider_type=self.provider.provider_type, model_id=self.model, status="pending",
            triggered_by=getattr(self.user, "id", None), trigger_type=source,
            entity_type="entry_type", entity_id=entry_type.id,
            input_json={"entry_type": entry_type.slug, "brief": brief} if log_inputs else None,
        )
        self.session.add(execution)
        self.session.commit()
        self.last_execution = execution

        start = time.monotonic()
        try:
            execution.status = "running"
            execution.started_at = datetime.now(UTC)
            self.session.commit()

            opts = CompletionOptions(temperature=self._temperature(), max_tokens=max_tokens)
            parsed, completion = self.provider.execute_operation(messages, self.model, output_schema, opts)

            fields = dict(parsed or {})
            title = fields.pop("title", None) or f"Untitled {entry_type.name}"
            summary = fields.pop("summary", None)
            proposed_tags = fields.pop("tags", None)
            allowed = schema_def.get_field_keys()
            data_json = {k: v for k, v in fields.items() if k in allowed}

            entry = self.repos.entries.create({
                "title": title,
                "summary": summary,
                "entry_type_id": entry_type.id,
                "status": "inbox",  # draft — review before publishing
                "data_json": data_json,
                "asset_attachments": asset_attachments or None,
                "created_by": getattr(self.user, "id", None),
            })
            self.session.commit()
            # Link the model's tags onto the draft — find-or-create by slug, reusing the vocabulary.
            if isinstance(proposed_tags, (list, tuple)) and proposed_tags:
                self.repos.entries.apply_fields(entry.id, {"tags": list(proposed_tags)})
            self._emit_entry_created(entry, entry_type)

            self._complete_execution(execution, completion, start, entity_id=entry.id, output={
                "entry_id": str(entry.id), "title": title, "status": entry.status,
                **({"fields": data_json} if log_outputs else {}),
            })
        except Exception as e:
            self._fail_execution(execution, str(e), start)
            raise

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

    def recipe_asset_attachments(self, asset_ids: list, entry_type) -> list[dict]:
        """Map provided assets to the type recipe's roles (first → hero, then declared order)."""
        from marvin.schemas.platform.entry_type_recipe import EntryTypeRecipe

        recipe = EntryTypeRecipe.model_validate(entry_type.recipe_json or {})
        roles = [r.role for r in recipe.assets.roles] if (recipe.assets and recipe.assets.roles) else []
        out: list[dict] = []
        for i, aid in enumerate(asset_ids):
            role = roles[i] if i < len(roles) else (roles[-1] if roles else None)
            out.append({"asset_id": str(aid), "role": role, "position": i})
        return out

    # ── Catalog grounding (reuse, don't duplicate) ───────────────────────────

    def _grounding_block(self, seed_text: str) -> str:
        """A prompt block listing what already exists — the workspace tag vocabulary plus (via RAG)
        resources/assets relevant to the seed — so the model reuses instead of inventing duplicates."""
        from marvin.db.models.platform import Tags

        parts: list[str] = []
        tags = self.session.query(Tags).filter_by(group_id=self.group_id).order_by(Tags.name).limit(80).all()
        if tags:
            parts.append(
                "Existing tags — REUSE these exact names where they fit; do not invent near-duplicates:\n  "
                + ", ".join(t.name for t in tags)
            )
        catalog = self._rag_catalog(seed_text)
        if catalog:
            parts.append(catalog)
        if not parts:
            return ""
        return "\n\n## Already in this workspace — reuse, don't duplicate\n" + "\n".join(parts)

    def _rag_catalog(self, seed_text: str) -> str:
        """RAG-relevant existing resources/assets for the seed text, as a short reuse hint."""
        if not (seed_text and self.provider and getattr(self.provider, "supports_embeddings", False)):
            return ""
        from marvin.services.ai.context import ContextBuilder
        from marvin.services.ai.embeddings import default_embedding_model
        from marvin.services.ai.entity_resolve import resolve_retrieved_sources

        emb = default_embedding_model(self.provider.provider_type)
        if not emb:
            return ""
        try:
            built = (
                ContextBuilder(self.session, self.group_id)
                .with_semantic_search(seed_text, self.provider, emb, limit=8, entity_types=["resource", "asset"])
                .build()
            )
            srcs = resolve_retrieved_sources(self.session, built.retrieved or [])
        except Exception as e:  # grounding must never break authoring
            self.logger.warning(f"AuthoringService: RAG grounding failed: {e}")
            return ""
        res = list(dict.fromkeys(s["title"] for s in srcs if s.get("entity_type") == "resource"))
        ass = list(dict.fromkeys(s["title"] for s in srcs if s.get("entity_type") == "asset"))
        out: list[str] = []
        if res:
            out.append("Relevant existing resources (reference/attach these rather than recreating): " + ", ".join(res))
        if ass:
            out.append("Relevant existing assets: " + ", ".join(ass))
        return "\n".join(out)

    # ── Execution-record + event machinery (self-contained) ──────────────────

    def _temperature(self) -> float:
        from marvin.core.config import get_app_settings

        return getattr(get_app_settings(), "AI_DEFAULT_TEMPERATURE", 0.7)

    def _complete_execution(self, execution, completion, start, *, entity_id, output: dict) -> None:
        from marvin.services.ai.pricing import estimate_cost

        execution.status = "completed"
        execution.completed_at = datetime.now(UTC)
        execution.duration_ms = int((time.monotonic() - start) * 1000)
        execution.entity_type = "entry"
        execution.entity_id = entity_id
        execution.output_json = output
        execution.prompt_tokens = completion.prompt_tokens
        execution.completion_tokens = completion.completion_tokens
        execution.total_tokens = completion.total_tokens
        execution.estimated_cost_usd = estimate_cost(
            self.provider.provider_type, self.model, completion.prompt_tokens, completion.completion_tokens,
        )
        self.session.commit()

    def _fail_execution(self, execution, message: str, start) -> None:
        try:
            execution.status = "failed"
            execution.error_message = message[:2000]
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = int((time.monotonic() - start) * 1000)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            self.logger.warning(f"AuthoringService: could not record failure: {e}")

    def _event_bus_or_default(self):
        if self._event_bus is not None:
            return self._event_bus
        from marvin.services.event_bus_service.event_bus_service import EventBusService

        return EventBusService(bg_tasks=None)

    def _emit_entry_created(self, entry, entry_type) -> None:
        """Dispatch entry_created so reactions fire (smart-collection routing, RAG index, …). Best-effort."""
        from marvin.services.event_bus_service.event_types import EventEntryData, EventOperation, EventTypes

        try:
            grp = self.repos.groups.get_one(self.group_id)
            self._event_bus_or_default().dispatch(
                integration_id="entry_management",
                group_id=self.group_id,
                event_type=EventTypes.entry_created,
                document_data=EventEntryData(
                    operation=EventOperation.create,
                    entry_id=entry.id,
                    entry_title=entry.title,
                    entry_type=entry_type.slug,
                    workspace_id=self.group_id,
                    workspace_name=getattr(grp, "name", None) if grp else None,
                    author_id=getattr(self.user, "id", None),
                ),
                message=f"Entry '{entry.title}' composed by AI",
                user_id=getattr(self.user, "id", None),
                entity_id=entry.id,
                entity_type="entry",
            )
        except Exception as e:
            self.logger.error(f"AuthoringService: failed to dispatch entry_created: {e}")

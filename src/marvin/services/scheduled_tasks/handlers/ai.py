"""
AI scheduled task handlers.

Rebuild semantic-search (RAG) embeddings on a schedule so answers stay fresh
without a manual reindex. Complements auto-embed-on-publish (event-driven, TBD).
"""

from marvin.core.root_logger import get_logger
from marvin.db.db_setup import session_context
from marvin.db.models.platform.scheduled_tasks import ScheduledTaskModel
from marvin.services.event_bus_service.event_bus_service import EventBusService

from . import ScheduledTaskHandler, TaskHandlerRegistry

logger = get_logger(__name__)


class ReindexEmbeddingsHandler(ScheduledTaskHandler):
    """
    Rebuild RAG embeddings for the task's workspace, or for every workspace when
    run as a system task (no group_id).

    Skips workspaces where AI is disabled or whose provider has no embeddings.
    Emits ai_embeddings_reindexed per workspace so notifications/webhooks fire.
    """

    name = "Reindex AI Embeddings"
    description = "Rebuild RAG embeddings for this workspace (or all workspaces for a system task)"
    config_schema = {"type": "object", "properties": {}}

    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> str | None:
        from marvin.db.models.groups.groups import Groups
        from marvin.services.ai.embeddings import default_embedding_model, reindex_workspace
        from marvin.services.ai.factory import AIDisabledError, get_workspace_ai_provider

        done = 0
        total_entities = total_chunks = 0
        with session_context() as session:
            if task.group_id:
                groups = session.query(Groups).filter(Groups.id == task.group_id).all()
            else:
                groups = session.query(Groups).all()

            for g in groups:
                try:
                    provider = get_workspace_ai_provider(session, g.id)
                except AIDisabledError:
                    continue  # AI off for this workspace
                except Exception as ex:
                    logger.warning("reindex: provider error for workspace %s: %s", g.id, ex)
                    continue
                if not getattr(provider, "supports_embeddings", False):
                    continue
                model = default_embedding_model(provider.provider_type)
                if not model:
                    continue

                entities, chunks = reindex_workspace(session, g.id, provider, model)
                total_entities += entities
                total_chunks += chunks
                done += 1
                self._emit(event_bus, g, model, entities, chunks)

        scope = "this workspace" if task.group_id else "all workspaces"
        summary = f"Reindexed {done} workspace(s) ({scope}): {total_entities} entities, {total_chunks} chunks"
        logger.info("AI embeddings reindex: %s", summary)
        return summary

    def _emit(self, event_bus: EventBusService, group, model: str, entities: int, chunks: int) -> None:
        from marvin.services.event_bus_service.event_types import EventAIEmbeddingsData, EventTypes

        try:
            event_bus.dispatch(
                integration_id="ai_scheduled",
                group_id=group.id,
                event_type=EventTypes.ai_embeddings_reindexed,
                document_data=EventAIEmbeddingsData(
                    model_id=model,
                    entities_indexed=entities,
                    chunks_indexed=chunks,
                    workspace_id=group.id,
                    workspace_name=group.name,
                ),
                message=f"Scheduled reindex: {entities} entities ({chunks} chunks)",
            )
        except Exception as ex:
            logger.warning("reindex: failed to emit event for %s: %s", group.id, ex)


TaskHandlerRegistry.register("ai_reindex_embeddings", ReindexEmbeddingsHandler)

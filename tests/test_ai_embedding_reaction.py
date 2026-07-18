"""
Unit tests for AIEmbeddingReactionListener gating.

These verify the "reaction" listener that keeps the RAG index fresh:
 - which events trigger it (entry_published + entry_updated), and
 - the re-embed gate for entry_updated, which must never index draft/inbox/archived
   saves and must not double-embed the publish transition.
"""

from types import SimpleNamespace
from uuid import uuid4

from marvin.services.event_bus_service.event_bus_listener import AIEmbeddingReactionListener
from marvin.services.event_bus_service.event_types import EventTypes


def _listener() -> AIEmbeddingReactionListener:
    return AIEmbeddingReactionListener(group_id=uuid4())


class TestTriggerEvents:
    """get_subscribers must only react to publish + update events."""

    def test_entry_published_triggers_embedding(self):
        # Arrange
        listener = _listener()
        event = SimpleNamespace(event_type=EventTypes.entry_published)
        # Act
        result = listener.get_subscribers(event)
        # Assert
        assert result == ["ai_embed"]

    def test_entry_updated_triggers_embedding(self):
        # Arrange
        listener = _listener()
        event = SimpleNamespace(event_type=EventTypes.entry_updated)
        # Act
        result = listener.get_subscribers(event)
        # Assert
        assert result == ["ai_embed"]

    def test_entry_created_does_not_trigger(self):
        listener = _listener()
        event = SimpleNamespace(event_type=EventTypes.entry_created)
        assert listener.get_subscribers(event) == []

    def test_entry_deleted_does_not_trigger(self):
        listener = _listener()
        event = SimpleNamespace(event_type=EventTypes.entry_deleted)
        assert listener.get_subscribers(event) == []


class TestUpdateGate:
    """_should_index_on_update encodes the key judgment call for entry_updated."""

    def test_published_and_already_indexed_reembeds(self):
        # A live, already-indexed entry whose content changed → re-embed.
        assert AIEmbeddingReactionListener._should_index_on_update("published", True) is True

    def test_published_but_not_yet_indexed_is_skipped(self):
        # First-publish transition: entry_published owns the initial index, so the
        # accompanying entry_updated must no-op to avoid a redundant double-embed.
        assert AIEmbeddingReactionListener._should_index_on_update("published", False) is False

    def test_draft_save_is_never_embedded(self):
        assert AIEmbeddingReactionListener._should_index_on_update("draft", True) is False

    def test_inbox_save_is_never_embedded(self):
        assert AIEmbeddingReactionListener._should_index_on_update("inbox", True) is False

    def test_archived_edit_is_never_embedded(self):
        assert AIEmbeddingReactionListener._should_index_on_update("archived", True) is False

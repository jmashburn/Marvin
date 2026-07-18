"""Unit tests for AIOperationsController._resolve_entity_id.

Ops accept a UUID or a slug for entity_id (MCP/CLI callers work in slugs); this resolver
normalizes a UUID and resolves a slug → the entity's id for entry/asset/resource.
"""

import uuid
from unittest.mock import MagicMock

from marvin.routes.ai.operations_controller import AIOperationsController


def _ctrl(row=None):
    fake = MagicMock()
    fake.session.query.return_value.filter_by.return_value.first.return_value = row
    return fake


def test_none_passes_through():
    assert AIOperationsController._resolve_entity_id(_ctrl(), "resource", None) is None


def test_uuid_is_normalized_and_returned():
    u = str(uuid.uuid4())
    result = AIOperationsController._resolve_entity_id(_ctrl(), "resource", u)
    assert str(result) == u
    assert isinstance(result, uuid.UUID)


def test_unknown_entity_type_returns_input_unchanged():
    assert AIOperationsController._resolve_entity_id(_ctrl(), "widget", "some-slug") == "some-slug"


def test_slug_resolves_to_entity_id():
    row = MagicMock()
    row.id = "resolved-id"
    assert AIOperationsController._resolve_entity_id(_ctrl(row), "resource", "merino-wool") == "resolved-id"


def test_unresolvable_slug_returns_input():
    # no matching row → return the input so downstream loaders 404 as before
    assert AIOperationsController._resolve_entity_id(_ctrl(None), "entry", "ghost-slug") == "ghost-slug"

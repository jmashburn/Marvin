"""Unit tests for the AI invocation-source gate.

The effective allow-list for a call is the INTERSECTION of the operation's declared sources
and the workspace's invocation_sources policy (an override map: enabled unless explicitly
false). This exercises `_check_invocation_source` directly with a mocked session.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from marvin.routes.ai.operations_controller import AIOperationsController

ALL = ("editor", "forms", "actions", "mcp", "scheduled", "agent", "api")


def _controller(policy):
    """A stand-in `self` whose settings row returns `policy` for invocation_sources."""
    fake = MagicMock()
    settings = MagicMock()
    settings.invocation_sources = policy
    fake.session.query.return_value.filter_by.return_value.first.return_value = settings
    return fake


def _check(policy, source, op_sources=ALL):
    AIOperationsController._check_invocation_source(_controller(policy), source, op_sources)


def test_unknown_source_is_rejected():
    with pytest.raises(HTTPException) as exc:
        _check(None, "telepathy")
    assert exc.value.status_code == 400


def test_operation_not_supporting_source_is_forbidden():
    # op supports only editor; caller claims mcp
    with pytest.raises(HTTPException) as exc:
        _check(None, "mcp", op_sources=("editor",))
    assert exc.value.status_code == 403


def test_workspace_policy_disabling_source_is_forbidden():
    with pytest.raises(HTTPException) as exc:
        _check({"mcp": False}, "mcp")
    assert exc.value.status_code == 403


def test_no_policy_allows_everything():
    # None policy → back-compat: all sources allowed
    _check(None, "mcp")  # should not raise


def test_policy_missing_key_defaults_to_allowed():
    # override map: a source absent from the policy is enabled
    _check({"forms": False}, "mcp")  # mcp not in policy → allowed


def test_policy_explicitly_enabled_is_allowed():
    _check({"mcp": True}, "mcp")


def test_intersection_requires_both():
    # workspace allows mcp, but the operation does not declare it → forbidden
    with pytest.raises(HTTPException) as exc:
        _check({"mcp": True}, "mcp", op_sources=("editor", "api"))
    assert exc.value.status_code == 403


def test_source_catalog_matches_invocation_sources():
    # Drift guard: the policy-editor catalog must cover exactly the real sources, so a new source
    # can't ship without a UI toggle (and the UI can't show a source the gate never checks).
    from marvin.services.ai.operations.base import INVOCATION_SOURCE_CATALOG, INVOCATION_SOURCES

    catalog_keys = [s["key"] for s in INVOCATION_SOURCE_CATALOG]
    assert catalog_keys == list(INVOCATION_SOURCES)  # same set AND order
    assert all(s.get("label") and s.get("description") for s in INVOCATION_SOURCE_CATALOG)

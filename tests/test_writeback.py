"""Unit tests for the AI write-back decision (apply vs stage) by approval_mode × status."""

from unittest.mock import MagicMock

from marvin.routes.ai.operations_controller import AIOperationsController


def _operation(writeback):
    op = MagicMock()
    op.writeback = writeback
    op.slug = "generate-summary"
    return op


def _call(status, mode, writeback=None, output=None, entity_type="entry"):
    if writeback is None:
        writeback = {"summary": "summary"}
    if output is None:
        output = {"summary": "new summary"}
    ctrl = MagicMock()
    ctrl.group_id = "g1"
    entry = MagicMock()
    entry.status = status
    entry.group_id = "g1"
    entry.id = "e1"
    entry.title = "T"
    ctrl.session.get.return_value = entry
    ctrl._approval_mode.return_value = mode
    return AIOperationsController._write_back(ctrl, _operation(writeback), entity_type, "e1", output, "exec1")


def test_non_entry_returns_none():
    assert _call("inbox", "allow-automatic-update", entity_type="resource") is None


def test_empty_writeback_returns_none():
    assert _call("inbox", "allow-automatic-update", writeback={}) is None


def test_suggest_only_stages():
    assert _call("inbox", "suggest-only") == "staged"


def test_draft_update_applies_on_draft():
    assert _call("inbox", "allow-draft-update") == "applied"
    assert _call("draft", "allow-draft-update") == "applied"


def test_draft_update_stages_on_published():
    assert _call("published", "allow-draft-update") == "staged"
    assert _call("archived", "allow-draft-update") == "staged"


def test_automatic_applies_even_on_published():
    assert _call("published", "allow-automatic-update") == "applied"

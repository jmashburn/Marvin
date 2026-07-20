"""Unit tests for operation prompt construction (no provider, no DB)."""

from marvin.services.ai.operations.base import OperationContext, get_operation

BLOB = "{'body': 'raw data_json blob'}"


def _ctx(content=BLOB):
    return OperationContext(entry={"content": content, "title": "T"}, workspace_name="W", site_locale="en")


def _user_msg(slug, input_, ctx=None):
    return get_operation(slug).build_prompt(input_, ctx or _ctx())[-1].content


# ── improve-writing: field-scoped input ───────────────────────────────────────
# ContextBuilder sets entry["content"] to str(data_json) — a structured blob, not prose. The
# caller must be able to pass the actual text, or the operation improves a dict repr and the
# result has no field to go back into.

def test_improve_writing_uses_caller_supplied_text():
    body = _user_msg("improve-writing", {"text": "Some real prose."})
    assert "Some real prose." in body
    assert "raw data_json blob" not in body


def test_improve_writing_falls_back_to_entry_content():
    # Legacy API/MCP callers that send no text must keep working.
    assert "raw data_json blob" in _user_msg("improve-writing", {})


def test_improve_writing_treats_blank_text_as_absent():
    assert "raw data_json blob" in _user_msg("improve-writing", {"text": "   "})


def test_improve_writing_tone_override_reaches_the_prompt():
    msgs = get_operation("improve-writing").build_prompt({"text": "x", "tone": "wry"}, _ctx())
    assert "wry" in msgs[0].content


def test_improve_writing_declares_text_and_field_inputs():
    props = get_operation("improve-writing").input_schema["properties"]
    assert "text" in props and "field" in props


def test_improve_writing_still_stages_nothing():
    # Suggestion-only by design: the UI fills the field for review, so no writeback map.
    assert not getattr(get_operation("improve-writing"), "writeback", {})


# ── generate-tags: staging target ─────────────────────────────────────────────

def test_generate_tags_writes_back_to_metadata_tags():
    assert get_operation("generate-tags").writeback == {"tags": "metadata_json.tags"}


def test_generate_tags_passes_existing_tags_into_the_prompt():
    body = _user_msg("generate-tags", {"existing_tags": ["denim", "workwear"]})
    assert "denim" in body and "workwear" in body

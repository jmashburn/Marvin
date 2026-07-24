"""Unit tests for the agent tool-dispatch loop (run_agent_loop).

Drives the loop with a scripted fake provider — no DB, no network. Covers: tool dispatch +
result feedback, token accounting, unknown-tool and tool-error handling, and the max-steps
force-final path.
"""

import json

from marvin.services.ai.agent import AgentTool, run_agent_loop
from marvin.services.ai.base import AIProvider, CompletionResult, Message, ToolCall


class ScriptedProvider(AIProvider):
    """Returns a pre-scripted CompletionResult per complete_with_tools call; records each call."""

    provider_type = "fake"
    display_name = "Fake"
    supports_tool_calls = True

    def __init__(self, results):
        self._results = list(results)
        self.calls = []  # list of (messages, tool_choice)

    def complete_with_tools(self, messages, model, tools, options=None, tool_choice="auto"):
        self.calls.append((list(messages), tool_choice))
        return self._results.pop(0)

    # unused abstract surface
    def complete(self, messages, model, options=None):  # pragma: no cover
        raise NotImplementedError

    def complete_structured(self, messages, model, output_schema, options=None):  # pragma: no cover
        raise NotImplementedError

    def list_models(self):  # pragma: no cover
        return []

    def test_connection(self):  # pragma: no cover
        return True, ""


def _result(content="", tool_calls=None, pt=5, ct=3):
    return CompletionResult(
        content=content,
        prompt_tokens=pt,
        completion_tokens=ct,
        total_tokens=pt + ct,
        model="m",
        tool_calls=tool_calls or [],
    )


def test_agent_runs_tool_then_answers():
    provider = ScriptedProvider(
        [
            _result(tool_calls=[ToolCall(id="c1", name="echo", arguments={"x": 1})]),
            _result(content="done"),
        ]
    )
    seen = []
    tool = AgentTool(
        name="echo",
        description="echo",
        input_schema={},
        run=lambda a: seen.append(a) or json.dumps({"echo": a}),
    )

    result = run_agent_loop(provider, "m", [Message(role="user", content="hi")], [tool])

    assert result.answer == "done"
    assert result.stopped_reason == "complete"
    assert seen == [{"x": 1}]
    assert len(result.steps) == 1 and result.steps[0].tool == "echo"
    assert result.total_tokens == 16  # two model calls × 8
    # the second model call saw the assistant tool-call turn + the tool result
    second_convo = provider.calls[1][0]
    assert any(m.role == "assistant" and m.tool_calls for m in second_convo)
    assert any(m.role == "tool" and m.tool_call_id == "c1" for m in second_convo)


def test_agent_unknown_tool_is_reported_not_fatal():
    provider = ScriptedProvider(
        [
            _result(tool_calls=[ToolCall(id="c1", name="missing", arguments={})]),
            _result(content="ok"),
        ]
    )
    result = run_agent_loop(provider, "m", [Message(role="user", content="hi")], [])
    assert result.answer == "ok"
    assert "unknown tool" in result.steps[0].result


def test_agent_tool_exception_is_captured():
    def boom(_a):
        raise ValueError("nope")

    provider = ScriptedProvider(
        [
            _result(tool_calls=[ToolCall(id="c1", name="boom", arguments={})]),
            _result(content="handled"),
        ]
    )
    tool = AgentTool(name="boom", description="", input_schema={}, run=boom)
    result = run_agent_loop(provider, "m", [Message(role="user", content="hi")], [tool])
    assert "nope" in result.steps[0].result
    assert result.answer == "handled"


def test_agent_max_steps_forces_final_answer():
    always_call = _result(tool_calls=[ToolCall(id="c", name="echo", arguments={})])
    provider = ScriptedProvider([always_call, always_call, _result(content="forced final")])
    tool = AgentTool(name="echo", description="", input_schema={}, run=lambda _a: "{}")

    result = run_agent_loop(provider, "m", [Message(role="user", content="hi")], [tool], max_steps=2)

    assert result.stopped_reason == "max_steps"
    assert result.answer == "forced final"
    assert len(result.steps) == 2  # two tool dispatches within budget
    assert provider.calls[-1][1] == "none"  # final answer requested with tools disabled

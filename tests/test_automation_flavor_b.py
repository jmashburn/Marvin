"""Unit tests for Flavor B — user-configurable orchestration (event → conditions → actions).

Covers the three pure/near-pure pieces of the engine:
 - the matcher (condition ops + $event/$previous interpolation),
 - the AutomationReactionListener trigger gate (incl. the loop-guard),
 - the engine's orchestration (trigger match, conditions, pipeline threading, skips) with a fake
   session + injected action runner, so no AI provider or real DB rows are needed.

The migration + model registration are exercised implicitly: conftest builds the whole schema by
running Alembic to head, so a broken workspace_automations migration would fail collection.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from marvin.services.automation import engine, matcher
from marvin.services.automation.runner import AutomationActionError
from marvin.services.event_bus_service.event_bus_listener import AutomationReactionListener
from marvin.services.event_bus_service.event_types import EventTypes


# ── Matcher: interpolation ────────────────────────────────────────────────────
class TestInterpolate:
    def test_whole_string_event_template_resolves_raw_value(self):
        ctx = {"event": {"entry_id": "abc"}, "previous": {}}
        assert matcher.interpolate("$event.entry_id", ctx) == "abc"

    def test_previous_template_resolves(self):
        ctx = {"event": {}, "previous": {"summary": "a tidy summary"}}
        assert matcher.interpolate("$previous.summary", ctx) == "a tidy summary"

    def test_non_template_string_passes_through(self):
        assert matcher.interpolate("literal", {"event": {}}) == "literal"

    def test_unknown_reference_is_none(self):
        assert matcher.interpolate("$event.missing", {"event": {}}) is None

    def test_nested_dict_and_list_are_recursed(self):
        ctx = {"event": {"entry_id": "e1"}, "previous": {"tags": ["x"]}}
        out = matcher.interpolate({"id": "$event.entry_id", "keep": [1, "$previous.tags"]}, ctx)
        assert out == {"id": "e1", "keep": [1, ["x"]]}


# ── Matcher: conditions ───────────────────────────────────────────────────────
class TestMatches:
    def _ctx(self, entry_type="recipe", status="published"):
        return {"event": {"event_type": "entry_published"},
                "entry": {"entry_type": entry_type, "status": status}, "previous": {}}

    def test_no_conditions_always_match(self):
        assert matcher.matches(None, self._ctx()) is True
        assert matcher.matches([], self._ctx()) is True

    def test_eq_matches_and_misses(self):
        conds = [{"field": "entry.entry_type", "op": "eq", "value": "recipe"}]
        assert matcher.matches(conds, self._ctx(entry_type="recipe")) is True
        assert matcher.matches(conds, self._ctx(entry_type="article")) is False

    def test_neq(self):
        conds = [{"field": "entry.status", "op": "neq", "value": "draft"}]
        assert matcher.matches(conds, self._ctx(status="published")) is True
        assert matcher.matches(conds, self._ctx(status="draft")) is False

    def test_contains(self):
        ctx = {"entry": {"title": "Waxed Canvas Care"}}
        assert matcher.matches([{"field": "entry.title", "op": "contains", "value": "Canvas"}], ctx) is True
        assert matcher.matches([{"field": "entry.title", "op": "contains", "value": "Leather"}], ctx) is False

    def test_exists(self):
        ctx = {"entry": {"entry_type": "recipe"}}
        assert matcher.matches([{"field": "entry.entry_type", "op": "exists"}], ctx) is True
        assert matcher.matches([{"field": "entry.missing", "op": "exists"}], ctx) is False
        # `value: false` inverts to must-not-exist
        assert matcher.matches([{"field": "entry.missing", "op": "exists", "value": False}], ctx) is True

    def test_all_conditions_are_anded(self):
        conds = [
            {"field": "entry.entry_type", "op": "eq", "value": "recipe"},
            {"field": "entry.status", "op": "eq", "value": "published"},
        ]
        assert matcher.matches(conds, self._ctx("recipe", "published")) is True
        assert matcher.matches(conds, self._ctx("recipe", "draft")) is False

    def test_unknown_operator_fails_closed(self):
        assert matcher.matches([{"field": "entry.entry_type", "op": "regex", "value": ".*"}], self._ctx()) is False


# ── Listener: trigger gate + loop-guard ───────────────────────────────────────
class TestListenerGate:
    def _listener(self):
        return AutomationReactionListener(group_id=uuid4())

    def test_entry_lifecycle_events_trigger(self):
        for et in (EventTypes.entry_created, EventTypes.entry_updated,
                   EventTypes.entry_published, EventTypes.entry_deleted):
            event = SimpleNamespace(event_type=et, reaction_depth=0)
            assert self._listener().get_subscribers(event) == ["automation"]

    def test_non_lifecycle_events_do_not_trigger(self):
        for et in (EventTypes.webhook_triggered, EventTypes.scheduled_task_created):
            event = SimpleNamespace(event_type=et, reaction_depth=0)
            assert self._listener().get_subscribers(event) == []

    def test_loop_guard_stops_deep_chains(self):
        # An automation's emit_event/write-back re-dispatches at reaction_depth+1; once a chain is
        # deep enough the listener refuses to react, so chains stay finite.
        from marvin.services.automation.engine import MAX_REACTION_DEPTH

        deep = SimpleNamespace(event_type=EventTypes.entry_published, reaction_depth=MAX_REACTION_DEPTH)
        assert self._listener().get_subscribers(deep) == []
        shallow = SimpleNamespace(event_type=EventTypes.entry_published, reaction_depth=0)
        assert self._listener().get_subscribers(shallow) == ["automation"]


# ── Engine: orchestration with a fake session + injected runner ───────────────
class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter_by(self, **kw):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    """Minimal stand-in: query() returns the automations; get() returns the entry."""

    def __init__(self, automations, entry=None):
        self._automations = automations
        self._entry = entry

    def query(self, _model):
        return _FakeQuery(self._automations)

    def get(self, _model, _id):
        return self._entry


def _automation(slug="auto", trigger="entry_published", conditions=None, actions=None):
    return SimpleNamespace(
        slug=slug,
        enabled=True,
        group_id=uuid4(),
        definition={"trigger": {"event": trigger}, "conditions": conditions or [], "actions": actions or []},
    )


def _entry(entry_type="recipe", status="published"):
    return SimpleNamespace(id=uuid4(), group_id="G", status=status, title="T", slug="t",
                           entry_type=SimpleNamespace(slug=entry_type))


def _recording_runner():
    calls = []

    def run(session, group_id, action, context, *, user_id=None):
        calls.append({"action": action, "previous": dict(context.get("previous", {}))})
        return {"summary": "generated"}

    run.calls = calls
    return run


class TestEngine:
    def _run(self, session, event_type="entry_published", run_action=None):
        gid = "G"
        # _entry_context checks entry.group_id == group_id; align the fake entry's group.
        if session._entry is not None:
            session._entry.group_id = gid
        ctx = {"event_type": event_type, "entry_id": uuid4(), "user_id": None}
        return engine.run_automations_for_event(session, gid, ctx, run_action=run_action)

    def test_matching_automation_runs_its_action(self):
        auto = _automation(actions=[{"kind": "operation", "op": "generate-summary", "write_back": True}])
        runner = _recording_runner()
        ran = self._run(_FakeSession([auto], entry=_entry("recipe")), run_action=runner)
        assert ran == 1
        assert len(runner.calls) == 1
        assert runner.calls[0]["action"]["op"] == "generate-summary"

    def test_trigger_mismatch_skips(self):
        auto = _automation(trigger="entry_published",
                           actions=[{"kind": "operation", "op": "generate-summary"}])
        runner = _recording_runner()
        ran = self._run(_FakeSession([auto], entry=_entry()), event_type="entry_updated", run_action=runner)
        assert ran == 0
        assert runner.calls == []

    def test_condition_gates_the_automation(self):
        auto = _automation(
            conditions=[{"field": "entry.entry_type", "op": "eq", "value": "recipe"}],
            actions=[{"kind": "operation", "op": "generate-summary"}],
        )
        runner = _recording_runner()
        # entry is an article → condition fails → no run
        ran = self._run(_FakeSession([auto], entry=_entry(entry_type="article")), run_action=runner)
        assert ran == 0
        assert runner.calls == []

    def test_pipeline_threads_previous_between_steps(self):
        auto = _automation(actions=[
            {"kind": "operation", "op": "generate-summary"},
            {"kind": "operation", "op": "generate-tags", "input": {"hint": "$previous.summary"}},
        ])
        runner = _recording_runner()
        self._run(_FakeSession([auto], entry=_entry()), run_action=runner)
        # First step sees empty previous; second sees the first step's output.
        assert runner.calls[0]["previous"] == {}
        assert runner.calls[1]["previous"] == {"summary": "generated"}

    def test_all_actions_dispatch_in_order(self):
        # The engine no longer filters by kind — every action is handed to the dispatcher in order;
        # routing by kind is the registry's job.
        auto = _automation(actions=[{"kind": "webhook", "url": "x"},
                                    {"kind": "operation", "op": "generate-summary"}])
        runner = _recording_runner()
        ran = self._run(_FakeSession([auto], entry=_entry()), run_action=runner)
        assert ran == 1
        assert [c["action"].get("kind") for c in runner.calls] == ["webhook", "operation"]

    def test_action_error_stops_the_pipeline(self):
        auto = _automation(actions=[
            {"kind": "operation", "op": "boom"},
            {"kind": "operation", "op": "never-runs"},
        ])
        calls = []

        def failing(session, group_id, action, context, *, user_id=None):
            calls.append(action["op"])
            raise AutomationActionError("nope")

        ran = self._run(_FakeSession([auto], entry=_entry()), run_action=failing)
        assert ran == 1          # the automation was matched + attempted
        assert calls == ["boom"]  # pipeline broke after the failing step


# ── Action-executor registry ──────────────────────────────────────────────────
class TestActionRegistry:
    def test_all_four_kinds_registered(self):
        from marvin.services.automation.actions import available_kinds

        assert set(available_kinds()) == {"operation", "emit_event", "handler", "webhook"}

    def test_unknown_kind_raises(self):
        from marvin.services.automation.actions import run_action

        with pytest.raises(AutomationActionError):
            run_action(None, "G", {"kind": "does-not-exist"}, {"previous": {}})


# ── Trigger matching: event / chained / on-error (T3) ─────────────────────────
class TestTriggerMatching:
    def _m(self, trig, ev):
        from marvin.services.automation.engine import _trigger_matches
        return _trigger_matches(trig, ev)

    def test_event_trigger(self):
        assert self._m({"type": "event", "event": "entry_published"}, {"event_type": "entry_published"})
        assert not self._m({"type": "event", "event": "entry_published"}, {"event_type": "entry_updated"})

    def test_chained_any_and_targeted(self):
        ev = {"event_type": "automation_ran", "automation_slug": "src", "automation_id": "id1"}
        assert self._m({"type": "chained"}, ev)                        # any
        assert self._m({"type": "chained", "automation": "any"}, ev)   # explicit any
        assert self._m({"type": "chained", "automation": "src"}, ev)   # by slug
        assert self._m({"type": "chained", "automation": "id1"}, ev)   # by id
        assert not self._m({"type": "chained", "automation": "other"}, ev)
        assert not self._m({"type": "chained"}, {"event_type": "automation_failed"})  # wrong lifecycle event

    def test_on_error(self):
        assert self._m({"type": "on_error"}, {"event_type": "automation_failed"})
        assert not self._m({"type": "on_error"}, {"event_type": "automation_ran"})

    def test_manual_and_schedule_never_fire_on_events(self):
        assert not self._m({"type": "manual"}, {"event_type": "entry_published"})
        assert not self._m({"type": "schedule"}, {"event_type": "automation_ran"})

    def test_listener_subscribes_to_automation_lifecycle_events(self):
        from marvin.services.event_bus_service.event_types import EventTypes
        listener = AutomationReactionListener(group_id=uuid4())
        for et in (EventTypes.automation_ran, EventTypes.automation_failed):
            ev = SimpleNamespace(event_type=et, reaction_depth=0)
            assert listener.get_subscribers(ev) == ["automation"]

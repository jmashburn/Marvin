"""Condition matching + value interpolation for Flavor B automations.

Pure functions over a plain `context` dict (no DB, no I/O) so they are cheap and fully unit-testable.
The context the engine passes looks like::

    {
      "event":    {"event_type": "entry_published", "entry_id": "...", "entry_type": "recipe", ...},
      "previous": {"summary": "...", ...},   # output of the last action, if any
    }

Conditions reference fields by dotted path (e.g. ``"event.entry_type"``); action inputs may embed
``"$event.entry_id"`` / ``"$previous.summary"`` templates, resolved by :func:`interpolate`.
"""

from typing import Any

# Supported condition operators. Kept deliberately small for v1.
_OPS = ("eq", "neq", "contains", "exists")


def resolve_path(path: str, context: dict) -> Any:
    """Resolve a dotted path (``"event.entry_type"``) against the context; None if any hop misses."""
    cur: Any = context
    for part in str(path).split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def interpolate(value: Any, context: dict) -> Any:
    """Resolve ``$event.*`` / ``$previous.*`` templates in a value (recursing dicts/lists).

    A whole-string template (``"$event.entry_id"``) resolves to the raw referenced value (preserving
    type). Non-template values pass through unchanged. Unknown references resolve to None.
    """
    if isinstance(value, str):
        if value.startswith("$"):
            return resolve_path(value[1:], context)
        return value
    if isinstance(value, dict):
        return {k: interpolate(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [interpolate(v, context) for v in value]
    return value


def _match_one(cond: dict, context: dict) -> bool:
    field = cond.get("field")
    op = cond.get("op", "eq")
    expected = interpolate(cond.get("value"), context)
    actual = resolve_path(field, context) if field else None

    if op == "exists":
        # `value: false` inverts to "must not exist".
        want = expected if isinstance(expected, bool) else True
        return (actual is not None) == want
    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    if op == "contains":
        try:
            return expected in actual  # substring or membership
        except TypeError:
            return False
    # Unknown operator → fail closed (never silently "match everything").
    return False


def matches(conditions: list | None, context: dict) -> bool:
    """True if EVERY condition holds (AND). No conditions → always matches."""
    if not conditions:
        return True
    return all(_match_one(c, context) for c in conditions if isinstance(c, dict))

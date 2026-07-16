"""Variable substitution for webhook custom_payload fields.

Delegates to the shared resolver so {{var}} tokens in custom_payload benefit
from the same resolution order as webhook headers:
  1. per-fire context (timestamp, workspace_slug, trigger, workspace_name)
  2. workspace Secrets (UPPER_CASE)
  3. workspace Variables (UPPER_CASE)
"""

from typing import Any

from pydantic import UUID4


def apply_substitutions(payload: Any, group_id: UUID4 | None, context: dict) -> Any:
    """Recursively resolve {{var}} tokens in all string values of payload."""
    from marvin.services.secrets.resolver import resolve

    if isinstance(payload, str):
        return resolve(payload, group_id=group_id, context=context)
    if isinstance(payload, dict):
        return {k: apply_substitutions(v, group_id, context) for k, v in payload.items()}
    if isinstance(payload, list):
        return [apply_substitutions(item, group_id, context) for item in payload]
    return payload

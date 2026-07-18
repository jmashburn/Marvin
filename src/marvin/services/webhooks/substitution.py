"""Variable substitution for webhook custom_payload fields.

Delegates to the shared resolver so {{var}} tokens in custom_payload benefit
from:
  1. per-fire context variables (timestamp, workspace_slug, trigger, workspace_name)
  2. workspace Variables (UPPER_CASE, plain-text)

Secrets are intentionally excluded (allow_secrets=False) — custom_payload
values appear in POST bodies that third-party endpoints receive, so secrets
must not leak through them.
"""

from typing import Any

from pydantic import UUID4


def apply_substitutions(payload: Any, group_id: UUID4 | None, context: dict) -> Any:
    """Recursively resolve {{var}} tokens in all string values of payload.

    Secrets are excluded; only per-fire context and workspace Variables resolve.
    """
    from marvin.services.secrets.resolver import resolve

    if isinstance(payload, str):
        return resolve(payload, group_id=group_id, allow_secrets=False, context=context)
    if isinstance(payload, dict):
        return {k: apply_substitutions(v, group_id, context) for k, v in payload.items()}
    if isinstance(payload, list):
        return [apply_substitutions(item, group_id, context) for item in payload]
    return payload

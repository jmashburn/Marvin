"""Generic webhook handler — sends custom_payload with variable substitution."""

from typing import Any

from .base_webhook import BaseWebhook
from .substitution import apply_substitutions


class GenericWebhook(BaseWebhook):
    def info(self, webhook_config: Any, context: dict) -> dict:
        return apply_substitutions(webhook_config.custom_payload or {}, self._group_id, context)

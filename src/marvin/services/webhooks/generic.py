"""Generic webhook handler — no built-in stats; payload comes entirely from custom_payload."""

from typing import Any

from .base_webhook import BaseWebhook


class GenericWebhook(BaseWebhook):
    def info(self, webhook_config: Any, context: dict) -> dict:
        return {}

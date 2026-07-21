"""Vercel Deploy Hook — a destination integration that rebuilds a site on demand.

A Vercel Deploy Hook is a URL you POST to; the URL embeds a token, so the URL *is* the
credential. Wire it to "on entry published → trigger_deploy" to rebuild the real site
whenever content changes — the honest, headless version of "custom domains".
"""

import json
import urllib.error
import urllib.request

from ..base import (
    CATEGORY_DESTINATION,
    CredentialField,
    IntegrationContext,
    IntegrationProvider,
    ProviderAction,
    register_provider,
)

_TIMEOUT = 15


@register_provider
class VercelDeployProvider(IntegrationProvider):
    slug = "vercel_deploy"
    name = "Vercel Deploy Hook"
    description = "Trigger a Vercel deployment (site rebuild) by POSTing a deploy hook."
    category = CATEGORY_DESTINATION

    credentials = (
        CredentialField(
            key="hook_url",
            label="Deploy Hook URL",
            help="Vercel → Project → Settings → Git → Deploy Hooks. The URL embeds a token, so it is stored as a secret.",
        ),
    )
    actions = (
        ProviderAction(
            key="trigger_deploy",
            label="Trigger deploy",
            description="POST the deploy hook to start a new build.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
    )

    def check(self, ctx: IntegrationContext) -> tuple[str, str | None]:
        if not ctx.secret:
            return ("unconfigured", "Missing deploy hook URL.")
        if not ctx.secret.startswith("https://"):
            return ("error", "Deploy hook URL must be https://.")
        return ("ok", None)

    def run_action(self, key: str, args: dict, ctx: IntegrationContext) -> dict:
        if key != "trigger_deploy":
            raise NotImplementedError(f"vercel_deploy has no action '{key}'")
        if not ctx.secret:
            raise ValueError("No deploy hook URL configured.")

        req = urllib.request.Request(ctx.secret, data=b"", method="POST")
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                body = resp.read().decode("utf-8", "replace")
                try:
                    parsed = json.loads(body)
                except ValueError:
                    parsed = {"raw": body[:500]}
                return {"status_code": resp.status, "response": parsed}
        except urllib.error.HTTPError as e:
            ctx.logger.warning(f"[vercel_deploy] hook returned {e.code}")
            raise ValueError(f"Deploy hook returned HTTP {e.code}") from e
        except urllib.error.URLError as e:
            ctx.logger.warning(f"[vercel_deploy] hook unreachable: {e.reason}")
            raise ValueError(f"Deploy hook unreachable: {e.reason}") from e

"""Vercel Deploy Hook — a destination integration that rebuilds a site on demand.

A Vercel Deploy Hook is a URL you POST to; the URL embeds a token, so the URL *is* the credential.
Wire it to "on entry published → trigger_deploy" to rebuild the live site whenever content changes —
the honest, headless version of "custom domains".
"""

from marvin_integration_sdk import (
    CATEGORY_DESTINATION,
    CredentialField,
    IntegrationContext,
    IntegrationProvider,
    ProviderAction,
    register_provider,
)


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

        try:
            resp = ctx.http.post(ctx.secret, data=b"")
        except Exception as e:  # noqa: BLE001 — surface any transport/guard failure as a clean error
            ctx.logger.warning(f"[vercel_deploy] hook unreachable: {e}")
            raise ValueError(f"Deploy hook unreachable: {e}") from e

        if not resp.ok:
            ctx.logger.warning(f"[vercel_deploy] hook returned {resp.status_code}")
            raise ValueError(f"Deploy hook returned HTTP {resp.status_code}")

        try:
            parsed = resp.json()
        except ValueError:
            parsed = {"raw": resp.text[:500]}
        return {"status_code": resp.status_code, "response": parsed}

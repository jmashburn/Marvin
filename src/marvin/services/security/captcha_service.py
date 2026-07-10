"""CAPTCHA verification service."""

import httpx


class CaptchaService:
    """Service for verifying CAPTCHA tokens."""

    HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"
    TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    def __init__(self, secret_key: str | None = None) -> None:
        self.secret_key = secret_key

    async def verify(self, token: str | None, provider: str = "hcaptcha", secret_key: str | None = None) -> bool:
        """Verify CAPTCHA token with provider.

        Args:
            token: CAPTCHA response token from frontend
            provider: CAPTCHA provider (hcaptcha | turnstile)
            secret_key: Provider secret key (overrides instance secret_key)

        Returns:
            True if verification succeeds, False otherwise
        """
        if not token:
            return False

        key = secret_key or self.secret_key
        if not key:
            return False  # No secret key configured

        # Select verification URL
        verify_url = self.HCAPTCHA_VERIFY_URL if provider == "hcaptcha" else self.TURNSTILE_VERIFY_URL

        # Verify with provider
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    verify_url,
                    data={
                        "secret": key,
                        "response": token,
                    },
                    timeout=10.0,
                )

                if response.status_code != 200:
                    return False

                result = response.json()
                return result.get("success", False)

        except Exception:
            # Network error or timeout - fail open? Or fail closed?
            # Fail closed for security: if CAPTCHA verification fails, reject submission
            return False

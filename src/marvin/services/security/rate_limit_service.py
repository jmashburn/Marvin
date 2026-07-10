"""Rate limiting service for form submissions."""

from datetime import datetime, timedelta, timezone

from pydantic import UUID4
from sqlalchemy.orm import Session

from marvin.db.models.platform.form_rate_limits import FormRateLimits


class RateLimitService:
    """Service for enforcing form submission rate limits."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def check_limit(self, form_id: UUID4, identifier: str, settings: dict | None) -> bool:
        """Check if submission is within rate limit.

        Args:
            form_id: Form UUID
            identifier: IP address or API client ID
            settings: Form settings_json containing rate limit config

        Returns:
            True if submission is allowed, False if rate limit exceeded
        """
        # Get rate limit settings
        if not settings or not settings.get("security", {}).get("rateLimit", {}).get("enabled", True):
            return True  # Rate limiting disabled

        rate_config = settings.get("security", {}).get("rateLimit", {})
        max_submissions = rate_config.get("maxSubmissions", 10)
        window_minutes = rate_config.get("windowMinutes", 60)

        # Calculate window start
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=window_minutes)

        # Get or create rate limit record
        rate_limit = (
            self.session.query(FormRateLimits)
            .filter(
                FormRateLimits.form_id == form_id,
                FormRateLimits.identifier == identifier,
                FormRateLimits.window_start >= window_start,
            )
            .first()
        )

        if not rate_limit:
            # First submission in this window
            rate_limit = FormRateLimits(
                session=self.session,
                form_id=form_id,
                identifier=identifier,
                window_start=now,
                submission_count=1,
            )
            self.session.add(rate_limit)
            self.session.commit()
            return True

        # Check if limit exceeded
        if rate_limit.submission_count >= max_submissions:
            return False

        # Increment count
        rate_limit.submission_count += 1
        self.session.commit()
        return True

    def cleanup_old_records(self, days: int = 7) -> None:
        """Clean up rate limit records older than N days.

        Args:
            days: Number of days to keep records
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        self.session.query(FormRateLimits).filter(FormRateLimits.window_start < cutoff).delete()
        self.session.commit()

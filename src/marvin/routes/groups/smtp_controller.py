"""Workspace SMTP Profiles API.

CRUD for named, workspace-scoped SMTP server configurations. A workspace may have
several profiles; at most one is active. Passwords are Fernet-encrypted at rest and
never returned. A per-profile test endpoint sends a live message through the profile.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4
from sqlalchemy import select

from marvin.db.models.groups.smtp_profiles import WorkspaceSMTPProfileModel
from marvin.routes._base import BaseUserController, controller
from marvin.schemas.group.smtp_profile import (
    SMTPProfileCreate,
    SMTPProfileRead,
    SMTPProfileTestRequest,
    SMTPProfileTestResult,
    SMTPProfileUpdate,
)
from marvin.services.email.email_senders import EmailOptions, Message

router = APIRouter(prefix="/groups/smtp-profiles")


def _encrypt(value: str) -> str:
    """Fernet-encrypt a password for at-rest storage in the profile row."""
    from marvin.services.secrets.backends.database import _get_fernet

    return _get_fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str | None:
    """Reverse of `_encrypt`; returns None if the ciphertext can't be read."""
    from marvin.services.secrets.backends.database import _get_fernet

    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except Exception:
        return None


def _to_read(profile: WorkspaceSMTPProfileModel) -> SMTPProfileRead:
    """Serialize a profile, exposing only whether a password is stored."""
    return SMTPProfileRead(
        id=profile.id,
        group_id=profile.group_id,
        name=profile.name,
        host=profile.host,
        port=profile.port,
        username=profile.username,
        from_name=profile.from_name,
        from_email=profile.from_email,
        auth_strategy=profile.auth_strategy,
        is_active=profile.is_active,
        has_password=bool(profile.password_encrypted),
        created_at=getattr(profile, "created_at", None),
        updated_at=getattr(profile, "updated_at", None),
    )


@controller(router)
class SMTPProfilesController(BaseUserController):
    """Workspace SMTP profile management."""

    def _get_or_404(self, profile_id: UUID4) -> WorkspaceSMTPProfileModel:
        profile = self.session.get(WorkspaceSMTPProfileModel, profile_id)
        if not profile or profile.group_id != self.group_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP profile not found.")
        return profile

    def _deactivate_others(self, keep_id: UUID4 | None) -> None:
        """Ensure at most one active profile — clear is_active on every other row."""
        rows = self.session.execute(
            select(WorkspaceSMTPProfileModel).where(
                WorkspaceSMTPProfileModel.group_id == self.group_id,
                WorkspaceSMTPProfileModel.is_active.is_(True),
            )
        ).scalars().all()
        for row in rows:
            if row.id != keep_id:
                row.is_active = False

    @router.get("", response_model=list[SMTPProfileRead], summary="List Workspace SMTP Profiles")
    def list_profiles(self) -> list[SMTPProfileRead]:
        rows = self.session.execute(
            select(WorkspaceSMTPProfileModel)
            .where(WorkspaceSMTPProfileModel.group_id == self.group_id)
            .order_by(WorkspaceSMTPProfileModel.name)
        ).scalars().all()
        return [_to_read(r) for r in rows]

    @router.post("", response_model=SMTPProfileRead, status_code=status.HTTP_201_CREATED, summary="Create SMTP Profile")
    def create_profile(self, data: SMTPProfileCreate) -> SMTPProfileRead:
        profile = WorkspaceSMTPProfileModel(
            session=self.session,
            group_id=self.group_id,
            name=data.name,
            host=data.host,
            port=data.port,
            username=data.username or None,
            password_encrypted=_encrypt(data.password) if data.password else None,
            from_name=data.from_name or None,
            from_email=data.from_email or None,
            auth_strategy=data.auth_strategy,
            is_active=data.is_active,
        )
        self.session.add(profile)
        self.session.flush()
        if data.is_active:
            self._deactivate_others(keep_id=profile.id)
        self.session.commit()
        self.session.refresh(profile)
        return _to_read(profile)

    @router.get("/{profile_id}", response_model=SMTPProfileRead, summary="Get an SMTP Profile")
    def get_profile(self, profile_id: UUID4) -> SMTPProfileRead:
        return _to_read(self._get_or_404(profile_id))

    @router.patch("/{profile_id}", response_model=SMTPProfileRead, summary="Update an SMTP Profile")
    def update_profile(self, profile_id: UUID4, data: SMTPProfileUpdate) -> SMTPProfileRead:
        profile = self._get_or_404(profile_id)

        for field in ("name", "host", "port", "username", "from_name", "from_email", "auth_strategy"):
            value = getattr(data, field)
            if value is not None:
                setattr(profile, field, value)

        # A non-empty password replaces the stored one; an explicit empty string clears it.
        if data.password is not None:
            profile.password_encrypted = _encrypt(data.password) if data.password else None

        if data.is_active is not None:
            profile.is_active = data.is_active
            if data.is_active:
                self._deactivate_others(keep_id=profile.id)

        self.session.commit()
        self.session.refresh(profile)
        return _to_read(profile)

    @router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an SMTP Profile")
    def delete_profile(self, profile_id: UUID4) -> None:
        profile = self._get_or_404(profile_id)
        self.session.delete(profile)
        self.session.commit()

    @router.post("/{profile_id}/test", response_model=SMTPProfileTestResult, summary="Send a test email via this profile")
    def test_profile(self, profile_id: UUID4, data: SMTPProfileTestRequest) -> SMTPProfileTestResult:
        profile = self._get_or_404(profile_id)

        from_email = profile.from_email or self.settings.SMTP_FROM_EMAIL
        from_name = profile.from_name or self.settings.SMTP_FROM_NAME or "Marvin"
        if not from_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This profile has no From address and no global SMTP_FROM_EMAIL fallback is set.",
            )

        strategy = (profile.auth_strategy or "TLS").upper()
        options = EmailOptions(
            host=profile.host,
            port=int(profile.port),
            username=profile.username or None,
            password=_decrypt(profile.password_encrypted) if profile.password_encrypted else None,
            tls=strategy == "TLS",
            ssl=strategy == "SSL",
        )

        message = Message(
            subject=f"Test email from '{profile.name}'",
            html=(
                f"<p>This is a test email sent through the <strong>{profile.name}</strong> "
                f"SMTP profile. If you received it, the profile works.</p>"
            ),
            mail_from_name=from_name,
            mail_from_address=from_email,
        )
        result = message.send(to_address=data.recipient_email, smtp_config=options)
        return SMTPProfileTestResult(success=result.success, message=result.message)

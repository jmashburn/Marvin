"""
Workspace Integrations API.

CRUD for credentialed connections to external services, plus a provider catalog, a
health check, and an action test-fire. Credentials are written to the configured secret
backend and referenced by `secret_ref` — never stored on the row or returned.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4
from slugify import slugify

from marvin.core.root_logger import get_logger
from marvin.db.models.groups.integrations import IntegrationModel
from marvin.routes._base import BaseUserController, controller
from marvin.schemas.group.integration import (
    IntegrationActionResult,
    IntegrationCheckResult,
    IntegrationCreate,
    IntegrationRead,
    IntegrationUpdate,
)
from marvin.services.integrations import IntegrationContext, get_provider, list_providers
from marvin.services.secrets import get_secret_backend
from marvin.services.secrets.resolver import resolve_secret

router = APIRouter(prefix="/groups/integrations")
logger = get_logger(__name__)


def _secret_ref(slug: str) -> str:
    """Slug under which this integration's credential lives in the secret backend."""
    return f"INTEGRATION_{slug.upper()}"


def _to_read(row: IntegrationModel) -> IntegrationRead:
    return IntegrationRead(
        id=row.id,
        provider=row.provider,
        name=row.name,
        slug=row.slug,
        enabled=row.enabled,
        config=row.config,
        has_credential=bool(row.secret_ref),
        status=row.status,
        last_checked_at=row.last_checked_at,
        last_error=row.last_error,
    )


@controller(router)
class IntegrationsController(BaseUserController):
    """Workspace integration management."""

    # ---- helpers -----------------------------------------------------------------

    def _get_or_404(self, integration_id: UUID4) -> IntegrationModel:
        row = self.session.get(IntegrationModel, integration_id)
        if not row or row.group_id != self.group_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")
        return row

    def _validate_config(self, provider, config: dict) -> None:
        """Light validation: required keys present. (Full JSON-schema validation is a later pass.)"""
        required = (provider.config_schema or {}).get("required", [])
        missing = [k for k in required if not (config or {}).get(k)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing required config: {', '.join(missing)}.",
            )

    def _context(self, row: IntegrationModel) -> IntegrationContext:
        secret = resolve_secret(row.secret_ref, self.group_id) if row.secret_ref else None
        return IntegrationContext(
            integration_id=row.id,
            group_id=self.group_id,
            slug=row.slug,
            config=row.config or {},
            secret=secret,
            session=self.session,
            logger=logger,
        )

    # ---- provider catalog --------------------------------------------------------

    @router.get("/providers")
    def list_provider_catalog(self) -> list[dict]:
        """The available integration providers (the 'add integration' catalog)."""
        return [p.info() for p in list_providers()]

    # ---- CRUD --------------------------------------------------------------------

    @router.get("", response_model=list[IntegrationRead])
    def list_integrations(self):
        """List this workspace's configured integrations."""
        rows = (
            self.session.query(IntegrationModel)
            .filter(IntegrationModel.group_id == self.group_id)
            .order_by(IntegrationModel.name)
            .all()
        )
        return [_to_read(r) for r in rows]

    @router.post("", response_model=IntegrationRead, status_code=status.HTTP_201_CREATED)
    def create_integration(self, data: IntegrationCreate):
        """Create an integration. Any credential is written to the secret backend."""
        try:
            provider = get_provider(data.provider)
        except KeyError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown provider '{data.provider}'.") from e

        slug = slugify(data.slug or data.name, separator="_")
        if not slug:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Could not derive a slug from the name.")

        existing = self.session.query(IntegrationModel).filter(
            IntegrationModel.group_id == self.group_id, IntegrationModel.slug == slug
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Integration slug '{slug}' already exists.")

        self._validate_config(provider, data.config)

        secret_ref = None
        if data.credential is not None:
            secret_ref = _secret_ref(slug)
            get_secret_backend().set(secret_ref, data.credential.get_secret_value(), self.group_id)

        row = IntegrationModel(
            session=self.session,
            group_id=self.group_id,
            provider=data.provider,
            name=data.name,
            slug=slug,
            config=data.config or None,
            secret_ref=secret_ref,
            status="unconfigured",
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)

        # Run an initial health check so the row lands with a real status.
        self._run_check(row)
        return _to_read(row)

    @router.patch("/{integration_id}", response_model=IntegrationRead)
    def update_integration(self, integration_id: UUID4, data: IntegrationUpdate):
        """Update name/enabled/config, or rotate the credential."""
        row = self._get_or_404(integration_id)
        provider = get_provider(row.provider)

        if data.name is not None:
            row.name = data.name
        if data.enabled is not None:
            row.enabled = data.enabled
        if data.config is not None:
            self._validate_config(provider, data.config)
            row.config = data.config or None
        if data.credential is not None:
            ref = row.secret_ref or _secret_ref(row.slug)
            get_secret_backend().set(ref, data.credential.get_secret_value(), self.group_id)
            row.secret_ref = ref

        self.session.commit()
        self.session.refresh(row)
        self._run_check(row)
        return _to_read(row)

    @router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_integration(self, integration_id: UUID4):
        """Delete an integration and its stored credential."""
        row = self._get_or_404(integration_id)
        if row.secret_ref:
            try:
                get_secret_backend().delete(row.secret_ref, self.group_id)
            except Exception as e:  # noqa: BLE001 — best-effort cleanup, never block the delete
                logger.warning(f"[integrations] could not delete secret {row.secret_ref}: {e}")
        self.session.delete(row)
        self.session.commit()

    # ---- health check ------------------------------------------------------------

    def _run_check(self, row: IntegrationModel) -> None:
        provider = get_provider(row.provider)
        try:
            status_str, err = provider.check(self._context(row))
        except Exception as e:  # noqa: BLE001 — a provider bug must not 500 the request
            status_str, err = "error", str(e)
        row.status = status_str
        row.last_error = err
        row.last_checked_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(row)

    @router.post("/{integration_id}/check", response_model=IntegrationCheckResult)
    def check_integration(self, integration_id: UUID4):
        """Run the provider's health check and persist the result."""
        row = self._get_or_404(integration_id)
        self._run_check(row)
        return IntegrationCheckResult(status=row.status, last_error=row.last_error, last_checked_at=row.last_checked_at)

    # ---- action test-fire --------------------------------------------------------

    @router.post("/{integration_id}/actions/{action_key}", response_model=IntegrationActionResult)
    def run_action(self, integration_id: UUID4, action_key: str, args: dict | None = None):
        """Manually fire a provider action (also how the automation engine will call it)."""
        row = self._get_or_404(integration_id)
        if not row.enabled:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Integration is disabled.")

        provider = get_provider(row.provider)
        if provider.get_action(action_key) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No action '{action_key}' on this provider.")

        try:
            result = provider.run_action(action_key, args or {}, self._context(row))
        except NotImplementedError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No action '{action_key}' on this provider.") from e
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
        return IntegrationActionResult(ok=True, result=result)

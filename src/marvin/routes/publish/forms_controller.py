"""Publishing API forms controller."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from marvin.core.dependencies import get_publishing_context
from marvin.core.permissions import Permissions
from marvin.db.db_setup import generate_session
from marvin.db.models.platform.forms import Forms
from marvin.db.models.platform.form_submissions import FormSubmissions
from marvin.schemas.platform.forms import FormSchemaDefinition
from marvin.schemas.publishing import FormSubmissionResponse, PublishedFormRead
from marvin.services.content_validator import ContentValidationError, ContentValidator
from marvin.services.security.captcha_service import CaptchaService
from marvin.services.security.rate_limit_service import RateLimitService

router = APIRouter()


@router.get(
    "/{workspace_slug}/forms/{form_slug}",
    response_model=PublishedFormRead,
    summary="Get Form Definition",
)
async def get_form(
    workspace_slug: str,
    form_slug: str,
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
) -> PublishedFormRead:
    """
    Get published form definition for rendering.

    **Authentication**: Requires API client token
    **Permissions**: read:published_entries
    """
    api_client, group, perms = context

    # Check permission
    perms.require_permission(Permissions.READ_PUBLISHED_ENTRIES, "form definition")

    # Get form
    form = (
        session.query(Forms)
        .filter(
            Forms.group_id == group.id,
            Forms.slug == form_slug,
            Forms.status == "published",
        )
        .first()
    )

    if not form:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")

    return PublishedFormRead(
        slug=form.slug,
        name=form.name,
        description=form.description,
        form_schema=form.schema_json,
        metadata=form.metadata_json,
    )


@router.post(
    "/{workspace_slug}/forms/{form_slug}/submit",
    response_model=FormSubmissionResponse,
    summary="Submit Form Data",
)
async def submit_form(
    workspace_slug: str,
    form_slug: str,
    submission_data: dict,
    request: Request,
    context: tuple = Depends(get_publishing_context),
    session: Session = Depends(generate_session),
) -> FormSubmissionResponse:
    """
    Submit data to a published form.

    **Authentication**: Requires API client token
    **Permissions**: write:form_submissions
    **Security**: Rate limiting, CAPTCHA, honeypot
    """
    api_client, group, perms = context

    # Check permission
    perms.require_permission(Permissions.WRITE_FORM_SUBMISSIONS, "form submission")

    # Get form
    form = (
        session.query(Forms)
        .filter(
            Forms.group_id == group.id,
            Forms.slug == form_slug,
            Forms.status == "published",
        )
        .first()
    )

    if not form:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")

    # Get settings
    settings = form.settings_json or {}

    # Rate limiting check
    ip_address = request.client.host if request.client else "unknown"
    rate_limit_service = RateLimitService(session)
    if not rate_limit_service.check_limit(form.id, ip_address, settings):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )

    # CAPTCHA verification (if enabled)
    security_settings = settings.get("security", {})
    if security_settings.get("enableCaptcha"):
        captcha_service = CaptchaService()
        captcha_token = submission_data.pop("captchaToken", None)
        captcha_provider = security_settings.get("captchaProvider", "hcaptcha")
        captcha_secret = security_settings.get("captchaSecretKey")

        if not await captcha_service.verify(captcha_token, captcha_provider, captcha_secret):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CAPTCHA verification failed",
            )

    # Honeypot check (if enabled)
    if security_settings.get("enableHoneypot"):
        honeypot_field = security_settings.get("honeypotFieldName", "_website")
        if submission_data.get(honeypot_field):
            # Silent success - likely spam
            return FormSubmissionResponse(
                success=True,
                message=settings.get("successMessage", "Thank you for your submission"),
            )
        # Remove honeypot field from data
        submission_data.pop(honeypot_field, None)

    # Validate submission against schema
    if form.schema_json and form.schema_json.get("fields"):
        validator = ContentValidator()
        try:
            schema_def = FormSchemaDefinition.model_validate(form.schema_json)
            validator.validate_form_submission(schema_def, submission_data)
        except ContentValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation failed: {e.message}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid submission data: {str(e)}",
            )

    # Create submission (if persistence enabled)
    submission_id = None
    if settings.get("persistSubmissions", True):
        submission = FormSubmissions(
            session=session,
            form_id=form.id,
            group_id=group.id,
            data_json=submission_data,
            metadata_json={
                "api_client_id": str(api_client.id),
                "referrer": request.headers.get("referer"),
            },
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            submitted_at=datetime.now(timezone.utc),
        )
        session.add(submission)
        session.commit()
        submission_id = submission.id

        # Update form stats
        form.submissions_count += 1
        form.last_submission_at = datetime.now(timezone.utc)
        session.commit()

    # Return response
    success_message = settings.get("successMessage", "Thank you for your submission")
    redirect_url = settings.get("redirectUrl")

    return FormSubmissionResponse(
        success=True,
        message=success_message,
        submission_id=submission_id,
        redirect_url=redirect_url,
    )

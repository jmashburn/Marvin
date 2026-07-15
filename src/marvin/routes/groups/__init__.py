from fastapi import APIRouter

from . import (
    email_template_controller,
    invitation_controller,
    notification_controller,
    preferences_controller,
    secrets_controller,
    webhook_controller,
)

router = APIRouter()

router.include_router(invitation_controller.router, tags=["Groups: Invitations"])
router.include_router(webhook_controller.router, tags=["Groups: Webhooks"])
router.include_router(secrets_controller.router, tags=["Groups: Secrets"])
router.include_router(notification_controller.router, tags=["Groups: Event Notifications"])
router.include_router(preferences_controller.router, tags=["Groups: Preferences"])
router.include_router(email_template_controller.router, tags=["Groups: Email Templates"])

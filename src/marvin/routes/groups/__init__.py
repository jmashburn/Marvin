from fastapi import APIRouter

from . import (
    invitation_controller,
    notification_controller,
    webhook_controller,
)

router = APIRouter()

router.include_router(invitation_controller.router, tags=["Groups: Invitations"])
router.include_router(webhook_controller.router, tags=["Groups: Webhooks"])
router.include_router(notification_controller.router, tags=["Groups: Event Notifications"])

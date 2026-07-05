"""Authenticated platform routes."""

from marvin.routes._base.routers import UserAPIRouter

from . import entries_controller, entry_types_controller

router = UserAPIRouter()

router.include_router(entry_types_controller.router, tags=["Platform: Entry Types"])
router.include_router(entries_controller.router, tags=["Platform: Entries"])

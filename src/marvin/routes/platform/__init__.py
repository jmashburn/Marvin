"""Authenticated platform routes."""

from marvin.routes._base.routers import UserAPIRouter

from . import (
    api_clients_controller,
    assets_controller,
    collections_controller,
    entries_controller,
    entry_types_controller,
    resources_controller,
    workspace_members_controller,
)

router = UserAPIRouter()

router.include_router(entry_types_controller.router, tags=["Platform: Entry Types"])
router.include_router(entries_controller.router, tags=["Platform: Entries"])
router.include_router(collections_controller.router, tags=["Platform: Collections"])
router.include_router(api_clients_controller.router, tags=["Platform: API Clients"])
router.include_router(resources_controller.router, tags=["Platform: Resources"])
router.include_router(assets_controller.router, tags=["Platform: Assets"])
router.include_router(workspace_members_controller.router, tags=["Platform: Workspace Members"])

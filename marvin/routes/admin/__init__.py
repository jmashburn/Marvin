from marvin.routes._base.routers import AdminAPIRouter

from . import (
    about_controller,
    maintenance_controller,
    group_controller,
    user_controller,
    debug_controller,
    email_controller,
)

router = AdminAPIRouter(prefix="/admin", tags=["Admin"])

router.include_router(about_controller.router, tags=["Admin: About"])
router.include_router(debug_controller.router, tags=["Admin: Debug"])
router.include_router(email_controller.router, tags=["Admin: Email"])
router.include_router(user_controller.router, tags=["Admin: Users"])
router.include_router(group_controller.router, tags=["Admin: Groups"])
router.include_router(maintenance_controller.router, tags=["Admin: Maintenance"])

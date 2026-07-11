"""
This module defines the FastAPI controller for administrative debugging endpoints
within the Marvin application.

It provides tools for administrators to test and verify the status of external
service integrations.
"""

from fastapi import APIRouter

from marvin.routes._base import BaseAdminController, controller

# APIRouter for admin "debug" section, prefixed with /debug
# All routes in this controller will be under /admin/debug.
router = APIRouter(prefix="/debug")


@controller(router)
class AdminDebugController(BaseAdminController):
    """
    Controller for administrative debugging endpoints.

    Provides functionality to test external service integrations to ensure they are
    configured and working correctly. Accessible only by administrators.
    """

    # REMOVED: POST /openai endpoint
    # Reason: OpenAI service integration is not implemented (marvin.services.openai module missing)
    # The endpoint had broken imports, dummy classes, and would never work in production
    # Future work: If OpenAI integration is needed, implement a proper service layer first
    # See code review issue #6 (HIGH priority - cleanup)
    pass

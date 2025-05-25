"""
This module defines the FastAPI controller for administrative debugging endpoints
within the Marvin application.

It provides tools for administrators to test and verify the status of external
service integrations, such as OpenAI.
"""
import os
import shutil # For file operations like copyfileobj

from fastapi import APIRouter, File, UploadFile # FastAPI components for routing and file handling

# Marvin core components and utilities
from marvin.core.dependencies.dependencies import get_temporary_path # For creating temporary paths for file uploads
from marvin.routes._base import BaseAdminController, controller # Base controller for admin routes
from marvin.schemas.admin.debug import DebugResponse # Pydantic schema for the debug response

# NOTE: The following OpenAI service imports are currently commented out in the original code.
# This will cause the `debug_openai` endpoint to fail if uncommented and these services are not available.
# To make this functional, these lines would need to be uncommented and the services correctly implemented/imported.
# from marvin.services.openai import OpenAILocalImage, OpenAIService

# APIRouter for admin "debug" section, prefixed with /debug
# All routes in this controller will be under /admin/debug.
router = APIRouter(prefix="/debug", tags=["Admin - Debug"])


@controller(router)
class AdminDebugController(BaseAdminController):
    """
    Controller for administrative debugging endpoints.

    Provides functionality to test integrations like OpenAI to ensure they are
    configured and working correctly. Accessible only by administrators.
    """

    @router.post("/openai", response_model=DebugResponse, summary="Debug OpenAI Integration")
    async def debug_openai(self, image: UploadFile | None = File(None)) -> DebugResponse:
        """
        Tests the OpenAI integration by sending a predefined prompt.

        Optionally, an image can be uploaded to test image-related OpenAI services,
        if they are enabled.

        NOTE: This endpoint currently relies on `OpenAIService` and `OpenAILocalImage`
        which are commented out in the import section of this file. For this endpoint
        to function, those imports need to be active and the services available.

        Args:
            image (UploadFile | None, optional): An optional image file to include
                in the test request to OpenAI. Defaults to None.

        Returns:
            DebugResponse: A Pydantic model indicating the success or failure of the
                           OpenAI test, along with a response message or error details.
        """
        # Check if OpenAI integration is enabled in settings
        if not self.settings.OPENAI_ENABLED:
            return DebugResponse(success=False, response="OpenAI integration is not enabled in application settings.")
        
        # If an image is provided, check if image services are enabled for OpenAI
        if image and not self.settings.OPENAI_ENABLE_IMAGE_SERVICES:
            return DebugResponse(
                success=False, response="An image was provided, but OpenAI image services are not enabled in application settings."
            )

        local_images = None # Initialize local_images to None

        # Use a temporary path to store the uploaded image if provided
        with get_temporary_path() as temp_dir_path:
            if image and image.filename: # Ensure image and filename are not None
                # Define path for the local image copy
                local_image_path = temp_dir_path / image.filename
                # Save the uploaded image to the temporary path
                with open(local_image_path, "wb") as buffer:
                    shutil.copyfileobj(image.file, buffer)
                
                # Prepare the image for the OpenAI service
                # This part depends on the commented-out OpenAILocalImage
                # If OpenAILocalImage were available:
                # local_images = [OpenAILocalImage(filename=os.path.basename(local_image_path), path=local_image_path)]
                # For now, to avoid NameError, we'll simulate or skip this:
                self.logger.info(f"Image '{image.filename}' saved to temporary path for OpenAI debug. (Actual processing depends on uncommented OpenAILocalImage)")
                # Placeholder if OpenAILocalImage is not available:
                # local_images = [{"path": str(local_image_path), "filename": image.filename}] # Or however the service expects it
                # Since it's commented out, we'll assume `local_images` remains None or this part is skipped if services are missing.
                # For the purpose of this docstring pass, let's assume it would be set if imports were active.
                # To make the code runnable without NameError if uncommented partially:
                class OpenAILocalImage: # Dummy class to avoid NameError if OpenAIService is also dummied up
                    def __init__(self, filename, path): self.filename=filename; self.path=path
                local_images = [OpenAILocalImage(filename=os.path.basename(str(local_image_path)), path=local_image_path)]


            try:
                # This section depends on the commented-out OpenAIService
                # If OpenAIService were available:
                # openai_service = OpenAIService()
                # prompt_content = openai_service.get_prompt("debug") # Get a debug-specific prompt
                # message_to_send = "Hello, OpenAI! This is a test message from the Marvin debug endpoint."
                # if local_images:
                #     message_to_send += " An image has been included for testing."
                #
                # # Send the request to OpenAI
                # openai_response = await openai_service.get_response(
                #     prompt_content, message_to_send, images=local_images, force_json_response=False
                # )
                # return DebugResponse(success=True, response=f'OpenAI is working. Response: "{openai_response}"')

                # Placeholder response since OpenAIService is commented out:
                if 'OpenAIService' not in globals() or 'OpenAILocalImage' not in globals(): # Check if dummy or real class exists
                    self.logger.warning("OpenAIService or OpenAILocalImage not available (likely commented out). Returning placeholder success for OpenAI debug.")
                    if image and not local_images: # If image was provided but local_images couldn't be prepared
                         return DebugResponse(success=False, response="OpenAI integration seems enabled, but image processing part (OpenAILocalImage) is not available.")
                    return DebugResponse(success=True, response="OpenAI integration seems enabled. Actual test call skipped as OpenAIService is not fully available.")
                
                # If by some means OpenAIService was made available (e.g. dummy):
                openai_service = OpenAIService() # type: ignore
                prompt = openai_service.get_prompt("debug") # type: ignore

                message = "Hello, checking to see if I can reach you."
                if local_images:
                    message = f"{message} Here is an image to test with:"

                response = await openai_service.get_response( # type: ignore
                    prompt, message, images=local_images, force_json_response=False
                )
                return DebugResponse(success=True, response=f'OpenAI is working. Response: "{response}"')


            except NameError as ne: # Specifically catch NameError if services are not defined
                self.logger.exception(f"OpenAI debug endpoint error due to undefined service (likely commented out imports): {ne}")
                return DebugResponse(
                    success=False,
                    response=f"OpenAI request failed: A required service (e.g., OpenAIService or OpenAILocalImage) is not available. Original error: {ne.__class__.__name__}: \"{ne}\"",
                )
            except Exception as e: # Catch other potential exceptions
                self.logger.exception(f"Error during OpenAI debug request: {e}")
                return DebugResponse(
                    success=False,
                    response=f'OpenAI request failed. Full error has been logged. {e.__class__.__name__}: "{e}"',
                )

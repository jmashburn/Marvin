from pydantic import BaseModel

from marvin.schemas._marvin import _MarvinModel


class ErrorResponse(BaseModel):
    message: str
    error: bool = True
    exception: str | None = None

    @classmethod
    def respond(cls, message: str, exception: str | None = None) -> dict:
        """
        This method is an helper to create an object and convert to a dictionary
        in the same call, for use while providing details to a HTTPException
        """
        return cls(message=message, exception=exception).model_dump()


class SuccessResponse(BaseModel):
    message: str
    error: bool = False

    @classmethod
    def respond(cls, message: str = "") -> dict:
        """
        This method is an helper to create an object and convert to a dictionary
        in the same call, for use while providing details to a HTTPException
        """
        return cls(message=message).model_dump()


class FileTokenResponse(_MarvinModel):
    file_token: str

    @classmethod
    def respond(cls, token: str) -> dict:
        """
        This method is an helper to create an object and convert to a dictionary
        in the same call, for use while providing details to a HTTPException
        """
        return cls(file_token=token).model_dump()

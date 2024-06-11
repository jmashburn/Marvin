from pydantic import BaseModel


class ErrorResponse(BaseModel):
    message: str
    error: bool = True
    exception: str | None = None

    @classmethod
    def respond(cls, message: str, exception: str | None = None) -> dict:
        return cls(message=message, exception=exception).model_dump()


class SuccessResponse(BaseModel):
    message: str
    error: bool = False

    @classmethod
    def respond(cls, message: str) -> dict:
        return cls(message=message).model_dump()

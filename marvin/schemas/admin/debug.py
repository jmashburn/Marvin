from marvin.schemas._marvin import _MarvinModel


class DebugResponse(_MarvinModel):
    success: bool
    response: str | None = None

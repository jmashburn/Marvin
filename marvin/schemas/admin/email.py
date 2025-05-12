from marvin.schemas._marvin import _MarvinModel


class EmailReady(_MarvinModel):
    ready: bool


class EmailSuccess(_MarvinModel):
    success: bool
    error: str | None = None


class EmailTest(_MarvinModel):
    email: str

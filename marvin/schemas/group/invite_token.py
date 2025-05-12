from uuid import UUID

from pydantic import ConfigDict

from marvin.schemas._marvin import _MarvinModel


class InviteTokenModel(_MarvinModel): ...


class InviteTokenCreate(InviteTokenModel):
    uses: int
    group_id: UUID | None = None


class InviteTokenUpdate(_MarvinModel):
    uses_left: int
    group_id: UUID
    token: str


class InviteTokenRead(_MarvinModel):
    token: str
    uses_left: int
    group_id: UUID
    model_config = ConfigDict(from_attributes=True)


class EmailInvitation(_MarvinModel):
    email: str
    token: str


class EmailInitationResponse(_MarvinModel):
    success: bool
    error: str | None = None

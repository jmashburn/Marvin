from uuid import UUID

from pydantic import ConfigDict

from marvin.schemas._marvin import _MarvinModel


class InviteTokenCreate(_MarvinModel):
    uses: int
    group_id: UUID
    model_config = ConfigDict(from_attributes=True)


class InviteTokenUpdate(InviteTokenCreate):
    uses_left: int


class InviteTokenRead(_MarvinModel):
    id: UUID
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

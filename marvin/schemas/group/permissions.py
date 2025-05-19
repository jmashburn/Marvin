from pydantic import UUID4
from marvin.schemas._marvin import _MarvinModel


class SetPermissions(_MarvinModel):
    user_id: UUID4
    can_manage: bool = False
    can_invite: bool = False
    can_organize: bool = False

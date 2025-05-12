from functools import cached_property

from pydantic import UUID4
from sqlalchemy.orm import Session

from marvin.db.models.groups import Groups, ReportEntryModel, ReportModel
from marvin.db.models.groups.events import GroupEventNotifierModel
from marvin.db.models.groups.invite_tokens import GroupInviteToken
from marvin.db.models.groups.preferences import GroupPreferencesModel
from marvin.db.models.groups.webhooks import GroupWebhooksModel
from marvin.db.models.users import LongLiveToken, Users
from marvin.db.models.users.password_reset import PasswordResetModel
from marvin.schemas.group import GroupRead
from marvin.schemas.group.event import GroupEventNotifierRead
from marvin.schemas.group.invite_token import InviteTokenRead
from marvin.schemas.group.preferences import GroupPreferencesRead
from marvin.schemas.group.report import ReportEntryRead, ReportRead
from marvin.schemas.group.webhook import WebhookRead
from marvin.schemas.user import LongLiveTokenRead, PrivateUser
from marvin.schemas.user.password import PrivatePasswordResetToken

from ._utils import NOT_SET, NotSet
from .groups import RepositoryGroup
from .repository_generic import GroupRepositoryGeneric
from .users import RepositoryUsers

PK_ID = "id"
PK_SLUG = "slug"
PK_TOKEN = "token"
PK_GROUP_ID = "group_id"


class AllRepositories:
    """
    `AllRepositories` class is the data access layer for all database actions within
    marvin. Database uses composition from classes derived from AccessModel. These
    can be substantiated from the AccessModel class or through inheritance when
    additional methods are required.
    """

    def __init__(
        self,
        session: Session,
        *,
        group_id: UUID4 | None | NotSet = NOT_SET,
    ) -> None:
        self.session = session
        self.group_id = group_id

    # # ================================================================
    # # Group

    # ================================================================
    # User

    @cached_property
    def users(self) -> RepositoryUsers:
        return RepositoryUsers(self.session, PK_ID, Users, PrivateUser, group_id=self.group_id)

    @cached_property
    def api_tokens(self) -> GroupRepositoryGeneric[LongLiveTokenRead, LongLiveToken]:
        return GroupRepositoryGeneric(self.session, PK_ID, LongLiveToken, LongLiveTokenRead, group_id=self.group_id)

    @cached_property
    def tokens_pw_reset(self) -> GroupRepositoryGeneric[PrivatePasswordResetToken, PasswordResetModel]:
        return GroupRepositoryGeneric(
            self.session, PK_TOKEN, PasswordResetModel, PrivatePasswordResetToken, group_id=self.group_id
        )

    # ================================================================
    # Group

    @cached_property
    def groups(self) -> RepositoryGroup:
        return RepositoryGroup(self.session, PK_ID, Groups, GroupRead)

    @cached_property
    def group_preferences(self) -> GroupRepositoryGeneric[GroupPreferencesRead, GroupPreferencesModel]:
        return GroupRepositoryGeneric(
            self.session, PK_GROUP_ID, GroupPreferencesModel, GroupPreferencesRead, group_id=self.group_id
        )

    @cached_property
    def group_reports(self) -> GroupRepositoryGeneric[ReportRead, ReportModel]:
        return GroupRepositoryGeneric(self.session, PK_ID, ReportModel, ReportRead, group_id=self.group_id)

    @cached_property
    def group_report_entries(self) -> GroupRepositoryGeneric[ReportEntryRead, ReportEntryModel]:
        return GroupRepositoryGeneric(self.session, PK_ID, ReportEntryModel, ReportEntryRead, group_id=self.group_id)

    @cached_property
    def group_invite_tokens(self) -> GroupRepositoryGeneric[InviteTokenRead, GroupInviteToken]:
        return GroupRepositoryGeneric(
            self.session,
            PK_TOKEN,
            GroupInviteToken,
            InviteTokenRead,
            group_id=self.group_id,
        )

    # ================================================================
    # Events

    @cached_property
    def group_event_notifier(self) -> GroupRepositoryGeneric[GroupEventNotifierRead, GroupEventNotifierModel]:
        return GroupRepositoryGeneric(
            self.session,
            PK_ID,
            GroupEventNotifierModel,
            GroupEventNotifierRead,
            group_id=self.group_id,
        )

    @cached_property
    def webhooks(self) -> GroupRepositoryGeneric[WebhookRead, GroupWebhooksModel]:
        return GroupRepositoryGeneric(self.session, PK_ID, GroupWebhooksModel, WebhookRead, group_id=self.group_id)

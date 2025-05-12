from logging import Logger
from uuid import uuid4

from fastapi import HTTPException, status

from marvin.core.security import hash_password
from marvin.repos.repository_factory import AllRepositories
from marvin.schemas.group import GroupCreate, GroupRead
from marvin.schemas.group.preferences import GroupPreferencesCreate
from marvin.schemas.user import PrivateUser, UserCreate
from marvin.schemas.user.registration import UserRegistrationCreate
from marvin.services.group.group_service import GroupService
from marvin.services.seeders.seeder_service import SeederService


class RegistrationService:
    logger: Logger
    repos: AllRepositories

    def __init__(self, logger: Logger, db: AllRepositories):
        self.logger = logger
        self.repos = db

    def _create_new_user(self, group: GroupRead, new_group: bool) -> PrivateUser:
        new_user = UserCreate(
            email=self.registration.email,
            username=self.registration.username,
            password=hash_password(self.registration.password),
            full_name=self.registration.full_name,
            advanced=self.registration.advanced,
            group=group,
            can_invite=new_group,
            can_manage=new_group,
            can_organize=new_group,
        )

        # TODO: problem with repository type, not type here
        return self.repos.users.create(new_user)  # type: ignore

    def _register_new_group(self) -> GroupRead:
        group_data = GroupCreate(name=self.registration.group)

        group_preferences = GroupPreferencesCreate(
            group_id=uuid4(),
            private_group=self.registration.private,
        )

        return GroupService.create_group(self.repos, group_data, group_preferences)

    def register_user(self, registration: UserRegistrationCreate) -> PrivateUser:
        self.registration = registration

        if self.repos.users.get_by_username(registration.username):
            raise HTTPException(status.HTTP_409_CONFLICT, {"message": self.t("exceptions.username-conflict-error")})
        elif self.repos.users.get_one(registration.email, "email"):
            raise HTTPException(status.HTTP_409_CONFLICT, {"message": self.t("exceptions.email-conflict-error")})

        token_entry = None
        new_group = False

        if registration.group_token:
            token_entry = self.repos.group_invite_tokens.get_one(registration.group_token)
            if not token_entry:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, {"message": "Invalid group token"})

            maybe_none_group = self.repos.groups.get_one(token_entry.group_id)
            if maybe_none_group is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, {"message": "Invalid group token"})
            group = maybe_none_group

        elif registration.group:
            new_group = True
            group = self._register_new_group()
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, {"message": "Missing group"})

        self.logger.info(f"Registering user {registration.username}")
        user = self._create_new_user(group, new_group)

        if new_group and registration.seed_data:
            seeder_service = SeederService(self.repos)

        if token_entry and user:
            token_entry.uses_left = token_entry.uses_left - 1

            if token_entry.uses_left == 0:
                self.repos.group_invite_tokens.delete(token_entry.token)

            else:
                self.repos.group_invite_tokens.update(token_entry.token, token_entry)

        return user

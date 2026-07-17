"""Base class and registry for named AI operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..base import Message

# WorkspaceRole numeric values for min_role checks
ROLE_VIEWER = 1
ROLE_AUTHOR = 2
ROLE_EDITOR = 3
ROLE_ADMIN = 4
ROLE_OWNER = 5

OPERATION_REGISTRY: dict[str, "AIOperation"] = {}


def register_operation(cls):
    """Class decorator that adds the operation to the global registry."""
    OPERATION_REGISTRY[cls.slug] = cls()
    return cls


def get_operation(slug: str) -> "AIOperation":
    if slug not in OPERATION_REGISTRY:
        raise KeyError(f"AI operation '{slug}' not found. Available: {list(OPERATION_REGISTRY)}")
    return OPERATION_REGISTRY[slug]


def list_operations() -> list["AIOperation"]:
    return list(OPERATION_REGISTRY.values())


@dataclass
class OperationContext:
    """Resolved context assembled by ContextBuilder before prompt construction."""
    workspace_name: str = ""
    site_title: str = ""
    site_locale: str = "en-US"
    current_date: str = ""
    variables: dict = field(default_factory=dict)
    entry: dict | None = None
    assets: list[dict] = field(default_factory=list)
    resources: list[dict] = field(default_factory=list)
    form_submission: dict | None = None
    retrieved: list[dict] = field(default_factory=list)  # semantic-search chunks (RAG)


class AIOperation(ABC):
    """
    Named, typed AI capability.

    Each subclass defines input/output schemas, minimum role,
    supported entity types, and prompt construction logic.
    """

    slug: str
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    min_role: int = ROLE_AUTHOR
    entity_types: list[str] = []   # which entity types this operation supports
    requires_vision: bool = False
    requires_retrieval: bool = False  # RAG: retrieve workspace chunks before prompting

    @abstractmethod
    def build_prompt(self, input: dict, ctx: OperationContext) -> list[Message]:
        """Construct the message list to send to the provider."""
        ...

    def info(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "min_role": self.min_role,
            "entity_types": self.entity_types,
            "requires_vision": self.requires_vision,
        }

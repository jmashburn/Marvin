"""Abstract base class and shared data types for AI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str | list  # list for multimodal (text + image parts)


@dataclass
class CompletionOptions:
    max_tokens: int | None = None
    temperature: float = 0.7
    top_p: float = 1.0
    extra: dict = field(default_factory=dict)


@dataclass
class CompletionResult:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    raw: dict = field(default_factory=dict)


class AIProvider(ABC):
    """
    Abstract base for all AI provider implementations.

    Follows the same pattern as SecretBackend and BaseStorageProvider —
    selected and instantiated by get_ai_provider() in factory.py.
    """

    provider_type: str
    display_name: str
    supports_vision: bool = False
    supports_structured_output: bool = False

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        model: str,
        options: CompletionOptions | None = None,
    ) -> CompletionResult:
        """Send a chat completion request and return the result."""
        ...

    @abstractmethod
    def complete_structured(
        self,
        messages: list[Message],
        model: str,
        output_schema: dict,
        options: CompletionOptions | None = None,
    ) -> dict:
        """Request structured (JSON) output conforming to output_schema."""
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return model IDs available from this provider."""
        ...

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """
        Validate the connection and credentials.
        Returns (success, message).
        """
        ...

    def execute_operation(
        self,
        messages: list[Message],
        model: str,
        output_schema: dict,
        options: CompletionOptions | None = None,
    ) -> tuple[dict, CompletionResult]:
        """
        Execute a structured-output operation and return (parsed_dict, result_with_usage).

        Default implementation: call complete() then parse JSON from content.
        Providers with native structured output (OpenAI, Anthropic) override this
        to use their native mechanisms while still returning token usage.
        """
        import json
        import re

        result = self.complete(messages, model, options)
        # Strip markdown code fences if the model wrapped JSON in ```json ... ```
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", result.content.strip())
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"raw": result.content}
        return parsed, result

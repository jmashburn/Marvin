"""Anthropic provider implementation."""

from ..base import AIProvider, CompletionOptions, CompletionResult, Message


class AnthropicProvider(AIProvider):
    provider_type = "anthropic"
    display_name = "Anthropic"
    supports_vision = True
    supports_structured_output = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _client(self):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install the anthropic package: uv add anthropic")
        return anthropic.Anthropic(api_key=self._api_key)

    def _split_messages(self, messages: list[Message]):
        system = " ".join(m.content for m in messages if m.role == "system" and isinstance(m.content, str))
        chat = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        return system or None, chat

    def complete(self, messages: list[Message], model: str, options: CompletionOptions | None = None) -> CompletionResult:
        opts = options or CompletionOptions()
        system, chat = self._split_messages(messages)
        client = self._client()
        kwargs = dict(model=model, messages=chat, max_tokens=opts.max_tokens or 4096, temperature=opts.temperature)
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        content = resp.content[0].text if resp.content else ""
        return CompletionResult(
            content=content,
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
            model=resp.model,
            raw=resp.model_dump(),
        )

    def complete_structured(self, messages: list[Message], model: str, output_schema: dict, options: CompletionOptions | None = None) -> dict:
        import json
        opts = options or CompletionOptions()
        system, chat = self._split_messages(messages)
        client = self._client()
        tool = {"name": "structured_output", "description": "Return structured output", "input_schema": output_schema}
        kwargs = dict(model=model, messages=chat, max_tokens=opts.max_tokens or 4096, tools=[tool], tool_choice={"type": "tool", "name": "structured_output"})
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        for block in resp.content:
            if hasattr(block, "input"):
                return block.input
        return json.loads(resp.content[0].text if resp.content else "{}")

    def list_models(self) -> list[str]:
        return ["claude-opus-4-8", "claude-sonnet-5", "claude-haiku-4-5-20251001"]

    def test_connection(self) -> tuple[bool, str]:
        try:
            client = self._client()
            client.messages.create(model="claude-haiku-4-5-20251001", messages=[{"role": "user", "content": "hi"}], max_tokens=1)
            return True, "Connected"
        except Exception as e:
            return False, str(e)

"""Azure OpenAI provider implementation."""

from ..base import AIProvider, CompletionOptions, CompletionResult, Message


class AzureOpenAIProvider(AIProvider):
    provider_type = "azure"
    display_name = "Azure OpenAI"
    supports_vision = True
    supports_structured_output = True

    def __init__(self, api_key: str, base_url: str, api_version: str = "2024-02-01") -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._api_version = api_version

    def _client(self):
        try:
            from openai import AzureOpenAI
        except ImportError:
            raise ImportError("Install the openai package: uv add openai")
        return AzureOpenAI(api_key=self._api_key, azure_endpoint=self._base_url, api_version=self._api_version)

    def complete(self, messages: list[Message], model: str, options: CompletionOptions | None = None) -> CompletionResult:
        opts = options or CompletionOptions()
        resp = self._client().chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_tokens=opts.max_tokens,
            temperature=opts.temperature,
        )
        choice = resp.choices[0]
        return CompletionResult(
            content=choice.message.content or "",
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
            total_tokens=resp.usage.total_tokens,
            model=resp.model,
            raw=resp.model_dump(),
        )

    def complete_structured(self, messages: list[Message], model: str, output_schema: dict, options: CompletionOptions | None = None) -> dict:
        import json
        opts = options or CompletionOptions()
        resp = self._client().chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            response_format={"type": "json_schema", "json_schema": {"name": "output", "schema": output_schema}},
            max_tokens=opts.max_tokens,
        )
        return json.loads(resp.choices[0].message.content or "{}")

    def list_models(self) -> list[str]:
        try:
            models = self._client().models.list()
            return [m.id for m in models.data]
        except Exception:
            return []

    def test_connection(self) -> tuple[bool, str]:
        try:
            self.list_models()
            return True, "Connected to Azure OpenAI"
        except Exception as e:
            return False, str(e)

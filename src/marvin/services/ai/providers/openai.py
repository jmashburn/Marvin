"""OpenAI provider implementation."""

from ..base import AIProvider, CompletionOptions, CompletionResult, ImagePart, Message


class OpenAIProvider(AIProvider):
    provider_type = "openai"
    display_name = "OpenAI"
    supports_vision = True
    supports_structured_output = True
    supports_embeddings = True

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._api_key = api_key
        self._base_url = base_url

    def _client(self):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("OpenAI SDK not installed. Run: uv sync --extra openai (or pip install 'marvin[openai]')")
        return OpenAI(api_key=self._api_key, base_url=self._base_url)

    def _render_content(self, content):
        """Translate agnostic content into OpenAI's chat format (str or multimodal parts)."""
        if isinstance(content, str):
            return content
        parts = []
        for p in content:
            if isinstance(p, ImagePart):
                parts.append({"type": "image_url", "image_url": {"url": f"data:{p.mime_type};base64,{p.data}"}})
            else:
                parts.append({"type": "text", "text": str(p)})
        return parts

    def _to_api_messages(self, messages: list[Message]):
        return [{"role": m.role, "content": self._render_content(m.content)} for m in messages]

    def complete(self, messages: list[Message], model: str, options: CompletionOptions | None = None) -> CompletionResult:
        opts = options or CompletionOptions()
        client = self._client()
        resp = client.chat.completions.create(
            model=model,
            messages=self._to_api_messages(messages),
            max_tokens=opts.max_tokens,
            temperature=opts.temperature,
            top_p=opts.top_p,
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
        client = self._client()
        resp = client.chat.completions.create(
            model=model,
            messages=self._to_api_messages(messages),
            response_format={"type": "json_schema", "json_schema": {"name": "output", "schema": output_schema, "strict": True}},
            max_tokens=opts.max_tokens,
            temperature=opts.temperature,
        )
        return json.loads(resp.choices[0].message.content or "{}")

    def list_models(self) -> list[str]:
        client = self._client()
        models = client.models.list()
        return sorted(m.id for m in models.data if "gpt" in m.id or "o1" in m.id or "o3" in m.id)

    def execute_operation(self, messages, model, output_schema, options=None):
        import json
        opts = options or CompletionOptions()
        client = self._client()
        resp = client.chat.completions.create(
            model=model,
            messages=self._to_api_messages(messages),
            response_format={"type": "json_schema", "json_schema": {"name": "output", "schema": output_schema, "strict": True}},
            max_tokens=opts.max_tokens,
            temperature=opts.temperature,
        )
        parsed = json.loads(resp.choices[0].message.content or "{}")
        result = CompletionResult(
            content=resp.choices[0].message.content or "",
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
            total_tokens=resp.usage.total_tokens,
            model=resp.model,
        )
        return parsed, result

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        resp = self._client().embeddings.create(model=model, input=texts)
        return [d.embedding for d in resp.data]

    def test_connection(self) -> tuple[bool, str]:
        try:
            models = self.list_models()
            return True, f"Connected — {len(models)} models available"
        except Exception as e:
            return False, str(e)

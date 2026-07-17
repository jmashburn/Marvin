"""Google Gemini provider implementation."""

from ..base import AIProvider, CompletionOptions, CompletionResult, ImagePart, Message


class GoogleProvider(AIProvider):
    provider_type = "google"
    display_name = "Google Gemini"
    supports_vision = True
    supports_structured_output = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _client(self):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("Google Generative AI SDK not installed. Run: uv sync --extra google (or pip install 'marvin[google]')")
        genai.configure(api_key=self._api_key)
        return genai

    def _to_parts(self, messages: list[Message]) -> list:
        """Flatten messages into Gemini content parts (text strings + inline image blobs)."""
        import base64
        parts: list = []
        for msg in messages:
            if isinstance(msg.content, str):
                parts.append(f"{msg.role}: {msg.content}")
                continue
            for p in msg.content:
                if isinstance(p, ImagePart):
                    parts.append({"mime_type": p.mime_type, "data": base64.b64decode(p.data)})
                else:
                    parts.append(str(p))
        return parts

    def complete(self, messages: list[Message], model: str, options: CompletionOptions | None = None) -> CompletionResult:
        opts = options or CompletionOptions()
        genai = self._client()
        m = genai.GenerativeModel(model)
        resp = m.generate_content(self._to_parts(messages), generation_config={"max_output_tokens": opts.max_tokens, "temperature": opts.temperature})
        usage = resp.usage_metadata
        return CompletionResult(
            content=resp.text,
            prompt_tokens=usage.prompt_token_count,
            completion_tokens=usage.candidates_token_count,
            total_tokens=usage.total_token_count,
            model=model,
        )

    def complete_structured(self, messages: list[Message], model: str, output_schema: dict, options: CompletionOptions | None = None) -> dict:
        import json
        opts = options or CompletionOptions()
        genai = self._client()
        m = genai.GenerativeModel(model)
        parts = self._to_parts(messages)
        parts.append(f"Return valid JSON matching this schema: {json.dumps(output_schema)}")
        resp = m.generate_content(parts, generation_config={"response_mime_type": "application/json", "max_output_tokens": opts.max_tokens})
        return json.loads(resp.text)

    def list_models(self) -> list[str]:
        return ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._client()
            return True, "Connected"
        except Exception as e:
            return False, str(e)

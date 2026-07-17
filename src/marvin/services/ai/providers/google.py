"""Google Gemini provider implementation."""

from ..base import AIProvider, CompletionOptions, CompletionResult, Message


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
            raise ImportError("Install the google-generativeai package: uv add google-generativeai")
        genai.configure(api_key=self._api_key)
        return genai

    def complete(self, messages: list[Message], model: str, options: CompletionOptions | None = None) -> CompletionResult:
        opts = options or CompletionOptions()
        genai = self._client()
        m = genai.GenerativeModel(model)
        prompt = "\n".join(f"{msg.role}: {msg.content}" for msg in messages if isinstance(msg.content, str))
        resp = m.generate_content(prompt, generation_config={"max_output_tokens": opts.max_tokens, "temperature": opts.temperature})
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
        prompt = "\n".join(f"{msg.role}: {msg.content}" for msg in messages if isinstance(msg.content, str))
        prompt += f"\n\nReturn valid JSON matching this schema: {json.dumps(output_schema)}"
        resp = m.generate_content(prompt, generation_config={"response_mime_type": "application/json", "max_output_tokens": opts.max_tokens})
        return json.loads(resp.text)

    def list_models(self) -> list[str]:
        return ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._client()
            return True, "Connected"
        except Exception as e:
            return False, str(e)

"""Ollama provider — calls the local Ollama REST API via httpx."""

import json

import httpx

from ..base import AIProvider, CompletionOptions, CompletionResult, Message


class OllamaProvider(AIProvider):
    provider_type = "ollama"
    display_name = "Ollama"
    supports_vision = False
    supports_structured_output = True

    def __init__(self, base_url: str = "http://localhost:11434", api_key: str | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        # api_key unused for local Ollama but kept for interface consistency

    def _chat(self, model: str, messages: list[dict], options: CompletionOptions, fmt: dict | None = None) -> dict:
        payload: dict = {"model": model, "messages": messages, "stream": False}
        if fmt:
            payload["format"] = fmt
        if options.temperature != 0.7:
            payload.setdefault("options", {})["temperature"] = options.temperature
        resp = httpx.post(f"{self._base_url}/api/chat", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()

    def complete(self, messages: list[Message], model: str, options: CompletionOptions | None = None) -> CompletionResult:
        opts = options or CompletionOptions()
        data = self._chat(model, [{"role": m.role, "content": m.content} for m in messages], opts)
        msg = data.get("message", {})
        usage = data.get("prompt_eval_count", 0), data.get("eval_count", 0)
        return CompletionResult(
            content=msg.get("content", ""),
            prompt_tokens=usage[0],
            completion_tokens=usage[1],
            total_tokens=usage[0] + usage[1],
            model=model,
            raw=data,
        )

    def complete_structured(self, messages: list[Message], model: str, output_schema: dict, options: CompletionOptions | None = None) -> dict:
        opts = options or CompletionOptions()
        data = self._chat(model, [{"role": m.role, "content": m.content} for m in messages], opts, fmt=output_schema)
        content = data.get("message", {}).get("content", "{}")
        return json.loads(content)

    def list_models(self) -> list[str]:
        resp = httpx.get(f"{self._base_url}/api/tags", timeout=10)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]

    def test_connection(self) -> tuple[bool, str]:
        try:
            models = self.list_models()
            return True, f"Connected — {len(models)} models available"
        except Exception as e:
            return False, str(e)

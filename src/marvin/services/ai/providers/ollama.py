"""Ollama provider — calls the local Ollama REST API via httpx."""

import json

import httpx

from ..base import AIProvider, CompletionOptions, CompletionResult, ImagePart, Message


class OllamaProvider(AIProvider):
    provider_type = "ollama"
    display_name = "Ollama"
    supports_vision = False
    supports_structured_output = True

    def __init__(self, base_url: str = "http://localhost:11434", api_key: str | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        # api_key unused for local Ollama but kept for interface consistency

    def _to_api_messages(self, messages: list[Message]) -> list[dict]:
        """Ollama carries images in a separate `images` list (base64) alongside text content."""
        out: list[dict] = []
        for m in messages:
            if isinstance(m.content, str):
                out.append({"role": m.role, "content": m.content})
                continue
            text = " ".join(str(p) for p in m.content if not isinstance(p, ImagePart))
            images = [p.data for p in m.content if isinstance(p, ImagePart)]
            msg: dict = {"role": m.role, "content": text}
            if images:
                msg["images"] = images
            out.append(msg)
        return out

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
        data = self._chat(model, self._to_api_messages(messages), opts)
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
        data = self._chat(model, self._to_api_messages(messages), opts, fmt=output_schema)
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

"""Ollama provider — calls the local Ollama REST API via httpx."""

import json

import httpx

from ..base import (
    AIProvider,
    CompletionOptions,
    CompletionResult,
    ImagePart,
    Message,
    ToolCall,
    ToolDefinition,
)


class OllamaProvider(AIProvider):
    provider_type = "ollama"
    display_name = "Ollama"
    supports_vision = False
    supports_structured_output = True
    supports_embeddings = True
    # Provider CAN pass tools to /api/chat; whether a call actually yields tool_calls depends on
    # the loaded model (llama3.1+, qwen2.5, …). The agent loop still gates on model support.
    supports_tool_calls = True

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

    def _to_api_tool_messages(self, messages: list[Message]) -> list[dict]:
        """Render the tool-calling round-trip into Ollama's native /api/chat shape.

        Ollama carries tool calls as `message.tool_calls[].function.{name,arguments}` (arguments an
        OBJECT, not a JSON string) and tool results as plain role="tool" messages — no call id.
        """
        out: list[dict] = []
        for m in messages:
            if m.role == "tool":
                content = m.content if isinstance(m.content, str) else str(m.content)
                out.append({"role": "tool", "content": content})
            elif m.role == "assistant" and m.tool_calls:
                out.append({
                    "role": "assistant",
                    "content": m.content if isinstance(m.content, str) else "",
                    "tool_calls": [
                        {"function": {"name": tc.name, "arguments": tc.arguments}} for tc in m.tool_calls
                    ],
                })
            else:
                out.extend(self._to_api_messages([m]))
        return out

    def _chat(
        self,
        model: str,
        messages: list[dict],
        options: CompletionOptions,
        fmt: dict | None = None,
        tools: list[dict] | None = None,
    ) -> dict:
        payload: dict = {"model": model, "messages": messages, "stream": False}
        if fmt:
            payload["format"] = fmt
        if tools:
            payload["tools"] = tools
        if options.temperature != 0.7:
            payload.setdefault("options", {})["temperature"] = options.temperature
        resp = httpx.post(f"{self._base_url}/api/chat", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()

    def complete_with_tools(
        self,
        messages: list[Message],
        model: str,
        tools: list[ToolDefinition],
        options: CompletionOptions | None = None,
        tool_choice: str = "auto",
    ) -> CompletionResult:
        # Ollama's native API has no tool_choice; the model decides. `tool_choice` is accepted for
        # interface parity and ignored.
        opts = options or CompletionOptions()
        api_tools = [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.input_schema}}
            for t in tools
        ]
        data = self._chat(model, self._to_api_tool_messages(messages), opts, tools=api_tools)
        msg = data.get("message", {})

        tool_calls: list[ToolCall] = []
        for i, rc in enumerate(msg.get("tool_calls") or []):
            fn = rc.get("function", {})
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            # Ollama does not return an id; synthesize a stable one for the round-trip.
            tool_calls.append(ToolCall(id=rc.get("id") or f"call_{i}", name=fn.get("name", ""), arguments=args))

        prompt_tokens, completion_tokens = data.get("prompt_eval_count", 0), data.get("eval_count", 0)
        return CompletionResult(
            content=msg.get("content", ""),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model=model,
            raw=data,
            tool_calls=tool_calls,
            stop_reason="tool_calls" if tool_calls else data.get("done_reason"),
        )

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

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            resp = httpx.post(f"{self._base_url}/api/embeddings", json={"model": model, "prompt": t}, timeout=60)
            resp.raise_for_status()
            out.append(resp.json()["embedding"])
        return out

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

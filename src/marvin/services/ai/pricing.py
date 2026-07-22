"""
Approximate AI provider pricing for cost estimation.

Prices are per 1M tokens (input/output separately).
Updated periodically — not real-time. Used only for estimates stored on executions.
"""

from dataclasses import dataclass


@dataclass
class ModelPricing:
    input_per_1m: float   # USD per 1M prompt tokens
    output_per_1m: float  # USD per 1M completion tokens


# provider_type → model_id → pricing
PRICING: dict[str, dict[str, ModelPricing]] = {
    "openai": {
        "gpt-4o": ModelPricing(input_per_1m=2.50, output_per_1m=10.00),
        "gpt-4o-mini": ModelPricing(input_per_1m=0.15, output_per_1m=0.60),
        "gpt-4.1": ModelPricing(input_per_1m=2.00, output_per_1m=8.00),
        "gpt-4.1-mini": ModelPricing(input_per_1m=0.40, output_per_1m=1.60),
        "gpt-4-turbo": ModelPricing(input_per_1m=10.00, output_per_1m=30.00),
        "o3": ModelPricing(input_per_1m=10.00, output_per_1m=40.00),
        "o4-mini": ModelPricing(input_per_1m=1.10, output_per_1m=4.40),
        # Image models — priced by the token usage the images API returns (input text, output image).
        "gpt-image-1": ModelPricing(input_per_1m=5.00, output_per_1m=40.00),
        "gpt-image-1-mini": ModelPricing(input_per_1m=2.00, output_per_1m=8.00),
    },
    "anthropic": {
        "claude-opus-4-8": ModelPricing(input_per_1m=15.00, output_per_1m=75.00),
        "claude-sonnet-5": ModelPricing(input_per_1m=3.00, output_per_1m=15.00),
        "claude-haiku-4-5-20251001": ModelPricing(input_per_1m=0.80, output_per_1m=4.00),
    },
    "google": {
        "gemini-1.5-pro": ModelPricing(input_per_1m=1.25, output_per_1m=5.00),
        "gemini-1.5-flash": ModelPricing(input_per_1m=0.075, output_per_1m=0.30),
        "gemini-2.0-flash": ModelPricing(input_per_1m=0.10, output_per_1m=0.40),
    },
    "azure": {
        # Azure mirrors OpenAI pricing; use the same rates
        "gpt-4o": ModelPricing(input_per_1m=2.50, output_per_1m=10.00),
        "gpt-4.1": ModelPricing(input_per_1m=2.00, output_per_1m=8.00),
    },
    # Ollama is self-hosted — no cost
    "ollama": {},
    "custom": {},
}

_FALLBACK = ModelPricing(input_per_1m=0.0, output_per_1m=0.0)


def estimate_cost(provider_type: str, model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return estimated USD cost for a completion. Returns 0.0 for unknown models."""
    pricing = PRICING.get(provider_type, {}).get(model_id, _FALLBACK)
    cost = (prompt_tokens / 1_000_000) * pricing.input_per_1m
    cost += (completion_tokens / 1_000_000) * pricing.output_per_1m
    return round(cost, 8)

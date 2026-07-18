# Task: Reconcile AI-ARCHITECTURE-PLAN.md with shipped code + settle open questions

## Goal
Update `docs/AI-ARCHITECTURE-PLAN.md` so the design doc re-converges with what Phases 1–3
actually shipped, resolves the one genuinely open architectural question (where capability
truth lives), and records the rejected alternatives (provider packages / entry points /
LangChain) so they don't get reopened. **Design-only. No implementation code.**

## Context
The prompt floated splitting providers into separate `marvin-ai-*` uv packages with
entry-point discovery and an optional LangChain provider. Review concluded that is a
*regression* from this plan, which already commits to a single package + switch-factory
(mirroring `get_secret_backend()`/`get_storage_provider()`) + a decorator registry.
Meanwhile the shipped code (base.py, factory.py, providers/*, operations/*) had drifted
from the doc. Fix the doc, don't split packages.

## Edits applied (all in docs/AI-ARCHITECTURE-PLAN.md)
- [x] §6 CompletionResult — add `total_tokens` (shipped code has it; doc omitted it)
- [x] §6 ABC — replace `complete_structured` with `execute_operation -> (dict, CompletionResult)`
- [x] §6 — vision moved to model layer; only `supports_structured_output` stays on provider
- [x] §6 — concrete provider snippets drop `supports_vision`
- [x] §6 — "Shipped in Phases 1–3" drift callout under the heading
- [x] §6 — Provider Isolation & Optional SDKs subsection (import boundary + extras)
- [x] §7 — `ai_models` rows authoritative for capabilities; pre-call `required ⊆ available`
      compat check specified (flagged not-yet-implemented, build before Phase 6)
- [x] §20 — items 8–10: reject provider packages / entry points / LangChain-as-provider

## Verification
- [x] No contradictions between §6, §7, §13 (capability truth now single-sourced to §7/§13 model rows)
- [x] Doc still "design only"; no implementation code added
- [x] Edits surgical — six targeted replacements, no unrelated churn

## Review
Doc and shipped code are back in sync. Two follow-ups are now explicit backlog items, not
hidden drift:
1. **Implement the §7 pre-call capability check** (`required ⊆ available`, 422 on mismatch) —
   currently specified but not built; needed before Phase 6 vision operations.
2. **Add SDK extras to pyproject** (`marvin[openai]`, `marvin[anthropic]`, …) — §6 lazy
   imports already assume this; the packaging just needs to be declared.
Neither is in scope for this doc task. No code was changed — providers/base.py etc. already
match the reconciled doc except for those two backlog items.

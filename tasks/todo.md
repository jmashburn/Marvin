# AI Subsystem — Backlog & Musings

Captured from working sessions. Grouped by effort. (The original AI-settings build plan
that lived here is shipped — replaced with the live backlog.)

## 🍂 Low-hanging
- [ ] **`AI_ALLOW_WORKSPACE_CREDENTIALS` platform toggle** — let a platform admin
      allow/disallow workspaces using their own AI keys (credential_mode=workspace).
      Enforce in the ai-settings PATCH + gate the UI. **← doing now**
- [ ] **Wire `logging_config`** — honor `log_inputs`/`log_outputs` when persisting
      executions, and add an ai_executions retention prune (mirror the event_log prune;
      `retention_days`). Today executions are always fully logged, never pruned.
- [ ] **`entry_updated` → re-embed** — extend the auto-embed reaction to re-index on
      update (watch draft-save noise before enabling).
- [ ] **Surface the `audited` flag per-event in the Events UI** — toggle audit on/off
      without editing the catalog.
- [ ] **Event Log**: optional dedicated status column (vs the inline dot).
- [ ] **"Ask Marvin" bubble — v1 (seed of the assistant below)** — a persistent corner
      bubble that opens RAG Ask (answer-workspace-question) from any page. Reuses the
      existing endpoint; gate on AI-enabled. Ship this first; it grows into ★ Marvin.
- [ ] Ops: actually create a `prune_event_logs` scheduled task (daily) — handler exists.

## 🌳 Medium / Features
- [ ] **Write-back step → make `approval_mode` real.** After an op returns output_json:
      field-mapping per op (summary→entry.summary, tags→entry.tags, …), apply gated by
      approval_mode × entity status (draft vs published), emit an event (re-triggers
      auto-embed), editor accept/diff UX. `operation_overrides` slots in here.
- [ ] **Wire `invocation_sources`** — gate operations by source (editor/forms/actions/
      mcp/scheduled). Currently stored, never checked.
- [ ] **Wire `moderation_config`** — add a moderation layer + `block_on_flag`.
- [ ] **Workspace Providers UI** — create/edit `AIProviderModel` rows (base_url, Azure
      api_version, Ollama endpoint). Needed for Ollama/Azure workspace setups.

## ★ North star: "Marvin" — the expandable workspace assistant
Persona: **Marvin the Martian** (playful, a little imperious — "where's the kaboom?").
The "Ask Marvin" bubble is his v1 shell. Not just RAG — a command surface that can *do* things:
- **Ask** — RAG Q&A over workspace content (one skill among many)
- **Actions** — Review, Publish, Test, Rebuild, … dispatched to existing endpoints
  (publishing, scheduled tasks, the operations registry)
- **Expandable** — a skill/tool registry so capabilities plug in rather than hardcode
- **MCP as the plugin layer** — host our operations as tools *and* connect external MCP
  servers, so Marvin's abilities grow without core changes
- Likely an **agentic loop** (Phase 8 agents) picking which skill/tool to run per request
Sequencing: operations registry (done) → skill/tool registry → agent loop → MCP host.
Ship the RAG bubble now as the seed; layer skills onto it.

## 🌲 Bigger / Phase 8
- [ ] **Prompt storage** — a `prompts` table (slug, template, variables, version).
      Builds on the existing `resolve_prompt_messages` {{SLUG}} interpolation. Backbone
      for user-authored operations/agents. Sequence right before agents.
- [ ] **MCP server** — expose operations as MCP tools (dependency installed, no code).
- [ ] **Agents** — AgentDefinition, agent_executions, agentic loop.
- [ ] **RAG-ify a curated log slice** — embed failures/AI-runs/publishes into a separate
      retrieval namespace so "what happened yesterday?" is answerable. NOT the whole log.
- [ ] **AI as a top-level main-nav section** (currently a Settings tab).
- [ ] **pgvector** — deferred; migrate from JSON+numpy cosine when scale demands.

## ✅ Shipped (recent sessions)
RAG Ask page + clickable citations · AI usage stats (month-to-date) · auto-embed-on-publish
reaction · Event Log viewer + outcome status dots + filters · nolog via catalog `audited`
flag · event_log prune task + retention setting · quiet httpx/openai logging · "AI Settings"
rename + dedicated AI settings tab · workspace-AI factory fallback (Settings form now works).

## Reference: wired vs cosmetic AI settings
- **Enforced:** enabled · credential_mode · provider/model/secret_ref · budget (daily
  requests + monthly cost).
- **Cosmetic (stored, no effect):** approval_mode · invocation_sources · operation_overrides
  · logging_config · moderation_config · budget.max_tokens_per_request.

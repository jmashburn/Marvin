# AI Subsystem — Backlog & Musings

Captured from working sessions. Grouped by effort. (The original AI-settings build plan
that lived here is shipped — replaced with the live backlog.)

---

## 📍 STATE OF PLAY (updated 2026-07-20)

**Where we stand: the platform is built; the frontier is capability depth + polish.**
67 backlog items shipped, 41 open. The open ones are mostly *depth* (make Marvin do more) and
*correctness debt* (settings that store-but-don't-enforce), not missing foundations.

### Solid ground — shipped & verified
- **AI core:** provider abstraction · operations registry · **agent loop with tools** · RAG · embeddings.
- **Context-aware assistant (A–E, all this week):** per-page grounding · real context block into
  the agent (proven: reviews cite real content with 0 tool calls) · conversation memory · entry
  AI menu + per-field improve · **tone register** (persona vs work-product split) · agent timeout budget.
- **Automation engine (Flavor B):** triggers T1–T5 (event · schedule · chat/chained/on-error ·
  MCP · incoming webhook) · entry actions (publish/unpublish/archive/restore) · set-based target
  selector + dry-run · execution audit tables.
- **External MCP servers:** end-to-end, agent-wired, allowlist-gated.
- **The safety keystone:** `invocation_sources` (source ∩ workspace policy) + per-op `min_role`.
- **Migration workflow (this session):** autogenerate un-broken (was JSONB, not the tool) ·
  all 44 models visible to alembic · `AUTO_MIGRATE` review gate · timestamp/NOW() portability.

### The frontier — the genuinely interesting open work (biggest leverage first)
1. **Attach/create write tools** — the top capability gap. Blocked by 4 *structural* things
   (junction write-back grammar · replace-all repo semantics · context can't see candidates ·
   banner can't render attachments). See "Deferred to next pass" below. This is what makes
   "add a hero image" / "create and attach a resource" possible.
2. **Cascading prompts (Site→Collection→Entry-type→Entry)** ⭐ — the *voice* backbone (Phase 8).
   Fixes "drafts sound generic," and is the substrate for user-authored operations. Note axis-C
   of the three-tone model — distinct from the register (axis-B) already shipped.
3. **Autonomous scheduled agent** ⭐ — the same agent loop the bubble uses, driven by cron. The
   pieces exist (agent loop + scheduled tasks + `run_workflow`); this wires them.
4. **Tagging system** — one shared vocabulary across entries/assets/resources (generate-tags
   already stages into `metadata_json.tags` as a placeholder awaiting this).
5. **Compose-entry-from-brief** ⭐ — the flagship demo, now that grounding + register exist.

### Correctness / trust debt — "looks done, isn't"
- **Cosmetic AI settings** (stored, no effect): `moderation_config`, `operation_overrides`,
  `budget.max_tokens_per_request`. `approval_mode` is now *mostly* real (writeback outcome is
  surfaced) but still not enforced everywhere.
- **54 of 122 `EventTypes` are never emitted** — the catalog over-advertises. Cheap test would pin it.
- **Content-model data quality** (from the 2026-07-20 audit, not yet actioned) — see new item below.
- **gemma4 agent returns empty at 4096 tokens** — local models not yet viable for the agent (see E).

### Papercuts worth a sweep
Workspace Providers UI missing · per-model tool capability (allow chat-only models to degrade
gracefully) · OAuth for MCP servers.
_(2026-07-20 polish pass cleared: `max_tokens_per_request` now enforced · `/run` enabled-check
was already fixed · dev-data fixed: 15 legacy `published_at` backfilled, `value-bane`→`value-band`
slug. axis-B UI = next.)_

---

## ▶ ACTIVE PLAN — Context-aware Marvin bubble + broader entry AI actions
> Implements the **"Per-page context"** bullet of the ★ North star (below, ~L463) using the
> mechanism it prescribes: pages *declare* a context object, no DOM scraping, route fallback.
> Grounding only — `min_role` + `invocation_sources` stay the permission wall.

**Goal:** on an entry page you can say "review and suggest" and Marvin knows which entry.
Then surface the entry AI actions that already exist but have no UI.

**Decisions (confirmed 2026-07-20):** scope = context + read/review actions (no attach/create
this pass) · agent/operation writes **respect `approval_mode`** and stage into `suggestion_json`
· conversation memory **is** in scope (single-turn breaks "review and suggest" → "do #2").

**Findings that shaped it:**
- `AIAgentRequest` **already accepts** `entity_type`/`entity_id` (UUID *or* slug, resolved
  server-side) — `schemas/group/ai_execution.py:66-76`. The frontend never sends them
  (`capabilities.ts:129-133` posts only `{message, source}`).
- Grounding today is cosmetic — one line appended to the user message
  (`operations_controller.py:697-698`); the model gets a bare UUID and must call `get_entry`.
- **`ContextBuilder` and the agent loop are entirely disjoint.** Operations get rich
  pre-assembled `OperationContext`; the agent gets nothing. Bridging them is the real fix.
- No conversation memory — `/api/ai/agent` builds `[system, user]` fresh every call.
- `improve-writing` + `generate-tags` are registered and working with **no UI trigger anywhere**;
  only `generate-summary` is reachable from an entry page.
- No `data-entity-*` convention exists yet; `entries/[id].astro` parses the id out of
  `window.location.pathname` ad hoc at lines 1506 and 1531.

### A. Context plumbing (frontend + SDK) — ✅ SHIPPED 2026-07-20 (except A6)
- [x] A1. `AppLayout.astro` — optional `entityType`/`entityId`/`entityLabel` props → stamp
      `data-entity-*` on `<body>`. One convention; replaces ad-hoc pathname parsing.
- [x] A2. Pass from detail pages. **Coverage rule: declare context only where the agent has a
      tool that can resolve that entity** (`get_entry`, `get_asset`, `get_resource`,
      `get_collection`, `get_entry_type`). Grounding a page the agent can't fetch invites
      hallucination instead of preventing it. Declared on all 7 such pages:
      `entries/[id]`, `assets/[id]`, `assets/[id]/view`, `resources/[id]`, `collections/[id]`,
      `collections/[id]/edit`, `entry-types/[id]`.
      **Deliberately NOT declared** (no resolving tool exists): `automation/**`,
      `scheduled-tasks/[id]`, `settings/email/[id]`, `invites/[token]/email`.
      **List pages are out of scope by design** — a list is a *scope*, not an entity, and the
      backend contract requires BOTH `entity_type` and `entity_id`
      (`if body.entity_type and entity_id`). Expressing "browsing entries filtered by
      status=needs_review" needs a separate scope field → Phase B design, not a fill-in.
- [x] A3. New `frontend/src/lib/marvin/context.ts` → `getPageContext()` reads the body dataset,
      with a route fallback. Also `getActiveContext()` (honours suppression) + `contextLabel()`.
- [x] A4. `capabilities.ts` agent skill sends `entityType`/`entityId`.
      **camelCase** — `_MarvinModel` uses `alias_generator=camelize`; snake_case also works via
      `populate_by_name=True`, but camelCase matches the rest of the frontend.
- [x] A5. `Marvin.astro` — context chip ("Entry · Chore Coat") + dismiss (×) that suppresses
      context for the page load. Static markup, so plain scoped styles reach it
      (see memory [[astro-scoped-styles-vs-dynamic-dom]]).
- [x] A6. SDK: `AIAgentRequest`/`AIAgentStep`/`AIAgentResult` types + `AIModule.agent()`; bubble
      moved off raw `fetchApi` onto `runAgent()` in `lib/api/aiBubble.ts` (matches the existing
      `sendChat`/`askWorkspace` pattern). **`node_modules/@inneropen/marvin-sdk` is an npm link
      to `/home/jared/code/MarvinSDK`** (despite package.json pinning the `develop` tag), and it
      resolves through `dist/` — so **`npm run build` in MarvinSDK is required** for changes to be
      visible here. See memory [[marvin-repo-topology]].

**Verified:** `/workspace/entries/abc-123` renders
`<body data-entity-type="entry" data-entity-id="abc-123">`; `/workspace/entries` renders a bare
`<body>` (no context leakage). `astro check` introduces zero new errors — the 4 errors in
`entries/[id].astro` are pre-existing (confirmed identical against HEAD, offset by the +5 line diff).

⚠️ **Do not use `git stash` in this repo** — commit signing is on, so it triggers GPG/pinentry and
hangs. Compare against HEAD with `git show HEAD:<file>` instead.

### B. Real grounding (backend) — ✅ SHIPPED 2026-07-20
- [x] B1. `_agent_context_block()` assembles title / type / status / summary / fields / attached
      assets + linked resources into the system prompt. Handles entry, asset, resource;
      collection + entry_type return None and fall back to the bare-id hint (the agent's own
      `get_collection` / `get_entry_type` cover those).
- [x] B2. Bounded — 400 chars for summary/description, 1200 for fields, lists capped at 8 with
      the true total and `(+N more)` still reported. Empty attachment lists say "none" explicitly,
      so the model can't infer attachments it can't see.
- [x] B3. Tools stay available; the block says so ("This is a summary, not the whole record").
      Any failure (unknown type, missing entity, builder exception) degrades to the old hint —
      grounding can never break a run.

🔐 **Security fix found while doing this:** `ContextBuilder.with_entry` loaded entries with **no
`group_id` check** — unlike `with_asset`/`with_resource`, which both verify it. A caller-supplied
UUID from another workspace would have been loaded into the AI context. This affected the
**existing operations path** too, not just the agent. Fixed + regression test both directions.

🐞 **Latent bug fixed:** `AIOperation` is a plain ABC but declared `input_schema`/`output_schema`/
`writeback` with `dataclasses.field(default_factory=dict)`. Outside a dataclass that never
resolves to `{}` — it leaves a **truthy `Field` object**, so `getattr(op, "writeback") or {}` kept
it and `.items()` raised, swallowed by `_write_back`'s best-effort handler. Every `improve-writing`
run on an entry was silently taking an exception path. Now plain `= {}`, matching the existing
`entity_types: list[str] = []` convention on the same class.

**Verified:** 161 backend tests pass (+15 context/bounding/scoping, +8 operation-prompt).

### C. Conversation memory — ✅ SHIPPED 2026-07-20
- [x] C1. `AIAgentTurn` + `AIAgentRequest.history`; `_bounded_history()` trims newest-first by
      **three** limits — turns (10), total chars (6000), per-turn chars (2000) — and **drops any
      role that isn't user/assistant** (history is a replay, not a system-instruction channel).
- [x] C2. Messages are now `[system, *history, user]`.
- [x] C3. Bubble publishes a plain-text snapshot via new `lib/marvin/history.ts`. Snapshot is
      taken **before** the new user turn is appended, so `history` is exactly "what came before"
      — no off-by-one duplicating the current question. `MarvinResult.text` carries the model's
      plain answer (HTML is useless as memory); falls back to `node.textContent`.
      "Clear" now clears memory too, not just the visible log. SDK gained `AIAgentTurn`.

**Verified:** 153 backend tests pass (+7 history tests: chronological order, newest-kept,
role filtering, blank-drop, per-turn truncation, total-budget trim). `astro check` unchanged at
106 pre-existing errors, none in touched files.

⚠️ **Gotcha hit:** `marvin.services.ai.base` is NOT a module-level import in
`operations_controller.py` — it's imported locally per-method. A class-body annotation
(`-> list[Message]`) therefore NameErrors at import time and takes the whole app down. Keep
`Message` imports local in that module.

### D. Entry AI action menu

**Blocker found while planning (2026-07-20): `improve-writing` cannot be wired as-is.**
`build_prompt` reads `ctx.entry["content"]`, which `ContextBuilder.with_entry` sets to
`str(entry.data_json or "")` — a **stringified dict** (`{'body': 'text…'}`), not prose. It then
returns `improved` as a plain string and declares **no `writeback` map**, so there is no field to
put it back into (`data_json` is structured). Shipping a button for it would be a trap. Fix first.

**STATUS 2026-07-20: ✅ D0–D4 SHIPPED AND VERIFIED IN-BROWSER** (Chore Coat entry, gpt-4o-mini).
Verified: AI menu opens with all 3 items · 3 per-field ✨ Improve buttons attach to prose fields
only (Overview/Description, not the JSON editors) · context chip reads "Entry · Chore Coat" ·
Review & suggest opens the bubble and returns a grounded review · **B1 proven: `tool steps: 0`**
— the model cited the entry's real sections (Overview, Design Intent, Materials, Specifications)
with ZERO tool calls, so the content reached it via the pre-assembled context block · tags flow
verified on BOTH branches (applied under `allow-automatic-update`, staged + banner re-rendered
in place under `suggest-only`). 164 tests pass.

**Two bugs found & fixed during verification:**
1. **Write-back outcome was invisible to clients.** `_write_back` returns `"applied"|"staged"`
   but the call site discarded it, so the UI claimed "review below" even when the entry had been
   auto-applied and no banner existed. Now recorded on `execution.metadata_json.writeback` (also
   auditable) and exposed via `AIExecutionRead.metadata_json`; the editor reports honestly.
2. 🎨 **Astro silently drops a rule whose selector is ENTIRELY `:global(...)`.** Converting the
   banner styles to `:global(.suggestion-banner)` removed them from every stylesheet — rules
   before and after survived, so it is not a parse error. Anchoring on a scoped ancestor
   (`#suggestion-mount :global(...)`) did NOT help either. `Marvin.astro`'s working pattern is a
   **class** ancestor (`.marvin-log :global(.mv-msg)` → `.marvin-log[data-astro-cid-…] .mv-msg`).
   **Resolution: moved the banner styles to `src/styles/global.css`** — the honest home for
   styles targeting JS-created nodes. See memory [[astro-scoped-styles-vs-dynamic-dom]].

**Environment issues found (not code):** the app loads `src/.env` (`BASE_DIR = CWD.parent.parent`),
NOT the repo-root `.env` — symlinked `src/.env -> ../.env` (gitignored). `OLLAMA_BASE_URL` had a
bad `/api` suffix (provider appends `/api/chat`) — corrected. Workspace `provider` was NULL, so
`AI_DEFAULT_PROVIDER` won; confirmed that setting workspace `provider` DOES override the env
default (ran on `gemma4:latest`, then switched back to `gpt-4o-mini`).

**Superseded note (kept for history):**
`astro check` unchanged at 106 pre-existing errors (the 4 in `entries/[id].astro` predate this).
Runtime curl verification is impossible — an unauthenticated request renders the error branch, so
the toolbar/menu never mount. **Needs a logged-in browser pass** on a real entry to confirm:
menu opens, per-field Improve buttons attach to the right fields, tags staging re-renders the
banner in place, and Review & suggest opens the bubble.
Known rough edge: `aiToast` writes to `#ai-summary-status`, which sits next to the Summary field —
feedback for an Improve action on a field far down the page appears off-screen. Wants a
per-field status line or a floating toast.

- [x] D0. **Make `improve-writing` field-scoped** (backend). Accept `input.text` (the prose to
      improve) and `input.field` (which field it came from, for the UI). `build_prompt` uses
      `input.text` when given, else falls back to today's behaviour so existing API/MCP callers
      don't break. Stays writeback-free — suggestion only; the UI fills the field for review.
      **Decision:** surfaced as **per-field ✨ Improve buttons** (Description + each long-text
      field in the entry-type schema), mirroring how Summary already works — not a menu picker.
- [x] D1. Entry AI menu on `entries/[id].astro` — one `✨ AI` menu for *entry-level* actions:
      Generate summary · Generate tags · Review & suggest. Field-level actions (Summary generate,
      per-field Improve) stay inline next to their field.
- [x] D2. Wire `generate-tags` — pass current tags as `existing_tags`; it has
      `writeback = {"tags": "metadata_json.tags"}` so under `suggest-only` it **stages**. UI must
      say "staged for review" and surface the suggestion banner (banner already understands
      `metadata_json.` targets), not claim it applied.
      **Decision:** re-render the banner **in place** (fetch the entry's suggestion, no reload) —
      an auto-reload would silently discard unsaved edits elsewhere in the form.
- [x] D3. "Review & suggest" → dispatch a `marvin:ask` CustomEvent; `Marvin.astro` listens,
      opens the panel, prefills and submits. Gives any page a clean way to drive the bubble
      without a global — the bubble currently exposes no public API.
- [x] D4. Preserve `aiEditorEnabled` gating. Also drop the ad-hoc
      `window.location.pathname.split('/').pop()` id parsing (lines ~1506/1535) in favour of the
      `data-entity-id` the layout now stamps.

### Verification
- [ ] Backend tests: grounding block assembled per entity type; history bounding truncates.
- [ ] Manual: entry page → "review and suggest" with no entity named in the message.
- [ ] Manual: follow-up "do #2" resolves against the prior turn (proves memory).
- [ ] Manual: `generate-tags` under `suggest-only` lands in the suggestion banner, not applied.
- [ ] Regression: `/api/ai/tools` + MCP projection unchanged; bubble still works off an entry
      page (no context → current behaviour).

### Deferred to next pass — attach/create is blocked by 4 structural gaps (documented so they
### aren't rediscovered)
1. Write-back grammar understands only a scalar column, `data_json.<key>`, or
   `metadata_json.<key>` (`_write_back`/`apply_fields`). **No target form can express a
   junction-table row** — "attach asset X as hero" is inexpressible today.
2. `repos.entries.update(asset_attachments=...)` is **replace-all** — a naive attach deletes
   every existing attachment. Needs append-oriented repo methods.
3. `ContextBuilder.with_assets` drops junction `role`/`position` and returns only
   already-attached assets — the model can't discover candidates or reason about placement.
4. The suggestion banner renders only scalar/`data_json`/`metadata_json` diffs; a staged
   attachment would show as raw JSON.

Also deferred: `create_resource` (+ attach), `propose_entry_changes` general write tool.

### E. Tone register (axis B) + agent timeout budget — ✅ SHIPPED 2026-07-20
- [x] **E1. Tone register.** `AIAgentRequest.register` = `auto | professional | playful`, resolved
      by `_register_clause()`. **`professional` WITHHOLDS the persona entirely** — that's the
      mechanism. The previous fix only *asked* the model to compartmentalise, which small models
      ignore. `auto` (default) keeps persona-for-framing + plain findings; `playful` applies the
      persona unscoped. Unknown values fall back to `auto` rather than erroring.
      The entry editor's "Review & suggest" sends `professional` via the `marvin:ask` detail;
      the register is **one-shot** (consumed per run) so a typed follow-up isn't silently affected.
      **Verified live:** review went from *"\*sigh\* Here we go again… make it slightly less dull"*
      → *"Here are specific suggestions… Current: '…' Improvement: '…'"* (also markedly more
      specific), while free-text chat immediately after still answered in persona. +9 tests.
- [x] **E2. Agent timeout budget.** `HttpClient.request/post` accept a per-request `timeout`
      (still clamped by the now-static `HttpClient.MAX_TIMEOUT` = 120s); `AIModule.agent()`
      defaults to `AGENT_TIMEOUT_MS` = 120s. The client-wide 30s default is unchanged — only the
      agent, which is multi-step and can run minutes on a local model, gets its own budget.
      **Verified live:** a `gemma4:latest` review **completed in 102.3s**; the identical request
      previously died at *"Request timeout after 30000ms"* while the server kept working.

⚠️ **New finding (not a timeout issue):** that gemma4 run completed but returned an **empty
answer** at exactly **4096 total tokens** — looks like a token/context ceiling (the grounding
block + history + tool schemas may exceed what gemma4 can carry, or `num_predict` is capping it).
Worth investigating before recommending local models for the agent. Backlog.

## ▶ ACTIVE PLAN — Flavor B: user-configurable orchestration (event → conditions → actions)
> The two automation "flavors" (see memory [[ai-automation-flavors]]):
> **Flavor A = developer-defined reactions** (hardcoded listener classes in `_get_listeners`;
> SHIPPED — auto-embed-on-publish). **Flavor B = user-configurable orchestration:** a workspace
> admin *declares* automations as data — a trigger event, a conditions matcher, and an ordered
> `actions` pipeline (steps pass data via `$event.*` / `$previous.*`). One generic listener loads
> and runs those DB rows. Flavor B is the **linear, admin-wired** sibling of the agentic loop
> (the ⭐ scheduled-agent) — same op registry + `invocation_sources` gate, deterministic control flow.
>
> **Design (grounded in existing primitives):**
> - **Data** — one model `WorkspaceAutomationModel` (mirrors `WorkspaceMcpServerModel`):
>   `group_id, name, enabled, definition JSON, created_by`, uq(group_id, slug). The `definition` is
>   `{ trigger:{event}, conditions:[{field,op,value}], actions:[{kind, ...}] }`.
> - **Trigger** — an `EventTypes` value the bus already emits (slice: `entry_published`).
> - **Conditions** — small matcher over the event payload/context: ops `eq|neq|contains|exists`.
>   No match → the automation no-ops.
> - **Actions** — ordered pipeline; `kind` routes to a real primitive: `operation` → OPERATION_REGISTRY
>   (slice), later `handler` → TaskHandlerRegistry (e.g. `request_site_rebuild`), `webhook` → WebhookPublisher.
>   `$event.*`/`$previous.*` interpolation threads data forward; optional `write_back` reuses the op's
>   `writeback` map.
> - **Engine** — `AutomationReactionListener(EventListenerBase)` added to `_get_listeners`, next to the
>   Flavor A listeners. Loads the group's ENABLED automations whose trigger matches → evaluates
>   conditions → runs actions in order with a `{event, previous}` context. Every op/handler call is
>   stamped **`source="automation"`** (NEW invocation_source) so the same gate protecting MCP/agent
>   protects this. Logs an `AIExecutionModel(trigger_type="automation")` per action for the Event Log.
> - **Guardrails** — deny-by-default (disabled row / op not allowed for `automation` source = no run);
>   **loop-guard** (slice: automation-origin events carry `integration_id="automation"` and the listener
>   skips them; a proper reaction-depth/provenance field is required BEFORE enabling `entry_updated`
>   triggers or publish actions); `max_actions` per automation; a **Test/dry-run** (run conditions +
>   actions with write-back suppressed) — mirrors the MCP server "test" button.
> - **UI (later phase)** — an Automations settings page (same kit as ai-mcp-servers.astro): master
>   switch, automation cards (trigger → condition summary → action chips), enable toggle, edit, delete,
>   Test. Guided authoring form v1 + raw-JSON fallback.
>
> **Flavor B vs the ⭐ scheduled-agent:** Flavor B = a fixed pipeline an admin wired (deterministic,
> auditable, cheap). Scheduled-agent = the model decides its own steps toward a goal (flexible, costs
> tokens). Same `source`-gating + op registry, different control flow. "Rebuild after publishing
> recipes" is Flavor B; "look at the inbox and do what's needed" is the agent.

### Flavor B — thin vertical slice (THIS build)
`entry_published` → condition `entry.entry_type == X` → ONE action `generate-summary`
(`write_back: entry.summary`). Exercises the whole spine: model · matcher+interpolation · one action
kind · write-back · `source="automation"` gate · loop-guard · Event Log row. Everything after
(more action kinds, multi-step `$previous`, guided authoring UI, CRUD API/SDK) is additive.

- [x] **P0 · Source** — add `"automation"` to `INVOCATION_SOURCES` (base.py). Default-all ops now
      accept it; workspace policy allows unless explicitly disabled.
- [x] **P1 · Model + migration** — `WorkspaceAutomationModel` (`workspace_automations`), registered in
      groups/__init__.py + `Groups.automations` back-ref. Alembic rev down_revision `f7a8b9c0d1e2`.
- [x] **P2 · Matcher** — `services/ai/automation/matcher.py`: `resolve(path, context)`,
      `interpolate(value, context)` (`$event.*`/`$previous.*`), `matches(conditions, context)`. Pure, unit-tested.
- [x] **P3 · Runner** — `services/ai/automation/runner.py`: `run_operation_action(session, group_id,
      action, context, *, user_id)` — resolve provider/model, ContextBuilder(entry), build_prompt,
      `provider.execute_operation`, log `AIExecutionModel(trigger_type="automation")`, apply the op's
      `writeback`. (Reuses factored primitives; unifying the controller onto this runner = follow-up.)
- [x] **P4 · Engine + listener** — `automation/engine.py: run_automations_for_event(...)` +
      `AutomationReactionListener` in event_bus_listener.py, wired into `_get_listeners`
      (skips `integration_id=="automation"` events → loop-guard). Best-effort, never breaks dispatch.
- [x] **P5 · Tests** — matcher (eq/neq/contains/exists + interpolation), model create, listener
      subscribes only to configured trigger, engine runs matching actions (fake runner), skips on
      no-match / disabled / loop-guard. `uv run pytest` green.
- [x] **PROVEN LIVE (2026-07-19)** ✅ — published a bench-note in Mash & Burn Co. → `trigger=automation`
      `generate-summary` completed (gpt-4o-mini, 214 tok) → "First prototype" summary written back.
      Full spine works. (Fixes en route: runner `_resolve_model` platform-mode AppSettings fallback;
      dev DB alembic pointer repointed to `ee87dac68e39` after the regenerated migration.)
**REFRAME (2026-07-19): Flavor B is NOT an AI feature — it's a general workflow engine over the event
bus that works with AI OFF. AI operations are ONE action kind, offered only when AI is enabled.** It
belongs in the existing **Automation** settings section (`/automation/*`: events, webhooks,
notifications, scheduled-tasks, event-log) as **Workflows** — not under AI. So:
- Relocate: `services/ai/automation/` → `services/automation/`; routes `/api/ai/automations` →
  `/api/automations`; SDK `client.ai.automations` → `client.automations`. (Model/table stay
  `workspace_automations`.)
- **Action-executor registry** (mirror OPERATION/TOOL registries): dispatch by `action.kind` →
  `operation` (AI, conditional), `emit_event` (dispatch an internal event → CHAINS reactions),
  `handler` (TaskHandlerRegistry: rebuild/reindex/publish), `webhook` (POST a URL).
- **Reaction-depth loop-guard** now REQUIRED (emit_event can cascade): events carry a depth; refuse
  past MAX_DEPTH. Replaces the interim `integration_id=="automation"` skip.
- `/options` returns all action kinds always; AI operations only when AI enabled.

- [x] **P6a · Backend foundation** — relocate + action-executor registry + 4 executors + depth guard
      + `/api/automations` CRUD + `/options` (AI-conditional). Tests green.
- [x] **P6b · SDK** — `client.automations` module + types (relocated out of `ai`).
- [x] **P6c · Workflows UI** — `/automation/workflows.astro`: guided builder (trigger → conditions →
      actions with the 4 kinds; AI-op dropdown only when AI enabled) + cards/enable/edit/delete +
      raw-JSON fallback + nav card under the Automation section. Runner `estimated_cost_usd` (done).
- [x] **P6d · invocation_sources coupling + UI DONE (2026-07-20)** ✅ — the gate already existed
      (runner + options: policy ∩ op.sources, deny-if-explicitly-false). Made the **policy editor**
      real: a source catalog (`INVOCATION_SOURCE_CATALOG`, 8 sources w/ labels+descriptions) +
      `GET /api/groups/ai-settings/sources`; the AI-Settings editor is now **catalog-driven** (fixes
      the old hardcoded list that had a wrong `scheduledJobs` key and was missing `scheduled`/`agent`/
      **`automation`**/`api`) — submit collects whatever's rendered, so it can't drift. Builder: the
      AI-operation kind shows a linked "turn it on in AI Settings" message when no ops are offered, and
      its dropdown option is disabled (unless the step already is an operation). Verified: 8 sources
      render with correct keys; gate returns 8 ops when `automation` on / **0** when off; normal builder
      path unaffected. SDK `ai.settings.sources()`; drift test. (Marvin, this commit; SDK.)

### Trigger types (generalize how workflows fire — beyond `entry_published`)
`trigger` is now typed: `{type, event?, …}` (defaults to `event`). All types funnel into the same
engine (`run_automation` / `run_automations_for_event`); event types go via the listener, the rest get
their own entrypoint. Full list the user wants: **event · manual · schedule · chained (another
automation) · chat (agent) · mcp tool (project workflow as an MCP tool) · on-error · incoming webhook**.
- [x] **T1 · event-expansion + Manual [Run]** ✅ — `trigger.type`; events widened to entry lifecycle
      (created/updated/published/deleted); `POST /api/automations/{id}/run` + Run button (also the
      test-it affordance); builder trigger-type selector (event/manual). SDK `automations.run()`.
- [x] **⭐ Generalize event triggers to ANY (sensible) event DONE (2026-07-20)** ✅ — both pieces:
      (1) the listener **flattens each event's `document_data` into `event.*`** (via jsonable_encoder,
      snake_case) so `$event.asset_type`/`$event.resource_type`/… conditions fire for non-entry
      events; the curated explicit keys (entry_id/payload/changed_fields) still override. (2)
      `services/automation/triggers.py` — a **curated grouped catalog** (Entries/Collections/Assets/
      Resources/Forms/Entry types = 26 emitted events; internal/audit noise excluded). Listener
      subscribes name-based off it; `/options` returns `triggers` + `trigger_groups`; builder renders
      the event dropdown as optgroups. Verified live (6 groups / 26 options). (Marvin, this commit.)
- [x] **T2 · Schedule** ✅ (2026-07-19) — `trigger.type=schedule` → upsert a `run_automation` ScheduledTaskModel on the
      existing Scheduler (interval/cron); a `RunAutomationHandler`. "rebuild nightly."
- [x] **T3 · Chat / Chained / On-error DONE (2026-07-19)** ✅ — `run_workflow` agent tool (min_role AUTHOR, also projected to MarvinMCP) lets chat run any workflow; engine emits `automation_ran`/`automation_failed`; `chained` + `on_error` trigger types (target a specific workflow or any). 114 tests.
      trigger on it · emit `automation_failed` + on-failure trigger.
- [x] **T4 · MCP tool DONE (2026-07-19)** ✅ — `mcp` trigger type (opt-in) in builder; MarvinMCP `workflowsCapability` projects each enabled trigger.type=="mcp" workflow as `marvin_wf_<slug>` → `automations.run(id)`. MCP build + 126 vitest green. Admin-scoped token required to project.
      external MCP hosts can invoke it.
- [x] **T5 · Incoming webhook DONE (2026-07-20)** ✅ — Model 2 / ingress (memory
      [[incoming-webhooks-ingress-model]]): `POST /api/hooks/{token}` (path token OR Bearer, 512KB
      cap, 202 + `?wait=1`) drops an `incoming_webhook` event on the bus → fans out to ANY subscriber,
      not bound to one automation. Full stack shipped + verified live: model/migration, public
      receiver + ADMIN CRUD `/api/incoming-webhooks` with mint/rotate/revoke token, `incoming_webhook`
      trigger (`_TRIGGERS` + `_trigger_matches` + `$event.payload.*`), SDK `client.incomingWebhooks`,
      management page (Settings→Automation→Incoming Webhooks) with editable **test payload**, builder
      trigger option. (Marvin ba79f73/b1b67f2, SDK 85e139b/5cc4981.)

### Flavor B — hardening backlog (from `docs/WORKFLOW_STATE_REVIEW.md`, 2026-07-19)
> Review of the built engine against `docs/WORKFLOW_SUGGESTIONS.md`. The skeleton is
> proportionate and shouldn't be redesigned; these are the gaps that make it *trustworthy*.
> Ordered by unlock, not by feature area.

**H0 · Foundation — do before any new action types**
- [x] **⭐⭐ Extract `services/entries/` DONE (2026-07-20)** ✅ — `services/entries/EntryService`
      owns `create/update/apply_fields/apply_suggestion/delete` (+ `set_status`) **and** the emit.
      Status transitions (published/unpublished/archived/restored) now fire by construction from any
      caller, in the `entry_updated`-first order the embedding reaction relies on; `reaction_depth`
      threaded. Controller delegates its write methods (−~230 lines); `runner._apply_writeback` routes
      through it — **which fixed the latent bug**: the old write-back emitted a bare `entry_updated`,
      so a write-back that flipped status silently skipped `entry_published` and chained automations
      stopped firing. Verified live: write-back publish now fires entry_published → automation_ran.
      (Marvin 7102908.)
- [x] **⭐ `changed_fields` / `before` / `after` on `EventEntryData` DONE (2026-07-20)** ✅ —
      EntryService computes the diff on update (it already had old + new from the extraction) over the
      tracked scalars (status/title/slug); before/after carry **only the changed fields**, so
      `event.after.status == needs_review` reads as "status changed to needs_review". Exposed in the
      engine context ($event.changed_fields/before/after) + advertised in the condition catalog;
      works with existing operators. Verified live. (Marvin 2cac535.)
- [x] **Validate `definition` with a Pydantic discriminated union DONE (2026-07-20)** ✅ — first an
      advisory `validate_definition()` + `POST /api/automations/validate` + per-trigger condition-field
      catalog + live warning banner (catches the entry.*-under-webhook silent no-op; Marvin 04447cc,
      SDK d39396c), then the full **discriminated-union-as-source-of-truth** (see H4 ⭐): structural
      validation now gates create/update and the JSON Schema ships in `/options`.

**H1 · Observability — makes the thing debuggable**
- [x] **⭐ `automation_executions` + `automation_action_executions` tables DONE (2026-07-20)** ✅ —
      every run + every step (per target×action across a fan-out) recorded. `ExecutionRecorder`
      (NullRecorder default keeps the engine unit-testable) wired at the 3 run sites (listener, /run,
      scheduled handler); truncated output snapshots, no secrets. Read endpoints + SDK
      `automations.executions()/execution()` + a "Runs" history panel on each workflow card (status,
      targets, N✓/M✗, duration → expand to per-step records). Also **lifted the target cap 25→250**
      now that runs are inspectable. Verified live. (Marvin 9ea65fa, SDK 8bc932a.)
- [x] **Correlation id threaded through `dispatch` + promoted to an `event_log` column DONE
      (2026-07-20)** ✅ — one id now ties every event + execution in a causal chain. Done with an
      **ambient scope** (`services/event_bus_service/correlation.py`: a `ContextVar` +
      `correlation_scope`), not a param threaded through 6 executor signatures: whoever roots a chain
      opens a scope and every `dispatch(...)` inside inherits the id (read synchronously at call time,
      so it's baked in even when publishing defers to a bg task). Roots: the automation engine (per
      triggering event — a whole reaction cascade shares the triggering event's id; a manual run mints
      one) and `EntryService`'s multi-event mutations (so `entry_updated` + its transition event share
      one id). `dispatch` gained a `correlation_id` param (explicit override, else ambient, else mint);
      `Event.correlation_id`; a real indexed `event_log.correlation_id` column (migration `930f9ab5902d`,
      +index); publisher persists it; `EventLogRead`/`Summary` expose it; `GET /api/events?correlation_id=`
      + repo filter returns a whole chain. The execution row already carried it — now it reuses the
      triggering event's id instead of minting, so events↔executions correlate. Runs panel shows the
      chain id. Verified live (dispatch → column; A+B in one scope share the id, C outside gets its own).
      6 tests; full suite 286 green. *(Causation id + parent-execution id still deferred — correlation
      alone makes the chain readable.)* (Marvin, this commit; SDK `eventLog.correlation_id` filter.)
- [x] **Snapshot the automation `definition` onto the execution row DONE (2026-07-20)** ✅ —
      `definition_snapshot` JSON column on `automation_executions` (part of the tables above).

**H2 · Honesty pass — cheap, removes user-visible lies**
- [x] **Gate the ~40 advertised-but-dead events DONE (2026-07-20)** ✅ — `_NO_EMITTER` frozenset in
      event_catalog.py forces the 40 EventTypes with no dispatch site to `enabled=False`, so
      `list_event_types` stops advertising subscriptions that can never deliver (site/publishing,
      form-submission, asset attach/detach, backups, approvals, comments, webhook CRUD/delivery,
      api_token, storage_quota, etc.). Enum members kept (no migration risk). (Marvin, this commit.)
- [x] **Add `test_every_catalog_entry_has_an_emitter` DONE (2026-07-20)** ✅ — `tests/
      test_event_catalog.py` scans src for real `EventTypes.X` references and asserts every
      *subscribable* catalog entry has an emitter (+ that `_NO_EMITTER` only hides genuinely-dead
      events). Catches the drift recurring. 3 tests.
- [x] **Fix the false comment at `runner.py:203` DONE (2026-07-20)** ✅ — moot: `_apply_writeback`
      was rewritten to route through EntryService (H0), and its new docstring states the loop-guard
      is the depth counter (not integration_id). The false claim is gone.
- [x] **`/run` checks `enabled` DONE (2026-07-20)** ✅ — `POST /api/automations/{id}/run` now 409s
      on a disabled workflow (consistent with the scheduled path, which already skips disabled); the
      builder's Run button is disabled on disabled cards. (Marvin, quick-win commit.)

**H3 · Expression ergonomics — DONE (2026-07-20)** ✅ *(Marvin, this commit; SDK)*
- [x] **Embedded `${...}` interpolation** ✅ — `interpolate` now substitutes embedded `${path}`
      (stringified) AND a whole `${path}` returns the raw value (type preserved). Bare `$path` still
      works. `"Summary: ${previous.summary}"` interpolates.
- [x] **Named step outputs `$steps.<id>.output.*`** ✅ — the engine records each step's output under
      `$steps.<position>` and `$steps.<id>` (action optional `id`); `$previous` stays as the
      last-output alias. Reordering no longer silently breaks a later reference.
- [x] **`any` / `not` / nesting in conditions + new operators** ✅ — `matches` evaluates
      `{all:[…]}` / `{any:[…]}` / `{not:…}` groups (nestable); a top-level list stays implicit AND.
      Operators added: `in` (list or CSV), `starts_with`, and change-aware `changed` / `changed_from`
      / `changed_to` (key on the diff). Builder shows friendly op labels; groups are JSON-mode.
- [x] **`MAX_ACTIONS` no longer silently truncates** ✅ — `validate_definition` warns when a workflow
      has >MAX_ACTIONS steps (only the first run), and the engine logs when it truncates.

**H4 · Simplifications & ideas worth taking**
- [x] **⭐ Pydantic definition schema as the ONE source of truth DONE (2026-07-20)** ✅ — new
      `schemas/group/automation_definition.py`: a discriminated-union model (triggers on `type`,
      actions on `kind` — one model per registered executor, conditions recursive leaf-or-group, plus
      the target selector). snake_case + `extra="allow"` (the engine reads the raw dict by literal
      key, untouched; models validate, don't re-serialize). From it fall out: (1) **structural
      validation gating the write path** — create/update now 422 on a malformed definition (unknown
      kind/type, missing required, bad literal) where before *zero* validation ran; lenient on extra
      keys so forward-compatible defs still save; (2) **`/validate` returns errors + warnings** —
      structural errors (block) merged ahead of the advisory 'won't match anything' warnings; (3) the
      **definition JSON Schema shipped in `/api/automations/options`** (`definition_schema`) so builder
      + SDK mirror one declaration; (4) SDK types point at the server as source of truth +
      `AutomationOptions.definitionSchema`. **Drift guards**: tests assert `ACTION_MODELS` == executor
      registry and `TRIGGER_MODELS` == validation trigger catalog, so a new executor can't ship without
      its model. Verified live (422 rejects `kind:delete_everything` and doesn't persist; valid def
      still 201s; existing DB automations all validate). 12 tests; full suite 260 green. *Full SDK
      codegen from the schema (vs the aligned hand-written types) deferred as its own follow-up; the
      MarvinMCP `marvin_wf_*` projection takes no structured input, so it's unaffected.* (Marvin, this
      commit; SDK.)
- [x] **`dry_run` as a flag on the engine DONE (2026-07-20)** ✅ — a `dry_run` bool threads through
      `run_automations_for_event` / `run_automation_now` → `_run_targets` → `_run_pipeline` → the
      executor contract. Each executor still gates (authz + source) and resolves its inputs
      (interpolation, slug→id target) but, when dry, returns a preview of what it *would* do instead
      of executing — no AI call / AIExecution row, no entry mutation, no event dispatch, no webhook
      POST (and the secret value is never resolved into the preview). A dry run records nothing (an
      in-memory `CollectingRecorder`) and fires no `automation_ran`; it returns `plan` — the resolved
      per-step preview. Surfaced at `POST /api/automations/{id}/run?dry_run=true` (works on a disabled
      draft), SDK `automations.dryRun()`, and a **Dry run** button on each workflow card that renders
      the plan. Verified live (generate-tags op resolved, executed nothing). 6 tests. (Marvin, this
      commit; SDK.)
- [x] **Allowlist the `handler` action DONE (2026-07-20)** ✅ — `AUTOMATION_ALLOWED_HANDLERS`
      (request_site_rebuild / publish_scheduled_entries / unpublish_expired_entries /
      ai_reindex_embeddings / resync_smart_collections). Anything else — the destructive maintenance
      jobs (remove_orphaned_assets, prune_*), session/invite pruning, and `run_automation` itself — is
      rejected even though it's a valid registry entry, with a message naming the allowlist. Builder
      datalist matches. 4 tests. (Marvin, quick-win commit.) *(New safe handlers must be opted in.)*
- [x] **Per-user authorization at execution DONE (2026-07-20)** ✅ — **definer's rights**: an
      automation's actions now run under its *author's* (`created_by`) current authority, not the
      tripping user's (which stays provenance-only). New `services/automation/authz.py` resolves the
      author's live role (`resolve_authorizer_role`: None→OWNER back-compat, removed/demoted→fail
      closed to 0) and `require_role` gates each action: operations enforce their declared `min_role`,
      `entry`/`emit_event` need AUTHOR, `handler`/`webhook` need ADMIN. Threaded `authorizer_role`
      through the engine (`run_automations_for_event`/`run_automation_now` → `_run_targets` →
      `_run_pipeline` → the executor contract). A denied action fails cleanly and is recorded on the
      execution row (visible in the Runs history), never runs with stale authority. 11 tests. (Marvin,
      this commit.) *Closes the last Flavor B security gap.*

**H5 · Entry action surface** *(thin once H0 lands — deliberately sequenced last)*
- [x] **`entry` action kind DONE (2026-07-20)** ✅ — `publish` / `unpublish` / `archive` / `restore`
      via `EntryService.set_status` (right transition events fire, chains reliable). Targets the
      triggering entry by default or one by slug (`entity_slug`); pairs with the target selector
      ("publish all inbox entries matching X"). Builder op+target fields, validation, recorder label.
      Verified live. `entry.delete` deliberately omitted. (Marvin 153dbd5, SDK 26cbaa4.)
- [x] **`entry.add_to_collection` · `entry.remove_from_collection` DONE (2026-07-20)** ✅ — first
      extracted collection membership into `EntryService.add_to_collection`/`remove_from_collection`
      (idempotent: `added`/`exists`/`removed`/`absent`/`None`; emits `entry_added_to_collection` /
      `entry_removed_from_collection` only on an actual change; resolves the collection by slug/name/id
      in the workspace). The entry controller now delegates to it (dropped ~90 lines of inline junction
      + event code, plus a dead helper + 3 unused imports). Then the `entry` action gained the two ops
      (targets a collection via `collection_slug`/`collection_id`, may be a `$event.*` template);
      pairs with the target selector ("add all drafts matching X to Featured"), honors authz (AUTHOR),
      dry-run previews without mutating, and structural + advisory validation cover them. Builder op +
      collection field (revealed only for membership ops). Verified live (validate clean; missing-
      collection warns; create 201; builder toggles). 6 DB-backed EntryService tests + 7 action tests.
      (Marvin, this commit; SDK.)

**H6 · Also shipped this session (2026-07-20) — beyond the review's list**
- [x] **⭐ Set-based target selector ("FROM" clause) + dry-run preview** ✅ — a workflow can carry a
      `target` selector (query: entry_type/status/text/collection/has_*) that SELECTS the entities to
      act on instead of only the trigger's one; the engine fans the pipeline over each match (capped
      MAX_TARGET_ENTITIES, now 250), and conditions become a true WHERE over the set. Query values may
      be `$event.*` templates. `POST /api/automations/preview` resolves the target (total/capped/
      WHERE-matched) WITHOUT running anything; builder "Run on a query of entries" section + Preview
      matches. This is the H4 `dry_run` idea, delivered target-first. (Marvin 8e927bb, SDK 4715a42.)
- [x] **Target entries by slug in actions (`entity_slug`)** ✅ — operation + entry actions can target
      an entry by human-readable slug (resolved at run time), not just id/`$event.entry_id`. (Marvin
      0b6b780, SDK 1aa26a0.)
- [x] **Context-aware condition builder + coherence validation** ✅ — see the PARTIAL note in H0
      (validate_definition + per-trigger field catalog + live warning banner).

**Explicitly NOT doing** (agreeing with the suggestions doc, emphatically): branching, loops,
`delay`/`wait_until`/`wait_for_event`, approval gates, native Slack, an internal notification system,
the outbox pattern, event sourcing, a visual node editor. Each is either n8n's job or needs persisted
mid-flight workflow state — the largest complexity jump available for the least return. Also skipping:
normalizing conditions/actions into tables (JSON + Pydantic is right, the joins aren't justified) and
automation versioning as infrastructure (the definition snapshot in H1 covers it).

## ▶ ACTIVE PLAN — External MCP servers, wired into the agent + UI (thin vertical slice)
> The north-star "connect external MCP servers" plugin layer. Decided posture (2026-07-19):
> **HTTP/SSE transports only, deny-by-default tool allowlist, ADMIN/OWNER-managed.** stdio
> (local subprocess — must be installed on the host) parked for a later self-hosted pass.
> Goal of THIS slice: an admin registers ONE HTTP MCP server in AI settings, tests it
> (tools/list), allowlists specific tools, enables it → those tools appear in the Ask Marvin
> agent and run, gated. Proves model→client→agent→UI end-to-end before broadening.

- [x] **P0 · De-risk the async bridge** ✅ — added `mcp[cli]>=1.28.1`. Spike proved a SYNC function
      can `asyncio.run` a streamable-HTTP MCP client through `initialize`→`list_tools`→`call_tool`
      (add(2,3)=5, BRIDGE_OK). Safe because the agent endpoint is sync `def` (threadpool, no running
      loop) → `asyncio.run` works; if a caller is ever async, `await` instead. Pattern for P2:
      `async with streamablehttp_client(url) as (r,w,_): async with ClientSession(r,w) as s: ...`.
- [x] **P1 · Data model** ✅ — `WorkspaceMcpServerModel` (`workspace_mcp_servers`: group_id, name,
      slug, transport['http'|'sse'], url, secret_ref, enabled=false, `allowed_tools` JSON → DENY by
      default, created_by, uq(group_id,slug)) + `Groups.mcp_servers` back-ref + registration.
      `external_mcp_enabled` master switch (default false) on ai_settings. Migration `f7a8b9c0d1e2`
      (dodged a revision-id collision with an existing `e5f6a7b8c9d0`). Applied to dev DB; 86 tests
      pass (schema rebuilds from migrations in conftest → validates it). Bonus: fixed a latent
      `updated_at`→`update_at` bug in get_entry/get_asset (base col is `update_at`; `updatedAt` was
      silently null).
- [x] **P2 · MCP client service** ✅ — `services/ai/mcp_client.py`: sync `list_tools`/`call_tool`
      (+ `list_server_tools`/`call_server_tool` over a model row) wrapping the async SDK via
      `asyncio.run` + hard timeout; auth `Bearer` header from `resolve_secret(secret_ref, group_id)`;
      HTTP + SSE transports. Failures → `McpClientError` (unreachable) or `(text, isError=True)`
      (server-side tool error) — never crash the agent. Verified live vs the spike server: list +
      call(add,40,2)=42, unknown-tool + bad-url both handled. Only connects/calls — gating is the
      caller's job.
- [x] **P3 · API + SDK** ✅ — `McpServersController` CRUD at `/api/ai/mcp-servers` + `POST /{id}/test`
      (connect → tools/list preview for the allowlist UI), ADMIN/OWNER gated, http/sse validated
      (stdio 422'd), auto-slug, deny-by-default. SDK `platform.ai.mcpServers` (list/get/create/
      update/delete/test) + camelCase types, built (SDK 94 green). Live e2e vs the spike server
      through :8080: create→test(["add"])→patch(allowlist+enable)→delete all pass; `/test` proves
      the async client works inside a real FastAPI request.
- [x] **P4 · Agent wiring** ✅ — `_external_mcp_tools()` in the controller: gated on
      `external_mcp_enabled`, for each ENABLED server `list_server_tools` → filter to `allowed_tools`
      → wrap as `AgentTool` named `mcp__<slug>__<tool>` (≤64), run() → `call_server_tool` (errors →
      JSON, non-fatal). A dead server is skipped (logged), never fatal. `_build_agent_tools` extends
      with these. Verified against the spike server with a stand-in self: switch-off→0, allowlisted→
      `['mcp__spike__add']` and run(2,3)="5", empty-allowlist→0 (deny-by-default). Internal-agent
      only (not re-projected via MarvinMCP). 86 tests green.
- [x] **P5 · Settings UI** ✅ — exposed `external_mcp_enabled` in the ai-settings schema
      (read+update; generic setattr applies it — live PATCH round-trip verified). New page
      `settings/ai-mcp-servers.astro` (linked from the AI settings tab): master switch, add-server
      form (name/url/transport/optional secret), and per-server Test (renders tools/list) →
      checkbox-allowlist → Save (PATCH allowed_tools+enabled) → Delete. Third-party warning shown.
      Uses `fetchApi` directly (frontend doesn't need the SDK). Typechecks clean; 86 backend tests
      green. (Frontend needs a rebuild/restart to serve the new page.)
- [ ] **P6 · Verify e2e** — stand up a trivial local HTTP MCP server; register → allowlist one tool
      → ask Marvin → confirm the external tool runs and returns in the bubble.

Security baked in: deny-by-default allowlist · ADMIN-only management · secret_ref auth · master
kill switch · per-call timeout · HTTP/SSE only. Later brainstorm: whether to add stdio (needs the
server binary installed on the Marvin host — great self-hosted, risky hosted/multi-tenant).

**Shipped this session (beyond P0–P5):** page uses the SDK end-to-end (`lib/api/aiMcpServers.ts` →
`platform.ai.mcpServers`/`platform.ai.settings`; added `externalMcpEnabled` to SDK types) — no
hand-rolled fetchApi; inline **Edit** on server cards; **idempotent Delete** (404=already-gone →
removes card, fixes "it deleted but said it didn't"); **`{{SLUG}}`-tolerant** secret resolution in
`mcp_client.headers_for_server` (users reach for the `{{X}}` variables form); unwrapped MCP errors
("HTTP 401 — requires authentication" not "TaskGroup"); tool descriptions clamped to 2 lines +
hover; master switch dims/disables the add+manage sections when off. Verified live: Cloudflare
`mcp.cloudflare.com` accepts a static API token as Bearer → `docs/search/execute`.

**MCP follow-ups (captured):**
- [x] **P6 · agent capstone** ✅ — live `POST /api/ai/agent` "search the Cloudflare docs for Workers
      KV" → step trace shows `mcp__cloudflare_mcp__docs {"query":"Workers KV"}` and a grounded answer
      (8019 tokens, complete). Bubble → external MCP proven end-to-end with a real LLM.
- [x] **Tighten tool descriptions to 1 line** ✅ — `.desc` clamp 2→1 line, full text on hover.
- [x] **Bug: system scheduled tasks emit Event with workspace_id=None** ✅ — `Event.workspace_id`
      made `UUID4 | None = None` (matches `user_id`'s "None for system events"); Prune/AI-prune/
      Resync system tasks now dispatch their trigger. 86 tests pass. (was: check_scheduled_tasks.py:62)
- [ ] **OAuth for MCP servers** — Cloudflare's hosted servers accept a static API token (works now),
      but OAuth-only servers (`www-authenticate: realm="OAuth"`) need the MCP authorization flow
      (browser sign-in + token storage/refresh). Bigger feature; unblocks the OAuth-gated hosts.
- [ ] **Auth-secret UX** — the field takes a WorkspaceSecret *slug*; consider inline "create secret"
      + a clearer hint (the `{{ }}` form is now tolerated, but the two-step still surprised the user).

- [ ] **⭐ Scheduled task runs an MCP agent (autonomous agent)** — the SAME agent loop the bubble
      runs, triggered by the scheduler instead of a user (`"scheduled"` is already a first-class
      `invocation_source`). E.g. a **"Rebuild site"** task runs the agent with a goal. Part of the
      grand e2e. Pieces:
      1. **Extract the tool-builder** out of `operations_controller` (`_build_agent_tools` +
         `_external_mcp_tools`) into `services/ai/agent_tools.py`:
         `build_agent_tools(session, group_id, provider, *, source, role, user=None)` — shared by
         the bubble endpoint AND a scheduled handler (also de-fattens the controller).
      2. **`RunAgentHandler(ScheduledTaskHandler)`** in `handlers/ai.py` (template:
         `ReindexEmbeddingsHandler`). `config={goal, model_override?, max_steps?, entity_type/id?}`
         → resolve provider/model, `build_agent_tools(source="scheduled", role=OWNER)`,
         `run_agent_loop`, log `AIExecutionModel(operation_slug="agent", trigger_type="scheduled")`,
         emit events. `task_type="run_agent"`.
      3. **No-user context** → gate on the workspace allowing the `"scheduled"` source + run with a
         service/OWNER role (the admin who created the task is the authz point). Thread
         `source="scheduled"` so compose/operations the agent calls are stamped/gated correctly.
      4. **The "rebuild" capability = a TOOL the agent calls** — DECISION: an external **MCP deploy
         tool** (e.g. Cloudflare Workers/`execute`, or a CI/deploy MCP) vs a **native Marvin rebuild
         action** exposed as a registry tool (`rebuild_site`). Shapes what the agent invokes.
      Guardrails matter MORE unattended: tool allowlist · `max_steps` · scheduled source gate ·
      optional dry-run/approval for first runs. See [[marvin-core-tool-registry]],
      [[marvin-agent-capability-architecture]].

## 🍂 Low-hanging
- [ ] **Content-model data quality** (from the 2026-07-20 audit of Mash & Burn Co. — never actioned).
      Concrete defects, not model design: **`value-bane` entry-type is a typo of `value-band`**
      (the collection is `value-band`) affecting 8 value entries · **15 entries have
      `status=published` but `publishedAt=NULL`** (breaks date sorting / feeds — likely a publish
      path that never stamped the timestamp; check the workflow, don't just backfill) · a leftover
      `Test` collection holding a stray `hero`-typed entry with placeholder metadata · content typos
      ("HSow shipping", "AA long-skirted"). Also observed: page-type sprawl (`page` vs
      `page-with-navigation` vs `about`) and navigation modeled two ways. Worth a cleanup pass +
      possibly a guard so published-without-timestamp can't happen again.
- [x] **axis-B register: per-workspace default + UI** ✅ (2026-07-20) — `default_register` column
      on `workspace_ai_settings` (migration was a clean one-line autogenerate — the payoff from
      un-breaking it) + "Default register" select under the persona textarea in
      `settings/ai-workflow.astro`. Resolution: explicit per-call register (e.g. "Review & suggest"
      → professional) > workspace `default_register` > "auto". `AIAgentRequest.register` changed
      `"auto"`→`None` so the server can tell "unset" from "explicitly auto". SDK `AISettings`
      gained `defaultRegister`. Verified: precedence + clause output correct; 208 tests.
      Note: `/chat` still applies persona unscoped (chat IS conversation) — left as-is, decided.
      Benign pre-existing warning: `register` field shadows a pydantic parent attr; round-trips
      fine, not worth a public-field rename.
- [x] **Marvin session memory** ✅ — the Ask Marvin bubble transcript now PERSISTS across page
      navigations. `sessionStorage` per tab (`marvin.transcript`), restored on load; only committed
      turns are stored (never the transient "thinking…" placeholder — committed via `commitReply`
      when the answer resolves); greeting is flavor-only and not persisted so it doesn't restore stale.
      Added a **Clear** control in the header (hidden until there's a real turn) + a 60-turn cap
      (quota + scrollback guard). Client-only, no backend. (Marvin.astro.)
- [x] **`/tools` bubble command** ✅ — answers "what can Marvin reach right now": lists the tools the
      `/agent` loop actually binds for the caller (built-in registry + compose + allowlisted external
      MCP, role-filtered), grouped Built-in vs per-server. New `GET /api/ai/agent/tools` (reuses
      `_build_agent_tools`, can't drift), SDK `ai.tools.listAgent()` + `AgentToolInfo`, frontend
      `lib/api/aiTools.ts` (SDK, no fetchApi) + `noArg` capability flag. `/help` stays about typed
      commands; `/tools` surfaces the enabled toolset.
- [x] **Resync SDK generated types** ✅ — schema regenerated off the live backend (recipe_json +
      compose-entry), `platform.ai.operations.composeEntry()` added, vitest green (89). Casts in
      frontend entryTypes.ts **dropped** — required the backend entry-type alias fix (camelCase-first
      AliasChoices + nullable flags so openapi-typescript marks them optional; repo coalesces
      None→defaults). entryTypes.ts now type-checks clean. (Marvin c682eec, SDK 6909a74.)
      *Same-pattern follow-up:* CollectionCreate in collections/new.astro has the identical
      defaulted-required issue.
- [ ] **Recipe UI placement** (thought, not mandate) — v1 recipe editor lives in the entry-type
      form. The admin "Custom Fields" / "Templates" placeholders under Entries could become a
      dedicated recipe builder (structured assets/resources/enrichment) instead of raw JSON.
- [x] **`AI_ALLOW_WORKSPACE_CREDENTIALS` platform toggle** ✅ — platform admin can
      allow/disallow workspaces using their own AI keys (credential_mode=workspace);
      factory fallback so the Settings form actually enables workspace AI.
- [x] **Wire `logging_config`** ✅ — `_logging_policy()` honors log_inputs/log_outputs (defaults
      preserve behavior: outputs logged, inputs not) in execute + compose; input_json now stored
      only when opted in. Daily `prune_ai_executions` task (per-workspace retention_days, else
      AI_EXECUTION_RETENTION_DAYS). Bonus: trigger_type now records the real source. (eabf648)
- [x] **`entry_updated` → re-embed** ✅ — extended AIEmbeddingReactionListener; re-embeds only
      when a *published* entry that's *already indexed* changes (gate avoids draft-save noise and
      the publish-transition double-embed). 9 tests. (8bde56f)
- [x] **Surface the `audited` flag per-event in the Events UI** ✅ (read-only) — "Audit coverage"
      panel lists non-audited types. Toggle deferred: no backend surfaces `audited`. **Backend gap
      to close:** add `audited` to `GET /api/event/types` + a PATCH to update it (and move the
      catalog audit policy to persistent storage, it's an in-code list today). (7c7555b)
- [x] **Event Log**: dedicated status column ✅ — status pill (dot + label) in its own column. (7c7555b)
- [x] **"Ask Marvin" bubble — v1** — floating capability-registry assistant on every
      page; v1 skill = Ask (RAG) + /help. Add a skill = push a Capability. → grows into ★ Marvin.
- [x] Ops: create a daily `prune_event_logs` scheduled task ✅ — new system-task seeder wired into
      startup lifespan (idempotent, group_id=NULL, interval 86400s). (7b514a3)

## 🌳 Medium / Features
- [x] **Route entries into collections via smart rules** ✅ (declarative half done) — smart
      collections are now REAL (materialized-via-reactions): `smart_rules` (entry_types + statuses,
      match all|any) evaluated by a reaction on entry create/update/publish/… → EntryCollections
      rows; reads/renderers-core unchanged; daily reconcile safety net. `tags` reserved as a
      forward-compatible rule dimension. (7c3abe1) SDK: `collections.createSmart` + typed
      `SmartCollectionRules` (d141bbe). **Remaining follow-ups:**
      · [x] **compose emits `entry_created`** ✅ (cc4fb0c) — composed entries first-class to all
        reactions; verified a composed draft lands in a smart "Drafts" (statuses:[inbox]) collection.
      · **smart-rule builder UI** (rules are set via the collections API; no editor yet).
      · **mixed smart+manual** collections (MVP is smart XOR manual — smart membership is fully derived).
      · optional **imperative recipe.collections** pins as an escape hatch (superseded for the
        orphaning problem by smart rules).
- [ ] **Schema-driven typing for resources? (assets: probably not)** — TODAY: only *entries* use
      entry_types. **Assets** have no type (mime_type + metadata blob) — leave as-is; a lightweight
      asset-kind + metadata schema is low value. **Resources** carry a plain `resource_type` STRING
      (supplier/tool/…) with no per-type fields — the real candidate. Options: (a) give resources
      their own schema-driven ResourceTypes mirroring entry_types (supplier→{url,contact}, tool→{brand});
      (b) unify — a resource becomes an entry of a resource-ish entry_type (ties to "forms fold into
      entry_types"). Decision deferred; leaning (a) for structured resources without collapsing the
      simpler model. Feeds recipe resource-extraction (entities→typed Resources).
- [ ] **Compose-entry-from-brief** ⭐ (the flagship demo). An AI op that takes an
      `entry_type` + image(s) + a short brief, uses the **entry_type's field schema as the
      LLM output schema**, and creates a **draft** entry (image attached, not generated).
      Human/Marvin reviews → set publish → existing `entry_published` → rebuild pipeline →
      live. Draft-first = `approval_mode` in practice. Front doors: Marvin skill + API
      endpoint + MCP tool (MarvinMCP already does the publish half via the SDK).
- [ ] **Write-back step → make `approval_mode` real.** After an op returns output_json:
      field-mapping per op (summary→entry.summary, tags→entry.tags, …), apply gated by
      approval_mode × entity status (draft vs published), emit an event (re-triggers
      auto-embed), editor accept/diff UX. `operation_overrides` slots in here.
- [ ] **Entry-type authoring "recipe"** ⭐ — a NEW `recipe_json`/`authoring_json` column (do NOT
      reuse `capabilities_json` — that already holds publishable/submittable/routable behavior
      flags consumed by publishing + marvin-renderers-core; `rendering_json` = layout/component).
      Fields today: schema_json=form · rendering_json=render · capabilities_json=behavior flags.
      recipe_json is the authoring contract beyond fields:
      1. **Media contract** — assets {min,max, roles: hero/gallery/thumbnail, derive: [...]}
      2. **Relationship contract** — resources {types, extract: entities→supplier/tool/etc.}
      3. **Enrichment steps** — per-field/op (compose body, alt-text, smart-crop, palette)
      Mechanisms: image *derivations* via Pillow (crop/resize/enhance/palette→metadata) — NOT
      image-gen; smart-crop = vision picks focal point + Pillow cuts; resource-extract = AI
      entities→Resources (e.g. Otter Wax→supplier). Rejigger list: EntryTypeCapabilities
      pydantic schema · services/media (Pillow) · new ops smart-crop + extract-resources ·
      recipe step-runner in compose · entry-type editor UI · **recipe-driven Create/Edit Entry
      page** (render asset drop-zones with role/count limits + resource slots from the manifest,
      not just validate) — same manifest, two front doors (human-filled vs AI-composed).
      Sequence: ① manifest+assets contract → ② image derivations → ③ resource extraction → ④ UI.
- [x] **Wire `invocation_sources`** ✅ (the keystone) — gate operations by source. Each call
      carries a `source`; allowed only if in the INTERSECTION of the operation's declared
      invocation_sources and the workspace policy (override map: enabled unless explicitly false).
      Enforced in execute + compose. min_role was **already** enforced (per-user authz wall);
      together they're the palette gate for MCP/agent. 7 tests. (09feb42)
      *Remaining (2nd half of "Track A"):* wire `logging_config` (honor log_inputs/log_outputs +
      ai_executions retention prune) — see the low-hanging item above. UI to edit the per-workspace
      invocation_sources policy dict is also still needed (the gate reads it; nothing sets it yet).
- [ ] **Wire `moderation_config`** — add a moderation layer + `block_on_flag`.
- [ ] **Aesthetic gatekeeping for images** — a vision op that scores an uploaded/derived image
      against the **site aesthetic profile** (from the theme cascade — e.g. "rustic leather &
      wood") and flags or gates mismatches ("flowery photo on a rustic site"). Runs on upload /
      compose / publish; flag (warn) vs gate (block) per config. Ties: theme cascade (defines
      the aesthetic to compare to) + recipe.enrichment (declare the check per type) + a new
      flavour of moderation. Store the fit score/flag in asset metadata for review.
## ▶ ACTIVE PLAN — Tagging system (shared vocabulary)
> Planned 2026-07-20 off a full research pass. **Decisions (confirmed):** ① entries-first,
> assets/resources as a fast phase 2 · ② **create-on-type** (freeform, find-or-create by slug) ·
> ③ **defer** AI integration — `generate-tags` keeps staging to `metadata_json.tags`; the chip UI
> is the real-tag write path (wiring the AI to real tags shares the junction-writeback gap with
> attach/create, so it comes later).
>
> **Two facts that shape it:**
> - 🎁 Smart collections ALREADY have a `tags` matcher (`smart_collections.py:59-62`), inert only
>   because `entry.tags` doesn't exist. Expose `entry.tags` returning tag NAMES and tag-based smart
>   collections light up with **zero matcher changes**. Design to that.
> - Convention is **concrete named junctions** (entry_assets/entry_resources/entry_collections),
>   NOT polymorphic. Mirror it: a group-scoped `tags` table (like Collections) + `entry_tags`
>   junction. Copy the **Collections full stack** (model→repo→schema→controller + entry-side attach)
>   as the template.
> - Data today: **11 entries** carry `metadata_json.tags`; assets/resources have none.

### Phase 1 — entries, end to end
- [x] **T1. Model + migration.** `Tags` table (`id, group_id, name, slug`, uq(group_id, slug),
      mirrors Collections) + `entry_tags` junction (`entry_id, tag_id` FKs, cascade, uq). Autogenerate
      the migration (works now). **Data promotion:** slugify/dedupe the 11 entries' `metadata_json.tags`
      into real tags + entry_tags; strip the now-redundant `metadata_json.tags` key.
- [x] **T2. `entry.tags` association** returning tag names (association_proxy over `secondary=entry_tags`,
      like `entries.py:63-106`) — this is what makes smart collections work. Verify a tag smart-rule
      matches with no matcher change.
- [x] **T3. Tag CRUD + attach API** ✅ (2026-07-20) — `TagsRepository` (find-or-create by slug, stable
      slug on rename), `TagsController` at `/api/platform/tags`: `GET/POST/PATCH/DELETE` + attach/detach
      `POST|DELETE /tags/{tag_id}/entries/{entry_id}` (idempotent, resyncs tag-based smart collections).
      `tag_ids` on `EntryCreate`/`EntryUpdate` → `_attach_tags`/`_replace_tags` (replace semantics, empty
      clears). Registered in schemas/repos/factory __init__s + platform router. 4 DB-backed repo tests;
      230 pass. Note: `POST /tags` is find-or-create so the chip UI resolves a typed name → id in one call.
- [x] **T4. Expose tags where wired explicitly** ✅ (2026-07-20) — admin `EntryRead` gained `tags:
      list[str]` (model_validate override maps the ORM Tag relationship → `tag_names` slugs; joinedload
      added). Publish `PublishedEntryRead` + `PublishedEntryListItem` carry `tags`; both builders populate
      from `entry.tag_names` (selectinload added). New `?tag=slug1,slug2` filter on `list_published_entries`
      (slugified, ANY-match via `Entries.tags.any()` EXISTS — no dup rows). MCP `get_entry`/`find_entries`
      emit `tags` (find_entries batches the lookup); `get_entry` description updated. MarvinMCP
      `serializeEntry` passes `tags` through (build + 126 vitest green). 5 tag tests; backend 230 pass.
- [x] **T5. Entry editor chip UI** ✅ (2026-07-20) — Tags sidebar-section in `entries/[id].astro`:
      removable chips + text input with `<datalist>` autocomplete over the workspace vocabulary,
      create-on-type (Enter/comma). Client keeps a hidden `tags_payload` = JSON `[{name,id?}]`; SSR save
      resolves it → `tag_ids` (existing chips use their id; bare names go through find-or-create `POST
      /tags`). SDK: new `TagsModule` (list/get/create/update/delete/attach/detach) + `PlatformTag*` types,
      schema regenerated from offline OpenAPI (carries `tags`/`tagIds`); built + npm-linked. Frontend
      `lib/api/tags.ts` wrapper. Page compiles + renders 200. (Create-flow attach stays deferred per ask.)
- [x] **T6. Entries list tag filter** ✅ (2026-07-20) — Tags dropdown in the `entries.astro` FilterBar
      (only tags with entryCount > 0, alpha), `data-tags` slug attribute on every wrapper (grid + grouped
      + uncollected), client `matchesTag` folded into the existing filter (AND with type/status/search).
      Deep-linkable: `?tag=slug` pre-selects via `defaultValue`. Page compiles + renders 200, no new
      type errors.
- [x] **Verify:** ✅ promotion migration idempotent + reversible (T1) · smart-collection-by-tag matches
      (T2, live) · tag_ids round-trips through tag_names (T3, live) · published entry + admin + MCP expose
      tags (T4, live) · editor + list pages compile & render 200 · 230 backend + 126 MCP tests green.

**Phase 1 COMPLETE (T1–T6).** Real queryable tags, tag-based smart collections, full read/write API,
editor chip UI, and list filter — end to end. Verified live in-browser (chip add/save/remove round-trip,
list filter + deep-link). Deferred by request: create-flow attach; AI generate-tags repoint (Phase 3).

**Follow-ups delivered (2026-07-20, verified live):**
- [x] **Backup/restore includes tags** — exporter emits a top-level tag vocabulary (slug+name+color) +
      per-entry slug lists; seed loader rebuilds the vocabulary and relinks (find-or-create, idempotent,
      clears entry_tags on overwrite). 3 round-trip tests. (Dev directory seeder left as-is — not the
      backup path, collections still a TODO there.)
- [x] **Tag admin UI** — settings "Entry Types" tab renamed to "Content Model"; new /workspace/tags
      full-CRUD page (recolor, rename w/ stable slug, delete, entry counts, add-tag). Rename round-trip
      verified live. Note: browser SDK mutations need matching host (localhost↔localhost), not
      127.0.0.1 — cross-host drops the cookie.

### Phase 2 — assets + resources ✅ COMPLETE (2026-07-20, verified live)
- [x] `asset_tags` + `resource_tags` junctions (+ migration/indexes) · `.tags`/`tag_names` on
      Assets/Resources · `tag_ids` on asset/resource update (resource create too) · `tags` slugs on
      AssetRead/ResourceRead + published schemas · attach/detach API (`/tags/{id}/assets|resources/{id}`) ·
      MCP asset/resource serializers · backup/restore round-trip (shared `_link_tags`) · SDK attach/detach
      + regen · reusable `TagChips.astro` chip UI on asset + resource editors · tag admin "Uses" count
      (entries+assets+resources via `usage_count`). 4 tests; suite 286. Live: resource chip add→save→persist,
      admin Uses 1→2→1 on revert.
- [ ] **Deferred:** smart collections of assets/resources (collections only hold entries today —
      separate feature) · lift the entries-only `_write_back` guard (couples to Phase 3).

### Phase 3 — AI integration (after, or with attach/create's junction-writeback work)
- [ ] Repoint `generate-tags` writeback (`system.py:72`) off `metadata_json.tags` onto real tags —
      needs a `tags` writeback target (a mini junction-writeback grammar; shares the gap with
      attach/create). Until then generate-tags stages to metadata_json.tags and the user promotes
      via the chip UI.
- [ ] Also: grow `resources.resourceType` into a richer/extensible taxonomy (related backlog thread).
- [x] **Asset/Resource as first-class schema field types** ✅ — `EntryTypeSchemaDefinition` excludes
      them today ("handled via the UI sidebar"), but entry types already carry `asset`/`resource`
      field types in schema_json → strict validation fails (only preserved via a warning). Add
      AssetFieldSchema / ResourceFieldSchema to the discriminated union so they validate cleanly.
      Reconcile with recipe asset-roles: recipe = type-level media *contract*; an asset field = a
      named *slot* in the form. (User: yes, they should be in the schema.)
- [ ] **Workspace Providers UI** — create/edit `AIProviderModel` rows (base_url, Azure
      api_version, Ollama endpoint). Needed for Ollama/Azure workspace setups.
- [x] **Ollama in-app model pull DONE (2026-07-20)** ✅ — AI Settings → "Ollama model library":
      installed-model chips + pull a model on demand with a live progress bar (`POST
      /api/ai/models/pull` runs a background thread streaming `/api/pull`; `GET /installed-models`).
      SDK `client.ai.models`. Also fixed the `OLLAMA_BASE_URL=…/api` double-`/api` bug (normalized in
      OllamaProvider) and made the installed list Ollama-specific (was showing the wrong provider's
      catalogue). (Marvin b48e250, SDK 5cc4981.)
- [x] **Ollama no-tools 400 → clear message** ✅ (2026-07-19) — `OllamaProvider._chat` now unwraps
      Ollama's error body; a text-only model (gemma/phi) asked to tool-call raises a clear "pick a
      tool-capable model (qwen3-coder/qwen2.5/llama3.1)" instead of a bare `400 Bad Request`. See
      memory [[ollama-tool-support-per-model]].
- [ ] **Per-model tool capability + allow chat-only models** (note from user 2026-07-19: "allow gemma
      or others if it's just chat") — tool support is **per-model**, not per-provider
      (`OllamaProvider.supports_tool_calls=True` is provider-level). Text-only models (gemma3, phi)
      should be first-class for **non-agent** flows (operations: summary/tags/etc., `/ask`, plain
      chat) — they already work — but the system should: (1) surface a per-model `supports_tools`
      capability (auto-detect via Ollama `/api/show` or a probe, or let the user set it on the model
      row) so the builder/agent can gate cleanly; (2) let a workspace pick a **separate tool-capable
      model for the agent** vs a cheaper/faster model for operations; (3) optionally a chat-only agent
      fallback (no tools) when the model can't tool-call. Ties into the Workspace Providers UI.

## ★ North star: "Marvin" — the expandable workspace assistant
> 📐 Full architecture & capability strategy: **`tasks/marvin-assistant-architecture.md`**
> (three planes: system owns / MCP projects / assistant chooses · manifest-as-contract ·
> `min_role`+`invocation_sources` as the palette gate · server-side brain → thin client
> anywhere · public-widget risks). Wire the gate FIRST — it's what makes it safe.

Persona: **Marvin the Paranoid Android** (Hitchhiker's Guide) — brilliant, world-weary,
deadpan. "Here I am, brain the size of a planet, and they ask me to reindex embeddings."
The "Ask Marvin" bubble is his v1 shell. Not just RAG — a command surface that can *do* things:
- **Ask** — RAG Q&A over workspace content (one skill among many)
- **Actions** — Review, Publish, Test, Rebuild, … dispatched to existing endpoints
  (publishing, scheduled tasks, the operations registry)
- **Per-page context ("what am I looking at?")** — the thin bubble captures the current page's
  grounding (route + the entity it's rendering: type, id, title) and sends it with each ask. Two
  answers: (a) *explain the page* — static route→purpose help, no AI; (b) *explain the data* —
  summarize/describe the entity in context (AI, scoped to that id). Mechanism: pages declare a
  small context object (e.g. `window.marvinContext = {entityType, entityId, title}` or a body
  data-attr) with a route fallback — NOT DOM scraping. Same context also grounds future actions
  ("publish this", "review this"). In the server-brain model the client just forwards the context;
  the agent uses it to scope tools. Grounding only — it does not change permissions (min_role stays
  the wall).
- **Expandable** — a skill/tool registry so capabilities plug in rather than hardcode
- **MCP as the plugin layer** — host our operations as tools *and* connect external MCP
  servers, so Marvin's abilities grow without core changes
- Likely an **agentic loop** (Phase 8 agents) picking which skill/tool to run per request
Sequencing: operations registry (done) → skill/tool registry → agent loop → MCP host.
Ship the RAG bubble now as the seed; layer skills onto it.

## 🌲 Bigger / Phase 8
> ⚠️ **Three tone axes — do not conflate them** (learned 2026-07-20: asked Marvin to review an
> entry, got the review written in-character as a depressed robot):
> **A. Assistant persona** — how Marvin *addresses you*. Workspace-level (`persona_prompt`).
> **B. Task register** — how *work product* reads (reviews, findings, critiques). Must default to
>   plain/professional. Had NO representation; axis A was leaking into it.
> **C. Content voice** — how *generated content* sounds (the brand's voice). ← this cascade item.
> Partial fix shipped: the `/agent` system prompt now scopes persona to address-only and demands
> work product be plain (`operations_controller.py` ~695). That's a prompt-level mitigation, not a
> mechanism — a weak local model can still drift. The durable fix is an explicit **register** on
> the request (playful | neutral | professional), defaulting to professional for analysis-shaped
> asks and suppressing persona entirely for them. Build B as its own axis; C does NOT solve it.

- [ ] **Prompt storage + cascading theme/tone** ⭐ — user-authored prompts, but resolved as a
      CSS-like cascade: **Site → Collection → Entry-type → Entry** (nearest wins), two facets —
      **tone/voice** (injected into compose/enrichment via ContextBuilder) and **style/theme**
      (design tokens for render, can feed AI palette matching). Storage: reuse metadata at each
      level (site settings · collection.metadata · entry.metadata) — no new tables for v1.
      Builds on `resolve_prompt_messages` {{SLUG}} interpolation. Fixes "drafts sound generic"
      at scale. Backbone for user-authored operations/agents.
      **Prompt = separate, overridable layer (not baked into recipe_json):** system entry_types
      ship a DEFAULT prompt/voice, but a created prompt (workspace/site/collection/entry) OVERRIDES
      it — never forced. Store overrides SEPARATELY from the system entry_type (cascade metadata /
      prompts store) so re-seeding refreshes the system default WITHOUT clobbering overrides.
      → generated entry-type recipes stay structure-only (assets/resources); voice lives here.
- [ ] **Junction metadata = typed relationships (assembly layer)** — EntryAssets.metadata (role:
      hero/gallery/thumbnail + crop/focal), EntryCollections.metadata (featured/sort/layout),
      EntryResources.metadata (primary/mentioned). Distinct from the recipe: recipe *drives
      generation*, junction metadata *types the assembled result* for rendering. Compose writes
      roles here; templates read them. **renderers-core ALREADY reads this**: resolve.ts
      `getFeaturedAsset` picks `role==='hero'||'featured'` from asset junction metadata. So
      use that exact vocabulary (hero/featured) — compose writing the role lights up rendering
      with zero render changes. capabilities_json (publishable/submittable/routable) +
      rendering_json (renderer/package/config) feed renderers-core's EntryTypeInfo — leave both
      as-is; the authoring recipe goes in a NEW recipe_json field.
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

**2026-07-20 session** — Context-aware Marvin (A–E, above) + infra hardening:
- **Provider settings completeness** — every provider now declares `*_API_KEY` + `*_BASE_URL`
  (was silently `None` for ollama/azure via undeclared getattr); fixed the `.env` src-symlink
  footgun and the `OLLAMA_BASE_URL` `/api` suffix.
- **Migration workflow un-broken** — `postgresql.JSONB`→`sa.JSON` (6 models) + `INET`→`sa.String`
  made `--autogenerate` work on SQLite for the first time; `alembic/env.py` now imports all
  models (was 41/44 visible); `AUTO_MIGRATE` review gate for the reload-applies-migrations
  footgun; timestamp columns made nullable + `NOW()` defaults dropped (portable, backend-owned).
- **CI** — stopped auto-releasing SDK/CLI/MCP from `develop` (was minting a public `-next.N` +
  a `chore(release)` commit every push; packages established, consumers use `npm link`); tests
  kept; MCP `ci.yml`→`test.yml` + now tests develop. Deleted 81 stale prerelease git tags.
- **Write-back outcome** now recorded (`execution.metadata_json.writeback`) + surfaced to clients.

## Reference: wired vs cosmetic AI settings
- **Enforced:** enabled · credential_mode · provider/model/secret_ref · budget (daily
  requests + monthly cost + **max_tokens_per_request** ✅ wired 2026-07-20) · min_role (per-op)
  · **invocation_sources** (source ∩ policy) · logging_config (via `_logging_policy`) ·
  approval_mode (apply/stage decision + outcome now surfaced).
- **Still cosmetic (stored, no effect):** operation_overrides · moderation_config.

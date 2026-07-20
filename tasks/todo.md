# AI Subsystem — Backlog & Musings

Captured from working sessions. Grouped by effort. (The original AI-settings build plan
that lived here is shipped — replaced with the live backlog.)

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
- [ ] **P6d · invocation_sources coupling + UI** — the `automation` source ALREADY gates AI-op actions
      in the runner (policy ∩ op.sources, deny-if-explicitly-false). Add the missing per-workspace
      **invocation_sources policy editor** to AI Settings (incl. the new `automation` source), and in
      the Workflows builder show the AI-operation kind as disabled (with a link to AI Settings) when
      AI is off OR the `automation` source is disabled.

### Trigger types (generalize how workflows fire — beyond `entry_published`)
`trigger` is now typed: `{type, event?, …}` (defaults to `event`). All types funnel into the same
engine (`run_automation` / `run_automations_for_event`); event types go via the listener, the rest get
their own entrypoint. Full list the user wants: **event · manual · schedule · chained (another
automation) · chat (agent) · mcp tool (project workflow as an MCP tool) · on-error · incoming webhook**.
- [x] **T1 · event-expansion + Manual [Run]** ✅ — `trigger.type`; events widened to entry lifecycle
      (created/updated/published/deleted); `POST /api/automations/{id}/run` + Run button (also the
      test-it affordance); builder trigger-type selector (event/manual). SDK `automations.run()`.
- [ ] **⭐ Generalize event triggers to ANY (sensible) event** (decided 2026-07-19, from the user's
      "why limit to lifecycle?") — NOT a hard limit; two pieces: (1) **flatten each event's
      `document_data` into `event.*`** in the engine context so `$event.<field>` + conditions work for
      non-entry events (asset/form/resource/publish/…); keep the `entry.*` object as a convenience
      when an entry_id is present. (2) **Curated trigger catalog** — widen `_TRIGGERS`/`options.triggers`
      to a *meaningful* grouped allowlist (Entries/Assets/Forms/Resources/Publishing…), NOT the raw
      EventTypes firehose (exclude internal/audit noise: ai_operation_executed, *_delivery_*,
      scheduled_task_*, embeddings_reindexed). Do this as part of the trigger work.
- [x] **T2 · Schedule** ✅ (2026-07-19) — `trigger.type=schedule` → upsert a `run_automation` ScheduledTaskModel on the
      existing Scheduler (interval/cron); a `RunAutomationHandler`. "rebuild nightly."
- [x] **T3 · Chat / Chained / On-error DONE (2026-07-19)** ✅ — `run_workflow` agent tool (min_role AUTHOR, also projected to MarvinMCP) lets chat run any workflow; engine emits `automation_ran`/`automation_failed`; `chained` + `on_error` trigger types (target a specific workflow or any). 114 tests.
      trigger on it · emit `automation_failed` + on-failure trigger.
- [x] **T4 · MCP tool DONE (2026-07-19)** ✅ — `mcp` trigger type (opt-in) in builder; MarvinMCP `workflowsCapability` projects each enabled trigger.type=="mcp" workflow as `marvin_wf_<slug>` → `automations.run(id)`. MCP build + 126 vitest green. Admin-scoped token required to project.
      external MCP hosts can invoke it.
- [ ] **T5 · Incoming webhook** — new subsystem: tokened inbound endpoint
      `POST /api/automations/hooks/{token}` mapping the request payload into `$event`.
      *(In flight 2026-07-19 — Model 2 / ingress, see memory [[incoming-webhooks-ingress-model]]:
      `POST /api/hooks/{token}` drops an `incoming_webhook` event on the bus and fans out to any
      subscriber rather than binding one automation. Model + migration + schema + controller landed,
      router registered. Remaining: `incoming_webhook` isn't in `_TRIGGERS` yet — folded into the
      ⭐ generalize-event-triggers item above.)*

### Flavor B — hardening backlog (from `docs/WORKFLOW_STATE_REVIEW.md`, 2026-07-19)
> Review of the built engine against `docs/WORKFLOW_SUGGESTIONS.md`. The skeleton is
> proportionate and shouldn't be redesigned; these are the gaps that make it *trustworthy*.
> Ordered by unlock, not by feature area.

**H0 · Foundation — do before any new action types**
- [ ] **⭐⭐ Extract `services/entries/`** — THE structural blocker. There is no entries service;
      all entry lifecycle logic (which status transition emits which event) lives in
      `routes/platform/entries_controller.py:173-260`. So the "Flavor B actions call the same
      domain service as API/UI/SDK/MCP" hierarchy has nothing to point at. Already biting:
      `runner.py:184-205` hand-duplicates the controller's emit for AI write-back. Every new entry
      action would duplicate it again, and each copy is a place a chained automation silently stops
      firing. Extract `create/update/publish/unpublish/archive/restore` owning mutation **+** emit.
- [ ] **⭐ `changed_fields` / `before` / `after` on `EventEntryData`** — the single biggest matching
      gap. `update_entry` loads `old_entry` and throws the old values away, so "status changed
      draft → review" is inexpressible. Changed-field names + **scalar** before/after only; rich
      fields and relationships by reference (id+type), never by value — bounds payload size and
      avoids persisting content into `event_log` the user may later delete. Natural to land inside H0.
- [ ] **Validate `definition` with a Pydantic discriminated union** — today it's a bare `dict`
      (`schemas/group/automation.py`), so malformed automations are accepted by the API and fail
      silently at run time. See H4 for why this one is worth more than it looks.

**H1 · Observability — makes the thing debuggable**
- [ ] **⭐ `automation_executions` + `automation_action_executions` tables** — there is no execution
      history at all. Only the `operation` action leaves a trace (an `AIExecutionModel` row);
      `webhook`, `handler`, and `emit_event` leave nothing, so a misbehaving automation is a black
      box. Also the prerequisite for most of the UI story (history view, execution detail, retry).
      Truncate input/output snapshots at a fixed byte cap; never persist resolved secrets.
- [ ] **Correlation id threaded through `dispatch`**, promoted to a real column on `event_log`
      (it currently exists only as `reaction_depth` buried in the `event_data` JSON blob).
      Causation id + parent-execution id can wait — correlation alone makes a chain readable.
- [ ] **Snapshot the automation `definition` onto the execution row** — one column buys full
      auditability without any versioning/revision infrastructure.

**H2 · Honesty pass — cheap, removes user-visible lies**
- [ ] **54 of 122 `EventTypes` members are never emitted**, yet the catalog advertises ~100
      subscribable events — the Events UI offers subscriptions that can never deliver. All 8
      site/publishing events, all 3 form-submission events, and both asset attach/detach events are
      declared and dead. Delete them or gate the catalog to events with a real emitter.
- [ ] **Add `test_every_catalog_entry_has_an_emitter`** — would have caught all 54. Cheap, and stops
      the drift recurring.
- [ ] **Fix the false comment at `runner.py:203`** — it claims the automation listener ignores its
      own writes via `integration_id`. No listener reads `integration_id` (it's only ever *set*, 5
      sites). Only the depth-3 counter bounds the loop. Fix the comment or implement the check;
      as written it's a trap for whoever touches loop-prevention next.
- [ ] **`/run` doesn't check `enabled`** — an admin can manually run a disabled automation.

**H3 · Expression ergonomics — the sharp edges users will hit**
- [ ] **Embedded `${...}` interpolation** — `interpolate` (`matcher.py:38`) only substitutes a string
      that *starts* with `$`, so `"Summary: $previous.summary"` passes through as a literal. This
      will surprise everyone who tries it.
- [ ] **Named step outputs `$steps.<action-id>.output.*`** (keep `$previous` as an alias) — today only
      the immediately preceding step is reachable, so reordering actions silently breaks a pipeline.
- [ ] **`any` / `not` / nesting in conditions** — currently a flat AND-list. Plus operators `in`,
      `starts_with`, and the change-aware `changed` / `changed_from` / `changed_to` (which only
      become possible once H0's before/after lands).
- [ ] **`MAX_ACTIONS = 10` truncates silently** (`engine.py:149`, `actions[:MAX_ACTIONS]`) — no error,
      no warning. Reject at validation time instead.

**H4 · Simplifications & ideas worth taking**
- [ ] **⭐ Make the Pydantic definition schema the ONE source of truth** — if trigger and action
      inputs are discriminated-union models, validation + the `/options` catalog JSON Schema + SDK
      types + the MarvinMCP tool projection all fall out of a single declaration. The suggestions doc
      treats the registry, the schemas, and the catalog as separate deliverables; they're one thing.
      Biggest simplification available.
- [ ] **`dry_run` as a flag on the engine, not a separate code path** — thread a bool through
      `run_automations_for_event`; each executor returns its resolved input instead of executing.
      ~10 lines per action, and it delivers the "evaluate trigger + conditions, resolve inputs, don't
      execute" test mode without a parallel simulation engine.
- [ ] **Allowlist the `handler` action** — currently the most powerful, least constrained thing in the
      system: full `TaskHandlerRegistry` with no allowlist, no schema, duck-typed config, reaching
      maintenance tasks like `remove_orphaned_assets`. Decide deliberately — promote specific handlers
      to first-class actions with schemas, or keep it as an explicit escape hatch behind an allowlist.
      The one item in this review I'd call a genuine risk.
- [ ] **Per-user authorization at execution** — `user_id` is provenance only, never authorization.
      An AUTHOR publishing an entry can trip an admin-authored automation that runs privileged
      handlers and webhooks under full workspace authority.

**H5 · Entry action surface** *(thin once H0 lands — deliberately sequenced last)*
- [ ] `entry.publish` · `entry.unpublish` · `entry.archive` · `entry.restore` ·
      `entry.add_to_collection` · `entry.remove_from_collection`. Keep `entry.delete` out for now.

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
- [ ] **Tagging system — entries + assets + resources (one shared vocabulary)** — a tagging
      system spanning all three (freeform + maybe relational/related-tags), so the same tags drive
      search, filtering, and **smart-collection rules** (the `tags` rule dimension is already wired
      forward-compatibly — it goes live the moment entries carry tags). Also grow
      `resources.resourceType` into a richer/extensible taxonomy. Ties: `generate-tags` AI op ·
      recipe resource-extraction · smart collections (of entries now; of assets/resources once they
      share the tag vocabulary).
- [x] **Asset/Resource as first-class schema field types** ✅ — `EntryTypeSchemaDefinition` excludes
      them today ("handled via the UI sidebar"), but entry types already carry `asset`/`resource`
      field types in schema_json → strict validation fails (only preserved via a warning). Add
      AssetFieldSchema / ResourceFieldSchema to the discriminated union so they validate cleanly.
      Reconcile with recipe asset-roles: recipe = type-level media *contract*; an asset field = a
      named *slot* in the form. (User: yes, they should be in the schema.)
- [ ] **Workspace Providers UI** — create/edit `AIProviderModel` rows (base_url, Azure
      api_version, Ollama endpoint). Needed for Ollama/Azure workspace setups.
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

## Reference: wired vs cosmetic AI settings
- **Enforced:** enabled · credential_mode · provider/model/secret_ref · budget (daily
  requests + monthly cost) · min_role (per-op) · **invocation_sources** (source ∩ policy).
- **Cosmetic (stored, no effect):** approval_mode · operation_overrides · logging_config
  · moderation_config · budget.max_tokens_per_request.

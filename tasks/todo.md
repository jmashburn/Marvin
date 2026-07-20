# AI Subsystem — Backlog & Musings

Captured from working sessions. Grouped by effort. (The original AI-settings build plan
that lived here is shipped — replaced with the live backlog.)

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

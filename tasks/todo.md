# AI Subsystem — Backlog & Musings

Captured from working sessions. Grouped by effort. (The original AI-settings build plan
that lived here is shipped — replaced with the live backlog.)

## 🍂 Low-hanging
- [ ] **Resync SDK generated types** — `cd MarvinSDK && npm run generate:types && npm run build`
      (openapi-typescript off the running backend). Picks up this session's backend surface
      (recipe_json, compose-entry, AI stats fields, event-log fix, …) and lets the frontend drop
      the `as Parameters<…>` casts in entryTypes.ts. Its own task — big generated diff + rebuild.
- [ ] **Recipe UI placement** (thought, not mandate) — v1 recipe editor lives in the entry-type
      form. The admin "Custom Fields" / "Templates" placeholders under Entries could become a
      dedicated recipe builder (structured assets/resources/enrichment) instead of raw JSON.
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
- [x] **"Ask Marvin" bubble — v1** — floating capability-registry assistant on every
      page; v1 skill = Ask (RAG) + /help. Add a skill = push a Capability. → grows into ★ Marvin.
- [ ] Ops: actually create a `prune_event_logs` scheduled task (daily) — handler exists.

## 🌳 Medium / Features
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
- [ ] **Wire `invocation_sources`** — gate operations by source (editor/forms/actions/
      mcp/scheduled). Currently stored, never checked.
- [ ] **Wire `moderation_config`** — add a moderation layer + `block_on_flag`.
- [ ] **Aesthetic gatekeeping for images** — a vision op that scores an uploaded/derived image
      against the **site aesthetic profile** (from the theme cascade — e.g. "rustic leather &
      wood") and flags or gates mismatches ("flowery photo on a rustic site"). Runs on upload /
      compose / publish; flag (warn) vs gate (block) per config. Ties: theme cascade (defines
      the aesthetic to compare to) + recipe.enrichment (declare the check per type) + a new
      flavour of moderation. Store the fit score/flag in asset metadata for review.
- [ ] **Tags on entries + expand resource typing** — a tagging system for entries (freeform +
      maybe relational/related-tags), and grow `resources.resourceType` beyond the current set
      into a richer/extensible taxonomy. Ties to the existing `generate-tags` AI op and resource
      extraction from the recipe.
- [ ] **Asset/Resource as first-class schema field types** — `EntryTypeSchemaDefinition` excludes
      them today ("handled via the UI sidebar"), but entry types already carry `asset`/`resource`
      field types in schema_json → strict validation fails (only preserved via a warning). Add
      AssetFieldSchema / ResourceFieldSchema to the discriminated union so they validate cleanly.
      Reconcile with recipe asset-roles: recipe = type-level media *contract*; an asset field = a
      named *slot* in the form. (User: yes, they should be in the schema.)
- [ ] **Workspace Providers UI** — create/edit `AIProviderModel` rows (base_url, Azure
      api_version, Ollama endpoint). Needed for Ollama/Azure workspace setups.

## ★ North star: "Marvin" — the expandable workspace assistant
Persona: **Marvin the Paranoid Android** (Hitchhiker's Guide) — brilliant, world-weary,
deadpan. "Here I am, brain the size of a planet, and they ask me to reindex embeddings."
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
  requests + monthly cost).
- **Cosmetic (stored, no effect):** approval_mode · invocation_sources · operation_overrides
  · logging_config · moderation_config · budget.max_tokens_per_request.

# Marvin (the assistant) — architecture & capability strategy

Design north-star for how "Marvin the Paranoid Android" (the chat/assistant surface),
MarvinMCP, and the core operations system fit together. Captured from a working
session. This is the *why* and the *seams* — the backlog in `todo.md` holds the tasks.

## The one-liner

**MCP is the bridge, not the brain.** The core system *owns* capabilities; MarvinMCP
*projects* them; Marvin-the-assistant *chooses* among them. Keep those three jobs in
three places and decoupling falls out for free.

## Three planes

```
┌─ BRAIN ──────────────────────────────────────────────┐
│ Marvin (the bubble) + any external LLM (Claude        │
│ Desktop, etc.). Runs the agent loop: "which tool?"    │
│ Holds NO business logic. Palette = discovered tools.  │
└───────────────────────────────────────────────────────┘
              ▲ tools/list, tools/call (MCP)  |  POST /api/ai/agent (thin chat)
┌─ BRIDGE ─────────────────────────────────────────────┐
│ MarvinMCP. Thin adapter. Enumerates system            │
│ capabilities → exposes each as an MCP tool. Auth via  │
│ a user token. Uses the SDK. Reimplements nothing.     │
└───────────────────────────────────────────────────────┘
              ▲ /api/ai/operations, /compose-entry, publish… (SDK)
┌─ SYSTEM ─────────────────────────────────────────────┐
│ Marvin backend. Operations registry + verbs           │
│ (compose, ask/RAG, publish, reindex). Source of       │
│ truth. Every capability self-describes.               │
└───────────────────────────────────────────────────────┘
```

Business logic lives in the **system** as an operation/verb (compose is already there —
correct). MCP must **never reimplement** it; it just calls the endpoint. That gives
**one implementation, three front doors**: the UI calls it directly, Marvin calls it via
the agent endpoint, an external LLM calls it via MCP. Same code path, same telemetry.

## The decoupling seam (the core idea)

**A capability is discovered data, not compiled code.**

- The operations registry already makes every op self-describing: `slug`, `input_schema`,
  `output_schema`, `min_role`, `entity_types`, `requires_vision`. That manifest **is** the
  contract.
- So MarvinMCP is a **loop, not N hand-written tools**:

  ```python
  for op in sdk.ai.operations.list():          # discovery, not hardcoding
      mcp.register_tool(op.slug, op.input_schema,
                        lambda **kw: sdk.ai.operations.execute(op.slug, kw))
  # + first-class verbs that aren't registry ops:
  mcp.register_tool("compose_entry", ..., sdk.ai.operations.composeEntry)
  mcp.register_tool("ask", ..., sdk.ai.ask)     # RAG
  ```

- Add an operation to the registry → it appears in MCP and the agent → **zero changes to
  the bridge or the brain.** That is the decoupling.

The on/off knob already exists in the schema: **`invocation_sources`** (today stored but
cosmetic) is exactly "which surfaces may call this op" — `editor / forms / actions / mcp /
scheduled / agent`. Wire that one field and it governs *what tools each surface exposes*,
per-op, as config, without touching bridge code.

## Capabilities flow in two directions

1. **Expose-out** — system operations → MCP/agent tools, gated by `invocation_sources`.
   Grows Marvin's power as you add ops.
2. **Bring-in** — Marvin is also an MCP **host**: it can connect to *other* MCP servers
   (GitHub, filesystem, search). Those capabilities live entirely outside the codebase —
   decoupled by construction.

Marvin's capabilities = *(operations exposed via MarvinMCP)* ∪ *(external MCP servers
connected)* — a union **discovered at runtime**, never a hardcoded list. The frontend
`capabilities.ts` registry pattern stays; only the *source of the list* moves from
compiled → fetched.

## Server-side brain → thin client anywhere

Decision: **the brain runs server-side** (`POST /api/ai/agent`), NOT in the client.
Payoff: a thin Marvin is just *fetch + render + hold conversation state* — a few hundred
lines you can drop into the admin bubble, a public site widget, the CLI, or Slack. The
guts (planner, palette, auth, budget, execution logging) live once. **The endpoint is the
product; the client is a skin.**

`/api/ai/agent` and MarvinMCP become **two faces of the same manifest**:
- **MarvinMCP** — for machine/LLM callers that bring their own brain.
- **`/api/ai/agent`** — for thin human chat clients that borrow *our* brain.
Both read the same capability list, both filtered by the same gate.

## The constraint a PUBLIC surface adds (per-caller palette = the security model)

"Thin client anywhere, including a public site" means the caller's identity picks the
tool palette. This is the load-bearing safety property:

- **Anonymous visitor** → `ask` / RAG over *published* content only. Read-only. No compose,
  no publish.
- **Author token** → compose, tag, publish — the authoring set.
- **Admin** → everything.

The seam already exists: every capability carries `min_role` (+ `invocation_sources`), so
scoping is one policy line at the top of the loop:

```python
palette = [op for op in manifest
           if caller.role >= op.min_role and "agent" in op.invocation_sources]
```

The brain **never sees** a tool the caller can't run — so a public visitor can't be
prompt-injected into a privileged action. `min_role` stops being UI-gating and becomes the
**security boundary that makes "same endpoint everywhere" safe.**

Two things a public surface forces that the admin bubble didn't:
1. **Abuse / budget** — an anonymous widget is an open mouth into AI spend. The server-side
   brain already puts the budget guard + execution log in the path, but add a
   **per-anon-session rate limit / budget bucket** or one scraper drains the workspace quota.
2. **Injection blast radius** — public RAG = untrusted questions over our content. With a
   read-only palette the worst case is a *bad answer*, not a *bad action*. The damage ceiling
   is set by the caller's role, not by prompt cleverness.

**Status/opinion:** a website chatbot is desirable but genuinely risky (cost + injection +
moderation surface). Worth investigating, not the first thing to ship. Ship the
authenticated admin bubble first; treat the public widget as a later, deliberately-scoped
mode of the *same* endpoint.

## Recommended sequence

1. **Wire `min_role` + `invocation_sources` enforcement** — now load-bearing, not cosmetic.
   This is the gate that makes everything else opt-in and the "thin client anywhere" promise
   safe. Do this first.
2. **MarvinMCP = auto-projection loop** over `/api/ai/operations` + the verbs
   (compose/ask/publish/reindex). Thin, SDK-backed. (SDK now has `composeEntry()`.)
3. **`/api/ai/agent`** — server-side planner/loop, palette scoped per caller, streaming
   (SSE) for chat feel, conversation id for state. Reuses auth/budget/execution-logging.
4. **Thin clients** — admin bubble switches `capabilities.ts` to render discovered tools;
   later, a scoped public widget as a read-only mode of the same endpoint.

## MarvinMCP: current state & evolution path (reviewed)

Read the repo (beside Marvin / SDK / CLI). It is **better than "read-only publish wrapper"** —
a well-architected MCP server whose own design already anticipates this plan.

**What's there:**
- A `Capability` abstraction (`src/capabilities/types.ts`) — 7 capabilities (`meta`, `workspace`,
  `entries`, `entry-types`, `collections`, `assets`, `resources`), each a module with
  `register(context)`, looped by `registerCapabilities()`. Each registers MCP tools + resources
  (`marvin://entries/{slug}`) + prompts.
- Prompts already encode **"never publish automatically / draft only"** — matches `approval_mode`.
- `MarvinClientLike` interface + fakes + vitest suite; serializers normalize SDK shapes.
- A `readOnly` config flag already exists (`src/config.ts`).
- **`docs/CAPABILITY_INVENTORY.md` already states the deferral**: platform/write capabilities
  *"intentionally not exposed until write authentication, permission-aware discovery, and mutation
  safety are designed."* — i.e. it independently reached the same `min_role` +
  `invocation_sources` gate conclusion and stopped at the safe line on purpose.

**The gap vs this doc is exactly two things:**
1. **Auth plane** — uses the SDK `/publish` client (**site token, read-only**; `MarvinClientLike`
   is all `get*`). Operations, compose, and the agent loop need the `/platform` client (**user
   token**). So today it *structurally* cannot reach the operations registry or `composeEntry` —
   the "read-only" ceiling is an auth boundary, not a missing-tool problem.
2. **Projection** — tools are **hand-wired per domain**; no connection to `/api/ai/operations`,
   no auto-projection loop yet.

**Verdict: evolve in place, do NOT rebuild.** The `Capability` interface + `registerCapabilities`
loop IS the seam. Auto-projection becomes *one new capability*:

```ts
// operationsCapability.register({ platform, server, caller })
for (const op of await platform.ai.operations.list())
  if (caller.role >= op.min_role && op.invocation_sources.includes('mcp'))   // palette gate
    server.registerTool(op.slug, toZod(op.input_schema),
                        (a) => platform.ai.operations.execute(op.slug, a));
// + verbs: compose_entry (SDK method now exists), ask (RAG)
```

It sits **alongside** the hand-wired read capabilities (which stay — the site-token read path is
already the "anonymous/public" palette).

**Neat realization — two tokens = two trust levels, natively.** Site token (public read) vs user
token (authoring) *is* this doc's "caller identity picks the palette," expressed at the MCP layer:
- site-token session → read-only palette (current 7 capabilities)
- user-token session → authoring palette (operations + compose)

Per-caller scoping isn't a bolt-on; it maps onto which credential the server was handed.

**Steps (map 1:1 to the sequence above):**
1. Backend: wire `min_role` + `invocation_sources` enforcement (authoritative wall; MCP-side
   filtering is only UX). ✅ **DONE** (09feb42): min_role was already enforced; invocation_sources
   now gates each call by `source` ∩ (operation sources, workspace policy). Nuance: `source` is
   *declared by the calling infrastructure* (the endpoint/MCP/agent sets it) — so it's surface
   gating + feature-flagging, NOT authz against the token holder; min_role stays that wall. For
   the public-widget case, the agent endpoint must set `source` itself from the authenticated
   caller, never trust a client-supplied value. Still TODO: a UI to edit the workspace
   invocation_sources policy dict (the gate reads it; nothing writes it yet).
2. MarvinMCP: add a `/platform` client behind config (`MARVIN_USER_TOKEN`) + the existing
   `readOnly` flag — the "write authentication" the inventory is waiting on. (`/platform` import
   is available; `composeEntry()` already in the SDK — step is unblocked.)
3. MarvinMCP: add `operationsCapability` (the projection loop) + `compose_entry`/`ask` verbs,
   gated by the palette filter.

## Open questions

- **Agent framework vs hand-rolled loop** for `/api/ai/agent` (tie-in: Phase 8 "Agents",
  AgentDefinition / agent_executions).
- **Conversation persistence** — reuse executions table vs a new conversations/messages store.
- **Streaming** transport (SSE) + how the thin client renders partial tool calls.
- **`agent` as a distinct `invocation_source`** value (vs reusing `mcp`) — probably distinct,
  since the agent endpoint and raw MCP are different trust surfaces.

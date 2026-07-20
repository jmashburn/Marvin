/**
 * Marvin — pluggable capability registry.
 *
 * Marvin (the Paranoid Android) is a command surface, not just RAG. Each capability is a
 * self-contained skill: give it slash-command aliases (or mark it the default free-text
 * handler) and a run() that returns rendered HTML. Adding a skill = push one object onto
 * CAPABILITIES (or call registerCapability); the bubble discovers it automatically and it
 * shows up in /help. Future skills — publish, rebuild, test, review — dispatch to their
 * existing endpoints the same way.
 */
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { fetchApi } from '@/lib/api/client';
import { listAgentTools } from '@/lib/api/aiTools';
import { sendChat, askWorkspace } from '@/lib/api/aiBubble';

export interface MarvinResult {
  /** Safe HTML for Marvin's reply. Escape ALL dynamic content with esc(). */
  html: string;
}

export interface Capability {
  id: string;
  label: string;
  /** One-line description shown in /help. */
  hint: string;
  /** Slash-command aliases that route to this capability, e.g. ['ask']. */
  commands: string[];
  /** If true, handles free-text input that matched no slash command. Only one should be default. */
  isDefault?: boolean;
  /** If true, the command runs with no argument (e.g. /tools). Skips the "give me something" guard. */
  noArg?: boolean;
  /** Execute the skill. `arg` is the text after the command (or the whole input for the default). */
  run(arg: string): Promise<MarvinResult>;
}

/** Escape untrusted text before putting it in innerHTML (attributes, inline chips, etc.). */
export function esc(s: unknown): string {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Render Marvin's answer (markdown from the model) to sanitized HTML for innerHTML.
 * The model output is untrusted (prompt-injectable via workspace content), so we sanitize with
 * DOMPurify after marked — never inject raw model HTML.
 */
export function renderMarkdown(text: unknown): string {
  const raw = marked.parse(String(text ?? ''), { async: false }) as string;
  return DOMPurify.sanitize(raw);
}

function entityHref(type: string, id: string): string | null {
  if (type === 'entry') return `/workspace/entries/${id}`;
  if (type === 'resource') return `/workspace/resources/${id}`;
  return null;
}

interface Thumb {
  url: string;
  alt: string;
  entryId?: string;
  title?: string;
}

/**
 * Deterministic thumbnail source: pull image assets (with real urls) out of the agent's tool
 * results — get_entry (`assets`) and find_entries (`entries[].assets`) — rather than trusting the
 * model to embed image URLs. Deduped by asset id; each thumb links to its parent entry.
 */
function collectThumbs(steps: any[]): Thumb[] {
  const out: Thumb[] = [];
  const seen = new Set<string>();
  const add = (a: any, entryId?: string, title?: string) => {
    if (!a || a.assetType !== 'image' || !a.url || seen.has(a.id)) return;
    seen.add(a.id);
    out.push({ url: a.url, alt: a.altText || a.filename || title || '', entryId, title });
  };
  for (const s of steps) {
    let r: any;
    try {
      r = typeof s.result === 'string' ? JSON.parse(s.result) : s.result;
    } catch {
      continue;
    }
    if (!r) continue;
    if (Array.isArray(r.assets)) for (const a of r.assets) add(a, r.id, r.title); // get_entry
    if (Array.isArray(r.entries)) {
      for (const e of r.entries) if (Array.isArray(e.assets)) for (const a of e.assets) add(a, e.id, e.title); // find_entries
    }
    if (Array.isArray(r.results)) {
      // search_content: entry hits carry DB-hydrated image refs; link to the entity.
      for (const hit of r.results)
        if (Array.isArray(hit.assets))
          for (const a of hit.assets) add(a, hit.entityType === 'entry' ? hit.entityId : undefined, hit.title);
    }
  }
  return out;
}

/** Render a thumbnail strip (each linked to its entry) from collected image assets. */
function thumbsHtml(steps: any[], cap = 12): string {
  const thumbs = collectThumbs(steps);
  if (!thumbs.length) return '';
  const items = thumbs.slice(0, cap).map((t) => {
    const img = `<img src="${esc(t.url)}" alt="${esc(t.alt)}" title="${esc(t.title || '')}" loading="lazy" />`;
    const href = t.entryId ? entityHref('entry', t.entryId) : null;
    return href ? `<a class="mv-thumb" href="${esc(href)}">${img}</a>` : `<span class="mv-thumb">${img}</span>`;
  });
  return `<div class="mv-thumbs">${items.join('')}</div>`;
}

// ── Built-in skill: Agent (tool-calling loop) ────────────────────────────────
// The default free-text handler. Give Marvin a goal; it decides which of its tools to use
// (search, browse, list types, compose a draft), chaining as many as needed, then answers.
const agent: Capability = {
  id: 'agent',
  label: 'Agent',
  hint: 'Give Marvin a goal — it searches, browses, and drafts to get it done.',
  commands: ['agent', 'do'],
  isDefault: true,
  async run(arg: string): Promise<MarvinResult> {
    let res: any;
    try {
      res = await fetchApi<any>('/api/ai/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: arg, source: 'editor' }),
      });
    } catch (err: any) {
      const msg = String(err?.message || err);
      // The agent needs a tool-capable provider; degrade to a helpful hint rather than snark.
      if (/tool.?call|tool-capable|does not support/i.test(msg)) {
        return {
          html: `<div class="mv-answer">This workspace's AI provider can't run the full agent (no tool-calling). Try <code>/ask</code> for a quick answer from your content instead.</div>`,
        };
      }
      throw err; // let the bubble show its standard error
    }

    const answer = res?.answer ?? '(no answer — the void stares back)';
    let html = `<div class="mv-answer">${renderMarkdown(answer)}</div>`;

    const steps: any[] = res?.steps ?? [];

    // Deterministic thumbnail strip from the tool results' image assets (real urls, not guessed).
    html += thumbsHtml(steps);

    // Surface any drafts the agent composed as clickable links.
    const drafts: string[] = [];
    for (const s of steps) {
      if (s.tool !== 'compose_entry') continue;
      try {
        const r = typeof s.result === 'string' ? JSON.parse(s.result) : s.result;
        if (r?.editUrl) drafts.push(`<a href="${esc(r.editUrl)}">${esc(r.title || 'New draft')}</a>`);
      } catch {
        /* ignore unparseable tool result */
      }
    }
    if (drafts.length) {
      html += `<div class="mv-sources"><span>Drafts:</span> ${drafts.join(' · ')}</div>`;
    }

    // Show which tools were used, as a subtle trace of the agent's work.
    if (steps.length) {
      const tools = [...new Set(steps.map((s) => s.tool))];
      html += `<div class="mv-sources"><span>Used:</span> ${tools.map((t) => `<code>${esc(t)}</code>`).join(' ')}</div>`;
    }
    return { html };
  },
};

// ── Built-in skill: Ask (RAG) ────────────────────────────────────────────────
const ask: Capability = {
  id: 'ask',
  label: 'Ask',
  hint: 'Quick answer from your workspace content, with sources (read-only, no tools).',
  commands: ['ask'],
  async run(arg: string): Promise<MarvinResult> {
    const exec: any = await askWorkspace(arg);
    const out = exec?.outputJson ?? exec?.output_json ?? {};
    const answer = out.answer ?? '(no answer — the void stares back)';
    const retrieved: any[] = out.retrieved_sources ?? [];

    let html = `<div class="mv-answer">${renderMarkdown(answer)}</div>`;
    const seen = new Set<string>();
    const links: string[] = [];
    for (const s of retrieved) {
      const key = `${s.entity_type}:${s.entity_id}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const href = entityHref(s.entity_type, s.entity_id);
      const label = esc(s.title || key);
      links.push(href ? `<a href="${esc(href)}">${label}</a>` : label);
    }
    if (links.length) {
      html += `<div class="mv-sources"><span>Sources:</span> ${links.join(' · ')}</div>`;
    }
    return { html };
  },
};

// ── Built-in skill: Chat (plain completion — no tools, no RAG) ───────────────
// Ungrounded conversation with the model, like the Ollama CLI. Works on ANY model, including
// text-only ones (gemma, phi) that can't run the tool-calling agent. Not grounded in workspace
// content — use /ask for that, /agent (default) to actually do things.
const chat: Capability = {
  id: 'chat',
  label: 'Chat',
  hint: 'Just talk to the model — no tools, no content lookup. Works on any model.',
  commands: ['chat'],
  async run(arg: string): Promise<MarvinResult> {
    const res = await sendChat(arg);
    const reply = res?.reply ?? '(no reply — the silence is deafening)';
    return { html: `<div class="mv-answer">${renderMarkdown(reply)}</div>` };
  },
};

// ── Built-in skill: Tools (what the agent can reach) ─────────────────────────
// Transparency, not a mode you drive: lists the tools the /agent loop actually binds for you —
// built-in registry tools plus any allowlisted external MCP tools — so "did my server wire in?"
// has an honest answer. You never call these directly; the agent picks from them.
const tools: Capability = {
  id: 'tools',
  label: 'Tools',
  hint: "See the tools I can reach right now (built-in + your external MCP servers).",
  commands: ['tools'],
  noArg: true,
  async run(): Promise<MarvinResult> {
    const all = await listAgentTools();
    if (!all.length) {
      return { html: `<div class="mv-tools">No tools are enabled. Bleak, but on brand.</div>` };
    }
    // Group: built-ins first, then one group per external MCP server.
    const groups = new Map<string, typeof all>();
    const label = (t: (typeof all)[number]) =>
      t.source === 'external' ? (t.server || 'External MCP') : 'Built-in';
    for (const t of all) {
      const k = label(t);
      (groups.get(k) ?? groups.set(k, []).get(k)!).push(t);
    }
    // Built-in group renders first; external servers follow in insertion order.
    const ordered = [...groups.entries()].sort(([a], [b]) =>
      a === 'Built-in' ? -1 : b === 'Built-in' ? 1 : 0,
    );
    const short = (d: string) => (d.length > 90 ? d.slice(0, 87).trimEnd() + '…' : d);
    const sections = ordered
      .map(([name, ts]) => {
        const rows = ts
          .map(
            (t) =>
              `<li><code>${esc(t.name)}</code> <span title="${esc(t.description)}">${esc(short(t.description))}</span></li>`,
          )
          .join('');
        return `<div class="mv-tools-group"><span class="mv-tools-head">${esc(name)}</span><ul>${rows}</ul></div>`;
      })
      .join('');
    return {
      html: `<div class="mv-tools">Here's what I can reach right now — I pick from these when you give me a goal:${sections}</div>`,
    };
  },
};

// ── Registry ─────────────────────────────────────────────────────────────────
export const CAPABILITIES: Capability[] = [agent, ask, chat, tools];

/** Register a new skill at runtime (e.g. from a plugin bundle). */
export function registerCapability(cap: Capability): void {
  CAPABILITIES.push(cap);
}

/**
 * Route raw input to a capability.
 *   "/cmd args"  → the capability whose commands include `cmd`
 *   "/help"|"/?" → help flag
 *   free text    → the default capability
 */
export function resolveCapability(input: string): { cap: Capability | null; arg: string; help?: boolean } {
  const trimmed = input.trim();
  if (trimmed.startsWith('/')) {
    const [cmd, ...rest] = trimmed.slice(1).split(/\s+/);
    if (cmd === 'help' || cmd === '?') return { cap: null, arg: '', help: true };
    const cap = CAPABILITIES.find((c) => c.commands.includes(cmd.toLowerCase())) ?? null;
    return { cap, arg: rest.join(' ') };
  }
  return { cap: CAPABILITIES.find((c) => c.isDefault) ?? null, arg: trimmed };
}

/** Rendered /help listing every registered skill. */
export function helpHtml(): string {
  const rows = CAPABILITIES.map(
    (c) => `<li><code>/${esc(c.commands[0] ?? c.id)}</code> — ${esc(c.hint)}</li>`,
  ).join('');
  return `<div class="mv-help">Brain the size of a planet, and here's what they let me do:<ul>${rows}</ul>Or just type a question and I'll do my best. It won't be enough.</div>`;
}

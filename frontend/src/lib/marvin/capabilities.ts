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
import { fetchApi } from '@/lib/api/client';

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
  /** Execute the skill. `arg` is the text after the command (or the whole input for the default). */
  run(arg: string): Promise<MarvinResult>;
}

/** Escape untrusted text before putting it in innerHTML. */
export function esc(s: unknown): string {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function entityHref(type: string, id: string): string | null {
  if (type === 'entry') return `/workspace/entries/${id}`;
  if (type === 'resource') return `/workspace/resources/${id}`;
  return null;
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
    let html = `<div class="mv-answer">${esc(answer)}</div>`;

    const steps: any[] = res?.steps ?? [];

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
    const exec = await fetchApi<any>('/api/ai/operations/answer-workspace-question/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: { question: arg } }),
    });
    const out = exec?.outputJson ?? exec?.output_json ?? {};
    const answer = out.answer ?? '(no answer — the void stares back)';
    const retrieved: any[] = out.retrieved_sources ?? [];

    let html = `<div class="mv-answer">${esc(answer)}</div>`;
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

// ── Registry ─────────────────────────────────────────────────────────────────
export const CAPABILITIES: Capability[] = [agent, ask];

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

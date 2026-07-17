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

// ── Built-in skill: Ask (RAG) ────────────────────────────────────────────────
const ask: Capability = {
  id: 'ask',
  label: 'Ask',
  hint: 'Answer a question from your workspace content, with sources.',
  commands: ['ask'],
  isDefault: true,
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
export const CAPABILITIES: Capability[] = [ask];

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

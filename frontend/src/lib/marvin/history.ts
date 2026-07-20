/**
 * Marvin — short-term conversation memory.
 *
 * The agent endpoint is stateless: every call replays the prior turns the client remembers.
 * The bubble owns the transcript (it already persists one in sessionStorage for rehydration);
 * this module is the hand-off point where it publishes a plain-text view for skills to send.
 *
 * Why a published snapshot rather than skills reading the transcript directly: the snapshot is
 * taken at submit time, *before* the new user turn is appended, so `history` is exactly "what
 * came before this message" — no off-by-one where the current question appears twice.
 *
 * Rendered HTML is useless to a model, so turns carry plain text. The server bounds this again
 * (turn count + characters), so over-sending is safe.
 */

export interface HistoryTurn {
  role: 'user' | 'assistant';
  content: string;
}

/** Client-side cap. The server trims further; this just avoids shipping a huge body. */
export const HISTORY_SEND_CAP = 10;

let snapshot: HistoryTurn[] = [];

/** Publish the turns that precede the message about to be sent. */
export function setHistory(turns: HistoryTurn[]): void {
  snapshot = turns.slice(-HISTORY_SEND_CAP);
}

/** The turns preceding the current message (oldest first). */
export function getHistory(): HistoryTurn[] {
  return snapshot;
}

export function clearHistory(): void {
  snapshot = [];
}

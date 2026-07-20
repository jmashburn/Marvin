/**
 * Ask Marvin bubble — SDK-backed calls (browser: omit token, uses the HttpOnly cookie).
 * Chat = plain completion; ask = grounded RAG answer via the answer-workspace-question operation.
 */

import { createSdkClient } from '../sdk';

/** Plain, ungrounded chat completion (no tools, no RAG). */
export async function sendChat(message: string) {
  return createSdkClient().ai.chat({ message, source: 'editor' });
}

/** Grounded answer from the workspace's indexed content (RAG). */
export async function askWorkspace(question: string) {
  return createSdkClient().ai.operations.execute('answer-workspace-question', {
    input: { question },
  });
}

/**
 * Agent loop — Marvin picks and chains tools to reach a goal.
 * `context` grounds the run in whatever the current page declared (see @/lib/marvin/context);
 * omit it for an unscoped, workspace-wide ask.
 */
export async function runAgent(
  message: string,
  context?: { entityType?: string; entityId?: string } | null,
  history?: { role: 'user' | 'assistant'; content: string }[],
  register?: 'auto' | 'professional' | 'playful',
) {
  return createSdkClient().ai.agent({
    message,
    source: 'editor',
    ...(register ? { register } : {}),
    ...(context?.entityType && context.entityId
      ? { entityType: context.entityType, entityId: context.entityId }
      : {}),
    ...(history?.length ? { history } : {}),
  });
}

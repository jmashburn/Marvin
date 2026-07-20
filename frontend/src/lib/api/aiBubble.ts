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

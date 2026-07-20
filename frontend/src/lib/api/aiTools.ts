/**
 * The agent's bound tool surface — SDK wrapper (platform.ai.tools.listAgent).
 * Pass authToken in SSR (from Astro.cookies); omit it in the browser to use the HttpOnly cookie.
 */

import { createSdkClient } from '../sdk';
import type { AgentToolInfo } from '@inneropen/marvin-sdk/platform';

export type { AgentToolInfo };

/** Tools the /agent loop actually binds for the caller (built-in + external MCP), role-filtered. */
export async function listAgentTools(authToken?: string): Promise<AgentToolInfo[]> {
  return createSdkClient(authToken).ai.tools.listAgent();
}

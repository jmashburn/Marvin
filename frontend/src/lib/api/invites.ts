/**
 * Workspace Invites API - manage invitation tokens
 */

import { fetchApi } from "./client";
import type { InviteTokenCreate, EmailInvitation } from "./types";

// SDK type for invite token response (only has token and usesLeft)
interface InviteTokenSummary {
  token: string;
  usesLeft: number;
}

/**
 * List all invite tokens for the current workspace
 */
export async function listInviteTokens(authToken?: string): Promise<InviteTokenSummary[]> {
  const response = await fetchApi<{ items: InviteTokenSummary[] }>(
    '/api/groups/invitations',
    {},
    authToken
  );
  return response.items || [];
}

/**
 * Create a new invite token
 */
export async function createInviteToken(
  data: InviteTokenCreate,
  authToken?: string
): Promise<InviteTokenSummary> {
  return fetchApi<InviteTokenSummary>(
    '/api/groups/invitations',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    },
    authToken
  );
}

/**
 * Send email invitation
 */
export async function sendEmailInvitation(
  data: EmailInvitation,
  authToken?: string
): Promise<void> {
  return fetchApi<void>(
    '/api/groups/invitations/email',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    },
    authToken
  );
}

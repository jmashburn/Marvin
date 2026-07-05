/**
 * Workspace Invites API - manage invitation tokens
 */

import { fetchApi } from "./client";
import type { InviteTokenRead, InviteTokenCreate, EmailInvitation } from "./types";

/**
 * List all invite tokens for the current workspace
 */
export async function listInviteTokens(authToken?: string): Promise<InviteTokenRead[]> {
  const response = await fetchApi<{ items: InviteTokenRead[] }>(
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
): Promise<InviteTokenRead> {
  return fetchApi<InviteTokenRead>(
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

/**
 * Workspace Invites API - manage invitation tokens (migrated to SDK)
 */

import { createSdkClient } from '../sdk';
import type { InviteTokenCreate, InviteTokenSummary, EmailInvitationRequest } from '@inneropen/marvin-sdk/platform';

/**
 * List all invite tokens for the current workspace
 */
export async function listInviteTokens(authToken?: string): Promise<InviteTokenSummary[]> {
  const sdk = createSdkClient(authToken!);
  return sdk.invites.list();
}

/**
 * Create a new invite token
 */
export async function createInviteToken(
  data: InviteTokenCreate,
  authToken?: string
): Promise<InviteTokenSummary> {
  const sdk = createSdkClient(authToken!);
  return sdk.invites.create(data);
}

/**
 * Send email invitation
 */
export async function sendEmailInvitation(
  data: EmailInvitationRequest,
  authToken?: string
): Promise<void> {
  const sdk = createSdkClient(authToken!);
  return sdk.invites.sendEmail(data);
}

// Type re-exports for backward compatibility
export type { InviteTokenCreate, InviteTokenSummary, EmailInvitationRequest };

// Legacy interface
export interface EmailInvitation extends EmailInvitationRequest {}

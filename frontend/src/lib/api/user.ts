/**
 * User Self-Service API
 * Migrated to use @inneropen/marvin-sdk
 */

import { createSdkClient } from '../sdk';
import type {
  UserProfile,
  ApiToken,
  ApiTokenCreate,
  ApiTokenWithToken,
  PasswordChange,
} from '@inneropen/marvin-sdk/platform';

export type { UserProfile, ApiToken, ApiTokenCreate, ApiTokenWithToken, PasswordChange };

/**
 * Get current user profile
 */
export async function getUserProfile(authToken: string): Promise<UserProfile> {
  const sdk = createSdkClient(authToken);
  return sdk.user.getProfile();
}

/**
 * List user's personal API tokens
 */
export async function listApiTokens(authToken: string): Promise<ApiToken[]> {
  const sdk = createSdkClient(authToken);
  return sdk.user.listApiTokens();
}

/**
 * Create a new personal API token
 */
export async function createApiToken(data: ApiTokenCreate, authToken: string): Promise<ApiTokenWithToken> {
  const sdk = createSdkClient(authToken);
  return sdk.user.createApiToken(data);
}

/**
 * Revoke an API token
 */
export async function revokeApiToken(tokenId: string, authToken: string): Promise<void> {
  const sdk = createSdkClient(authToken);
  return sdk.user.revokeApiToken(tokenId);
}

/**
 * Rotate an API token (revoke old, create new)
 */
export async function rotateApiToken(tokenId: string, authToken: string): Promise<ApiTokenWithToken> {
  const sdk = createSdkClient(authToken);
  return sdk.user.rotateApiToken(tokenId);
}

/**
 * Delete an API token
 */
export async function deleteApiToken(tokenId: string, authToken: string): Promise<void> {
  const sdk = createSdkClient(authToken);
  return sdk.user.deleteApiToken(tokenId);
}

/**
 * Change user password
 */
export async function changePassword(data: PasswordChange, authToken: string): Promise<void> {
  const sdk = createSdkClient(authToken);
  return sdk.user.changePassword(data);
}

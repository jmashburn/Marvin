/**
 * Platform API methods - Assets and API Clients (Site Clients)
 * Migrated to use @inneropen/marvin-sdk
 */

import type {
  PlatformAPIClient,
  PlatformAPIClientCreate,
  PlatformAPIClientUpdate,
  PlatformAPIClientWithToken,
  PlatformAsset,
} from "@inneropen/marvin-sdk/platform";
import { createSdkClient } from "../sdk";

// Re-export SDK types with legacy names for backward compatibility
export type MarvinAsset = PlatformAsset;
export type APIClientRead = PlatformAPIClient;
export type APIClientCreate = PlatformAPIClientCreate;
export type APIClientUpdate = PlatformAPIClientUpdate;
export type APIClientWithToken = PlatformAPIClientWithToken;

// WorkspaceSiteInfo type (for preview) - map to SDK type
export type WorkspaceSiteInfo = PlatformAPIClient; // Preview returns the same structure

/**
 * Get all assets in the current workspace
 */
export async function getAssets(authToken: string): Promise<MarvinAsset[]> {
  const sdk = createSdkClient(authToken);
  return sdk.assets.list();
}

// ===== API Client Management (Admin Operations) =====

/**
 * Get all API clients for the current workspace
 * Auth: Normal Marvin user session, workspace-scoped
 */
export async function getSiteClients(authToken: string): Promise<APIClientRead[]> {
  const sdk = createSdkClient(authToken);
  return sdk.apiClients.list();
}

/**
 * Create a new API client
 * Returns plaintext token ONCE - store securely
 * Auth: Workspace ADMIN/OWNER required
 */
export async function createSiteClient(data: APIClientCreate, authToken: string): Promise<APIClientWithToken> {
  const sdk = createSdkClient(authToken);
  return sdk.apiClients.create(data);
}

/**
 * Rotate (regenerate) an API client token
 * Old token is immediately invalidated
 * Returns new plaintext token ONCE - store securely
 * Auth: Workspace ADMIN/OWNER required
 */
export async function rotateSiteClientToken(id: string, authToken: string): Promise<APIClientWithToken> {
  const sdk = createSdkClient(authToken);
  return sdk.apiClients.rotateToken(id);
}

/**
 * Update API client metadata (name, description, permissions, enabled status)
 * Auth: Workspace ADMIN/OWNER required
 */
export async function updateSiteClient(id: string, data: APIClientUpdate, authToken: string): Promise<APIClientRead> {
  const sdk = createSdkClient(authToken);
  return sdk.apiClients.update(id, data);
}

/**
 * Delete an API client
 * Auth: Workspace ADMIN/OWNER required
 */
export async function deleteSiteClient(id: string, authToken: string): Promise<void> {
  const sdk = createSdkClient(authToken);
  return sdk.apiClients.delete(id);
}

/**
 * Preview publishing API payload for an API client
 * Shows what external consumers would receive WITHOUT needing a token
 * Auth: Normal Marvin user session (read access to workspace)
 */
export async function previewPublishPayload(id: string, authToken: string): Promise<WorkspaceSiteInfo> {
  const sdk = createSdkClient(authToken);
  return sdk.apiClients.preview(id) as Promise<WorkspaceSiteInfo>;
}

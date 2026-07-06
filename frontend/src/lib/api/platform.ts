/**
 * Platform API methods - Assets and API Clients (Site Clients)
 * Note: Entries are now accessed via entries.ts
 */

import { fetchApi } from "./client";
import type {
  ApiListResponse,
  MarvinAsset,
  APIClientRead,
  APIClientCreate,
  APIClientUpdate,
  APIClientWithToken,
  WorkspaceSiteInfo
} from "./types";

function unwrapList<T>(response: ApiListResponse<T> | T[]): T[] {
  return Array.isArray(response) ? response : response.data;
}

/**
 * Get all assets in the current workspace
 */
export async function getAssets(authToken?: string): Promise<MarvinAsset[]> {
  return unwrapList(await fetchApi<ApiListResponse<MarvinAsset> | MarvinAsset[]>('/api/platform/assets', {}, authToken));
}

// ===== API Client Management (Admin Operations) =====

/**
 * Get all API clients for the current workspace
 * Auth: Normal Marvin user session, workspace-scoped
 */
export async function getSiteClients(authToken?: string): Promise<APIClientRead[]> {
  return fetchApi<APIClientRead[]>('/api/platform/api-clients', {}, authToken);
}

/**
 * Create a new API client
 * Returns plaintext token ONCE - store securely
 * Auth: Workspace ADMIN/OWNER required
 */
export async function createSiteClient(data: APIClientCreate, authToken?: string): Promise<APIClientWithToken> {
  return fetchApi<APIClientWithToken>('/api/platform/api-clients', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, authToken);
}

/**
 * Rotate (regenerate) an API client token
 * Old token is immediately invalidated
 * Returns new plaintext token ONCE - store securely
 * Auth: Workspace ADMIN/OWNER required
 */
export async function rotateSiteClientToken(id: string, authToken?: string): Promise<APIClientWithToken> {
  return fetchApi<APIClientWithToken>(`/api/platform/api-clients/${id}/rotate-token`, {
    method: 'POST',
  }, authToken);
}

/**
 * Update API client metadata (name, description, permissions, enabled status)
 * Auth: Workspace ADMIN/OWNER required
 */
export async function updateSiteClient(id: string, data: APIClientUpdate, authToken?: string): Promise<APIClientRead> {
  return fetchApi<APIClientRead>(`/api/platform/api-clients/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, authToken);
}

/**
 * Delete an API client
 * Auth: Workspace ADMIN/OWNER required
 */
export async function deleteSiteClient(id: string, authToken?: string): Promise<void> {
  return fetchApi<void>(`/api/platform/api-clients/${id}`, { method: 'DELETE' }, authToken);
}

/**
 * Preview publishing API payload for an API client
 * Shows what external consumers would receive WITHOUT needing a token
 * Auth: Normal Marvin user session (read access to workspace)
 */
export async function previewPublishPayload(id: string, authToken?: string): Promise<WorkspaceSiteInfo> {
  return fetchApi<WorkspaceSiteInfo>(`/api/platform/api-clients/${id}/preview`, {}, authToken);
}

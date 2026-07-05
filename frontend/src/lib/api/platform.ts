/**
 * Platform API methods - Assets and Site Clients
 * Note: Entries are now accessed via entries.ts
 */

import { fetchApi } from "./client";
import type { ApiListResponse, MarvinAsset, SiteClient } from "./types";

function unwrapList<T>(response: ApiListResponse<T> | T[]): T[] {
  return Array.isArray(response) ? response : response.data;
}

/**
 * Get all assets in the current workspace
 */
export async function getAssets(): Promise<MarvinAsset[]> {
  return unwrapList(await fetchApi<ApiListResponse<MarvinAsset> | MarvinAsset[]>('/api/assets'));
}

/**
 * Get all site clients (publishing destinations)
 */
export async function getSiteClients(): Promise<SiteClient[]> {
  return fetchApi<SiteClient[]>('/api/admin/platform/site-clients');
}

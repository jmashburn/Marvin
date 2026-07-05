import { GROUP_SLUG, hasApiBackend } from "./config";
import { fetchApi } from "./client";
import { sampleAssets, sampleEntries, sampleSiteClients } from "./sample-data";
import type { ApiListResponse, MarvinAsset, MarvinEntry, SiteClient } from "./types";

function unwrapList<T>(response: ApiListResponse<T> | T[]) {
  return Array.isArray(response) ? response : response.data;
}

export async function getEntries(entryType?: string): Promise<MarvinEntry[]> {
  if (!hasApiBackend()) {
    return entryType ? sampleEntries.filter((entry) => entry.entry_type === entryType) : sampleEntries;
  }

  const params = new URLSearchParams();
  if (entryType) {
    params.set("entry_type", entryType);
  }

  const path = `/api/publish/${GROUP_SLUG}/entries${params.size ? `?${params.toString()}` : ""}`;
  return unwrapList(await fetchApi<ApiListResponse<MarvinEntry> | MarvinEntry[]>(path));
}

export async function getAssets(): Promise<MarvinAsset[]> {
  if (!hasApiBackend()) {
    return sampleAssets;
  }

  return unwrapList(await fetchApi<ApiListResponse<MarvinAsset> | MarvinAsset[]>(`/api/publish/${GROUP_SLUG}/assets`));
}

export async function getSiteClients(): Promise<SiteClient[]> {
  if (!hasApiBackend()) {
    return sampleSiteClients;
  }

  return fetchApi<SiteClient[]>("/api/admin/platform/site-clients");
}

/**
 * Resources API client
 */

import { fetchApi } from "./client";
import type { ResourceRead, ResourceCreate, ResourceUpdate } from "./types";

/**
 * List all resources in the current workspace
 */
export async function listResources(authToken?: string): Promise<ResourceRead[]> {
  return fetchApi<ResourceRead[]>('/api/resources', {}, authToken);
}

/**
 * Get a single resource by ID
 */
export async function getResource(id: string, authToken?: string): Promise<ResourceRead> {
  return fetchApi<ResourceRead>(`/api/resources/${id}`, {}, authToken);
}

/**
 * Create a new resource
 */
export async function createResource(data: ResourceCreate, authToken?: string): Promise<ResourceRead> {
  return fetchApi<ResourceRead>('/api/resources', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, authToken);
}

/**
 * Update an existing resource
 */
export async function updateResource(id: string, data: ResourceUpdate, authToken?: string): Promise<ResourceRead> {
  return fetchApi<ResourceRead>(`/api/resources/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, authToken);
}

/**
 * Delete a resource
 */
export async function deleteResource(id: string, authToken?: string): Promise<void> {
  return fetchApi<void>(`/api/resources/${id}`, {
    method: 'DELETE',
  }, authToken);
}

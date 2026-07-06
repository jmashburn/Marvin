/**
 * Collections API client
 */

import { fetchApi } from "./client";
import type {
  CollectionRead,
  CollectionCreate,
  CollectionUpdate,
} from "./types";

/**
 * List all collections in the current workspace
 */
export async function listCollections(authToken?: string): Promise<CollectionRead[]> {
  return fetchApi<CollectionRead[]>('/api/platform/collections', {}, authToken);
}

/**
 * Get a single collection by ID
 */
export async function getCollection(id: string, authToken?: string): Promise<CollectionRead> {
  return fetchApi<CollectionRead>(`/api/platform/collections/${id}`, {}, authToken);
}

/**
 * Create a new collection
 */
export async function createCollection(data: CollectionCreate, authToken?: string): Promise<CollectionRead> {
  return fetchApi<CollectionRead>('/api/platform/collections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, authToken);
}

/**
 * Update an existing collection
 */
export async function updateCollection(id: string, data: CollectionUpdate, authToken?: string): Promise<CollectionRead> {
  return fetchApi<CollectionRead>(`/api/platform/collections/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, authToken);
}

/**
 * Delete a collection
 */
export async function deleteCollection(id: string, authToken?: string): Promise<void> {
  return fetchApi<void>(`/api/platform/collections/${id}`, {
    method: 'DELETE',
  }, authToken);
}

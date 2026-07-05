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
  return fetchApi<CollectionRead[]>('/api/collections', {}, authToken);
}

/**
 * Get a single collection by ID
 */
export async function getCollection(id: string): Promise<CollectionRead> {
  return fetchApi<CollectionRead>(`/api/collections/${id}`);
}

/**
 * Create a new collection
 */
export async function createCollection(data: CollectionCreate): Promise<CollectionRead> {
  return fetchApi<CollectionRead>('/api/collections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing collection
 */
export async function updateCollection(id: string, data: CollectionUpdate): Promise<CollectionRead> {
  return fetchApi<CollectionRead>(`/api/collections/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

/**
 * Delete a collection
 */
export async function deleteCollection(id: string): Promise<void> {
  return fetchApi<void>(`/api/collections/${id}`, {
    method: 'DELETE',
  });
}

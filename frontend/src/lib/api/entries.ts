/**
 * Entries API client
 */

import { fetchApi } from "./client";
import type {
  EntryRead,
  EntryCreate,
  EntryUpdate,
  CollectionRead,
} from "./types";

/**
 * List all entries in the current workspace
 */
export async function listEntries(authToken?: string): Promise<EntryRead[]> {
  return fetchApi<EntryRead[]>('/api/platform/entries', {}, authToken);
}

/**
 * Get a single entry by ID
 */
export async function getEntry(id: string, authToken?: string): Promise<EntryRead> {
  return fetchApi<EntryRead>(`/api/platform/entries/${id}`, {}, authToken);
}

/**
 * Create a new entry
 */
export async function createEntry(data: EntryCreate, authToken?: string): Promise<EntryRead> {
  return fetchApi<EntryRead>('/api/platform/entries', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, authToken);
}

/**
 * Update an existing entry
 */
export async function updateEntry(id: string, data: EntryUpdate, authToken?: string): Promise<EntryRead> {
  return fetchApi<EntryRead>(`/api/platform/entries/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, authToken);
}

/**
 * Delete an entry
 */
export async function deleteEntry(id: string, authToken?: string): Promise<void> {
  return fetchApi<void>(`/api/platform/entries/${id}`, {
    method: 'DELETE',
  }, authToken);
}

/**
 * Get collections that contain this entry
 */
export async function getEntryCollections(entryId: string, authToken?: string): Promise<CollectionRead[]> {
  return fetchApi<CollectionRead[]>(`/api/platform/entries/${entryId}/collections`, {}, authToken);
}

/**
 * Add an entry to a collection
 */
export async function addEntryToCollection(entryId: string, collectionId: string, authToken?: string): Promise<void> {
  return fetchApi<void>(`/api/platform/entries/${entryId}/collections/${collectionId}`, {
    method: 'POST',
  }, authToken);
}

/**
 * Remove an entry from a collection
 */
export async function removeEntryFromCollection(entryId: string, collectionId: string, authToken?: string): Promise<void> {
  return fetchApi<void>(`/api/platform/entries/${entryId}/collections/${collectionId}`, {
    method: 'DELETE',
  }, authToken);
}

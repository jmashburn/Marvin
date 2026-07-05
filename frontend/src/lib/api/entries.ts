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
export async function listEntries(): Promise<EntryRead[]> {
  return fetchApi<EntryRead[]>('/api/entries');
}

/**
 * Get a single entry by ID
 */
export async function getEntry(id: string): Promise<EntryRead> {
  return fetchApi<EntryRead>(`/api/entries/${id}`);
}

/**
 * Create a new entry
 */
export async function createEntry(data: EntryCreate): Promise<EntryRead> {
  return fetchApi<EntryRead>('/api/entries', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing entry
 */
export async function updateEntry(id: string, data: EntryUpdate): Promise<EntryRead> {
  return fetchApi<EntryRead>(`/api/entries/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

/**
 * Delete an entry
 */
export async function deleteEntry(id: string): Promise<void> {
  return fetchApi<void>(`/api/entries/${id}`, {
    method: 'DELETE',
  });
}

/**
 * Get collections that contain this entry
 */
export async function getEntryCollections(entryId: string): Promise<CollectionRead[]> {
  return fetchApi<CollectionRead[]>(`/api/entries/${entryId}/collections`);
}

/**
 * Add an entry to a collection
 */
export async function addEntryToCollection(entryId: string, collectionId: string): Promise<void> {
  return fetchApi<void>(`/api/entries/${entryId}/collections/${collectionId}`, {
    method: 'POST',
  });
}

/**
 * Remove an entry from a collection
 */
export async function removeEntryFromCollection(entryId: string, collectionId: string): Promise<void> {
  return fetchApi<void>(`/api/entries/${entryId}/collections/${collectionId}`, {
    method: 'DELETE',
  });
}

/**
 * Entry Types API client
 */

import { fetchApi } from "./client";
import type {
  EntryTypeRead,
  EntryTypeCreate,
  EntryTypeUpdate,
} from "./types";

/**
 * List all entry types in the current workspace
 */
export async function listEntryTypes(): Promise<EntryTypeRead[]> {
  return fetchApi<EntryTypeRead[]>('/api/entry-types');
}

/**
 * Get a single entry type by ID
 */
export async function getEntryType(id: string): Promise<EntryTypeRead> {
  return fetchApi<EntryTypeRead>(`/api/entry-types/${id}`);
}

/**
 * Create a new entry type
 */
export async function createEntryType(data: EntryTypeCreate): Promise<EntryTypeRead> {
  return fetchApi<EntryTypeRead>('/api/entry-types', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing entry type
 */
export async function updateEntryType(id: string, data: EntryTypeUpdate): Promise<EntryTypeRead> {
  return fetchApi<EntryTypeRead>(`/api/entry-types/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

/**
 * Delete an entry type
 */
export async function deleteEntryType(id: string): Promise<void> {
  return fetchApi<void>(`/api/entry-types/${id}`, {
    method: 'DELETE',
  });
}

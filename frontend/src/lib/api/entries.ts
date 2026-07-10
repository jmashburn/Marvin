/**
 * Entries API client - SDK wrapper
 * Migrated to use @inneropen/marvin-sdk
 */

import { createSdkClient } from '../sdk';
import type {
  PlatformEntry,
  PlatformEntryCreate,
  PlatformEntryUpdate,
  PlatformCollection,
} from '@inneropen/marvin-sdk/platform';

// Re-export SDK types with legacy names for backward compatibility
export type EntryRead = PlatformEntry;
export type EntryCreate = PlatformEntryCreate;
export type EntryUpdate = PlatformEntryUpdate;
export type CollectionRead = PlatformCollection;

/**
 * List all entries in the current workspace
 */
export async function listEntries(authToken: string): Promise<EntryRead[]> {
  const sdk = createSdkClient(authToken);
  return sdk.entries.list();
}

/**
 * Get a single entry by ID
 */
export async function getEntry(id: string, authToken: string): Promise<EntryRead> {
  const sdk = createSdkClient(authToken);
  return sdk.entries.get(id);
}

/**
 * Create a new entry
 */
export async function createEntry(data: EntryCreate, authToken: string): Promise<EntryRead> {
  const sdk = createSdkClient(authToken);
  return sdk.entries.create(data);
}

/**
 * Update an existing entry
 */
export async function updateEntry(id: string, data: EntryUpdate, authToken: string): Promise<EntryRead> {
  const sdk = createSdkClient(authToken);
  return sdk.entries.update(id, data);
}

/**
 * Delete an entry
 */
export async function deleteEntry(id: string, authToken: string): Promise<void> {
  const sdk = createSdkClient(authToken);
  return sdk.entries.delete(id);
}

/**
 * Get collections that contain this entry
 */
export async function getEntryCollections(entryId: string, authToken: string): Promise<CollectionRead[]> {
  const sdk = createSdkClient(authToken);
  return sdk.entries.listCollections(entryId);
}

/**
 * Add an entry to a collection
 */
export async function addEntryToCollection(entryId: string, collectionId: string, authToken: string): Promise<void> {
  const sdk = createSdkClient(authToken);
  await sdk.entries.addToCollection(entryId, collectionId);
}

/**
 * Remove an entry from a collection
 */
export async function removeEntryFromCollection(entryId: string, collectionId: string, authToken: string): Promise<void> {
  const sdk = createSdkClient(authToken);
  return sdk.entries.removeFromCollection(entryId, collectionId);
}

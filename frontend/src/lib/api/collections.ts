/**
 * Collections API client - SDK wrapper
 * Migrated to use @inneropen/marvin-sdk
 */

import { createSdkClient } from '../sdk';
import type {
  PlatformCollection,
  PlatformCollectionCreate,
  PlatformCollectionUpdate,
  PlatformEntry,
} from '@inneropen/marvin-sdk/platform';

// Re-export SDK types with legacy names for backward compatibility
export type CollectionRead = PlatformCollection;
export type CollectionCreate = PlatformCollectionCreate;
export type CollectionUpdate = PlatformCollectionUpdate;
export type EntryRead = PlatformEntry;

/**
 * List all collections in the current workspace
 */
export async function listCollections(authToken: string): Promise<CollectionRead[]> {
  const sdk = createSdkClient(authToken);
  return sdk.collections.list();
}

/**
 * Get a single collection by ID
 */
export async function getCollection(id: string, authToken: string): Promise<CollectionRead> {
  const sdk = createSdkClient(authToken);
  return sdk.collections.get(id);
}

/**
 * Create a new collection
 */
export async function createCollection(data: CollectionCreate, authToken: string): Promise<CollectionRead> {
  const sdk = createSdkClient(authToken);
  return sdk.collections.create(data);
}

/**
 * Update an existing collection
 */
export async function updateCollection(id: string, data: CollectionUpdate, authToken: string): Promise<CollectionRead> {
  const sdk = createSdkClient(authToken);
  return sdk.collections.update(id, data);
}

/**
 * Delete a collection
 */
export async function deleteCollection(id: string, authToken: string): Promise<void> {
  const sdk = createSdkClient(authToken);
  return sdk.collections.delete(id);
}

/**
 * Get entries in a collection
 */
export async function getCollectionEntries(collectionId: string, authToken: string): Promise<EntryRead[]> {
  const sdk = createSdkClient(authToken);
  return sdk.collections.getEntries(collectionId);
}

/**
 * Update junction fields (role, metadata) for an entry in a collection
 */
export async function updateCollectionEntry(
  collectionId: string,
  entryId: string,
  data: { role?: string | null; metadataJson?: Record<string, unknown> | null },
  authToken: string
): Promise<void> {
  const sdk = createSdkClient(authToken);
  return sdk.collections.updateEntryJunction(collectionId, entryId, data);
}

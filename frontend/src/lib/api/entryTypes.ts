/**
 * Entry Types API client - SDK wrapper
 * Migrated to use @inneropen/marvin-sdk
 */

import { createSdkClient } from '../sdk';
import type { PlatformEntryType } from '@inneropen/marvin-sdk/platform';

// Re-export SDK types with legacy names for backward compatibility
export type EntryTypeRead = PlatformEntryType;

/**
 * List all entry types in the current workspace
 */
export async function listEntryTypes(authToken: string): Promise<EntryTypeRead[]> {
  const sdk = createSdkClient(authToken);
  return sdk.entryTypes.list();
}

/**
 * Get a single entry type by ID
 */
export async function getEntryType(id: string, authToken: string): Promise<EntryTypeRead> {
  const sdk = createSdkClient(authToken);
  return sdk.entryTypes.get(id);
}

/**
 * Marvin Publishing Client
 *
 * Portable TypeScript client for fetching published content from Marvin CMS.
 *
 * @example
 * ```ts
 * import { createMarvinClient } from '@/lib/marvin';
 *
 * const marvin = createMarvinClient();
 * const entries = await marvin.getEntries();
 * ```
 */

export { MarvinClient, createMarvinClient } from './client';
export type {
  MarvinSite,
  MarvinEntry,
  MarvinEntryType,
  MarvinCollection,
  MarvinAsset,
  MarvinPublishResponse,
  MarvinClientConfig,
  GetEntriesOptions,
  GetAssetsOptions,
} from './types';

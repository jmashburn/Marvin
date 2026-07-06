/**
 * Marvin TypeScript SDK
 *
 * The official SDK for integrating with Marvin CMS.
 *
 * @example
 * ```ts
 * import { createMarvinClient } from '@marvin/sdk';
 *
 * const marvin = createMarvinClient();
 *
 * // Workspace-first API
 * const workspace = await marvin.getWorkspace();
 * const entries = await workspace.entries.list();
 *
 * // Convenience API
 * const entry = await marvin.entry('about');
 * const projects = await marvin.projects();
 *
 * // Backwards-compatible API
 * const site = await marvin.getSite();
 * ```
 */

export { MarvinClient } from './client/marvin';
export { createConfigFromEnv } from './client/config';
export type { MarvinConfig } from './client/config';

// Types
export type {
  MarvinSite,
  MarvinEntry,
  MarvinEntryType,
  MarvinCollection,
  MarvinAsset,
  MarvinPublishResponse,
  GetEntriesOptions,
  GetAssetsOptions,
} from './types';

// Workspace & Modules
export { Workspace } from './workspaces/workspace';
export { Entry } from './entries/entry';
export { Collection } from './collections/collection';

/**
 * Create a Marvin client instance from environment variables
 *
 * @param config - Optional configuration overrides
 * @returns Configured Marvin client
 *
 * @example
 * ```ts
 * // From environment variables
 * const marvin = createMarvinClient();
 *
 * // With overrides
 * const marvin = createMarvinClient({
 *   apiUrl: 'https://marvin.example.com',
 *   autoInitialize: true
 * });
 * ```
 */
export function createMarvinClient(config?: Partial<import('./client/config').MarvinConfig>): import('./client/marvin').MarvinClient {
  const { MarvinClient } = require('./client/marvin');
  const { createConfigFromEnv } = require('./client/config');

  const finalConfig = createConfigFromEnv(config);
  return new MarvinClient(finalConfig);
}

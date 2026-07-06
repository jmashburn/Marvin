/**
 * Marvin Publishing Client
 *
 * A portable TypeScript client for fetching published content from Marvin.
 * Designed for use in Astro and other static site generators.
 */

import type {
  MarvinSite,
  MarvinEntry,
  MarvinCollection,
  MarvinAsset,
  MarvinClientConfig,
  GetEntriesOptions,
  GetAssetsOptions,
} from './types';

export class MarvinClient {
  private config: MarvinClientConfig;

  constructor(config: MarvinClientConfig) {
    this.validateConfig(config);
    this.config = config;
  }

  private validateConfig(config: MarvinClientConfig): void {
    if (!config.apiUrl) {
      throw new Error('MARVIN_API_URL is required');
    }
    if (!config.siteClientToken) {
      throw new Error('MARVIN_SITE_CLIENT_TOKEN is required');
    }
    if (!config.workspaceSlug) {
      throw new Error('MARVIN_WORKSPACE_SLUG is required');
    }
  }

  private async fetch<T>(endpoint: string): Promise<T> {
    const url = `${this.config.apiUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${this.config.siteClientToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `Marvin API error: ${response.status} ${response.statusText} at ${endpoint}\n${errorText}`
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof Error) {
        // Don't leak the token in error messages
        const safeMessage = error.message.replace(
          this.config.siteClientToken,
          '[REDACTED]'
        );
        throw new Error(safeMessage);
      }
      throw error;
    }
  }

  private buildQueryString(params: Record<string, string | number | undefined>): string {
    const filtered = Object.entries(params)
      .filter(([_, value]) => value !== undefined)
      .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`);

    return filtered.length > 0 ? `?${filtered.join('&')}` : '';
  }

  /**
   * Get site configuration and metadata
   *
   * @returns Site configuration including title, description, and metadata
   */
  async getSite(): Promise<MarvinSite> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/site
    const endpoint = `/api/publish/${this.config.workspaceSlug}/site`;
    return this.fetch<MarvinSite>(endpoint);
  }

  /**
   * Get all published entries
   *
   * @param options - Filtering and pagination options
   * @returns Array of published entries
   */
  async getEntries(options: GetEntriesOptions = {}): Promise<MarvinEntry[]> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/entries
    const queryString = this.buildQueryString({
      entry_type: options.entryType,
      collection: options.collection,
      limit: options.limit,
      offset: options.offset,
      status: options.status || 'published',
    });

    const endpoint = `/api/publish/${this.config.workspaceSlug}/entries${queryString}`;
    return this.fetch<MarvinEntry[]>(endpoint);
  }

  /**
   * Get a single published entry by slug
   *
   * @param slug - The entry slug
   * @returns Single entry with full content
   */
  async getEntry(slug: string): Promise<MarvinEntry> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/entries/{slug}
    const endpoint = `/api/publish/${this.config.workspaceSlug}/entries/${slug}`;
    return this.fetch<MarvinEntry>(endpoint);
  }

  /**
   * Get all collections
   *
   * @returns Array of collections
   */
  async getCollections(): Promise<MarvinCollection[]> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/collections
    const endpoint = `/api/publish/${this.config.workspaceSlug}/collections`;
    return this.fetch<MarvinCollection[]>(endpoint);
  }

  /**
   * Get a single collection by slug
   *
   * @param slug - The collection slug
   * @returns Single collection
   */
  async getCollection(slug: string): Promise<MarvinCollection> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/collections/{slug}
    const endpoint = `/api/publish/${this.config.workspaceSlug}/collections/${slug}`;
    return this.fetch<MarvinCollection>(endpoint);
  }

  /**
   * Get all entries in a collection
   *
   * @param slug - The collection slug
   * @returns Array of entries in the collection
   */
  async getCollectionEntries(slug: string): Promise<MarvinEntry[]> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/collections/{slug}/entries
    const endpoint = `/api/publish/${this.config.workspaceSlug}/collections/${slug}/entries`;
    return this.fetch<MarvinEntry[]>(endpoint);
  }

  /**
   * Get all published assets
   *
   * @param options - Filtering and pagination options
   * @returns Array of assets
   */
  async getAssets(options: GetAssetsOptions = {}): Promise<MarvinAsset[]> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/assets
    const queryString = this.buildQueryString({
      type: options.type,
      limit: options.limit,
      offset: options.offset,
    });

    const endpoint = `/api/publish/${this.config.workspaceSlug}/assets${queryString}`;
    return this.fetch<MarvinAsset[]>(endpoint);
  }
}

/**
 * Create a Marvin client instance from environment variables
 *
 * @returns Configured Marvin client
 */
export function createMarvinClient(config?: Partial<MarvinClientConfig>): MarvinClient {
  const finalConfig: MarvinClientConfig = {
    apiUrl: config?.apiUrl || process.env.MARVIN_API_URL || '',
    siteClientToken: config?.siteClientToken || process.env.MARVIN_SITE_CLIENT_TOKEN || '',
    workspaceSlug: config?.workspaceSlug || process.env.MARVIN_WORKSPACE_SLUG || '',
  };

  return new MarvinClient(finalConfig);
}

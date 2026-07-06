/**
 * Resources Module - Manage resources
 */

import type { MarvinHttpClient } from '../client/http';
import type { MarvinResource, MarvinEntry } from '../types';
import { Resource } from './resource';

export interface GetResourcesOptions {
  resourceType?: string;
  limit?: number;
  offset?: number;
}

export class ResourcesModule {
  constructor(
    private http: MarvinHttpClient,
    private workspaceSlug: string
  ) {}

  /**
   * Get all published resources
   */
  async list(options: GetResourcesOptions = {}): Promise<MarvinResource[]> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/resources
    const queryString = this.http.buildQueryString({
      resource_type: options.resourceType,
      limit: options.limit,
      offset: options.offset,
    });

    const endpoint = `/api/publish/${this.workspaceSlug}/resources${queryString}`;
    return this.http.fetch<MarvinResource[]>(endpoint);
  }

  /**
   * Get a single resource by slug
   */
  async get(slug: string): Promise<Resource> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/resources/{slug}
    const endpoint = `/api/publish/${this.workspaceSlug}/resources/${slug}`;
    const data = await this.http.fetch<MarvinResource>(endpoint);
    return new Resource(data, this.http, this.workspaceSlug);
  }

  /**
   * Get entries that reference this resource
   */
  async entries(slug: string): Promise<MarvinEntry[]> {
    const resource = await this.get(slug);
    return resource.entries();
  }
}

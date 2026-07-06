/**
 * Resource - Rich object representing a single resource
 */

import type { MarvinHttpClient } from '../client/http';
import type { MarvinResource, MarvinEntry, MarvinAsset } from '../types';

export class Resource {
  constructor(
    private data: MarvinResource,
    private http: MarvinHttpClient,
    private workspaceSlug: string
  ) {}

  // Expose all resource data as properties
  get id() { return this.data.id; }
  get name() { return this.data.name; }
  get slug() { return this.data.slug; }
  get resourceType() { return this.data.resourceType; }
  get description() { return this.data.description; }
  get externalId() { return this.data.externalId; }
  get url() { return this.data.url; }
  get metadata() { return this.data.metadata; }
  get createdAt() { return this.data.createdAt; }
  get updatedAt() { return this.data.updatedAt; }

  /**
   * Get all entries that reference this resource
   */
  async entries(): Promise<MarvinEntry[]> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/resources/{slug}/entries
    const endpoint = `/api/publish/${this.workspaceSlug}/resources/${this.data.slug}/entries`;
    return this.http.fetch<MarvinEntry[]>(endpoint);
  }

  /**
   * Get assets related to this resource (future)
   */
  async assets(): Promise<MarvinAsset[]> {
    // TODO: Implement resource assets endpoint
    // Expected: GET /api/publish/{workspaceSlug}/resources/{slug}/assets
    throw new Error('Resource assets not yet implemented');
  }

  /**
   * Get raw resource data
   */
  toJSON(): MarvinResource {
    return this.data;
  }
}

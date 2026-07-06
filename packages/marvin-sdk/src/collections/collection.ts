/**
 * Collection - Rich object representing a single collection
 */

import type { MarvinHttpClient } from '../client/http';
import type { MarvinCollection, MarvinEntry, MarvinAsset } from '../types';

export class Collection {
  constructor(
    private data: MarvinCollection,
    private http: MarvinHttpClient,
    private workspaceSlug: string
  ) {}

  // Expose all collection data as properties
  get id() { return this.data.id; }
  get name() { return this.data.name; }
  get slug() { return this.data.slug; }
  get description() { return this.data.description; }
  get icon() { return this.data.icon; }
  get color() { return this.data.color; }
  get sortOrder() { return this.data.sortOrder; }
  get isSmart() { return this.data.isSmart; }
  get smartRules() { return this.data.smartRules; }
  get createdAt() { return this.data.createdAt; }
  get updatedAt() { return this.data.updatedAt; }

  /**
   * Get all entries in this collection
   */
  async entries(): Promise<MarvinEntry[]> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/collections/{slug}/entries
    const endpoint = `/api/publish/${this.workspaceSlug}/collections/${this.data.slug}/entries`;
    return this.http.fetch<MarvinEntry[]>(endpoint);
  }

  /**
   * Get assets in this collection (future)
   */
  async assets(): Promise<MarvinAsset[]> {
    // TODO: Implement collection assets endpoint
    throw new Error('Collection assets not yet implemented');
  }

  /**
   * Get collection metadata (future)
   */
  async metadata(): Promise<any> {
    // TODO: Implement collection metadata endpoint
    throw new Error('Collection metadata not yet implemented');
  }

  /**
   * Get raw collection data
   */
  toJSON(): MarvinCollection {
    return this.data;
  }
}

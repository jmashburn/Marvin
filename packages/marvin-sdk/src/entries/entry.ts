/**
 * Entry - Rich object representing a single entry
 */

import type { MarvinHttpClient } from '../client/http';
import type { MarvinEntry, MarvinAsset, MarvinCollection } from '../types';

export class Entry {
  constructor(
    private data: MarvinEntry,
    private http: MarvinHttpClient,
    private workspaceSlug: string
  ) {}

  // Expose all entry data as properties
  get id() { return this.data.id; }
  get title() { return this.data.title; }
  get slug() { return this.data.slug; }
  get summary() { return this.data.summary; }
  get description() { return this.data.description; }
  get contentMarkdown() { return this.data.contentMarkdown; }
  get metadataJson() { return this.data.metadataJson; }
  get status() { return this.data.status; }
  get publishedAt() { return this.data.publishedAt; }
  get createdAt() { return this.data.createdAt; }
  get updatedAt() { return this.data.updatedAt; }
  get entryTypeId() { return this.data.entryTypeId; }
  get entryType() { return this.data.entryType; }

  /**
   * Get entry assets
   */
  get assets(): MarvinAsset[] {
    return this.data.assets || [];
  }

  /**
   * Get entry collections
   */
  get collections(): MarvinCollection[] {
    return this.data.collections || [];
  }

  /**
   * Get related entries (future)
   */
  async relatedEntries(): Promise<MarvinEntry[]> {
    // TODO: Implement related entries endpoint
    throw new Error('Related entries not yet implemented');
  }

  /**
   * Get raw entry data
   */
  toJSON(): MarvinEntry {
    return this.data;
  }
}

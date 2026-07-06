/**
 * Entries Module - Manage entries
 */

import type { MarvinHttpClient } from '../client/http';
import type { MarvinEntry } from '../types';
import { Entry } from './entry';

export interface GetEntriesOptions {
  entryType?: string;
  collection?: string;
  limit?: number;
  offset?: number;
  status?: string;
}

export class EntriesModule {
  constructor(
    private http: MarvinHttpClient,
    private workspaceSlug: string
  ) {}

  /**
   * Get all published entries
   */
  async list(options: GetEntriesOptions = {}): Promise<MarvinEntry[]> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/entries
    const queryString = this.http.buildQueryString({
      entry_type: options.entryType,
      collection: options.collection,
      limit: options.limit,
      offset: options.offset,
      status: options.status || 'published',
    });

    const endpoint = `/api/publish/${this.workspaceSlug}/entries${queryString}`;
    return this.http.fetch<MarvinEntry[]>(endpoint);
  }

  /**
   * Get a single entry by slug
   */
  async get(slug: string): Promise<Entry> {
    // TODO: Implement this endpoint in Marvin backend
    // Expected: GET /api/publish/{workspaceSlug}/entries/{slug}
    const endpoint = `/api/publish/${this.workspaceSlug}/entries/${slug}`;
    const data = await this.http.fetch<MarvinEntry>(endpoint);
    return new Entry(data, this.http, this.workspaceSlug);
  }

  /**
   * Convenience: Get all pages
   */
  async pages(options?: Omit<GetEntriesOptions, 'entryType'>): Promise<MarvinEntry[]> {
    return this.list({ ...options, entryType: 'page' });
  }

  /**
   * Convenience: Get all blog posts
   */
  async posts(options?: Omit<GetEntriesOptions, 'entryType'>): Promise<MarvinEntry[]> {
    return this.list({ ...options, entryType: 'blog' });
  }

  /**
   * Convenience: Get all projects
   */
  async projects(options?: Omit<GetEntriesOptions, 'entryType'>): Promise<MarvinEntry[]> {
    return this.list({ ...options, entryType: 'project' });
  }
}

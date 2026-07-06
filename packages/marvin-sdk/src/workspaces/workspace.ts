/**
 * Workspace - First-class object representing a Marvin workspace
 */

import type { MarvinHttpClient } from '../client/http';
import type { MarvinSite } from '../types';
import { EntriesModule } from '../entries/entries';
import { CollectionsModule } from '../collections/collections';
import { AssetsModule } from '../assets/assets';
import { ResourcesModule } from '../resources/resources';

export class Workspace {
  private _site: MarvinSite | null = null;
  private _slug: string;

  public entries: EntriesModule;
  public collections: CollectionsModule;
  public assets: AssetsModule;
  public resources: ResourcesModule;

  constructor(
    private http: MarvinHttpClient,
    slug: string
  ) {
    this._slug = slug;
    this.entries = new EntriesModule(http, slug);
    this.collections = new CollectionsModule(http, slug);
    this.assets = new AssetsModule(http, slug);
    this.resources = new ResourcesModule(http, slug);
  }

  /**
   * Get workspace slug
   */
  get slug(): string {
    return this._slug;
  }

  /**
   * Get site configuration (cached after first load)
   */
  get site(): MarvinSite | null {
    return this._site;
  }

  /**
   * Load site configuration
   */
  async loadSite(): Promise<MarvinSite> {
    const endpoint = `/api/publish/${this._slug}/site`;
    this._site = await this.http.fetch<MarvinSite>(endpoint);
    return this._site;
  }

  /**
   * Get workspace info (name and slug only)
   */
  async getInfo(): Promise<{ slug: string; name: string }> {
    const endpoint = `/api/publish/${this._slug}`;
    return this.http.fetch<{ slug: string; name: string }>(endpoint);
  }

  /**
   * Get workspace settings (future)
   */
  async settings(): Promise<any> {
    // TODO: Implement settings endpoint
    throw new Error('Workspace settings not yet implemented');
  }
}

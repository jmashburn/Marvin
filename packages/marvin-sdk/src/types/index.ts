/**
 * Marvin Publishing Client Types
 *
 * TypeScript types for the Marvin publishing API responses.
 */

export interface MarvinSite {
  id: string;
  name: string;
  slug: string;
  title?: string;
  tagline?: string;
  description?: string;
  canonicalUrl?: string;
  logo?: string;
  favicon?: string;
  locale?: string;
  timezone?: string;
  metadata?: Record<string, unknown>;
}

export interface MarvinEntryType {
  id: string;
  name: string;
  slug: string;
  icon?: string;
  color?: string;
  description?: string;
  sortOrder: number;
  isSystem: boolean;
}

export interface MarvinAsset {
  id: string;
  name: string;
  slug: string;
  url: string;
  mimeType: string;
  fileSize?: number;
  width?: number;
  height?: number;
  altText?: string;
  description?: string;
  focalPoint?: string;
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface MarvinCollection {
  id: string;
  name: string;
  slug: string;
  description?: string;
  icon?: string;
  color?: string;
  sortOrder: number;
  isSmart: boolean;
  smartRules?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface MarvinEntry {
  id: string;
  title: string;
  slug: string;
  summary?: string;
  description?: string;
  contentMarkdown?: string;
  metadataJson?: Record<string, unknown>;
  status: string;
  publishedAt?: string;
  createdAt: string;
  updatedAt: string;

  // Relationships
  entryTypeId: string;
  entryType?: MarvinEntryType;
  collections?: MarvinCollection[];
  assets?: MarvinAsset[];
}

export interface MarvinPublishResponse<T> {
  data: T;
  meta?: {
    total?: number;
    page?: number;
    limit?: number;
  };
}

export interface MarvinClientConfig {
  apiUrl: string;
  siteClientToken: string;
  workspaceSlug: string;
}

export interface GetEntriesOptions {
  entryType?: string;
  collection?: string;
  limit?: number;
  offset?: number;
  status?: string;
}

export interface GetAssetsOptions {
  type?: string;
  limit?: number;
  offset?: number;
}

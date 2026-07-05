export type EntryStatus = "draft" | "review" | "published";

export type EntryType = "project" | "bench_note" | "reference" | "article" | "product" | string;

export type AssetPlacementRole = "hero" | "featured" | "support" | "inline" | "download" | string;

export type AssetPlacementUsage = "material" | "process" | "detail" | "texture" | "workshop" | string;

export interface MarvinAsset {
  id: string;
  slug: string;
  name: string;
  url?: string;
  mime_type: string;
  alt_text?: string | null;
  file_size?: number;
  width?: number | null;
  height?: number | null;
  description?: string | null;
  metadata?: Record<string, unknown> | null;
  role?: AssetPlacementRole | null;
  usage?: AssetPlacementUsage | null;
  position?: number;
  focal_point?: string | null;
  caption?: string | null;
  placement_metadata?: Record<string, unknown> | null;
}

export interface MarvinEntry {
  id: string;
  slug: string;
  title: string;
  entry_type: EntryType;
  summary?: string | null;
  content_markdown?: string;
  frontmatter?: Record<string, unknown> | null;
  status: EntryStatus;
  published_at?: string | null;
  collections?: string[];
  resources?: string[];
  assets?: MarvinAsset[];
}

export interface SiteClient {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  permissions: string[];
  last_used_at?: string | null;
}

export interface ApiListResponse<T> {
  data: T[];
  meta?: {
    total?: number;
    page?: number;
    page_size?: number;
  };
}

// Enums
export type EntryStatus = "inbox" | "processing" | "draft" | "needs_review" | "approved" | "published" | "archived";

export type WorkspaceRole = "OWNER" | "ADMIN" | "CONTRIBUTOR" | "VIEWER";

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

// ===== Workspace/Group Types =====

export interface GroupPreferencesRead {
  private_group: boolean;
  first_day_of_week: number;
  recipe_public: boolean;
  recipe_show_nutrition: boolean;
  recipe_show_assets: boolean;
  recipe_landscape_view: boolean;
  recipe_disable_comments: boolean;
  recipe_disable_amount: boolean;
}

export interface GroupPreferencesUpdate extends Partial<GroupPreferencesRead> {}

export interface GroupCreate {
  name: string;
}

export interface GroupAdminUpdate {
  id: string;
  name: string;
  preferences?: GroupPreferencesUpdate | null;
}

export interface UserSummary {
  id: string;
  username: string;
  email: string;
  full_name?: string | null;
}

export interface GroupRead {
  id: string;
  name: string;
  slug?: string | null;
  users?: UserSummary[] | null;
  preferences?: GroupPreferencesRead | null;
  webhooks?: unknown[];
}

export interface WorkspaceActivationRequest {
  workspace_id: string;
}

export interface WorkspaceWithMembership {
  workspace: GroupRead;
  role: WorkspaceRole;
  is_active: boolean;
}

// ===== Entry Type Types =====

export interface EntryTypeCreate {
  name: string;
  slug: string;
  icon?: string | null;
  color?: string | null;
  description?: string | null;
  sort_order?: number;
  is_system?: boolean;
}

export interface EntryTypeUpdate {
  name?: string;
  slug?: string;
  icon?: string | null;
  color?: string | null;
  description?: string | null;
  sort_order?: number;
  is_system?: boolean;
}

export interface EntryTypeRead {
  id: string;
  group_id: string;
  name: string;
  slug: string;
  icon?: string | null;
  color?: string | null;
  description?: string | null;
  sort_order: number;
  is_system: boolean;
  created_at?: string | null;
  update_at?: string | null;
}

// ===== Collection Types =====

export interface CollectionCreate {
  name: string;
  slug: string;
  description?: string | null;
  sort_order?: number;
  icon?: string | null;
  color?: string | null;
  is_smart?: boolean;
  smart_rules?: Record<string, unknown> | null;
}

export interface CollectionUpdate {
  name?: string;
  slug?: string;
  description?: string | null;
  sort_order?: number;
  icon?: string | null;
  color?: string | null;
  is_smart?: boolean;
  smart_rules?: Record<string, unknown> | null;
}

export interface CollectionRead {
  id: string;
  group_id: string;
  name: string;
  slug: string;
  description?: string | null;
  sort_order: number;
  icon?: string | null;
  color?: string | null;
  is_smart: boolean;
  smart_rules?: Record<string, unknown> | null;
  created_at?: string | null;
  update_at?: string | null;
}

// ===== Entry Types =====

export interface ResourceSummary {
  id: string;
  name: string;
  slug: string;
}

export interface EntryCreate {
  entry_type_id: string;
  title: string;
  slug: string;
  summary?: string | null;
  description?: string | null;
  content_markdown?: string | null;
  status?: EntryStatus;
  published_at?: string | null;
}

export interface EntryUpdate {
  entry_type_id?: string;
  title?: string;
  slug?: string;
  summary?: string | null;
  description?: string | null;
  content_markdown?: string | null;
  status?: EntryStatus;
  published_at?: string | null;
}

export interface EntryRead {
  id: string;
  group_id: string;
  entry_type_id: string;
  title: string;
  slug: string;
  summary?: string | null;
  description?: string | null;
  content_markdown?: string | null;
  status: EntryStatus;
  published_at?: string | null;
  created_by?: string | null;
  created_at?: string | null;
  update_at?: string | null;
  resources?: ResourceSummary[];
  assets?: MarvinAsset[];
}

// Backwards compatibility with old interface
export interface MarvinEntry extends EntryRead {
  entry_type: string;
  frontmatter?: Record<string, unknown> | null;
  collections?: string[];
}

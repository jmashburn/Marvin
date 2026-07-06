export type MarvinClientConfig = {
  apiUrl?: string;
  token?: string;
  workspaceSlug?: string;
};

export type MarvinEntry = {
  // Publishing API returns these fields
  slug: string;
  title: string;
  entryType: string; // Entry type slug (e.g., "page", "project")
  summary?: string | null;
  contentMarkdown?: string | null;
  publishedAt?: string | null;
  metadata?: Record<string, unknown> | null;
  collections?: string[]; // Array of collection slugs
  resources?: unknown[];
  assets?: unknown[];

  // Legacy/admin fields
  id?: string;
  status?: string;
  description?: string | null;
  updatedAt?: string | null;
  updateAt?: string | null;
  metadataJson?: Record<string, unknown> | null;
};

export type MarvinCollection = {
  // Publishing API returns these fields
  slug: string;
  name: string;
  description?: string | null;
  entryCount?: number;
  sortOrder?: number;
  icon?: string | null;
  color?: string | null;

  // When fetching single collection with entries
  entries?: MarvinEntry[];

  // Legacy/admin fields
  id?: string;
  collectionType?: string;
  type?: string;
  visibility?: string;
  updatedAt?: string | null;
  updateAt?: string | null;
};

export type MarvinResource = {
  // Publishing API returns these fields
  slug: string;
  name: string;
  resourceType: string; // e.g., "fabric", "tool", "supplier"
  description?: string | null;
  url?: string | null;
  externalId?: string | null;
  metadata?: Record<string, unknown> | null;

  // Legacy/admin fields
  id?: string;
  metadataJson?: Record<string, unknown> | null;
  updatedAt?: string | null;
  updateAt?: string | null;
};

export type MarvinAsset = {
  // Publishing API returns these fields
  slug: string;
  name: string;
  mimeType: string;
  width?: number | null;
  height?: number | null;
  altText?: string | null;
  fileUrl: string;

  // Legacy/admin fields
  id?: string;
  filename?: string;
  originalFilename?: string;
  contentType?: string;
  publicUrl?: string;
};

export type PaginatedResponse<T> = {
  data: T[];
  meta: {
    total?: number;
    page?: number;
    limit?: number;
  };
};

function required(value: string | undefined, name: string): string {
  if (!value || value.trim() === "") {
    throw new Error(`${name} is required. Set it in .env or pass it as a CLI option.`);
  }
  return value.replace(/\/$/, "");
}

function queryString(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value));
  }
  const out = search.toString();
  return out ? `?${out}` : "";
}

export class MarvinApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public endpoint: string,
    body: string,
  ) {
    super(`Marvin API error: ${status} ${statusText} at ${endpoint}${body ? `\n${body}` : ""}`);
  }
}

export function createMarvinClient(config: MarvinClientConfig = {}) {
  const apiUrl = required(config.apiUrl ?? process.env.MARVIN_API_URL, "MARVIN_API_URL");
  const token = required(config.token ?? process.env.MARVIN_SITE_CLIENT_TOKEN, "MARVIN_SITE_CLIENT_TOKEN");
  const workspaceSlug = required(config.workspaceSlug ?? process.env.MARVIN_WORKSPACE_SLUG, "MARVIN_WORKSPACE_SLUG");

  async function request<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${apiUrl}${endpoint}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      const body = await response.text().catch(() => "");
      throw new MarvinApiError(response.status, response.statusText, endpoint, body);
    }

    return (await response.json()) as T;
  }

  const publishBase = `/api/publish/${encodeURIComponent(workspaceSlug)}`;

  return {
    workspaceSlug,
    getSite: () => request<unknown>(`${publishBase}/site`),
    getEntries: async (options: { entryType?: string; collection?: string; limit?: number; offset?: number } = {}) => {
      const response = await request<PaginatedResponse<MarvinEntry>>(`${publishBase}/entries${queryString(options)}`);
      return response.data;
    },
    getEntry: (slug: string) => request<MarvinEntry>(`${publishBase}/entries/${encodeURIComponent(slug)}`),
    getCollections: () => request<MarvinCollection[]>(`${publishBase}/collections`),
    getCollection: (slug: string) => request<MarvinCollection>(`${publishBase}/collections/${encodeURIComponent(slug)}`),
    getCollectionEntries: async (slug: string) => {
      const response = await request<PaginatedResponse<MarvinEntry>>(`${publishBase}/collections/${encodeURIComponent(slug)}/entries`);
      return response.data;
    },
    getAssets: (options: { type?: string; limit?: number; offset?: number } = {}) =>
      request<MarvinAsset[]>(`${publishBase}/assets${queryString(options)}`),
    getResources: () => request<MarvinResource[]>(`${publishBase}/resources`),
    getResource: (slug: string) => request<MarvinResource>(`${publishBase}/resources/${encodeURIComponent(slug)}`),
    getResourceEntries: async (slug: string) => {
      const response = await request<PaginatedResponse<MarvinEntry>>(`${publishBase}/resources/${encodeURIComponent(slug)}/entries`);
      return response.data;
    },
  };
}

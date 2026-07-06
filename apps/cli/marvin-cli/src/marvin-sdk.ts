export type MarvinClientConfig = {
  apiUrl?: string;
  token?: string;
  workspaceSlug?: string;
};

export type MarvinEntry = {
  id?: string;
  title: string;
  slug: string;
  summary?: string | null;
  description?: string | null;
  contentMarkdown?: string | null;
  status?: string;
  updatedAt?: string | null;
  updateAt?: string | null;
  publishedAt?: string | null;
  metadataJson?: Record<string, unknown> | null;
  entryType?: unknown;
  collections?: unknown[];
  assets?: unknown[];
};

export type MarvinCollection = {
  id?: string;
  name: string;
  slug: string;
  description?: string | null;
  collectionType?: string;
  type?: string;
  visibility?: string;
  updatedAt?: string | null;
  updateAt?: string | null;
};

export type MarvinResource = {
  id?: string;
  name: string;
  slug: string;
  resourceType?: string | null;
  description?: string | null;
  metadataJson?: Record<string, unknown> | null;
  updatedAt?: string | null;
  updateAt?: string | null;
};

export type MarvinAsset = {
  id?: string;
  filename?: string;
  originalFilename?: string;
  slug?: string;
  contentType?: string;
  publicUrl?: string;
  altText?: string | null;
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
    getEntries: (options: { entryType?: string; collection?: string; limit?: number; offset?: number } = {}) =>
      request<MarvinEntry[]>(`${publishBase}/entries${queryString(options)}`),
    getEntry: (slug: string) => request<MarvinEntry>(`${publishBase}/entries/${encodeURIComponent(slug)}`),
    getCollections: () => request<MarvinCollection[]>(`${publishBase}/collections`),
    getCollection: (slug: string) => request<MarvinCollection>(`${publishBase}/collections/${encodeURIComponent(slug)}`),
    getCollectionEntries: (slug: string) => request<MarvinEntry[]>(`${publishBase}/collections/${encodeURIComponent(slug)}/entries`),
    getAssets: (options: { type?: string; limit?: number; offset?: number } = {}) =>
      request<MarvinAsset[]>(`${publishBase}/assets${queryString(options)}`),
    getResources: () => request<MarvinResource[]>(`${publishBase}/resources`),
    getResource: (slug: string) => request<MarvinResource>(`${publishBase}/resources/${encodeURIComponent(slug)}`),
    getResourceEntries: (slug: string) => request<MarvinEntry[]>(`${publishBase}/resources/${encodeURIComponent(slug)}/entries`),
  };
}

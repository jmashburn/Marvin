# Astro Integration Guide

This document describes how to integrate Marvin's publishing API with Astro-based static sites.

## Overview

Astro sites consume published content from Marvin via the read-only Publishing API. Each Astro site has its own site client token scoped to a specific workspace.

## Setup

### 1. Create a Site Client in Marvin Admin

In Marvin Admin (`/admin/platform/site-clients`):

1. Click "Create Site Client"
2. Enter site name: `My Astro Site`
3. Enter slug: `my-astro-site`
4. Select permissions:
   - `read:published_entries`
   - `read:collections`
   - `read:assets`
5. Copy the token (shown only once!)
6. Store securely in your Astro environment

### 2. Configure Astro Environment Variables

In `.env.local` (never commit this file):

```bash
# Marvin Publishing API Configuration
MARVIN_API_URL=https://marvin.example.com
MARVIN_SITE_CLIENT_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
MARVIN_GROUP_SLUG=my-workspace
```

### 3. Create a Marvin Client

Create `src/lib/marvin.ts`:

```typescript
const MARVIN_BASE = import.meta.env.MARVIN_API_URL;
const MARVIN_TOKEN = import.meta.env.MARVIN_SITE_CLIENT_TOKEN;
const GROUP_SLUG = import.meta.env.MARVIN_GROUP_SLUG;

interface MarvinEntry {
  id: string;
  slug: string;
  title: string;
  entry_type: string;
  summary?: string;
  content_markdown: string;
  frontmatter?: Record<string, unknown>;
  published_at: string;
  collections?: Array<{ id: string; slug: string; name: string }>;
  assets?: Array<{
    id: string;
    slug: string;
    url: string;
    alt_text?: string;
    role?: 'hero' | 'featured' | 'support' | 'inline' | 'download';
    usage?: 'material' | 'process' | 'detail' | 'texture' | 'workshop';
    position?: number;
    focal_point?: string;
    caption?: string;
    placement_metadata?: Record<string, unknown>;
  }>;
}

interface MarvinCollection {
  id: string;
  slug: string;
  name: string;
  description?: string;
  entries?: Array<{ id: string; slug: string; title: string }>;
}

const headers = {
  'Authorization': `Bearer ${MARVIN_TOKEN}`,
  'Content-Type': 'application/json',
};

export async function getPublishedEntries(): Promise<MarvinEntry[]> {
  const res = await fetch(
    `${MARVIN_BASE}/api/publish/${GROUP_SLUG}/entries`,
    { headers }
  );
  
  if (!res.ok) {
    throw new Error(`Failed to fetch entries: ${res.statusText}`);
  }
  
  const data = await res.json();
  return data.data || data;
}

export async function getEntry(slug: string): Promise<MarvinEntry> {
  const res = await fetch(
    `${MARVIN_BASE}/api/publish/${GROUP_SLUG}/entries/${slug}`,
    { headers }
  );
  
  if (!res.ok) {
    throw new Error(`Failed to fetch entry: ${res.statusText}`);
  }
  
  return res.json();
}

export async function getCollections(): Promise<MarvinCollection[]> {
  const res = await fetch(
    `${MARVIN_BASE}/api/publish/${GROUP_SLUG}/collections`,
    { headers }
  );
  
  if (!res.ok) {
    throw new Error(`Failed to fetch collections: ${res.statusText}`);
  }
  
  const data = await res.json();
  return data.data || data;
}

export async function getAssets() {
  const res = await fetch(
    `${MARVIN_BASE}/api/publish/${GROUP_SLUG}/assets`,
    { headers }
  );
  
  if (!res.ok) {
    throw new Error(`Failed to fetch assets: ${res.statusText}`);
  }
  
  const data = await res.json();
  return data.data || data;
}
```

## Usage

### Display a List of Entries

In `src/pages/blog/index.astro`:

```astro
---
import { getPublishedEntries } from '@/lib/marvin';

const entries = await getPublishedEntries();
---

<html>
  <head>
    <title>Blog</title>
  </head>
  <body>
    <h1>Blog Posts</h1>
    <ul>
      {entries.map((entry) => (
        <li>
          <a href={`/blog/${entry.slug}`}>
            {entry.title}
          </a>
          {entry.summary && <p>{entry.summary}</p>}
        </li>
      ))}
    </ul>
  </body>
</html>
```

### Display a Single Entry

In `src/pages/blog/[slug].astro`:

```astro
---
import { getPublishedEntries, getEntry } from '@/lib/marvin';

export async function getStaticPaths() {
  const entries = await getPublishedEntries();
  return entries.map((entry) => ({
    params: { slug: entry.slug },
  }));
}

const { slug } = Astro.params;
const entry = await getEntry(slug);
---

<html>
  <head>
    <title>{entry.title}</title>
  </head>
  <body>
    <article>
      <h1>{entry.title}</h1>
      {entry.summary && <p class="summary">{entry.summary}</p>}
      
      {entry.assets && entry.assets.length > 0 && (
        <figure>
          <img
            src={entry.assets[0].url}
            alt={entry.assets[0].alt_text || entry.title}
          />
        </figure>
      )}
      
      <div set:html={markdownToHtml(entry.content_markdown)} />
      
      {entry.collections && entry.collections.length > 0 && (
        <footer>
          <p>
            Collections: {entry.collections.map(c => c.name).join(', ')}
          </p>
        </footer>
      )}
    </article>
  </body>
</html>
```

### Markdown Rendering

Install a markdown parser:

```bash
npm install marked
```

In `src/lib/marvin.ts`, add:

```typescript
import { marked } from 'marked';

export async function renderMarkdown(markdown: string): Promise<string> {
  return marked(markdown);
}
```

Then in your component:

```astro
---
import { renderMarkdown } from '@/lib/marvin';

const html = await renderMarkdown(entry.content_markdown);
---

<div set:html={html} />
```

### Displaying Collections

In `src/pages/collections.astro`:

```astro
---
import { getCollections } from '@/lib/marvin';

const collections = await getCollections();
---

<html>
  <body>
    <h1>Collections</h1>
    <ul>
      {collections.map((collection) => (
        <li>
          <h2>{collection.name}</h2>
          {collection.description && <p>{collection.description}</p>}
          {collection.entries && (
            <ul>
              {collection.entries.map((entry) => (
                <li>
                  <a href={`/blog/${entry.slug}`}>{entry.title}</a>
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  </body>
</html>
```

## Error Handling

The Marvin API returns standard HTTP status codes:

- **200 OK**: Successful request
- **401 Unauthorized**: Invalid or missing token
- **403 Forbidden**: Token doesn't have access to this workspace
- **404 Not Found**: Entry/collection/asset not found or not published
- **429 Too Many Requests**: Rate limited (check `Retry-After` header)

Example error handling:

```typescript
export async function safeGetEntry(slug: string) {
  try {
    return await getEntry(slug);
  } catch (error) {
    console.error(`Error fetching entry ${slug}:`, error);
    return null;
  }
}
```

## Static Generation

Astro's static generation mode works perfectly with Marvin:

```astro
---
// This runs at build time
const entries = await getPublishedEntries();

// Generate a static page for each entry
export async function getStaticPaths() {
  return entries.map((entry) => ({
    params: { slug: entry.slug },
    props: { entry },
  }));
}
---
```

Rebuild your Astro site when content is published in Marvin using:

- Webhook triggers (deploy on Marvin publish event)
- Scheduled builds (e.g., hourly via CI/CD)
- Manual rebuilds

## Caching

Consider caching Marvin API responses to reduce network requests:

```typescript
const CACHE_TTL = 3600; // 1 hour in seconds
const cache = new Map<string, { data: unknown; timestamp: number }>();

export async function getCachedEntries() {
  const key = 'entries';
  const cached = cache.get(key);
  
  if (cached && Date.now() - cached.timestamp < CACHE_TTL * 1000) {
    return cached.data;
  }
  
  const data = await getPublishedEntries();
  cache.set(key, { data, timestamp: Date.now() });
  return data;
}
```

## Best Practices

1. **Environment Variables**: Never commit tokens. Use `.env.local` and add to `.gitignore`
2. **Error Boundaries**: Wrap API calls in try-catch blocks
3. **Type Safety**: Use TypeScript interfaces for Marvin responses
4. **Caching**: Cache API responses to minimize bandwidth and build time
5. **Rebuild Triggers**: Set up webhooks or scheduled builds to keep content fresh
6. **Asset URLs**: Always use absolute URLs from the asset API response
7. **Markdown Parsing**: Choose a markdown library that suits your needs (marked, remark, etc)
8. **Metadata**: Extract frontmatter for SEO tags, structured data, etc

## Deployment

### Environment Variables in Vercel

1. Go to Project Settings → Environment Variables
2. Add `MARVIN_API_URL`, `MARVIN_SITE_CLIENT_TOKEN`, `MARVIN_GROUP_SLUG`
3. Redeploy

### Webhook-Based Rebuilds

Configure Marvin to trigger rebuilds on publish:

```
Webhook URL: https://api.vercel.com/v1/deployments
Method: POST
Headers:
  Authorization: Bearer <VERCEL_TOKEN>
  Content-Type: application/json
```

This keeps your static site in sync when content is published in Marvin.

## Troubleshooting

### 401 Unauthorized

- Check token is correct and hasn't expired
- Verify `MARVIN_API_URL` is correct
- Check token starts with `Bearer `

### 404 Not Found

- Entry exists but isn't published (check status in Marvin)
- Group slug is wrong
- Entry slug doesn't match

### 429 Too Many Requests

- Rate limit exceeded
- Build too frequently
- Implement caching to reduce API calls

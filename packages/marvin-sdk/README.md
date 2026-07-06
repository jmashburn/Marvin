# Marvin TypeScript SDK

The official TypeScript SDK for Marvin CMS. A modern, workspace-first SDK for building applications that integrate with Marvin.

## Why This SDK?

Marvin is becoming a platform, not simply a CMS. This SDK is the primary way to integrate with Marvin across:

- **Static Site Generators** (Astro, Next.js, Nuxt)
- **Server Applications** (Express, Fastify, Hono)
- **CLI Tools** & **Build Scripts**
- **Automation** (n8n, GitHub Actions)
- **AI Agents** & **Custom Integrations**

The SDK provides:

- 🎯 **Workspace-First Architecture** - Work with Marvin concepts (Workspace, Entry, Collection)
- 🚀 **Performance Optimized** - Built-in caching for build-time usage
- 📘 **Fully Typed** - Complete TypeScript support
- 🔄 **Backwards Compatible** - Works with existing publishing APIs
- 🎨 **Object-Oriented** - Rich objects instead of raw JSON
- 🔒 **Secure** - Site client tokens, never user tokens

## Installation

```bash
# Copy into your project
cp -r /path/to/marvin/packages/marvin-sdk src/lib/marvin
```

Or symlink for development:

```bash
ln -s /path/to/marvin/packages/marvin-sdk src/lib/marvin
```

## Quick Start

### 1. Configure Environment

```env
MARVIN_API_URL=https://marvin.example.com
MARVIN_SITE_CLIENT_TOKEN=your-token-here
MARVIN_WORKSPACE_SLUG=your-workspace
```

### 2. Create Client

```ts
import { createMarvinClient } from './marvin-sdk';

const marvin = createMarvinClient();
```

### 3. Fetch Content

```ts
// Get workspace
const workspace = await marvin.getWorkspace();
console.log(workspace.site?.title);

// Get entries
const entries = await marvin.entries.list();

// Get a specific entry
const entry = await marvin.entry('about-us');
console.log(entry.title, entry.contentMarkdown);

// Get collection entries
const projects = await marvin.collection('projects');
const projectEntries = await projects.entries();
```

## Architecture

### Workspace-First Design

Everything starts with the **Workspace**:

```ts
const workspace = await marvin.getWorkspace();

// Access workspace modules
workspace.entries   // Entries module
workspace.collections // Collections module
workspace.assets    // Assets module
workspace.site      // Site configuration (cached)
```

### Modular Structure

The SDK is organized into focused modules:

```
@marvin/sdk
├── client/       → Core client & HTTP
├── workspaces/   → Workspace object
├── entries/      → Entries module
├── collections/  → Collections module
├── assets/       → Assets module
├── auth/         → Authentication (future)
├── types/        → TypeScript types
└── utils/        → Cache & utilities
```

## API Styles

The SDK supports **three API styles**:

### 1. Workspace API (Recommended)

```ts
const workspace = await marvin.getWorkspace();
const entries = await workspace.entries.list();
const collection = await workspace.collections.get('featured');
```

### 2. Convenience API

```ts
const entry = await marvin.entry('about');
const projects = await marvin.projects();
const pages = await marvin.pages();
```

### 3. Backwards-Compatible API

```ts
// Still works! (Deprecated but supported)
const site = await marvin.getSite();
const entries = await marvin.getEntries();
const entry = await marvin.getEntry('about');
```

## Core Concepts

### Workspace

The workspace is the root object representing your Marvin workspace.

```ts
const workspace = await marvin.getWorkspace();

// Cached site configuration
workspace.site?.title
workspace.site?.description

// Access modules
workspace.entries.list()
workspace.collections.get('slug')
workspace.assets.images()
workspace.resources.list()
```

### Content Primitives

Marvin has four first-class content primitives:

- **Entries** - Content you create (pages, blog posts, projects)
- **Collections** - Organize and group entries
- **Assets** - Binary files and media (images, videos, documents)
- **Resources** - Reusable structured objects (fabrics, tools, suppliers, APIs)

### Entries

Rich entry objects with methods and properties:

```ts
const entry = await marvin.entry('about-us');

// Properties
entry.title
entry.slug
entry.contentMarkdown
entry.metadata
entry.publishedAt

// Relationships
entry.assets        // MarvinAsset[]
entry.collections   // MarvinCollection[]
entry.resources     // MarvinResource[]

// Methods (future)
await entry.relatedEntries()
```

### Collections

Collections as first-class objects:

```ts
const collection = await marvin.collection('projects');

// Properties
collection.name
collection.slug
collection.isSmart
collection.smartRules

// Methods
const entries = await collection.entries();

// Future
await collection.assets()
await collection.metadata()
```

### Resources

Resources are reusable structured objects referenced by entries:

```ts
const resource = await marvin.resource('kuroki-s022');

// Properties
resource.name
resource.slug
resource.resourceType    // 'fabric', 'tool', 'supplier', etc.
resource.description
resource.externalId
resource.url
resource.metadata

// Methods
const entries = await resource.entries();  // Entries that reference this resource

// Future
await resource.assets()
```

**Examples of Resources:**
- Fabrics (denim, canvas, etc.)
- Tools (sewing machine, cutting tool)
- Suppliers (fabric mills, button manufacturers)
- Git repositories
- APIs and services
- Books and documents

**Note:** Resources are not binary files. Use Assets for media files.

## Usage Examples

### Astro Static Site

```ts
// src/pages/[slug].astro
---
import { marked } from 'marked';
import { createMarvinClient } from '@/lib/marvin';

const marvin = createMarvinClient();

export async function getStaticPaths() {
  const pages = await marvin.pages();
  
  return pages.map((page) => ({
    params: { slug: page.slug },
    props: { page },
  }));
}

const { page } = Astro.props;
const contentHtml = marked.parse(page.contentMarkdown ?? '');
---

<article>
  <h1>{page.title}</h1>
  <div set:html={contentHtml} />
</article>
```

### Next.js App

```ts
// app/blog/page.tsx
import { createMarvinClient } from '@/lib/marvin';

const marvin = createMarvinClient();

export default async function BlogPage() {
  const posts = await marvin.posts();
  
  return (
    <div>
      {posts.map((post) => (
        <article key={post.id}>
          <h2>{post.title}</h2>
          <p>{post.summary}</p>
        </article>
      ))}
    </div>
  );
}
```

### Express Server

```ts
import express from 'express';
import { createMarvinClient } from './marvin-sdk';

const app = express();
const marvin = createMarvinClient();

app.get('/api/posts', async (req, res) => {
  const posts = await marvin.posts();
  res.json(posts);
});

app.get('/api/posts/:slug', async (req, res) => {
  const entry = await marvin.entry(req.params.slug);
  res.json(entry.toJSON());
});
```

### CLI Tool

```ts
#!/usr/bin/env node
import { createMarvinClient } from '@marvin/sdk';

const marvin = createMarvinClient();

async function main() {
  await marvin.initialize();
  
  console.log('Site:', marvin.site?.title);
  
  const entries = await marvin.entries.list();
  console.log(`Found ${entries.length} entries`);
  
  for (const entry of entries) {
    console.log(`- ${entry.title} (${entry.status})`);
  }
}

main().catch(console.error);
```

## Initialization & Caching

### Auto-Initialize

```ts
const marvin = createMarvinClient({
  autoInitialize: true,
});

// Site is preloaded
console.log(marvin.site?.title);
```

### Manual Initialize

```ts
const marvin = createMarvinClient();

await marvin.initialize();

// Now site is cached
console.log(marvin.site?.title);
```

### Cache Duration

```ts
const marvin = createMarvinClient({
  cacheDuration: 10 * 60 * 1000, // 10 minutes
});
```

## Convenience Methods

Quick access to common content types:

```ts
// Pages
const pages = await marvin.pages();
const about = await marvin.entry('about');

// Blog posts
const posts = await marvin.posts({ limit: 10 });

// Projects
const projects = await marvin.projects();

// Collections
const featured = await marvin.collection('featured');
const entries = await featured.entries();

// Assets
const images = await marvin.assets.images();
const videos = await marvin.assets.videos();

// Resources
const resources = await marvin.resources.list();
const fabric = await marvin.resource('kuroki-s022');
const entries = await fabric.entries();
```

## API Reference

### Client Methods

#### `createMarvinClient(config?)`

Create a new Marvin client instance.

**Config Options:**
- `apiUrl?: string` - API URL (default: `process.env.MARVIN_API_URL`)
- `siteClientToken?: string` - Site client token (default: `process.env.MARVIN_SITE_CLIENT_TOKEN`)
- `workspaceSlug?: string` - Workspace slug (default: `process.env.MARVIN_WORKSPACE_SLUG`)
- `autoInitialize?: boolean` - Auto-initialize on creation (default: `false`)
- `cacheDuration?: number` - Cache duration in ms (default: `300000` / 5 min)

#### `marvin.initialize()`

Initialize the SDK and preload workspace data.

#### `marvin.getWorkspace()`

Get the workspace object.

#### `marvin.entry(slug)`

Get a single entry by slug (returns `Entry` object).

#### `marvin.collection(slug)`

Get a single collection by slug (returns `Collection` object).

#### `marvin.pages(options?)`

Get all pages.

#### `marvin.posts(options?)`

Get all blog posts.

#### `marvin.projects(options?)`

Get all projects.

### Workspace

#### `workspace.site`

Site configuration (cached after `initialize()`).

#### `workspace.entries`

Entries module.

#### `workspace.collections`

Collections module.

#### `workspace.assets`

Assets module.

### Entries Module

#### `entries.list(options?)`

Get all entries with optional filtering.

**Options:**
- `entryType?: string` - Filter by entry type slug
- `collection?: string` - Filter by collection slug
- `status?: string` - Filter by status (default: `'published'`)
- `limit?: number` - Max results
- `offset?: number` - Pagination offset

#### `entries.get(slug)`

Get a single entry (returns `Entry` object).

#### `entries.pages(options?)`

Get all pages.

#### `entries.posts(options?)`

Get all blog posts.

#### `entries.projects(options?)`

Get all projects.

### Entry Object

Properties:
- `id`, `title`, `slug`, `summary`, `description`
- `contentMarkdown` - Raw Markdown content
- `metadata` - Custom metadata object
- `status`, `publishedAt`, `createdAt`, `updatedAt`
- `entryTypeId`, `entryType`
- `assets` - Array of related assets
- `collections` - Array of related collections

Methods:
- `entry.toJSON()` - Get raw entry data

### Collections Module

#### `collections.list()`

Get all collections.

#### `collections.get(slug)`

Get a single collection (returns `Collection` object).

#### `collections.entries(slug)`

Get entries in a collection.

### Collection Object

Properties:
- `id`, `name`, `slug`, `description`
- `icon`, `color`, `sortOrder`
- `isSmart`, `smartRules`
- `createdAt`, `updatedAt`

Methods:
- `collection.entries()` - Get entries in collection
- `collection.toJSON()` - Get raw collection data

### Assets Module

#### `assets.list(options?)`

Get all assets.

**Options:**
- `type?: string` - Filter by type
- `limit?: number` - Max results
- `offset?: number` - Pagination offset

#### `assets.images(options?)`

Get all images.

#### `assets.videos(options?)`

Get all videos.

#### `assets.documents(options?)`

Get all documents.

### Resources Module

#### `resources.list(options?)`

Get all resources.

**Options:**
- `resourceType?: string` - Filter by resource type
- `limit?: number` - Max results
- `offset?: number` - Pagination offset

#### `resources.get(slug)`

Get a single resource (returns `Resource` object).

#### `resources.entries(slug)`

Get entries that reference a resource.

### Resource Object

Properties:
- `id`, `name`, `slug`
- `resourceType` - Type of resource (fabric, tool, supplier, etc.)
- `description`, `externalId`, `url`
- `metadata` - Custom metadata object
- `createdAt`, `updatedAt`

Methods:
- `resource.entries()` - Get entries that reference this resource
- `resource.toJSON()` - Get raw resource data

## Expected Backend Endpoints

The SDK expects these endpoints (marked with TODO in code):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/publish/{workspace}/site` | GET | Site configuration |
| `/api/publish/{workspace}/entries` | GET | List entries |
| `/api/publish/{workspace}/entries/{slug}` | GET | Get entry |
| `/api/publish/{workspace}/collections` | GET | List collections |
| `/api/publish/{workspace}/collections/{slug}` | GET | Get collection |
| `/api/publish/{workspace}/collections/{slug}/entries` | GET | Collection entries |
| `/api/publish/{workspace}/assets` | GET | List assets |
| `/api/publish/{workspace}/resources` | GET | List resources |
| `/api/publish/{workspace}/resources/{slug}` | GET | Get resource |
| `/api/publish/{workspace}/resources/{slug}/entries` | GET | Resource entries |

## Security

### Site Client Tokens

Always use **site client tokens**, never user tokens.

Get a site client token:
1. Log into Marvin
2. Go to **Settings → Publishing → Site Clients**
3. Create a new client
4. Copy the token

### Server-Side Only

**Never expose tokens in browser code:**

```ts
// ✅ Good - Server/build time
const marvin = createMarvinClient();

// ❌ Bad - Browser code with exposed token
<script>
  const marvin = createMarvinClient({
    siteClientToken: '{TOKEN}' // DON'T DO THIS!
  });
</script>
```

## Future Modules

The SDK architecture supports future expansion:

- ✅ **Publishing** - Implemented
- 🔜 **Authentication** - User authentication
- 🔜 **Users** - User management
- 🔜 **Workspaces** - Workspace management
- 🔜 **Events** - Event streams
- 🔜 **Webhooks** - Webhook management
- 🔜 **Search** - Full-text search
- 🔜 **AI** - AI-powered features

## Design Philosophy

The SDK is inspired by:

- [Supabase JavaScript SDK](https://github.com/supabase/supabase-js)
- [Stripe SDK](https://github.com/stripe/stripe-node)
- [GitHub Octokit](https://github.com/octokit/octokit.js)

**Simple to start, powerful as you grow.**

Consumers think in **Marvin concepts** (Workspace, Entry, Collection), not raw REST endpoints.

## Troubleshooting

### "MARVIN_API_URL is required"

Make sure your `.env` file exists with all required variables.

### "401 Unauthorized"

- Verify your site client token is valid
- Check that you're using a site client token, not a user token
- Ensure the token hasn't expired

### TypeScript Errors

Make sure your `tsconfig.json` includes:

```json
{
  "compilerOptions": {
    "moduleResolution": "bundler",
    "types": ["node"]
  }
}
```

## License

MIT - Part of the Marvin project.

## Support

- 📖 [Full Documentation](./examples.md)
- 🚀 [Quick Start Guide](./QUICKSTART.md)
- 🐛 [Report Issues](https://github.com/jmashburn/Marvin/issues)

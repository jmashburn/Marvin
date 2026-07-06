# Marvin Publishing Client

A portable TypeScript client for fetching published content from Marvin CMS. Designed for use in Astro and other static site generators.

## Features

- 🚀 **Portable** - Copy into any TypeScript/Astro project
- 🔒 **Secure** - Uses site client tokens (not user tokens)
- 🏗️ **Build-time** - Optimized for static site generation
- 📘 **Typed** - Full TypeScript support
- 🎯 **Simple** - Clean, focused API

## Installation

### Option 1: Copy Files

Copy the entire `marvin-client` directory into your project:

```bash
# In your Astro project
mkdir -p src/lib/marvin
cp -r /path/to/marvin/packages/marvin-client/* src/lib/marvin/
```

### Option 2: Symlink (Development)

```bash
# In your Astro project
ln -s /path/to/marvin/packages/marvin-client src/lib/marvin
```

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```env
# Marvin API URL (no trailing slash)
MARVIN_API_URL=https://marvin.example.com

# Site Client Token (get this from Marvin workspace settings)
MARVIN_SITE_CLIENT_TOKEN=your-site-client-token-here

# Workspace Slug
MARVIN_WORKSPACE_SLUG=mash-burn
```

**Security Note**: Never commit `.env` to version control. Add it to `.gitignore`.

### Getting a Site Client Token

1. Log into your Marvin workspace
2. Go to **Settings > Publishing > Site Clients**
3. Create a new site client for your website
4. Copy the generated token
5. Add it to your `.env` file

**Important**: Site client tokens should only be used server-side or at build-time. Never expose them in browser-side code.

## Usage

### Basic Setup

```ts
// src/lib/marvin.ts
import { createMarvinClient } from './marvin-client';

export const marvin = createMarvinClient();
```

### Fetching Site Configuration

```ts
import { marvin } from '@/lib/marvin';

const site = await marvin.getSite();

console.log(site.title); // "Mash & Burn Co."
console.log(site.tagline); // "Handcrafted with Purpose"
```

### Fetching All Entries

```ts
import { marvin } from '@/lib/marvin';

const entries = await marvin.getEntries();

// Filter by entry type
const pages = await marvin.getEntries({ entryType: 'page' });
const projects = await marvin.getEntries({ entryType: 'project' });
```

### Fetching a Single Entry

```ts
import { marvin } from '@/lib/marvin';

const entry = await marvin.getEntry('about-us');

console.log(entry.title); // "About Us"
console.log(entry.contentMarkdown); // Full markdown content
```

### Fetching Collections

```ts
import { marvin } from '@/lib/marvin';

// Get all collections
const collections = await marvin.getCollections();

// Get a specific collection
const featuredCollection = await marvin.getCollection('featured');

// Get entries in a collection
const featuredProjects = await marvin.getCollectionEntries('featured-projects');
```

### Fetching Assets

```ts
import { marvin } from '@/lib/marvin';

const assets = await marvin.getAssets();

// Filter by type
const images = await marvin.getAssets({ type: 'image' });
```

## Astro Integration

### Dynamic Pages with getStaticPaths

Create dynamic routes that build at compile time:

```ts
// src/pages/[slug].astro
---
import { marvin } from '@/lib/marvin';

export async function getStaticPaths() {
  const entries = await marvin.getEntries({ entryType: 'page' });

  return entries.map((entry) => ({
    params: { slug: entry.slug },
    props: { entry },
  }));
}

const { entry } = Astro.props;
---

<html>
  <head>
    <title>{entry.title}</title>
  </head>
  <body>
    <h1>{entry.title}</h1>
    <div set:html={entry.contentMarkdown} />
  </body>
</html>
```

### Rendering Markdown

Astro can render Markdown directly:

```astro
---
const entry = await marvin.getEntry('about');
---

<article>
  <h1>{entry.title}</h1>
  
  <!-- Render markdown as HTML -->
  <div class="content" set:html={entry.contentMarkdown} />
</article>
```

For more control over Markdown rendering:

```ts
import { Marked } from 'marked';
import { markedHighlight } from 'marked-highlight';
import hljs from 'highlight.js';

const marked = new Marked(
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang) {
      const language = hljs.getLanguage(lang) ? lang : 'plaintext';
      return hljs.highlight(code, { language }).value;
    },
  })
);

const html = marked.parse(entry.contentMarkdown);
```

### Project Listing Page

```ts
// src/pages/projects/index.astro
---
import { marvin } from '@/lib/marvin';

const projects = await marvin.getCollectionEntries('projects');
---

<div class="projects">
  {projects.map((project) => (
    <article>
      <h2><a href={`/projects/${project.slug}`}>{project.title}</a></h2>
      <p>{project.summary}</p>
    </article>
  ))}
</div>
```

### Using Site Configuration

```ts
// src/layouts/BaseLayout.astro
---
import { marvin } from '@/lib/marvin';

const site = await marvin.getSite();
---

<html lang={site.locale || 'en'}>
  <head>
    <title>{site.title}</title>
    <meta name="description" content={site.description} />
    <link rel="icon" href={site.favicon} />
  </head>
  <body>
    <header>
      <h1>{site.title}</h1>
      <p>{site.tagline}</p>
    </header>
    <slot />
  </body>
</html>
```

## API Reference

### Methods

#### `getSite(): Promise<MarvinSite>`

Fetches site configuration and metadata.

**Returns**: Site object with title, description, logo, etc.

#### `getEntries(options?): Promise<MarvinEntry[]>`

Fetches published entries with optional filtering.

**Options**:
- `entryType?: string` - Filter by entry type slug
- `collection?: string` - Filter by collection slug
- `status?: string` - Filter by status (default: 'published')
- `limit?: number` - Max entries to return
- `offset?: number` - Pagination offset

**Returns**: Array of entries

#### `getEntry(slug: string): Promise<MarvinEntry>`

Fetches a single entry by slug.

**Parameters**:
- `slug` - Entry slug

**Returns**: Single entry with full content

#### `getCollections(): Promise<MarvinCollection[]>`

Fetches all collections.

**Returns**: Array of collections

#### `getCollection(slug: string): Promise<MarvinCollection>`

Fetches a single collection by slug.

**Parameters**:
- `slug` - Collection slug

**Returns**: Single collection

#### `getCollectionEntries(slug: string): Promise<MarvinEntry[]>`

Fetches all entries in a collection.

**Parameters**:
- `slug` - Collection slug

**Returns**: Array of entries in the collection

#### `getAssets(options?): Promise<MarvinAsset[]>`

Fetches published assets.

**Options**:
- `type?: string` - Filter by asset type (e.g., 'image')
- `limit?: number` - Max assets to return
- `offset?: number` - Pagination offset

**Returns**: Array of assets

## Expected Marvin API Endpoints

The client expects the following endpoints to be available in Marvin:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/publish/{workspace}/site` | GET | Site configuration |
| `/api/publish/{workspace}/entries` | GET | List published entries |
| `/api/publish/{workspace}/entries/{slug}` | GET | Single entry by slug |
| `/api/publish/{workspace}/collections` | GET | List collections |
| `/api/publish/{workspace}/collections/{slug}` | GET | Single collection |
| `/api/publish/{workspace}/collections/{slug}/entries` | GET | Entries in collection |
| `/api/publish/{workspace}/assets` | GET | List published assets |

**Note**: All endpoints marked with `TODO` in `client.ts` need to be implemented in the Marvin backend. The client will throw errors if these endpoints don't exist yet.

## Error Handling

The client throws descriptive errors:

```ts
try {
  const entry = await marvin.getEntry('non-existent');
} catch (error) {
  console.error(error.message);
  // "Marvin API error: 404 Not Found at /api/publish/workspace/entries/non-existent"
}
```

Tokens are automatically redacted from error messages for security.

## Security Best Practices

### ✅ DO

- Store site client tokens in `.env` files
- Use tokens only in server-side or build-time code
- Add `.env` to `.gitignore`
- Rotate tokens if they're ever exposed

### ❌ DON'T

- Commit tokens to version control
- Use tokens in browser-side JavaScript
- Share tokens publicly
- Use user tokens instead of site client tokens

## Development

### Type Checking

The client includes full TypeScript types. Use them for autocomplete and type safety:

```ts
import type { MarvinEntry } from '@/lib/marvin';

const entry: MarvinEntry = await marvin.getEntry('about');
```

### Testing Locally

When developing locally with Marvin running on `http://localhost:8000`:

```env
MARVIN_API_URL=http://localhost:8000
MARVIN_SITE_CLIENT_TOKEN=dev-token
MARVIN_WORKSPACE_SLUG=local-workspace
```

## Troubleshooting

### "MARVIN_API_URL is required"

Make sure your `.env` file exists and contains all required variables.

### "401 Unauthorized"

- Check that your site client token is valid
- Verify the token hasn't expired
- Ensure you're using a site client token, not a user token

### "404 Not Found"

- The endpoint may not be implemented yet (check for `TODO` comments)
- Verify the workspace slug is correct
- Check that the entry/collection slug exists

### TypeScript Errors

If you see import errors, make sure your `tsconfig.json` includes:

```json
{
  "compilerOptions": {
    "moduleResolution": "bundler",
    "types": ["astro/client"]
  }
}
```

## License

This client is part of the Marvin project and follows the same license.

## Support

For issues or questions:
- Check the Marvin documentation
- Review the TODO comments in `client.ts`
- Open an issue in the Marvin repository

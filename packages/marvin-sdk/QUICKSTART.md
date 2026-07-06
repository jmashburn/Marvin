# Marvin SDK Quick Start

Get up and running with the Marvin TypeScript SDK in 5 minutes.

The Marvin SDK is framework-agnostic and works with Astro, Next.js, Express, CLI tools, automation workflows, and any trusted runtime.

---

## Step 1: Copy the SDK

Copy the SDK into your project:

```bash
# Navigate to your project
cd /path/to/your-project

# Create lib directory
mkdir -p src/lib

# Copy the SDK
cp -r /path/to/marvin/packages/marvin-sdk src/lib/marvin
```

## Step 2: Configure Environment Variables

Create a `.env` file in your project root:

```env
MARVIN_API_URL=https://marvin.example.com
MARVIN_SITE_CLIENT_TOKEN=your-token-here
MARVIN_WORKSPACE_SLUG=your-workspace
```

**Get your Site Client Token:**

1. Log into Marvin
2. Go to **Settings → Publishing → Site Clients**
3. Create a new client for your application
4. Copy the token

**🔒 Security Note:** Site client tokens must only be used in **server-side, build-time, or trusted backend code**. Never expose them in browser-side bundles.

## Step 3: Create SDK Instance

Create a file to initialize the SDK:

```ts
// src/lib/marvin.ts
import { createMarvinClient } from './marvin';

export const marvin = createMarvinClient();
```

### Optional: Preload Workspace Data

If you want to preload site configuration at startup:

```ts
// src/lib/marvin.ts
import { createMarvinClient } from './marvin';

export const marvin = createMarvinClient({
  autoInitialize: true, // Preload site config on creation
});
```

Or initialize manually when needed:

```ts
import { marvin } from '@/lib/marvin';

// Initialize when needed
await marvin.initialize();

// Now site config is cached
console.log(marvin.site?.title);
```

## Step 4: Fetch Content

### Workspace-First API (Recommended)

```ts
import { marvin } from '@/lib/marvin';

// Get workspace
const workspace = await marvin.getWorkspace();
console.log(workspace.site?.title);

// Get entries
const entries = await workspace.entries.list();

// Get a collection
const collection = await workspace.collections.get('projects');
const projectEntries = await collection.entries();

// Get resources
const resources = await workspace.resources.list();
const fabric = await workspace.resources.get('kuroki-s022');
const entriesUsingFabric = await fabric.entries();
```

### Convenience API

```ts
import { marvin } from '@/lib/marvin';

// Quick access to entries
const entry = await marvin.entry('about-us');
const projects = await marvin.projects();

// Get entries by type
const articles = await marvin.getEntries({ entryType: 'article' });

// Get a collection
const featured = await marvin.collection('featured');

// Get resources
const fabric = await marvin.resource('kuroki-s022');
```

### Backwards-Compatible API

```ts
import { marvin } from '@/lib/marvin';

// Still works! (Deprecated but supported)
const site = await marvin.getSite();
const entries = await marvin.getEntries();
const entry = await marvin.getEntry('about');
```

---

## Framework Examples

### Astro (Static Site)

```astro
---
// src/pages/[slug].astro
import { marked } from 'marked';
import { marvin } from '@/lib/marvin';

export async function getStaticPaths() {
  const entries = await marvin.getEntries({ entryType: 'page' });
  
  return entries.map((entry) => ({
    params: { slug: entry.slug },
    props: { entry },
  }));
}

const { entry } = Astro.props;

// Parse Markdown to HTML
const contentHtml = marked.parse(entry.contentMarkdown ?? '');
---

<html>
  <head>
    <title>{entry.title}</title>
  </head>
  <body>
    <h1>{entry.title}</h1>
    <div class="content" set:html={contentHtml} />
  </body>
</html>
```

### Next.js (App Router)

```tsx
// app/projects/page.tsx
import { marvin } from '@/lib/marvin';

export default async function ProjectsPage() {
  const projects = await marvin.projects();
  
  return (
    <div>
      <h1>Projects</h1>
      {projects.map((project) => (
        <article key={project.id}>
          <h2>{project.title}</h2>
          <p>{project.summary}</p>
          <a href={`/projects/${project.slug}`}>View project →</a>
        </article>
      ))}
    </div>
  );
}
```

### Express (Server)

```ts
import express from 'express';
import { marvin } from './lib/marvin';

const app = express();

app.get('/api/entries', async (req, res) => {
  const entries = await marvin.getEntries({
    entryType: req.query.type as string,
  });
  res.json(entries);
});

app.get('/api/entries/:slug', async (req, res) => {
  const entry = await marvin.entry(req.params.slug);
  res.json(entry.toJSON());
});

app.listen(3000, () => {
  console.log('Server running on http://localhost:3000');
});
```

### CLI Tool

```ts
#!/usr/bin/env node
import { marvin } from './lib/marvin';

async function main() {
  // Initialize SDK
  await marvin.initialize();
  
  console.log('Site:', marvin.site?.title);
  
  // List all entries
  const entries = await marvin.getEntries();
  console.log(`\nFound ${entries.length} entries:`);
  
  for (const entry of entries) {
    console.log(`- ${entry.title} (${entry.status})`);
  }
  
  // List collections
  const collections = await marvin.getCollections();
  console.log(`\nFound ${collections.length} collections:`);
  
  for (const collection of collections) {
    console.log(`- ${collection.name}`);
  }
}

main().catch(console.error);
```

---

## Rendering Markdown Content

**Important:** `entry.contentMarkdown` is raw Markdown, not HTML. You must parse it before rendering.

### Install Markdown Parser

```bash
npm install marked
```

### Parse Before Rendering

```ts
import { marked } from 'marked';

const entry = await marvin.entry('about');

// Parse Markdown to HTML
const contentHtml = marked.parse(entry.contentMarkdown ?? '');

// Then render in your template
// Astro: <div set:html={contentHtml} />
// React: <div dangerouslySetInnerHTML={{ __html: contentHtml }} />
```

---

## Build Your Application

```bash
npm run build
```

Your application will fetch all content from Marvin at build time!

---

## API Styles

The SDK supports three API styles:

### 1. Workspace API (Recommended)

Work with workspace as a first-class object:

```ts
const workspace = await marvin.getWorkspace();
const entries = await workspace.entries.list();
const collection = await workspace.collections.get('featured');
```

### 2. Convenience API

Quick access to common patterns:

```ts
const entry = await marvin.entry('about');
const projects = await marvin.projects();
const featured = await marvin.collection('featured');
```

### 3. Backwards-Compatible API

Original publishing client methods still work:

```ts
const site = await marvin.getSite();
const entries = await marvin.getEntries();
const entry = await marvin.getEntry('about');
```

---

## Security Best Practices

### ✅ DO

- Use site client tokens in **server-side** code only
- Use tokens at **build time** in static site generators
- Use tokens in **trusted backend** services
- Store tokens in `.env` files (never commit to git)
- Add `.env` to `.gitignore`

### ❌ DON'T

- Expose tokens in browser-side JavaScript
- Commit tokens to version control
- Use tokens in client-side bundles
- Share tokens publicly
- Use user tokens instead of site client tokens

---

## Next Steps

- 📖 Read the [full README](./README.md) for all API methods
- 💡 Check out [examples](./examples.md) for real-world usage patterns
- 🎯 Explore object-oriented APIs (Entry, Collection objects)
- 🚀 Build with your framework of choice
- 🔧 Use convenience methods for common content types

---

## Troubleshooting

### Cannot find module '@/lib/marvin'

Add path alias to your `tsconfig.json`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

### "MARVIN_API_URL is required"

Make sure:
1. `.env` file exists in project root
2. All three variables are set
3. Restart your dev server after adding `.env`

### 401 Unauthorized

- Verify your site client token is correct
- Check that the token hasn't expired
- Make sure you're using a **site client token**, not a user token
- Ensure the token is only used server-side

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

---

## Need Help?

- 📖 Read the [full documentation](./README.md)
- 💡 Check the [examples](./examples.md)
- 🐛 Report issues on GitHub
- 🚀 Check TODO comments for upcoming features

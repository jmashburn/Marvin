# Marvin SDK Quick Start

Get up and running with the Marvin TypeScript SDK in 5 minutes.

## Step 1: Copy the SDK

Copy the SDK into your project:

```bash
# Navigate to your project
cd /path/to/your-project

# Create lib directory
mkdir -p src/lib/marvin

# Copy the SDK files
cp -r /path/to/marvin/packages/marvin-sdk/* src/lib/marvin/
```

## Step 2: Configure Environment Variables

Create a `.env` file in your project root:

```bash
# Copy the example
cp src/lib/marvin/.env.example .env
```

Edit `.env` and add your Marvin credentials:

```env
MARVIN_API_URL=https://marvin.example.com
MARVIN_SITE_CLIENT_TOKEN=your_token_here
MARVIN_WORKSPACE_SLUG=your-workspace
```

**Get your Site Client Token:**
1. Log into Marvin
2. Go to **Settings → Publishing → Site Clients**
3. Create a new client for your application
4. Copy the token

## Step 3: Create SDK Instance

Create a file to initialize the SDK:

```ts
// src/lib/marvin.ts
import { createMarvinClient } from './marvin/src';

export const marvin = createMarvinClient({
  autoInitialize: true, // Preload site config
});
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
const projects = await collection.entries();
```

### Convenience API

```ts
import { marvin } from '@/lib/marvin';

// Quick access to common content
const entry = await marvin.entry('about-us');
const pages = await marvin.pages();
const projects = await marvin.projects();
const featured = await marvin.collection('featured');
```

### Backwards-Compatible API

```ts
import { marvin } from '@/lib/marvin';

// Still works! (Deprecated but supported)
const site = await marvin.getSite();
const entries = await marvin.getEntries();
const entry = await marvin.getEntry('about');
```

## Step 5: Use in Astro

Create dynamic pages for your content:

```astro
---
// src/pages/[slug].astro
import { marked } from 'marked';
import { marvin } from '@/lib/marvin';

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

<html>
  <head>
    <title>{page.title}</title>
  </head>
  <body>
    <h1>{page.title}</h1>
    <div class="content" set:html={contentHtml} />
  </body>
</html>
```

## Step 6: Use in Next.js

```tsx
// app/blog/page.tsx
import { marvin } from '@/lib/marvin';

export default async function BlogPage() {
  const posts = await marvin.posts();
  
  return (
    <div>
      <h1>Blog</h1>
      {posts.map((post) => (
        <article key={post.id}>
          <h2>{post.title}</h2>
          <p>{post.summary}</p>
          <a href={`/blog/${post.slug}`}>Read more →</a>
        </article>
      ))}
    </div>
  );
}
```

## Step 7: Use in Express

```ts
import express from 'express';
import { marvin } from './lib/marvin';

const app = express();

app.get('/api/posts', async (req, res) => {
  const posts = await marvin.posts();
  res.json(posts);
});

app.get('/api/posts/:slug', async (req, res) => {
  const entry = await marvin.entry(req.params.slug);
  res.json(entry.toJSON());
});

app.listen(3000);
```

## Build Your Site

```bash
npm run build
```

Your application will fetch all content from Marvin at build time!

## API Styles

The SDK supports three API styles:

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
// Still works!
const site = await marvin.getSite();
const entries = await marvin.getEntries();
```

## Next Steps

- Read the [full README](./README.md) for all API methods
- Check out [examples](./examples.md) for real-world usage patterns
- Explore object-oriented APIs (Entry, Collection objects)
- Build with multiple frameworks (Astro, Next.js, Express)
- Use convenience methods for common content types

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

## Need Help?

- 📖 Read the [full documentation](./README.md)
- 💡 Check the [examples](./examples.md)
- 🐛 Report issues on GitHub
- 🚀 Check TODO comments for upcoming features

# Marvin Client Usage Examples

Real-world examples for using the Marvin publishing client in an Astro site.

## Table of Contents

1. [Basic Setup](#basic-setup)
2. [Markdown Rendering](#markdown-rendering)
3. [Site Configuration](#site-configuration)
4. [Blog/News Pages](#blognews-pages)
5. [Project Portfolio](#project-portfolio)
6. [Dynamic Routes](#dynamic-routes)
7. [Collections](#collections)
8. [Resources](#resources)
9. [Assets & Images](#assets--images)
10. [Metadata & SEO](#metadata--seo)

---

## Basic Setup

### Create the Marvin Client Instance

```ts
// src/lib/marvin.ts
import { createMarvinClient } from './marvin-client';

// Create client from environment variables
export const marvin = createMarvinClient();

// Or pass config explicitly
export const marvinProd = createMarvinClient({
  apiUrl: 'https://marvin.example.com',
  siteClientToken: import.meta.env.MARVIN_SITE_CLIENT_TOKEN,
  workspaceSlug: 'mash-burn',
});
```

### Environment Variables

```env
# .env
MARVIN_API_URL=https://marvin.mashburn.co
MARVIN_SITE_CLIENT_TOKEN=mbc_abc123xyz789
MARVIN_WORKSPACE_SLUG=mash-burn
```

---

## Markdown Rendering

**Critical**: Entry content is returned as **raw Markdown**, not HTML. You must parse it before rendering.

### Install Markdown Parser

```bash
npm install marked
```

### Create a Helper Function

```ts
// src/lib/markdown.ts
import { marked } from 'marked';

/**
 * Parse Markdown to HTML
 */
export function renderMarkdown(markdown: string): string {
  return marked.parse(markdown ?? '');
}
```

### Use in Astro Components

```astro
---
import { renderMarkdown } from '@/lib/markdown';
import { marvin } from '@/lib/marvin';

const entry = await marvin.getEntry('about');
const contentHtml = renderMarkdown(entry.contentMarkdown ?? '');
---

<article>
  <h1>{entry.title}</h1>
  <!-- Render parsed HTML -->
  <div class="content" set:html={contentHtml} />
</article>
```

### Common Mistake

**❌ WRONG** - This will render raw Markdown as text:
```astro
<div set:html={entry.contentMarkdown} />
```

**✅ CORRECT** - Parse Markdown first:
```astro
---
import { marked } from 'marked';
const contentHtml = marked.parse(entry.contentMarkdown ?? '');
---
<div set:html={contentHtml} />
```

---

## Site Configuration

### Use Site Config in Layout

```astro
// src/layouts/BaseLayout.astro
---
import { marvin } from '@/lib/marvin';

const site = await marvin.getSite();
const { title = 'Mash & Burn Co.' } = Astro.props;
---

<!DOCTYPE html>
<html lang={site.locale || 'en'}>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title} | {site.title}</title>
    <meta name="description" content={site.description} />
    <link rel="icon" type="image/x-icon" href={site.favicon || '/favicon.ico'} />
    <link rel="canonical" href={site.canonicalUrl} />
  </head>
  <body>
    <header>
      <a href="/">
        {site.logo && <img src={site.logo} alt={site.title} />}
        <h1>{site.title}</h1>
      </a>
      <p class="tagline">{site.tagline}</p>
    </header>

    <main>
      <slot />
    </main>

    <footer>
      <p>&copy; {new Date().getFullYear()} {site.title}</p>
    </footer>
  </body>
</html>
```

---

## Blog/News Pages

### Blog Index Page

```astro
// src/pages/blog/index.astro
---
import BaseLayout from '@/layouts/BaseLayout.astro';
import { marvin } from '@/lib/marvin';

// Fetch all blog posts
const posts = await marvin.getEntries({ entryType: 'blog' });

// Sort by published date, newest first
const sortedPosts = posts.sort((a, b) => {
  const dateA = new Date(a.publishedAt || a.createdAt).getTime();
  const dateB = new Date(b.publishedAt || b.createdAt).getTime();
  return dateB - dateA;
});
---

<BaseLayout title="Blog">
  <h1>Blog</h1>
  
  <div class="posts">
    {sortedPosts.map((post) => (
      <article class="post-preview">
        <h2>
          <a href={`/blog/${post.slug}`}>{post.title}</a>
        </h2>
        
        <time datetime={post.publishedAt}>
          {new Date(post.publishedAt).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
          })}
        </time>
        
        {post.summary && <p>{post.summary}</p>}
        
        <a href={`/blog/${post.slug}`} class="read-more">
          Read more →
        </a>
      </article>
    ))}
  </div>
</BaseLayout>
```

### Individual Blog Post

```astro
// src/pages/blog/[slug].astro
---
import { marked } from 'marked';
import BaseLayout from '@/layouts/BaseLayout.astro';
import { marvin } from '@/lib/marvin';

export async function getStaticPaths() {
  const posts = await marvin.getEntries({ entryType: 'blog' });
  
  return posts.map((post) => ({
    params: { slug: post.slug },
    props: { post },
  }));
}

const { post } = Astro.props;

// Parse Markdown to HTML
const contentHtml = marked.parse(post.contentMarkdown ?? '');
---

<BaseLayout title={post.title}>
  <article class="blog-post">
    <header>
      <h1>{post.title}</h1>
      
      <time datetime={post.publishedAt}>
        {new Date(post.publishedAt).toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        })}
      </time>
    </header>

    {post.assets && post.assets.length > 0 && (
      <img 
        src={post.assets[0].url} 
        alt={post.assets[0].altText || post.title}
        class="featured-image"
      />
    )}

    <div class="content" set:html={contentHtml} />

    {post.metadata?.tags && (
      <div class="tags">
        {post.metadata.tags.map((tag: string) => (
          <span class="tag">{tag}</span>
        ))}
      </div>
    )}
  </article>
</BaseLayout>
```

---

## Project Portfolio

### Projects Gallery

```astro
// src/pages/projects/index.astro
---
import BaseLayout from '@/layouts/BaseLayout.astro';
import { marvin } from '@/lib/marvin';

// Get all projects
const projects = await marvin.getEntries({ entryType: 'project' });

// Or get projects from a collection
const featuredProjects = await marvin.getCollectionEntries('featured-projects');
---

<BaseLayout title="Projects">
  <h1>Our Projects</h1>
  
  <div class="projects-grid">
    {projects.map((project) => (
      <a href={`/projects/${project.slug}`} class="project-card">
        {project.assets && project.assets[0] && (
          <img 
            src={project.assets[0].url}
            alt={project.assets[0].altText || project.title}
            loading="lazy"
          />
        )}
        
        <h2>{project.title}</h2>
        <p>{project.summary}</p>
        
        {project.metadata?.year && (
          <span class="year">{project.metadata.year}</span>
        )}
      </a>
    ))}
  </div>
</BaseLayout>

<style>
  .projects-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 2rem;
  }
  
  .project-card {
    text-decoration: none;
    border: 1px solid #ddd;
    border-radius: 8px;
    overflow: hidden;
    transition: transform 0.2s;
  }
  
  .project-card:hover {
    transform: translateY(-4px);
  }
</style>
```

### Project Detail Page

```astro
// src/pages/projects/[slug].astro
---
import { marked } from 'marked';
import BaseLayout from '@/layouts/BaseLayout.astro';
import { marvin } from '@/lib/marvin';

export async function getStaticPaths() {
  const projects = await marvin.getEntries({ entryType: 'project' });
  
  return projects.map((project) => ({
    params: { slug: project.slug },
    props: { project },
  }));
}

const { project } = Astro.props;
const metadata = project.metadata || {};

// Parse Markdown to HTML
const contentHtml = marked.parse(project.contentMarkdown ?? '');
---

<BaseLayout title={project.title}>
  <article class="project">
    <header>
      <h1>{project.title}</h1>
      
      <div class="meta">
        {metadata.client && <span>Client: {metadata.client}</span>}
        {metadata.year && <span>Year: {metadata.year}</span>}
        {metadata.category && <span>Category: {metadata.category}</span>}
      </div>
    </header>

    {project.assets && project.assets.length > 0 && (
      <div class="gallery">
        {project.assets.map((asset) => (
          <img
            src={asset.url}
            alt={asset.altText || project.title}
            width={asset.width}
            height={asset.height}
            loading="lazy"
          />
        ))}
      </div>
    )}

    <div class="content" set:html={contentHtml} />

    {metadata.technologies && (
      <div class="technologies">
        <h3>Technologies Used</h3>
        <ul>
          {metadata.technologies.map((tech: string) => (
            <li>{tech}</li>
          ))}
        </ul>
      </div>
    )}
  </article>
</BaseLayout>
```

---

## Dynamic Routes

### Catch-All Route for Pages

```astro
// src/pages/[...slug].astro
---
import { marked } from 'marked';
import BaseLayout from '@/layouts/BaseLayout.astro';
import { marvin } from '@/lib/marvin';

export async function getStaticPaths() {
  const pages = await marvin.getEntries({ entryType: 'page' });
  
  return pages.map((page) => ({
    params: { slug: page.slug },
    props: { page },
  }));
}

const { page } = Astro.props;

// Parse Markdown to HTML
const contentHtml = marked.parse(page.contentMarkdown ?? '');
---

<BaseLayout title={page.title}>
  <article class="page">
    <h1>{page.title}</h1>
    <div class="content" set:html={contentHtml} />
  </article>
</BaseLayout>
```

---

## Collections

### Featured Items Showcase

```astro
// src/pages/index.astro
---
import BaseLayout from '@/layouts/BaseLayout.astro';
import { marvin } from '@/lib/marvin';

const featuredProjects = await marvin.getCollectionEntries('featured');
const latestPosts = await marvin.getEntries({ 
  entryType: 'blog',
  limit: 3 
});
---

<BaseLayout>
  <section class="hero">
    <h1>Welcome to Mash & Burn Co.</h1>
    <p>Handcrafted with Purpose</p>
  </section>

  <section class="featured">
    <h2>Featured Projects</h2>
    <div class="grid">
      {featuredProjects.map((project) => (
        <a href={`/projects/${project.slug}`}>
          {project.assets?.[0] && (
            <img src={project.assets[0].url} alt={project.title} />
          )}
          <h3>{project.title}</h3>
        </a>
      ))}
    </div>
  </section>

  <section class="latest-posts">
    <h2>Latest from the Blog</h2>
    {latestPosts.map((post) => (
      <article>
        <h3><a href={`/blog/${post.slug}`}>{post.title}</a></h3>
        <p>{post.summary}</p>
      </article>
    ))}
  </section>
</BaseLayout>
```

### Collection Landing Page

```astro
// src/pages/collections/[slug].astro
---
import BaseLayout from '@/layouts/BaseLayout.astro';
import { marvin } from '@/lib/marvin';

export async function getStaticPaths() {
  const collections = await marvin.getCollections();
  
  return collections.map((collection) => ({
    params: { slug: collection.slug },
    props: { collection },
  }));
}

const { collection } = Astro.props;
const entries = await marvin.getCollectionEntries(collection.slug);
---

<BaseLayout title={collection.name}>
  <header>
    {collection.icon && <span class="icon">{collection.icon}</span>}
    <h1>{collection.name}</h1>
    {collection.description && <p>{collection.description}</p>}
  </header>

  <div class="entries">
    {entries.map((entry) => (
      <article>
        <h2><a href={`/${entry.entryType?.slug}/${entry.slug}`}>{entry.title}</a></h2>
        <p>{entry.summary}</p>
      </article>
    ))}
  </div>
</BaseLayout>
```

---

## Resources

Resources are reusable structured objects that entries can reference (fabrics, tools, suppliers, etc.).

### List Resources by Type

```astro
// src/pages/materials/fabrics.astro
---
import BaseLayout from '@/layouts/BaseLayout.astro';
import { marvin } from '@/lib/marvin';

const fabrics = await marvin.getResources({ resourceType: 'fabric' });
---

<BaseLayout title="Fabrics">
  <h1>Our Fabrics</h1>
  
  <div class="resources-grid">
    {fabrics.map((fabric) => (
      <article class="resource-card">
        <h2>
          <a href={`/materials/fabrics/${fabric.slug}`}>{fabric.name}</a>
        </h2>
        
        {fabric.description && <p>{fabric.description}</p>}
        
        {fabric.metadata?.weight && (
          <span class="meta">Weight: {fabric.metadata.weight}</span>
        )}
        
        {fabric.metadata?.composition && (
          <span class="meta">Composition: {fabric.metadata.composition}</span>
        )}
        
        {fabric.url && (
          <a href={fabric.url} target="_blank" rel="noopener">
            View supplier →
          </a>
        )}
      </article>
    ))}
  </div>
</BaseLayout>
```

### Resource Detail Page with Related Entries

```astro
// src/pages/materials/fabrics/[slug].astro
---
import BaseLayout from '@/layouts/BaseLayout.astro';
import { marvin } from '@/lib/marvin';

export async function getStaticPaths() {
  const fabrics = await marvin.getResources({ resourceType: 'fabric' });
  
  return fabrics.map((fabric) => ({
    params: { slug: fabric.slug },
    props: { fabric },
  }));
}

const { fabric } = Astro.props;

// Get entries that use this fabric
const relatedEntries = await marvin.getResourceEntries(fabric.slug);
const metadata = fabric.metadata || {};
---

<BaseLayout title={fabric.name}>
  <article class="resource-detail">
    <header>
      <h1>{fabric.name}</h1>
      {fabric.resourceType && (
        <span class="type">{fabric.resourceType}</span>
      )}
    </header>
    
    {fabric.description && (
      <p class="description">{fabric.description}</p>
    )}
    
    <dl class="metadata">
      {fabric.externalId && (
        <>
          <dt>ID</dt>
          <dd>{fabric.externalId}</dd>
        </>
      )}
      
      {metadata.weight && (
        <>
          <dt>Weight</dt>
          <dd>{metadata.weight}</dd>
        </>
      )}
      
      {metadata.composition && (
        <>
          <dt>Composition</dt>
          <dd>{metadata.composition}</dd>
        </>
      )}
      
      {metadata.color && (
        <>
          <dt>Color</dt>
          <dd>{metadata.color}</dd>
        </>
      )}
      
      {fabric.url && (
        <>
          <dt>Supplier</dt>
          <dd><a href={fabric.url} target="_blank" rel="noopener">{fabric.url}</a></dd>
        </>
      )}
    </dl>
    
    {relatedEntries.length > 0 && (
      <section class="related-entries">
        <h2>Used In</h2>
        <div class="entries">
          {relatedEntries.map((entry) => (
            <article>
              <h3>
                <a href={`/${entry.entryType?.slug}/${entry.slug}`}>
                  {entry.title}
                </a>
              </h3>
              {entry.summary && <p>{entry.summary}</p>}
            </article>
          ))}
        </div>
      </section>
    )}
  </article>
</BaseLayout>
```

### Display Resources in Entry Pages

```astro
// src/pages/projects/[slug].astro
---
import { marked } from 'marked';
import BaseLayout from '@/layouts/BaseLayout.astro';
import { marvin } from '@/lib/marvin';

export async function getStaticPaths() {
  const projects = await marvin.getEntries({ entryType: 'project' });
  
  return projects.map((project) => ({
    params: { slug: project.slug },
    props: { project },
  }));
}

const { project } = Astro.props;
const contentHtml = marked.parse(project.contentMarkdown ?? '');
---

<BaseLayout title={project.title}>
  <article class="project">
    <h1>{project.title}</h1>
    <div class="content" set:html={contentHtml} />
    
    {/* Display linked resources */}
    {project.resources && project.resources.length > 0 && (
      <section class="materials">
        <h2>Materials Used</h2>
        <div class="resources">
          {project.resources.map((resource) => (
            <a href={`/materials/${resource.resourceType}/${resource.slug}`} class="resource-tag">
              {resource.name}
              {resource.metadata?.weight && (
                <span class="meta">({resource.metadata.weight})</span>
              )}
            </a>
          ))}
        </div>
      </section>
    )}
  </article>
</BaseLayout>
```

### Resource Categories Index

```astro
// src/pages/materials/index.astro
---
import BaseLayout from '@/layouts/BaseLayout.astro';
import { marvin } from '@/lib/marvin';

const resources = await marvin.getResources();

// Group resources by type
const byType = resources.reduce((acc, resource) => {
  const type = resource.resourceType || 'other';
  if (!acc[type]) acc[type] = [];
  acc[type].push(resource);
  return acc;
}, {} as Record<string, typeof resources>);

const types = Object.keys(byType).sort();
---

<BaseLayout title="Materials & Resources">
  <h1>Materials & Resources</h1>
  
  {types.map((type) => (
    <section class="resource-category">
      <h2>{type.charAt(0).toUpperCase() + type.slice(1)}</h2>
      
      <ul class="resource-list">
        {byType[type].map((resource) => (
          <li>
            <a href={`/materials/${type}/${resource.slug}`}>
              {resource.name}
            </a>
            {resource.description && (
              <span class="description">{resource.description}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  ))}
</BaseLayout>
```

---

## Assets & Images

### Image Gallery

```astro
// src/pages/gallery.astro
---
import BaseLayout from '@/layouts/BaseLayout.astro';
import { marvin } from '@/lib/marvin';

const images = await marvin.getAssets({ type: 'image' });
---

<BaseLayout title="Gallery">
  <h1>Gallery</h1>
  
  <div class="gallery">
    {images.map((image) => (
      <figure>
        <img
          src={image.url}
          alt={image.altText || image.name}
          width={image.width}
          height={image.height}
          loading="lazy"
        />
        {image.description && (
          <figcaption>{image.description}</figcaption>
        )}
      </figure>
    ))}
  </div>
</BaseLayout>

<style>
  .gallery {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1rem;
  }
  
  figure {
    margin: 0;
  }
  
  img {
    width: 100%;
    height: auto;
    object-fit: cover;
    aspect-ratio: 1;
  }
</style>
```

---

## Metadata & SEO

### SEO Component

```astro
// src/components/SEO.astro
---
import type { MarvinEntry } from '@/lib/marvin';

interface Props {
  entry: MarvinEntry;
  siteName: string;
}

const { entry, siteName } = Astro.props;
const canonicalUrl = `${import.meta.env.SITE}/${entry.slug}`;
const ogImage = entry.assets?.[0]?.url;
---

<head>
  <title>{entry.title} | {siteName}</title>
  <meta name="description" content={entry.summary || entry.description} />
  <link rel="canonical" href={canonicalUrl} />
  
  <!-- Open Graph -->
  <meta property="og:type" content="article" />
  <meta property="og:title" content={entry.title} />
  <meta property="og:description" content={entry.summary || entry.description} />
  <meta property="og:url" content={canonicalUrl} />
  {ogImage && <meta property="og:image" content={ogImage} />}
  
  <!-- Twitter Card -->
  <meta name="twitter:card" content={ogImage ? 'summary_large_image' : 'summary'} />
  <meta name="twitter:title" content={entry.title} />
  <meta name="twitter:description" content={entry.summary || entry.description} />
  {ogImage && <meta name="twitter:image" content={ogImage} />}
  
  <!-- Article Meta -->
  {entry.publishedAt && (
    <meta property="article:published_time" content={entry.publishedAt} />
  )}
  {entry.metadata?.tags && (
    entry.metadata.tags.map((tag: string) => (
      <meta property="article:tag" content={tag} />
    ))
  )}
</head>
```

### Usage in Page

```astro
// src/pages/blog/[slug].astro
---
import BaseLayout from '@/layouts/BaseLayout.astro';
import SEO from '@/components/SEO.astro';
import { marvin } from '@/lib/marvin';

export async function getStaticPaths() {
  const posts = await marvin.getEntries({ entryType: 'blog' });
  return posts.map((post) => ({
    params: { slug: post.slug },
    props: { post },
  }));
}

const { post } = Astro.props;
const site = await marvin.getSite();
---

<html>
  <SEO entry={post} siteName={site.title} />
  <body>
    <!-- page content -->
  </body>
</html>
```

---

## Advanced Examples

### Pagination

```astro
// src/pages/blog/[...page].astro
---
import type { GetStaticPaths } from 'astro';
import { marvin } from '@/lib/marvin';

export const getStaticPaths: GetStaticPaths = async ({ paginate }) => {
  const posts = await marvin.getEntries({ entryType: 'blog' });
  
  return paginate(posts, { pageSize: 10 });
};

const { page } = Astro.props;
---

<div class="posts">
  {page.data.map((post) => (
    <article>
      <h2><a href={`/blog/${post.slug}`}>{post.title}</a></h2>
    </article>
  ))}
</div>

<nav class="pagination">
  {page.url.prev && <a href={page.url.prev}>← Previous</a>}
  <span>Page {page.currentPage} of {page.lastPage}</span>
  {page.url.next && <a href={page.url.next}>Next →</a>}
</nav>
```

### Sitemap Generation

```ts
// src/pages/sitemap.xml.ts
import type { APIRoute } from 'astro';
import { marvin } from '@/lib/marvin';

export const GET: APIRoute = async () => {
  const [pages, posts, projects] = await Promise.all([
    marvin.getEntries({ entryType: 'page' }),
    marvin.getEntries({ entryType: 'blog' }),
    marvin.getEntries({ entryType: 'project' }),
  ]);

  const entries = [...pages, ...posts, ...projects];
  const baseUrl = import.meta.env.SITE;

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  ${entries.map((entry) => `
  <url>
    <loc>${baseUrl}/${entry.slug}</loc>
    <lastmod>${entry.updatedAt}</lastmod>
  </url>`).join('')}
</urlset>`;

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml',
    },
  });
};
```

# Marvin Client Quick Start

Get up and running with the Marvin publishing client in 5 minutes.

## Step 1: Copy the Client

Copy the client into your Astro project:

```bash
# Navigate to your Astro project
cd /path/to/mash-burn-astro

# Create lib directory
mkdir -p src/lib/marvin

# Copy the client files
cp -r /path/to/marvin/packages/marvin-client/* src/lib/marvin/
```

## Step 2: Configure Environment Variables

Create a `.env` file in your project root:

```bash
# Copy the example
cp src/lib/marvin/.env.example .env
```

Edit `.env` and add your Marvin credentials:

```env
MARVIN_API_URL=https://marvin.mashburn.co
MARVIN_SITE_CLIENT_TOKEN=your_token_here
MARVIN_WORKSPACE_SLUG=mash-burn
```

**Get your Site Client Token:**
1. Log into Marvin
2. Go to Settings → Publishing → Site Clients
3. Create a new client for "Mash & Burn Co. Website"
4. Copy the token

## Step 3: Create Client Instance

Create a file to initialize the client:

```ts
// src/lib/marvin.ts
import { createMarvinClient } from './marvin';

export const marvin = createMarvinClient();
```

## Step 4: Fetch Content

Use the client in any `.astro` file:

```astro
---
// src/pages/index.astro
import { marvin } from '@/lib/marvin';

const site = await marvin.getSite();
const entries = await marvin.getEntries();
---

<html>
  <head>
    <title>{site.title}</title>
  </head>
  <body>
    <h1>{site.title}</h1>
    <p>{site.tagline}</p>
    
    <ul>
      {entries.map((entry) => (
        <li><a href={`/${entry.slug}`}>{entry.title}</a></li>
      ))}
    </ul>
  </body>
</html>
```

## Step 5: Create Dynamic Routes

Create dynamic pages for your content:

```astro
---
// src/pages/[slug].astro
import { marvin } from '@/lib/marvin';

export async function getStaticPaths() {
  const pages = await marvin.getEntries({ entryType: 'page' });
  
  return pages.map((page) => ({
    params: { slug: page.slug },
    props: { page },
  }));
}

const { page } = Astro.props;
---

<html>
  <head>
    <title>{page.title}</title>
  </head>
  <body>
    <h1>{page.title}</h1>
    <div set:html={page.contentMarkdown} />
  </body>
</html>
```

## Step 6: Build Your Site

```bash
npm run build
```

Your site will fetch all content from Marvin at build time!

## Next Steps

- Read the [full README](./README.md) for all API methods
- Check out [examples](./examples.md) for real-world usage patterns
- Add SEO metadata using entry data
- Create collection landing pages
- Build a blog or project portfolio

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

## Need Help?

- 📖 Read the [full documentation](./README.md)
- 💡 Check the [examples](./examples.md)
- 🐛 Check for `TODO` comments in `client.ts` for missing endpoints

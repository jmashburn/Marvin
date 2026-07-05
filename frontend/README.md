# Marvin Frontend

Modern content management interface for the Marvin platform, built with Astro 5.13.5.

## Features

- **Multi-Workspace Support**: Switch between workspaces with persistent state
- **Entry Management**: Create, edit, and organize entries by type
- **Collections**: Curate and group related entries
- **Entry Types**: Define custom content types with icons and colors
- **Assets**: Upload and manage media files
- **Publishing**: Configure site clients for external content delivery

## Getting Started

### Prerequisites

- Node.js 18+ (or compatible runtime)
- Marvin backend API running on `http://localhost:8080`

### Environment Variables

Create a `.env` file in the `frontend` directory:

```bash
MARVIN_API_URL=http://localhost:8080
MARVIN_SITE_CLIENT_TOKEN=your_token_here  # Optional, for site client auth
```

### Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The frontend will be available at `http://localhost:4321`

## Architecture

### Tech Stack

- **Astro 5.13.5**: SSR-first framework with file-based routing
- **TypeScript**: Type-safe API client and components
- **No Client Framework**: Progressive enhancement with vanilla JS

### Directory Structure

```
frontend/
├── src/
│   ├── components/       # Reusable Astro components
│   ├── layouts/          # Page layouts (AppLayout, etc.)
│   ├── lib/
│   │   └── api/          # Backend API client modules
│   ├── pages/            # File-based routing
│   │   ├── api/          # Server-side API endpoints (proxies)
│   │   ├── entries/      # Entry management pages
│   │   ├── collections/  # Collection pages
│   │   ├── entry-types/  # Entry type management
│   │   ├── workspaces/   # Workspace management
│   │   └── settings/     # Settings pages
│   └── styles/           # Global CSS
└── public/               # Static assets
```

### API Integration

The frontend communicates with the Marvin backend via:

1. **Direct API calls** in Astro pages (SSR)
2. **Proxy endpoints** (`/api/*`) for form submissions
3. **Workspace context** managed by backend via cookies

All API clients are in `src/lib/api/`:
- `workspaces.ts` - Workspace management
- `entries.ts` - Entry CRUD operations
- `entryTypes.ts` - Entry type management
- `collections.ts` - Collection management
- `platform.ts` - Assets and site clients

### State Management

- **No client-side state**: All data fetched fresh on each page load (SSR)
- **Workspace switching**: Handled by backend `active_group_id` on user model
- **Form submissions**: POST to `/api/*` endpoints, redirect on success

## Key Pages

| Route | Description |
|-------|-------------|
| `/` | Dashboard with stats and recent entries |
| `/entries` | List all entries, filterable by type |
| `/entries/new` | Create new entry form |
| `/entries/[id]` | Edit entry (markdown editor + metadata) |
| `/entry-types` | Manage entry types |
| `/collections` | Manage collections |
| `/assets` | Media library |
| `/site-clients` | Publishing client management |
| `/workspaces` | List all accessible workspaces |
| `/settings/workspace` | Workspace preferences |

## Styling

Uses a custom design system with CSS variables defined in `styles/global.css`:

- Minimal, content-first aesthetic
- Dark sidebar navigation
- Responsive grid layouts
- Consistent spacing and typography

## Development Notes

### Adding New Pages

1. Create page in `src/pages/` (auto-routed)
2. Use `AppLayout.astro` for consistent shell
3. Fetch data in page frontmatter (SSR)
4. Handle errors gracefully with try/catch

### Adding API Endpoints

1. Create endpoint in `src/pages/api/`
2. Import API client from `src/lib/api/`
3. Handle POST/PATCH/DELETE, redirect on success
4. Return JSON error on failure

### Form Pattern

```astro
---
// SSR data fetching
const data = await fetchSomething();
---

<form method="POST" action="/api/resource/create">
  <input name="field" required />
  <button type="submit">Create</button>
</form>
```

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Progressive enhancement for JavaScript-disabled browsers
- Responsive design for mobile/tablet

## License

See main Marvin project LICENSE.

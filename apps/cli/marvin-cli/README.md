# Marvin CLI (`marvinctl`)

Command-line interface for interacting with the Marvin Publishing API. Query entries, collections, resources, and assets from your terminal.

## Features

- 📊 **Table output by default** - Human-readable tables in your terminal
- 🔄 **Multiple output formats** - Table, JSON, YAML, CSV
- 🔍 **Filter and query** - Filter by entry type, collection, asset type
- 🚀 **Fast** - Direct HTTP calls to publishing API
- 🔐 **Site client tokens** - Uses publishing API (not admin API)

## Prerequisites

- Node.js 18+ 
- A running Marvin instance
- A site client token (get from Marvin → Settings → Publishing → Site Clients)

## Installation

### 1. Install dependencies

```bash
cd apps/cli/marvin-cli
npm install
```

### 2. Configure environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your Marvin configuration:

```env
MARVIN_API_URL=http://localhost:8000
MARVIN_SITE_CLIENT_TOKEN=marvin_sk_your_token_here
MARVIN_WORKSPACE_SLUG=your-workspace-slug
```

**Where to get these values:**

- **MARVIN_API_URL**: Your Marvin instance URL (e.g., `http://localhost:8000` for local dev)
- **MARVIN_SITE_CLIENT_TOKEN**: Create in Marvin UI → Settings → Publishing → Site Clients
- **MARVIN_WORKSPACE_SLUG**: Your workspace slug (e.g., `mash-burn`)

### 3. Build the CLI

```bash
npm run build
```

### 4. Link globally (optional)

To use `marvinctl` from anywhere:

```bash
npm link
```

Or run directly without linking:

```bash
npm start -- entries  # Run without linking
```

After linking, you can run `marvinctl` from any directory.

## Usage

### Basic Commands

```bash
# Get workspace site configuration
marvinctl site

# List all published entries
marvinctl entries

# Get a single entry
marvinctl entry about

# List collections
marvinctl collections

# Get a collection with its entries
marvinctl collection featured

# List entries in a collection
marvinctl collection-entries featured

# List all resources
marvinctl resources

# Get a single resource
marvinctl resource kuroki-s022

# Get entries that use a resource
marvinctl resource-entries kuroki-s022

# List all assets
marvinctl assets
```

### Filtering

```bash
# Filter entries by type
marvinctl entries --entry-type page
marvinctl entries --entry-type project

# Filter entries by collection
marvinctl entries --collection featured

# Limit results
marvinctl entries --limit 10

# Filter assets by MIME type
marvinctl assets --type image
marvinctl assets --type video
```

### Output Formats

The CLI supports four output formats:

#### Table (default)

```bash
marvinctl entries
```

Output:
```
┌───────────────┬─────────┬─────────┬───────────┬────────────┐
│ Title         │ Slug    │ Type    │ Status    │ Published  │
├───────────────┼─────────┼─────────┼───────────┼────────────┤
│ About Us      │ about   │ page    │ published │ 2026-07-01 │
│ Contact       │ contact │ page    │ published │ 2026-07-02 │
└───────────────┴─────────┴─────────┴───────────┴────────────┘
```

#### JSON

```bash
marvinctl entries --json
# or
marvinctl entries --output json
```

Output:
```json
[
  {
    "slug": "about",
    "title": "About Us",
    "entryType": "page",
    "status": "published",
    "publishedAt": "2026-07-01T12:00:00Z"
  }
]
```

#### YAML

```bash
marvinctl collections --yaml
```

Output:
```yaml
- slug: featured
  name: Featured Projects
  description: Our best work
  entryCount: 5
```

#### CSV

```bash
marvinctl resources --csv > resources.csv
```

Output:
```csv
Name,Slug,Type,Description,URL
Kuroki S022 Denim,kuroki-s022,fabric,Premium Japanese selvedge,https://kuroki.com
```

### Command-Line Options

Global options (use before the command):

```bash
marvinctl --help                    # Show help
marvinctl --version                 # Show version
marvinctl --api-url <url>           # Override MARVIN_API_URL
marvinctl --token <token>           # Override MARVIN_SITE_CLIENT_TOKEN
marvinctl --workspace <slug>        # Override MARVIN_WORKSPACE_SLUG
marvinctl --output <format>         # Set output format (table, json, yaml, csv)
marvinctl --json                    # Shortcut for --output json
marvinctl --yaml                    # Shortcut for --output yaml
marvinctl --csv                     # Shortcut for --output csv
```

**Example:**

```bash
# Use a different workspace
marvinctl --workspace other-workspace entries

# Output as JSON
marvinctl entries --json

# Override API URL and output CSV
marvinctl --api-url https://marvin.example.com assets --csv
```

## Commands Reference

### Site

```bash
marvinctl site [--json|--yaml]
```

Fetch workspace site configuration (title, tagline, logo, etc.).

### Entries

```bash
marvinctl entries [options]
```

**Options:**
- `--entry-type <slug>` - Filter by entry type (e.g., `page`, `project`)
- `--collection <slug>` - Filter by collection
- `--limit <number>` - Limit results

**Examples:**
```bash
marvinctl entries                          # All entries
marvinctl entries --entry-type page        # Only pages
marvinctl entries --collection featured    # Entries in "featured" collection
marvinctl entries --limit 5                # First 5 entries
```

### Entry

```bash
marvinctl entry <slug>
```

Fetch a single entry by slug.

### Collections

```bash
marvinctl collections
```

List all collections with entry counts.

### Collection

```bash
marvinctl collection <slug>
```

Fetch a single collection with metadata.

### Collection Entries

```bash
marvinctl collection-entries <slug>
```

List all entries in a collection.

### Resources

```bash
marvinctl resources
```

List all resources (fabrics, tools, suppliers, etc.).

### Resource

```bash
marvinctl resource <slug>
```

Fetch a single resource by slug.

### Resource Entries

```bash
marvinctl resource-entries <slug>
```

List all entries that reference a resource.

### Assets

```bash
marvinctl assets [options]
```

**Options:**
- `--type <type>` - Filter by MIME type prefix (e.g., `image`, `video`, `audio`)
- `--limit <number>` - Limit results

**Examples:**
```bash
marvinctl assets                # All assets
marvinctl assets --type image   # Only images
marvinctl assets --type video   # Only videos
```

## Scripting Examples

### Export all entries to JSON

```bash
marvinctl entries --json > entries.json
```

### Get entry count

```bash
marvinctl entries --json | jq 'length'
```

### Export resources to CSV for spreadsheet

```bash
marvinctl resources --csv > resources.csv
```

### Check if a specific entry exists

```bash
if marvinctl entry about --json > /dev/null 2>&1; then
  echo "About page exists"
else
  echo "About page not found"
fi
```

### List all image assets

```bash
marvinctl assets --type image --json | jq -r '.[].name'
```

## Troubleshooting

### "MARVIN_API_URL is required"

Make sure your `.env` file exists and contains all required variables:

```bash
cat .env  # Check file exists
```

If missing, copy from the example:

```bash
cp .env.example .env
```

### "401 Unauthorized"

Your site client token is invalid or expired. Generate a new one:

1. Log into Marvin
2. Go to Settings → Publishing → Site Clients
3. Create a new client
4. Copy the token to your `.env` file

### "404 Not Found"

Check that:
- Your `MARVIN_API_URL` is correct
- The Marvin server is running
- The workspace slug is correct
- The entry/collection/resource slug exists

### "Command not found: marvinctl"

You need to link the CLI globally:

```bash
npm link
```

Or run directly:

```bash
npm start -- entries
```

### Build errors

Make sure you're using Node.js 18+:

```bash
node --version  # Should be v18 or higher
```

Reinstall dependencies:

```bash
rm -rf node_modules package-lock.json
npm install
npm run build
```

## Development

### Run without building

```bash
npm start -- entries --json
```

### Watch mode

```bash
npm run dev
```

Then in another terminal:

```bash
marvinctl entries
```

### Run tests

```bash
npm test
```

## Architecture

This CLI uses:
- **Commander.js** - CLI framework
- **Native fetch** - HTTP requests to Marvin API
- **dotenv** - Environment configuration
- **TypeScript** - Type safety

The CLI is a thin wrapper around the Marvin Publishing API. It does NOT:
- Import the Python backend
- Start the FastAPI server
- Access the database directly
- Require admin authentication

It ONLY makes HTTP calls to the Publishing API endpoints using site client tokens.

## Related

- [Marvin SDK](../../../packages/marvin-sdk/README.md) - TypeScript SDK for Astro/Next.js sites
- [Publishing API Docs](../../../docs/api/publishing.md) - API endpoint reference

## License

See main Marvin repository license.

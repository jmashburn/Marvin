# Mash & Burn Co. Seed Script

Idempotent seed script for importing Mash & Burn Co. content into Marvin.

## Overview

This script imports the complete Mash & Burn Co. website content from the [mashandburnco repository](https://github.com/iWobble/mashandburnco) (develop branch) into Marvin as structured Entry data.

**Source Data:**
- `src/data/site.ts` - Site configuration and navigation
- `src/data/projects.ts` - 7 workshop projects with full metadata

**Imported Content:**
- 1 Workspace (Mash & Burn Co.)
- 5 Entry Types (Page, Project, Bench Note, Product, Guide)
- 10 Collections (Site Pages, Projects, Featured, etc.)
- 7 Project Entries with resources and asset metadata
- 5 Page Entries (Home, Projects, Workshop, About, Contact)

## Quick Start

### After Fresh Database Reset

```bash
# 1. Reset database (run migrations)
task dev:clean
uv run alembic --config src/marvin/alembic.ini upgrade head

# 2. Start the server to ensure schema is ready
task py &

# 3. Run the seed script (creates API client automatically)
uv run scripts/seed_mashandburnco.py

# 4. Copy the API token from the output and test it!
```

The script will output:
- ✅ Summary of what was created
- 📝 **API Client Token** (save this!)
- 🧪 Ready-to-use curl commands for testing

### Rerunning the Seed

The script is **idempotent** - you can run it multiple times without duplicating data:

```bash
uv run scripts/seed_mashandburnco.py
```

It will:
- ✅ Create missing records
- ✅ Update existing records
- ✅ Skip duplicates
- ✅ Preserve workspace scoping
- ✅ Clear and rebuild relationships

## What Gets Seeded

### 1. Workspace

**Slug:** `mash-and-burn-co`  
**Name:** Mash & Burn Co.

### 2. Entry Types

| Slug | Name | Description |
|------|------|-------------|
| `page` | Page | Static site pages |
| `project` | Project | Workshop projects and products |
| `bench-note` | Bench Note | Workshop notes and updates |
| `product` | Product | Available products |
| `guide` | Guide | How-to guides and resources |

### 3. Collections

| Slug | Name | Icon | Purpose |
|------|------|------|---------|
| `site-pages` | Site Pages | - | All static pages |
| `projects` | Projects | - | All workshop projects |
| `featured` | Featured | - | Featured projects |
| `current-project` | Current Project | - | Currently available |
| `on-the-bench` | On the Bench | - | In-progress projects |
| `jackets` | Jackets | work-jacket | Jacket category |
| `totes-and-bags` | Totes & Bags | field-tote | Bag category |
| `accessories` | Accessories | watch-cap | Accessories category |
| `historical-wear` | Historical Wear | historical-wear | Historical pieces |
| `other` | Other | - | Miscellaneous |

### 4. Project Entries

Seven projects imported from `projects.ts`:

1. **Leather Tricorn Hat** (`leather-tricorn-hat`) - Historical Wear
2. **18th Century Frock Coat** (`18th-century-frock-coat`) - Historical Wear
3. **The Foundry Jacket** (`foundry-jacket`) - Jackets ⭐ Featured
4. **Chore Coat** (`chore-coat`) - Jackets
5. **Standard Issue Jean** (`standard-issue-jean`) - Other
6. **Field Tote** (`field-tote`) - Totes & Bags
7. **Watch Cap** (`watch-cap`) - Accessories

**Each project includes:**
- Full metadata preservation (projectNumber, category, workshopVerdict, etc.)
- Generated Markdown content (story, design intent, materials, care)
- Resources extracted from materials lists
- Asset metadata placeholders (hero images, support images)
- Collection assignments (Projects + category + featured status)

### 5. Page Entries

Five static pages:

1. **Home** (`home`) - Landing page with brand values
2. **Projects** (`projects`) - Project index
3. **Workshop** (`workshop`) - Workshop information
4. **About** (`about`) - About Mash & Burn Co.
5. **Contact** (`contact`) - Contact information

**Each page includes:**
- Route metadata for Astro integration
- Order for navigation
- Full page copy extracted from Astro components

### 6. Resources

Resources are automatically created from project materials:

**Types:**
- `material` - Fabrics, leathers, canvas
- `construction` - Stitching methods, seams
- `hardware` - Rivets, buttons, zippers
- `location` - Made in locations

**Example:** The Foundry Jacket creates resources for:
- 12oz Japanese Selvedge Denim (material)
- Yarn-Dyed Herringbone Twill Lining (material)
- Brass Button & Copper Rivets (hardware)
- Triple Needle Felled Seams (construction)
- Made in Raleigh, NC (location)

### 7. Assets

Asset **metadata** placeholders (actual files not imported):

**Roles:**
- `hero` - Featured/hero image for each project
- `detail` - Detail shots
- `material` - Material close-ups
- `process` - Process/workshop shots
- `texture` - Texture details

**Note:** The seed script creates asset records with alt text and metadata, but does NOT import actual image files. File serving will be implemented in Phase 8.

## Testing the Seed

### 1. Verify Publishing API

```bash
# Get workspace info
curl http://localhost:8080/api/publish/mash-and-burn-co

# List all published entries
curl http://localhost:8080/api/publish/mash-and-burn-co/entries

# Get a specific project
curl http://localhost:8080/api/publish/mash-and-burn-co/entries/foundry-jacket

# List collections
curl http://localhost:8080/api/publish/mash-and-burn-co/collections

# Get a collection with entries
curl http://localhost:8080/api/publish/mash-and-burn-co/collections/jackets
```

### 2. Get API Client Token

**The seed script automatically creates an API client!**

The token is printed at the end of the seed output:

```
📝 API Client Token (save this!):
   marvin_sk_8SQHV9K3bBYkglfW1Q9AjocpZzPFq-0KDUuhwU30TXI
```

If you need to regenerate the token later, use the admin UI or rotate it via the API.

### 3. Test with Bearer Token

```bash
TOKEN="marvin_sk_..."

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/publish/mash-and-burn-co/entries
```

## Data Mapping

### Project → Entry Mapping

| Source Field | Marvin Field | Notes |
|--------------|--------------|-------|
| `slug` | `slug` | Direct mapping |
| `title` | `title` | Direct mapping |
| `shortDescription` or `notes` | `summary` | Summary field |
| `notes` | `description` | Description field |
| Generated from story/intent/materials | `content_markdown` | Full Markdown content |
| `'published'` | `status` | All seeded as published |
| All original fields | `metadata_json` | Preserved for reference |

### Metadata Preservation

The `metadata_json` field preserves all original project data:

```json
{
  "id": "project-006",
  "projectNumber": "Project 006",
  "category": "Jackets",
  "material": "12oz Japanese Selvedge Denim",
  "projectStatus": "current",
  "availability": "Available",
  "workshopVerdict": "Probably Overbuilt.",
  "started": "Pattern Draft",
  "buildStage": "Current Build",
  "leadTime": "2-3 Weeks",
  "madeIn": "Raleigh, NC",
  "care": "Wash cold. Hang dry. Wear often.",
  "details": [...],
  "imageTone": "foundry",
  "href": "/projects/foundry-jacket",
  "featured": true
}
```

## Integration with Astro

Once seeded, the Astro site can consume data from Marvin instead of local `src/data/projects.ts`:

```typescript
// Before: Local data
import { projects } from '../data/projects';

// After: Marvin Publishing API
const response = await fetch(
  'https://marvin.example.com/api/publish/mash-and-burn-co/entries?entry_type=project',
  {
    headers: {
      'Authorization': `Bearer ${process.env.MARVIN_API_TOKEN}`
    }
  }
);
const { data: projects } = await response.json();
```

See `docs/ASTRO-INTEGRATION.md` for complete integration guide.

## Script Implementation Details

### Idempotency Strategy

**Workspace:** Upserted by slug  
**Entry Types:** Upserted by slug within workspace  
**Collections:** Upserted by slug within workspace  
**Entries:** Upserted by slug within workspace  
**Resources:** Found or created by slug, then linked  
**Assets:** Found or created by slug, then linked  
**Relationships:** Deleted and recreated on each run

### Logging

The script provides detailed logging:

```
==========================================================
Mash & Burn Co. Seed Script
==========================================================
Using admin user: admin

1. Setting up workspace...
✓ Workspace 'mash-and-burn-co' already exists

2. Setting up entry types...
  ✓ Entry type 'page' exists
  ✓ Entry type 'project' exists
  ...

3. Setting up collections...
  ✓ Collection 'projects' exists
  ...

4. Importing 7 projects...
  ✓ Created project entry 'foundry-jacket'
  ...

5. Importing 5 pages...
  ✓ Created page entry 'home'
  ...

==========================================================
✅ Seed complete!
==========================================================
```

### Error Handling

- ❌ **No admin user:** Script exits with clear error
- ❌ **Database connection fails:** SQLAlchemy raises exception
- ❌ **Duplicate constraint violation:** Script rolls back transaction

## Troubleshooting

### "No admin user found"

Create an admin user first:

```bash
# Through the application startup or manually insert
```

### "FOREIGN KEY constraint failed"

Ensure migrations are up to date:

```bash
uv run alembic --config src/marvin/alembic.ini upgrade head
```

### Script runs but no data appears

Check the workspace slug:

```python
# In the script, verify:
workspace_slug = "mash-and-burn-co"
```

Then query directly:

```bash
curl http://localhost:8080/api/publish/mash-and-burn-co
```

## Next Steps

After seeding:

1. **Create API Client** - Generate token for Astro integration
2. **Test Publishing API** - Verify all endpoints return data
3. **Build Astro PoC** - Follow `docs/ASTRO-INTEGRATION.md`
4. **Implement Asset Serving** - Phase 8 endpoint for actual file delivery
5. **Performance Optimization** - Add joinedload() for scale beyond 100 entries

## Files

- **Script:** `scripts/seed_mashandburnco.py`
- **Docs:** `docs/MASH-AND-BURN-SEED.md` (this file)
- **Source:** `https://github.com/iWobble/mashandburnco` (develop branch)
- **Publishing API Docs:** `docs/PUBLISHING-API-COMPLETE.md`
- **Astro Integration:** `docs/ASTRO-INTEGRATION.md`

## License

Seed script: Part of Marvin platform  
Source content: © Mash & Burn Co. / iWobble Labs

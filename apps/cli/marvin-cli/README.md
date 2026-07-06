# Marvin CLI

Small CLI for testing Marvin publish API / SDK-style access.

## Install

```bash
npm install
npm run build
npm link
```

Copy `.env.example` to `.env` and set:

```env
MARVIN_API_URL=http://localhost:8000
MARVIN_SITE_CLIENT_TOKEN=your-token
MARVIN_WORKSPACE_SLUG=mash-burn
```

## Output formats

The CLI supports `table`, `json`, `yaml`, and `csv`.

```bash
marvinctl collections
marvinctl collections --output json
marvinctl collections --output yaml
marvinctl collections --output csv

# Shortcuts
marvinctl entries --json
marvinctl resources --yaml
marvinctl assets --csv
```

`table` is the default for human-readable terminal output. Use `json`, `yaml`, or `csv` for scripting/export.

## Commands

```bash
marvinctl site
marvinctl entries
marvinctl entries --entry-type page
marvinctl entry about

marvinctl collections
marvinctl collection site-pages
marvinctl collection-entries site-pages

marvinctl resources
marvinctl resource kuroki-s022
marvinctl resource-entries kuroki-s022

marvinctl assets
```

## Notes

This CLI uses only HTTP calls to Marvin. It should not import or start the Python/FastAPI backend.

If `marvin` starts Uvicorn, you are running the backend command, not this CLI. Use `marvinctl`.

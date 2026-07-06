# Marvin Packages

External, portable packages that can be used outside of the main Marvin application.

## Available Packages

### [@marvin/sdk](./marvin-sdk/)

The official TypeScript SDK for Marvin CMS. A modern, workspace-first SDK for building applications that integrate with Marvin.

**Use Case**: The primary way to integrate with Marvin across static sites, servers, CLIs, automation, and custom applications.

**Key Features**:
- 🎯 Workspace-First - Work with Marvin concepts (Workspace, Entry, Collection)
- 🚀 Performance - Built-in caching for build-time usage
- 📘 Fully Typed - Complete TypeScript support
- 🔄 Backwards Compatible - Works with existing APIs
- 🎨 Object-Oriented - Rich objects instead of raw JSON
- 🔒 Secure - Uses site client tokens (not user tokens)

**Quick Start**:

```bash
# Copy into your project
cp -r packages/marvin-sdk src/lib/marvin

# Configure environment variables
MARVIN_API_URL=https://marvin.example.com
MARVIN_SITE_CLIENT_TOKEN=your-token
MARVIN_WORKSPACE_SLUG=your-workspace

# Use in your code
import { createMarvinClient } from '@/lib/marvin';
const marvin = createMarvinClient();

// Workspace-first API
const workspace = await marvin.getWorkspace();
const entries = await workspace.entries.list();

// Convenience API
const entry = await marvin.entry('about');
const projects = await marvin.projects();
```

See [marvin-sdk/README.md](./marvin-sdk/README.md) for full documentation.

---

## Package Guidelines

Packages in this directory should be:

1. **Portable** - Can be copied or installed into external projects
2. **Self-contained** - No dependencies on Marvin internals
3. **Well-documented** - Complete README with examples
4. **Typed** - Full TypeScript support
5. **Versioned** - Follow semantic versioning

## Adding a New Package

1. Create a new directory: `packages/package-name/`
2. Add the following files:
   - `README.md` - Full documentation
   - `package.json` - Package metadata
   - `index.ts` - Main entry point
   - `types.ts` - TypeScript types (if applicable)
   - `.env.example` - Example environment configuration (if applicable)
3. Update this README with package information
4. Add usage examples

## License

Packages follow the same license as the main Marvin project unless otherwise specified.

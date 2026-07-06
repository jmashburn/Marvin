# Marvin Packages

External, portable packages that can be used outside of the main Marvin application.

## Available Packages

### [@marvin/client](./marvin-client/)

A portable TypeScript client for fetching published content from Marvin CMS.

**Use Case**: Integrate Marvin as a headless CMS in Astro, Next.js, or other static site generators.

**Key Features**:
- 🚀 Portable - Copy into any TypeScript project
- 🔒 Secure - Uses site client tokens (not user tokens)
- 🏗️ Build-time - Optimized for static site generation
- 📘 Typed - Full TypeScript support

**Quick Start**:

```bash
# Copy into your project
cp -r packages/marvin-client src/lib/marvin

# Configure environment variables
MARVIN_API_URL=https://marvin.example.com
MARVIN_SITE_CLIENT_TOKEN=your-token
MARVIN_WORKSPACE_SLUG=your-workspace

# Use in your code
import { createMarvinClient } from '@/lib/marvin';
const marvin = createMarvinClient();
const entries = await marvin.getEntries();
```

See [marvin-client/README.md](./marvin-client/README.md) for full documentation.

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

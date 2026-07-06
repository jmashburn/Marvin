# GitHub Actions Setup

This repository includes automated workflows for testing and publishing.

## Workflows

### 1. Test Workflow (`test.yml`)
- **Triggers**: On every PR to `main` and every push to `main`
- **Actions**:
  - Installs dependencies
  - Builds the package
  - Runs TypeScript type checking
  - Validates package contents

### 2. Publish Workflow (`publish.yml`)
- **Triggers**: On every push to `main` (after PR merge)
- **Actions**:
  - Builds the package
  - Runs type checking
  - Publishes to npm with provenance
  - Uses `--access public` for scoped package

## Required Setup

### NPM Token Configuration

To enable automatic publishing, you need to configure an npm access token:

1. **Create npm Access Token**:
   - Log in to https://www.npmjs.com
   - Go to Access Tokens: https://www.npmjs.com/settings/YOUR_USERNAME/tokens
   - Click "Generate New Token" → "Classic Token"
   - Select "Automation" type (recommended for CI/CD)
   - Copy the token (starts with `npm_`)

2. **Add Token to GitHub Secrets**:
   - Go to: https://github.com/InnerOpen/marvin-sdk/settings/secrets/actions
   - Click "New repository secret"
   - Name: `NPM_TOKEN`
   - Value: Paste your npm token
   - Click "Add secret"

3. **Verify Permissions**:
   - The npm token must have publish permissions
   - Your npm account must have publish access to `@marvin` scope
   - If the `@marvin` scope doesn't exist, create it first or publish under a different scope

## Package Versioning

The workflow publishes whatever version is in `package.json`. To release a new version:

1. Update version in `package.json`:
   ```bash
   npm version patch  # 1.0.0 → 1.0.1
   npm version minor  # 1.0.0 → 1.1.0
   npm version major  # 1.0.0 → 2.0.0
   ```

2. Commit and push:
   ```bash
   git add package.json
   git commit -m "chore: bump version to X.Y.Z"
   git push origin main
   ```

3. The workflow automatically publishes the new version to npm

## Provenance

The publish workflow uses `--provenance` flag, which:
- Links the published package to its source commit
- Provides transparency about package origin
- Requires `id-token: write` permission (already configured)
- Only works with npm automation tokens

## Manual Publishing

If you need to publish manually:

```bash
npm login
npm run build
npm publish --access public
```

## Troubleshooting

### "402 Payment Required" Error
- The `@marvin` scope might require a paid npm organization
- Solution: Create an npm organization or publish under personal scope

### "403 Forbidden" Error
- The npm token doesn't have publish permissions
- Solution: Regenerate token with "Automation" type

### "401 Unauthorized" Error
- The `NPM_TOKEN` secret is missing or incorrect
- Solution: Check GitHub secrets configuration

### Package Already Published
- npm doesn't allow republishing the same version
- Solution: Bump version in `package.json` before merging to main

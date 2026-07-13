# Release Process

## Overview

The Marvin server uses **Python Semantic Release** to automate versioning based on [Conventional Commits](https://www.conventionalcommits.org/).

## Automatic Versioning

Versions are determined by commit messages following the Conventional Commits specification:

### Version Bumps

- **Major** (1.0.0 → 2.0.0): Breaking changes
  ```bash
  git commit -m "feat!: remove legacy API endpoints"
  # or
  git commit -m "feat: migrate to new auth system

  BREAKING CHANGE: Old auth tokens are no longer valid"
  ```

- **Minor** (1.0.0 → 1.1.0): New features (backward compatible)
  ```bash
  git commit -m "feat: add workspace templates feature"
  ```

- **Patch** (1.0.0 → 1.0.1): Bug fixes
  ```bash
  git commit -m "fix: resolve email template rendering issue"
  ```

### Commit Types

Recognized commit types:
- `feat`: New feature (triggers minor version bump)
- `fix`: Bug fix (triggers patch version bump)
- `perf`: Performance improvement (triggers patch version bump)
- `docs`: Documentation only (no version bump)
- `style`: Code style changes (no version bump)
- `refactor`: Code refactoring (no version bump)
- `test`: Adding tests (no version bump)
- `build`: Build system changes (no version bump)
- `ci`: CI configuration changes (no version bump)
- `chore`: Other changes (no version bump)

## Branch Strategy

### `main` branch
- Stable releases
- Tagged as `v1.0.0`, `v1.1.0`, etc.
- No prerelease suffix

### `develop` branch
- Development/preview releases
- Tagged as `v1.0.0-next.1`, `v1.1.0-next.2`, etc.
- Includes `-next` prerelease suffix

## Automated Release Workflow

When you push to `main` or `develop`, GitHub Actions automatically:

1. **Analyzes commits** since the last release
2. **Determines version bump** based on commit types
3. **Updates version** in:
   - `pyproject.toml` (`project.version`)
   - `src/marvin/__init__.py` (`__version__`)
4. **Generates/updates** `CHANGELOG.md`
5. **Creates git tag** (e.g., `v1.2.0` or `v1.2.0-next.1`)
6. **Creates GitHub Release** with release notes
7. **Commits changes** back to the branch with `[skip ci]`

## Manual Release Process

If you need to trigger a release manually:

```bash
# Install python-semantic-release
pip install python-semantic-release

# Preview what would happen (dry run)
semantic-release version --dry-run

# Create a new version
semantic-release version

# Publish the release
semantic-release publish
```

## Version File Locations

The version is maintained in two places:

1. **pyproject.toml**
   ```toml
   [project]
   version = "0.2.0"
   ```

2. **src/marvin/__init__.py**
   ```python
   __version__ = "0.2.0"
   ```

Python Semantic Release keeps these in sync automatically.

## Example Workflows

### Feature Development

```bash
# Work on develop branch
git checkout develop

# Make changes
git add .
git commit -m "feat: add user profile export feature"
git push origin develop

# → Auto-publishes v0.3.0-next.1 (or next increment)
```

### Bug Fix

```bash
# Work on develop branch
git checkout develop

# Fix the bug
git add .
git commit -m "fix: resolve workspace deletion cascade issue"
git push origin develop

# → Auto-publishes v0.2.1-next.1 (patch bump)
```

### Promoting to Stable

```bash
# Merge develop into main
git checkout main
git merge develop
git push origin main

# → Auto-publishes v0.3.0 (stable release)
```

### Breaking Change

```bash
# Work on develop branch
git checkout develop

# Make breaking change
git add .
git commit -m "feat!: migrate to new workspace permissions model

BREAKING CHANGE: The workspace_role field has been replaced with
granular permissions. Update your API calls to use the new permission
system."
git push origin develop

# → Auto-publishes v1.0.0-next.1 (major bump)
```

## Checking Current Version

```bash
# Check pyproject.toml
grep "^version" pyproject.toml

# Check __init__.py
grep "__version__" src/marvin/__init__.py

# Check latest git tag
git describe --tags --abbrev=0

# Check all tags
git tag -l "v*" | sort -V
```

## Release Notes

Release notes are automatically generated from commit messages and organized by type:

- ✨ **Features**: All `feat:` commits
- 🐛 **Bug Fixes**: All `fix:` commits
- 📚 **Documentation**: All `docs:` commits
- 🔧 **Chores**: All `chore:`, `build:`, `ci:` commits
- ♻️ **Refactoring**: All `refactor:`, `perf:` commits
- 🧪 **Tests**: All `test:` commits

## Configuration

Semantic release is configured in `pyproject.toml`:

```toml
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
version_variables = ["src/marvin/__init__.py:__version__"]
branch = "main"
tag_format = "v{version}"
upload_to_pypi = false
upload_to_vcs_release = true
```

## Troubleshooting

### No version bump triggered

**Cause**: No commits with `feat:` or `fix:` since last release

**Solution**: Ensure your commits follow conventional commit format

### GitHub Actions workflow fails

**Cause**: Missing `GITHUB_TOKEN` permissions

**Solution**: Check that the workflow has `contents: write` permission in `.github/workflows/release.yml`

### Version conflicts

**Cause**: Manual version edits conflict with automated versioning

**Solution**: Don't manually edit version numbers - let semantic-release manage them

## Best Practices

1. **Always use conventional commits** for clear version history
2. **Write descriptive commit messages** - they become your release notes
3. **Test on develop** before merging to main
4. **Use `BREAKING CHANGE:` footer** for major version bumps
5. **Squash fixup commits** before merging to keep changelog clean
6. **Review the generated CHANGELOG.md** after each release

## References

- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Python Semantic Release Documentation](https://python-semantic-release.readthedocs.io/)
- [Semantic Versioning](https://semver.org/)

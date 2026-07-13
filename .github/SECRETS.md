# GitHub Secrets Configuration

This document lists all required GitHub secrets for the Marvin CI/CD pipeline.

## How to Add Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the secret name and value
5. Click **Add secret**

## Required Secrets

### Container Registry

#### `GITHUB_TOKEN` (Auto-provided)
- **Required for**: All workflows
- **Description**: Automatically provided by GitHub Actions
- **Permissions**: Configured via `permissions:` in each workflow
- **Uses**:
  - Docker image publishing to GHCR
  - GitHub Releases creation
  - Accessing other repos (SDK/CLI) for testing
- **Note**: No manual setup required

### Optional Secrets

#### `GHCR_TOKEN` (Not Required)
- **Alternative to**: `GITHUB_TOKEN` for container registry
- **Description**: GitHub Container Registry personal access token
- **How to create**:
  1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
  2. Generate new token with `write:packages` and `read:packages` scopes
  3. Copy the token
- **Note**: Only needed if `GITHUB_TOKEN` lacks necessary permissions (rare)

#### `PYPI_TOKEN` (Future)
- **Required for**: Future PyPI publishing
- **Description**: PyPI API token for publishing Python packages
- **How to create**:
  1. Log in to pypi.org
  2. Account settings → API tokens
  3. Create token with scope for your project
- **Note**: Not currently used, but will be needed if publishing Marvin server to PyPI

### Testing (Optional)

#### `MARVIN_TEST_DATABASE_URL`
- **Required for**: Custom test database configuration
- **Description**: PostgreSQL connection string for integration tests
- **Format**: `postgresql://user:password@host:port/database`
- **Note**: Optional - workflows use service containers by default

#### `MARVIN_TEST_REDIS_URL`
- **Required for**: Custom Redis configuration
- **Description**: Redis connection string for integration tests
- **Format**: `redis://host:port/db`
- **Note**: Optional - workflows use service containers by default

### Deployment (Future)

#### `KUBE_CONFIG`
- **Required for**: Kubernetes deployment workflows
- **Description**: Base64-encoded kubeconfig file for cluster access
- **How to create**:
  ```bash
  cat ~/.kube/config | base64 -w 0
  ```
- **Note**: Not currently used - for future deployment automation

#### `HELM_REGISTRY_TOKEN`
- **Required for**: Private Helm registry publishing
- **Description**: Authentication token for private Helm chart registry
- **Note**: Not currently used if publishing to GitHub Releases only

### Code Scanning

#### GitHub Token (Auto-provided)
- **Name**: `GITHUB_TOKEN`
- **Description**: Automatically provided by GitHub Actions
- **Scopes**: Varies by workflow, configured via `permissions:` in workflow files
- **Note**: No manual setup required

## Environment-Specific Secrets

### Production Environment
Create an environment called `production` with these secrets:

- `PRODUCTION_DATABASE_URL`
- `PRODUCTION_REDIS_URL`
- `PRODUCTION_SECRET_KEY`

### Staging Environment
Create an environment called `staging` with these secrets:

- `STAGING_DATABASE_URL`
- `STAGING_REDIS_URL`
- `STAGING_SECRET_KEY`

## Secret Usage by Workflow

| Workflow | Required Secrets | Optional Secrets |
|----------|------------------|------------------|
| pr-ci.yml | None | None |
| test.yml | None | `MARVIN_TEST_DATABASE_URL`, `MARVIN_TEST_REDIS_URL` |
| docker.yml | `GITHUB_TOKEN` (auto) | `GHCR_TOKEN` |
| release.yml | `GITHUB_TOKEN` (auto) | `PYPI_TOKEN` |
| codeql.yml | `GITHUB_TOKEN` (auto) | None |
| helm.yml | None | `HELM_REGISTRY_TOKEN` |
| sdk.yml | `GITHUB_TOKEN` (auto) | None |
| cli.yml | `GITHUB_TOKEN` (auto) | None |
| workspace.yml | None | None |
| docs.yml | `GITHUB_TOKEN` (auto) | None |

## SDK and CLI Publishing

**Important:** The SDK and CLI are published from their own repositories, not from the Marvin server repository.

### marvin-sdk Repository
- **Location**: `InnerOpen/marvin-sdk`
- **Secret needed**: `NPM_TOKEN` (configured in SDK repo)
- **Publishes**: `@inneropen/marvin-sdk` to npm
- **Workflow**: Has its own `.github/workflows/release.yml`

### marvin-cli Repository
- **Location**: `InnerOpen/marvin-cli`
- **Secret needed**: `NPM_TOKEN` (configured in CLI repo)
- **Publishes**: `@inneropen/marvin-cli` to npm
- **Workflow**: Has its own `.github/workflows/release.yml`

The Marvin server repository only publishes:
- ✅ Docker images to GitHub Container Registry (ghcr.io)
- ✅ Helm charts to GitHub Releases

## Validating Secrets

### Test GitHub Token
```bash
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
```

### Test Docker Registry
```bash
echo YOUR_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

## Security Best Practices

1. **Never commit secrets** to the repository
2. **Use minimal scopes** for tokens (principle of least privilege)
3. **Rotate tokens regularly** (every 90 days recommended)
4. **Use environments** for sensitive deployments
5. **Review secret access** in audit logs periodically
6. **Delete unused secrets** to minimize exposure
7. **Use OIDC** for cloud providers when possible (AWS, GCP, Azure)

## Troubleshooting

### Secret Not Found Error
```
Error: Secret SOME_SECRET not found
```
**Solution**: Verify secret name matches exactly (case-sensitive)

### Authentication Failed
```
Error: authentication required
```
**Solution**:
1. Verify token hasn't expired
2. Check token has correct permissions
3. Regenerate token if necessary

### Permission Denied
```
Error: permission denied
```
**Solution**: Ensure workflow has correct `permissions:` block

## OIDC Tokens (Future Enhancement)

GitHub Actions can use OpenID Connect (OIDC) to authenticate with cloud providers without storing long-lived credentials:

### AWS Example (Future)
```yaml
permissions:
  id-token: write
  contents: read

- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::ACCOUNT:role/GitHubActionsRole
    aws-region: us-east-1
```

### GCP Example (Future)
```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: 'projects/PROJECT_ID/locations/global/...'
    service_account: 'github-actions@PROJECT_ID.iam.gserviceaccount.com'
```

## Monitoring

Monitor secret usage via:
1. GitHub Actions audit log
2. npm registry access logs
3. Docker registry access logs
4. Cloud provider audit trails

## Support

For secret-related issues:
1. Check this documentation
2. Verify secret configuration in GitHub settings
3. Review workflow logs for specific errors
4. Contact repository maintainers

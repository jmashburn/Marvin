# Marvin Helm Chart

Helm chart for deploying Marvin event bus application to Kubernetes/OpenShift.

## Overview

Marvin is an event bus application with webhook delivery, scheduling, and state persistence. This Helm chart provides:

- Automated database migrations via Helm hooks
- Multi-environment support (dev, staging, production)
- OpenShift Route integration
- Persistent storage for SQLite database
- Configurable resource limits
- Health checks and readiness probes

## Prerequisites

- Kubernetes 1.19+ or OpenShift 4.x+
- Helm 3.0+
- PersistentVolume provisioner support (for SQLite data)
- Container registry access (for pulling Marvin image)

## Installation

### Quick Start (Development)

```bash
# Install with default development values
helm install marvin ./marvin-chart

# Or specify namespace
helm install marvin ./marvin-chart --namespace marvin-dev --create-namespace
```

### Staging Deployment

```bash
helm install marvin ./marvin-chart \
  --namespace marvin-staging \
  --create-namespace \
  --values marvin-chart/values-staging.yaml \
  --set image.tag=$(git rev-parse --short HEAD)
```

### Production Deployment

```bash
helm upgrade --install marvin ./marvin-chart \
  --namespace marvin-prod \
  --create-namespace \
  --values marvin-chart/values-production.yaml \
  --set image.tag=$(git rev-parse --short HEAD) \
  --wait \
  --timeout 15m \
  --atomic
```

## Configuration

### Values Files

The chart includes three values files for different environments:

- **values.yaml** - Development defaults (1 replica, debug logging, local SMTP)
- **values-staging.yaml** - Staging overrides (2 replicas, info logging)
- **values-production.yaml** - Production settings (2+ replicas, strict security)

### Key Configuration Options

#### Image Settings

```yaml
image:
  repository: marvin
  pullPolicy: IfNotPresent
  tag: "latest"
```

#### Application Configuration

```yaml
config:
  production: false          # Enable production mode
  allowSignup: true          # Allow user signups
  logLevel: DEBUG            # Logging level (DEBUG, INFO, WARNING, ERROR)
  dbEngine: sqlite           # Database engine
  dataDir: /app/data         # Data directory for SQLite
  apiPort: 8080              # API server port
  webhookRetryAttempts: 3    # Webhook retry count
  webhookTimeout: 30         # Webhook timeout in seconds
```

#### Resource Limits

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

#### Persistence

```yaml
persistence:
  enabled: true
  size: 10Gi
  storageClass: ""           # Empty = cluster default
  accessMode: ReadWriteOnce
```

#### OpenShift Route

```yaml
route:
  enabled: true
  host: ""                   # Auto-generated if empty
  tls:
    enabled: true
    termination: edge
```

### Secrets Management

**Development:** Secrets can be specified in values.yaml

**Production:** Use sealed-secrets or external secret management:

```bash
# Create sealed secret
kubectl create secret generic marvin-secrets \
  --from-literal=SMTP_HOST=smtp.example.com \
  --from-literal=SMTP_PORT=587 \
  --from-literal=JWT_SECRET=your-secret-here \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > marvin-chart/templates/sealed-secret.yaml

# Then disable default secret in values-production.yaml
# and reference the sealed secret in deployment
```

## Database Migrations

Database migrations run automatically via Helm pre-upgrade hooks:

1. User runs `helm upgrade`
2. Migration job executes `alembic upgrade head`
3. Job must complete successfully before deployment proceeds
4. New pods start with updated schema

To view migration logs:

```bash
MIGRATION_JOB=$(oc get jobs -l job-type=migration --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
oc logs job/$MIGRATION_JOB
```

## Upgrading

### Standard Upgrade

```bash
# Production upgrade with automatic migration
helm upgrade marvin ./marvin-chart \
  --namespace marvin-prod \
  --values marvin-chart/values-production.yaml \
  --set image.tag=$(git rev-parse --short HEAD) \
  --wait \
  --timeout 15m \
  --atomic
```

### Dry Run (Preview Changes)

```bash
helm upgrade marvin ./marvin-chart \
  --namespace marvin-prod \
  --values marvin-chart/values-production.yaml \
  --set image.tag=new-version \
  --dry-run --debug
```

### Breaking Schema Changes

For breaking migrations (like TIME → DATETIME conversion):

1. **Backup first:**
   ```bash
   POD=$(oc get pods -l app.kubernetes.io/name=marvin -o jsonpath='{.items[0].metadata.name}')
   oc exec $POD -- tar czf /tmp/backup.tar.gz /app/data
   oc cp $POD:/tmp/backup.tar.gz ./marvin-backup-$(date +%Y%m%d).tar.gz
   ```

2. **Run upgrade** (migration happens automatically via hook)

3. **Verify** migration success before traffic resumes

## Rollback

### Quick Rollback (Code Only)

```bash
# View release history
helm history marvin -n marvin-prod

# Rollback to previous release
helm rollback marvin -n marvin-prod

# Or rollback to specific revision
helm rollback marvin 3 -n marvin-prod
```

### Full Rollback (Code + Database)

If data corruption or migration issues occur:

```bash
# 1. Scale down application
oc scale deployment/marvin --replicas=0

# 2. Restore database backup (see ROLLBACK_PROCEDURES.md)

# 3. Rollback Helm release
helm rollback marvin -n marvin-prod
```

See `ROLLBACK_PROCEDURES.md` for detailed rollback instructions.

## Monitoring

### Health Checks

```bash
# Get route URL
ROUTE=$(oc get route marvin -o jsonpath='{.spec.host}')

# Check health endpoint
curl -v https://$ROUTE/api/health
```

### View Logs

```bash
# Get pod name
POD=$(oc get pods -l app.kubernetes.io/name=marvin -o jsonpath='{.items[0].metadata.name}')

# Tail logs
oc logs -f $POD

# Check for errors
oc logs $POD | grep ERROR
```

### Verify Migration Status

```bash
oc exec $POD -- bash -c 'cd /app/src/marvin && uv run alembic current'
```

### Check Scheduler State

```bash
oc exec $POD -- cat /app/data/scheduler_state.json
```

## Troubleshooting

### Migration Job Failed

```bash
# View migration job logs
MIGRATION_JOB=$(oc get jobs -l job-type=migration --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
oc logs job/$MIGRATION_JOB

# Delete failed job and retry
oc delete job $MIGRATION_JOB
helm upgrade marvin ./marvin-chart [options]
```

### Pod CrashLoopBackOff

```bash
# Check pod logs
oc logs $POD --previous

# Check events
oc get events --sort-by='.lastTimestamp'

# Describe pod
oc describe pod $POD
```

### PVC Not Mounting

```bash
# Check PVC status
oc get pvc

# Check PVC events
oc describe pvc marvin-data

# Verify storage class
oc get sc
```

## Uninstalling

```bash
# Uninstall release (keeps PVC by default)
helm uninstall marvin -n marvin-prod

# Delete PVC manually if needed
oc delete pvc marvin-data
```

## Chart Development

### Linting

```bash
helm lint ./marvin-chart
```

### Template Rendering

```bash
helm template marvin ./marvin-chart \
  --values marvin-chart/values-production.yaml \
  --set image.tag=test
```

### Packaging

```bash
helm package ./marvin-chart
```

## Support

For issues and questions:
- GitHub: https://github.com/yourusername/marvin/issues
- Documentation: See `HELM_DEPLOYMENT_GUIDE.md`
- Rollback procedures: See `ROLLBACK_PROCEDURES.md`

## License

[Your License]

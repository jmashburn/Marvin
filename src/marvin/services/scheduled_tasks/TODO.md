# Scheduled Tasks Subsystem - TODO

## ✅ Complete (Production Ready)

### Infrastructure
- [x] Database models (`ScheduledTaskModel`, `ScheduledTaskExecutionLogModel`)
- [x] Alembic migration (2026-07-08-22.00.00_add_scheduled_tasks.py)
- [x] Repository layer with CRUD and execution logging
- [x] Handler base class and registry system
- [x] Event bus integration (8 new event types)
- [x] `ScheduledTaskListener` for executing triggered tasks
- [x] Scheduler integration (`check_scheduled_tasks()` runs every minute)
- [x] Platform API with 7 endpoints (CRUD + execute + history)
- [x] Task type discovery API (`GET /task-types?detailed=true`)

### Working Handlers
- [x] `cleanup_temp_files` - Removes old files from temp storage
- [x] `request_site_rebuild` - Triggers site rebuild via event

---

## ❌ Incomplete (Needs Implementation)

### 1. Schedule Calculation Logic

**Status:** Critical missing piece - tasks can be created but `next_run_at` is never calculated

**What's needed:**
- [ ] Create `/services/scheduled_tasks/schedule_calculator.py`
- [ ] Implement `calculate_next_run(schedule_type, schedule_config, last_run_at)` function
  - [ ] Parse cron expressions (use `croniter` library)
  - [ ] Handle interval schedules (seconds → next datetime)
  - [ ] Handle one-time schedules (parse ISO datetime)
  - [ ] Support timezone conversion
- [ ] Call calculator in `ScheduledTasksRepository.create()` to set initial `next_run_at`
- [ ] Call calculator in `ScheduledTasksRepository.update()` when schedule changes
- [ ] Call calculator in `ScheduledTaskListener` after task execution to update `next_run_at`

**Files to modify:**
- `/repos/platform/scheduled_tasks.py` - Add `next_run_at` calculation on create/update
- `/services/event_bus_service/event_bus_listener.py` - Update `next_run_at` after execution in `ScheduledTaskListener`

**Dependencies:**
```bash
# Add to requirements.txt or pyproject.toml
croniter>=1.3.0  # For cron expression parsing
python-dateutil>=2.8.0  # For timezone handling
```

---

### 2. Scheduled Publishing Feature

**Status:** Handler exists but needs DB schema changes

**What's needed:**

#### A. Database Migration
- [ ] Add fields to `entries` table:
  ```python
  publish_at: Mapped[datetime | None] = mapped_column(NaiveDateTime, nullable=True, index=True)
  expires_at: Mapped[datetime | None] = mapped_column(NaiveDateTime, nullable=True, index=True)
  ```
- [ ] Create Alembic migration
- [ ] Add composite index: `ix_entries_publish_at_status` on `(publish_at, status)`
- [ ] Add composite index: `ix_entries_expires_at_status` on `(expires_at, status)`

**Command:**
```bash
alembic revision -m "add_publish_at_expires_at_to_entries"
```

#### B. Schema Updates
- [ ] Update `/schemas/platform/entries.py`:
  - Add `publish_at: datetime | None` to `EntryCreate`
  - Add `expires_at: datetime | None` to `EntryCreate`
  - Add both fields to `EntryRead`

#### C. Handler Implementation
- [ ] Implement `PublishScheduledEntriesHandler.execute()` in `/handlers/publishing.py`:
  ```python
  # Query for entries with publish_at <= now AND status != 'published'
  # Update each entry: status = 'published', published_at = now
  # Emit entry.published event for each
  ```
- [ ] Implement `UnpublishExpiredEntriesHandler.execute()` in `/handlers/publishing.py`:
  ```python
  # Query for entries with expires_at <= now AND status = 'published'
  # Update each entry: status = 'archived'
  # Emit entry.unpublished event for each
  ```

#### D. Repository Queries
- [ ] Add `get_entries_to_publish(now)` method to `EntriesRepository`
- [ ] Add `get_entries_to_unpublish(now)` method to `EntriesRepository`

**Files to modify:**
- `/db/models/platform/entries.py`
- `/schemas/platform/entries.py`
- `/repos/platform/entries.py`
- `/services/scheduled_tasks/handlers/publishing.py`

---

### 3. Maintenance Handlers (Incomplete Logic)

#### A. `prune_expired_invitations`
**Status:** Handler exists but invitation expiry not implemented

- [ ] Add `expires_at: datetime | None` field to `GroupInviteToken` model (if not exists)
- [ ] Implement query logic in handler:
  ```python
  # Query for invitations where expires_at <= now
  # Delete them
  # Emit invitation.revoked events
  ```

#### B. `remove_orphaned_assets`
**Status:** Handler exists but needs SQL join query

- [ ] Implement query logic in handler:
  ```python
  # SELECT assets.* FROM assets
  # LEFT JOIN entry_assets ON assets.id = entry_assets.asset_id
  # WHERE entry_assets.asset_id IS NULL
  # AND assets.created_at < (now - age_days)
  ```
- [ ] If `auto_delete=true`, call storage service to delete files
- [ ] Emit `asset.deleted` events

**Files to modify:**
- `/services/scheduled_tasks/handlers/maintenance.py`

---

### 4. Additional Handler Categories

**Status:** Planned but not implemented

#### A. Asset Processing Handlers
Create `/services/scheduled_tasks/handlers/assets.py`:

- [ ] `MetadataExtractionHandler` - Extract EXIF from images
  - Use `Pillow` or `exifread` library
  - Update `assets.metadata_json` field
- [ ] `GenerateThumbnailsHandler` - Create image thumbnails
  - Check if thumbnail already exists
  - Generate via storage service
- [ ] `VerifyStorageConsistencyHandler` - Verify DB vs storage
  - Query all assets from DB
  - Check if files exist in storage
  - Log discrepancies

#### B. Event Retry Handlers
Create `/services/scheduled_tasks/handlers/events.py`:

- [ ] `RetryFailedWebhooksHandler` - Retry failed webhooks
  - Query event_log for failed webhook deliveries
  - Re-emit events for retry
- [ ] `PruneOldEventLogsHandler` - Archive old audit logs
  - Move old event_log entries to archive table
  - Or delete entries older than retention policy

**Files to create:**
- `/services/scheduled_tasks/handlers/assets.py`
- `/services/scheduled_tasks/handlers/events.py`

---

### 5. Handler Metadata

**Status:** Base infrastructure added, but only 1 handler has metadata

**What's needed:**
- [ ] Add `name`, `description`, and `config_schema` to all handlers:
  - [x] `CleanupTempFilesHandler` (done as example)
  - [ ] `PruneExpiredSessionsHandler`
  - [ ] `PruneExpiredInvitationsHandler`
  - [ ] `RemoveOrphanedAssetsHandler`
  - [ ] `PublishScheduledEntriesHandler`
  - [ ] `UnpublishExpiredEntriesHandler`
  - [ ] `RequestSiteRebuildHandler`

**Example:**
```python
class MyHandler(ScheduledTaskHandler):
    name = "Human Readable Name"
    description = "What this handler does"
    config_schema = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
        }
    }
```

---

### 6. CLI Integration

**Status:** Not started (separate repo)

**What's needed in `marvin-cli` repo:**

- [ ] Create `src/commands/platform/tasks.ts`
- [ ] Implement commands:
  - [ ] `marvinctl platform tasks list` - List all tasks
  - [ ] `marvinctl platform tasks create` - Create task (interactive)
  - [ ] `marvinctl platform tasks get <id>` - Get task details
  - [ ] `marvinctl platform tasks update <id>` - Update task
  - [ ] `marvinctl platform tasks delete <id>` - Delete task
  - [ ] `marvinctl platform tasks run <id>` - Manually trigger
  - [ ] `marvinctl platform tasks history <id>` - View execution logs
  - [ ] `marvinctl platform tasks types` - List available task types
- [ ] Support output formats: `--output table|json|yaml|csv`

**Repository:** `~/Code/marvin-cli` (separate from main Marvin repo)

---

### 7. SDK Integration

**Status:** Will auto-generate, but not tested

**What's needed:**
- [ ] Run OpenAPI spec generator after API changes
- [ ] Verify TypeScript types are correct in SDK
- [ ] Add example usage to SDK README
- [ ] Test SDK methods:
  ```typescript
  await marvin.platform.tasks.list()
  await marvin.platform.tasks.create({...})
  await marvin.platform.tasks.run(taskId)
  ```

**Note:** SDK auto-generates from OpenAPI spec, so minimal work needed

---

## 🧪 Testing Checklist

### Unit Tests Needed
- [ ] Test `ScheduledTasksRepository.get_due_tasks()`
- [ ] Test `ScheduledTaskExecutionLogRepository.log_execution()`
- [ ] Test `TaskHandlerRegistry.register()` and `get_handler()`
- [ ] Test schedule calculator logic (when implemented)

### Integration Tests Needed
- [ ] Test creating a task via API
- [ ] Test manually triggering a task
- [ ] Test task execution flow (trigger → listener → handler → event → log)
- [ ] Test task history retrieval
- [ ] Test task type discovery API

### End-to-End Test
- [ ] Create a task with interval schedule
- [ ] Wait for scheduler to trigger it
- [ ] Verify execution logged
- [ ] Verify `next_run_at` updated
- [ ] Verify events emitted
- [ ] Verify webhooks triggered (if configured)

---

## 📦 Deployment Checklist

Before using in production:

### Required
- [x] Run migration: `alembic upgrade head`
- [ ] **CRITICAL:** Implement schedule calculation (tasks won't run without this!)
- [ ] Add scheduled publishing fields to entries (if using that feature)
- [ ] Add handler metadata to all handlers
- [ ] Test at least one working task end-to-end

### Recommended
- [ ] Add monitoring for failed task executions
- [ ] Set up alerts for tasks with high failure_count
- [ ] Create backup/restore procedure for scheduled_tasks table
- [ ] Document available task types for users
- [ ] Add rate limiting to manual trigger endpoint

### Optional
- [ ] Implement remaining handlers (assets, events)
- [ ] Add CLI commands
- [ ] Create admin UI for managing tasks
- [ ] Add metrics/dashboards for task execution

---

## 📝 Documentation Needed

- [ ] API documentation (OpenAPI/Swagger should auto-generate)
- [ ] Handler development guide (how to create custom handlers)
- [ ] Schedule configuration guide (cron syntax, intervals, timezones)
- [ ] Troubleshooting guide (common issues, debugging)
- [ ] Migration guide for existing cron jobs
- [ ] User guide with examples of common tasks

---

## 🎯 Priority Order

1. **CRITICAL (blocks usage):**
   - Schedule calculation logic

2. **High Priority (core features):**
   - Scheduled publishing DB migration + handler implementation
   - Handler metadata for all handlers
   - End-to-end testing

3. **Medium Priority (polish):**
   - Complete maintenance handlers
   - CLI commands
   - Documentation

4. **Low Priority (nice-to-have):**
   - Asset processing handlers
   - Event retry handlers
   - Admin UI

---

## 📞 Questions / Decisions Needed

- [ ] **Timezone strategy:** Store all times in UTC? Support per-task timezones?
- [ ] **Concurrency:** Should tasks be allowed to run overlapping? Add locking?
- [ ] **Retry policy:** Auto-retry on failure? Max retries? Backoff strategy?
- [ ] **Monitoring:** What metrics to expose? Prometheus format? Logging level?
- [ ] **Permissions:** Who can create system-wide tasks (group_id=NULL)?

---

**Last Updated:** 2026-07-08
**Status:** Infrastructure complete, features partially implemented
**Blocker:** Schedule calculation logic must be implemented before system is usable

# Task: AI Workflow Settings Area

## Goal
Build the AI Workflow settings section inside Workspace Settings → Automation tab. This governs
whether AI is enabled per workspace, which credential mode to use (platform-owned, workspace-owned
via Secrets, or disabled), what subsystems may invoke AI, approval behavior, and per-operation
overrides. No new credential storage — raw keys must live in the existing Workspace Secrets system.

---

## Architecture Map

### What exists already (no changes needed)
| Concern | Lives in | Notes |
|---|---|---|
| Raw API credentials | `workspace_secrets` (Fernet-encrypted) | `secretRef` must point here |
| Variable interpolation | `workspace_variables` + `resolver.py` | `{{VAR_SLUG}}` already works in prompt templates |
| Platform-level AI config | `AppSettings` env vars (`OPENAI_*`) | Fallback when credential_mode = "platform" |
| Secret resolution engine | `services/secrets/resolver.py` | Already handles `{{SLUG}}` → value |

### Resolution precedence (read-only policy, not stored)
```
Operation override → Workspace AI Workflow setting → Platform AI default (AppSettings)
```

### New items to build
| Item | Location | Notes |
|---|---|---|
| DB model | `db/models/groups/ai_settings.py` | New one-to-one table with groups |
| Alembic migration | `alembic/versions/` | `workspace_ai_settings` table |
| Pydantic schemas | `schemas/group/ai_settings.py` | Create / Update / Read |
| Repo accessor | `db/repos/all_repositories.py` | `workspace_ai_settings` property |
| API routes | `routes/groups/ai_settings_controller.py` | GET + PATCH under `/api/groups/ai-settings` |
| Frontend page | `frontend/src/pages/workspace/settings/ai-workflow.astro` | Full settings UI |
| Frontend API helper | `frontend/src/lib/api/aiWorkflowSettings.ts` | Typed fetch helpers |
| Settings hub card | `frontend/src/pages/workspace/settings/index.astro` | Enable the disabled card |
| SDK types | (marvin-sdk repo, separate step) | `WorkspaceAISettings` interface |

### Fields that belong in secrets (not in ai_settings table)
- Raw provider API key → stored as a `WorkspaceSecret`, referenced by slug only

### Fields that belong in platform settings (AppSettings)
- `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL` — platform fallback when mode = "platform"
- These are NOT duplicated in workspace config

### Fields that belong in variables (not in ai_settings table)
- Brand tone, default language, site context → stored as `WorkspaceVariable`, referenced via `{{SLUG}}`

---

## DB Schema Design

```python
# workspace_ai_settings table (one-to-one with groups)
enabled: bool = True
credential_mode: str = "platform"    # "platform" | "workspace" | "disabled"
provider: str | None = None          # "openai" | "anthropic" | ...
model: str | None = None             # e.g. "gpt-4o", "claude-sonnet-5"
secret_ref: str | None = None        # slug of a WorkspaceSecret (workspace mode only)
approval_mode: str = "suggest-only"  # "suggest-only" | "allow-draft-update" | "allow-automatic-update"
invocation_sources: dict | None = None   # JSON: {editor, forms, actions, mcp, scheduledJobs}
operation_overrides: dict | None = None  # JSON: per-operation model/approval overrides
budget_config: dict | None = None        # JSON: token limits, cost limits
logging_config: dict | None = None       # JSON: log_inputs, log_outputs, redact_patterns, retention_days
moderation_config: dict | None = None    # JSON: enabled, block_on_flag
```

---

## Plan
- [ ] **Phase 1: DB + Schema**
  - [ ] Create `src/marvin/db/models/groups/ai_settings.py` — `WorkspaceAISettingsModel` (one-to-one with groups, `@auto_init()`)
  - [ ] Add `ai_settings` relationship to `Groups` model in `db/models/groups/groups.py`
  - [ ] Create Alembic migration: `alembic revision --autogenerate -m "add_workspace_ai_settings_table"`
  - [ ] Create `src/marvin/schemas/group/ai_settings.py` — `WorkspaceAISettingsCreate`, `WorkspaceAISettingsUpdate`, `WorkspaceAISettingsRead` schemas
  - [ ] Add `workspace_ai_settings` property to `AllRepositories`

- [ ] **Phase 2: API Routes**
  - [ ] Create `src/marvin/routes/groups/ai_settings_controller.py` with:
    - `GET /api/groups/ai-settings` — returns current settings (or defaults if not yet configured)
    - `PATCH /api/groups/ai-settings` — upsert (create on first write, update thereafter)
  - [ ] Register router in `src/marvin/routes/groups/__init__.py`
  - [ ] Validate `secret_ref` slug exists in workspace secrets on write (soft warning, not hard block)

- [ ] **Phase 3: Frontend API Helper**
  - [ ] Create `frontend/src/lib/api/aiWorkflowSettings.ts` — typed `getAIWorkflowSettings()`, `updateAIWorkflowSettings()` helpers matching the pattern used by secrets/variables

- [ ] **Phase 4: Frontend Settings Page**
  - [ ] Create `frontend/src/pages/workspace/settings/ai-workflow.astro`
  - [ ] Sections: Enable/Disable toggle → Credential Mode → Provider & Model → Secret Reference → Invocation Sources → Approval Mode → Advanced (budget, logging, moderation)
  - [ ] Credential mode "workspace" shows secret slug picker (fetches existing secrets list)
  - [ ] Credential mode "platform" shows informational note (configured by platform admin)
  - [ ] Credential mode "disabled" greys out all AI features
  - [ ] All saves via PATCH; show save confirmation

- [ ] **Phase 5: Enable the Settings Hub Card**
  - [ ] In `frontend/src/pages/workspace/settings/index.astro`, replace the disabled "AI Workflows" card with a live link to `/workspace/settings/ai-workflow`

- [ ] **Phase 6: Verify End-to-End**
  - [ ] Run dev server, navigate to Workspace Settings → Automation → AI Workflows
  - [ ] Verify GET returns defaults for a workspace with no AI settings yet
  - [ ] Save settings, verify PATCH persists and GET returns updated values
  - [ ] Verify secret_ref picker shows existing workspace secrets
  - [ ] Verify credential_mode="disabled" is stored and readable

## Questions / Dependencies
- Should `secret_ref` validation on write be a hard error (400) or a soft warning? Recommend: soft warning, since the secret can be created after AI settings are saved.
- Operation-level overrides: for now, store as freeform JSON with a code-editor UI field; structured per-operation UI is a future phase.
- Platform admin override (disable AI workspace-wide regardless of workspace setting): not in scope unless raised.

## Results
(fill in when done)

## Lessons
(fill in if anything unexpected happens)

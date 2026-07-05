# Admin Model

Marvin distinguishes between two levels of administrative access:

## Super Admin (Platform Administrator)

A **Super Admin** has platform-level privileges across all workspaces.

### Current Implementation
- Uses the existing `users.admin = True` flag from Mealie
- Can access admin routes under `/api/admin`
- Can perform user management operations

### Future Requirements
- View all workspaces (not scoped to `users.group_id`)
- Create/edit/delete workspaces
- Manage workspace settings for any workspace
- Switch active workspace context (future UI feature)
- Perform platform-level operations

### Notes
- Super admins are rare - typically only the platform owner
- Current Marvin implementation inherits Mealie's admin flag
- No explicit super admin vs workspace admin distinction yet
- Future: Add `is_superuser` flag or similar to clarify platform-level access

## Workspace Admin (Workspace Owner/Manager)

A **Workspace Admin** has full control over their own workspace but cannot access other workspaces.

### Current Implementation
- Uses the existing group/workspace scoping (`users.group_id`)
- All authenticated routes automatically scope to `current_user.group_id`
- Can manage entries, entry types, collections, assets, resources, and site clients for their workspace

### Permissions
Within their workspace, workspace admins can:
- Create/edit/delete entries, entry types, collections
- Upload and manage assets
- Create and manage site clients (API tokens for publishing)
- Configure workspace settings (site configuration, preferences)
- Invite/manage workspace members (future)

### Scope Rules
- All queries are automatically filtered by `group_id`
- Cannot view or modify content in other workspaces
- Cannot create workspaces (super admin only)
- Cannot access platform-level settings

## Implementation Notes

### Group Scoping
All workspace-scoped resources use these patterns:

```python
# Repository layer - scoped by group_id
repos = get_repositories(session, group_id=current_user.group_id)
entry = repos.entries.get_one(entry_id)  # Automatically scoped

# Direct queries - manual filtering
entry = session.query(Entries).filter(
    Entries.group_id == current_user.group_id,
    Entries.id == entry_id
).first()
```

### Admin Routes vs Publishing Routes

**Admin Routes** (`/api/admin/*`, `/api/entries`, etc.):
- Require user authentication (JWT token)
- Scoped to `current_user.group_id` 
- Return all entry states (draft, review, published)
- Include admin metadata (created_by, internal notes, etc.)
- Write operations allowed

**Publishing Routes** (`/api/publish/{workspace_slug}/*`):
- Require API client token authentication (`marvin_sk_*`)
- Scoped to workspace associated with the API client
- Only return `status = 'published'` entries
- Exclude all admin fields
- Read-only operations only

### Site Client Permissions

Site clients (API tokens for publishing) are:
- Scoped to one workspace
- Read-only (cannot create/edit/delete)
- Can only see published content
- Cannot impersonate users or access admin APIs

See: `docs/site-clients-and-publishing.md`

## Future Improvements

### Explicit RBAC
Future iterations may add:
- `users.is_superuser` flag (distinct from workspace admin)
- `workspace_members` table with role-based permissions
- Granular permissions (e.g., can_manage_entries, can_publish, can_invite_users)
- Workspace-level roles (owner, editor, contributor, viewer)

### Multi-Workspace Users
Future support for users belonging to multiple workspaces:
- `workspace_memberships` table
- Active workspace context switching
- Per-workspace roles

### Audit Trail
Track admin actions:
- Who published/unpublished entries
- Who created site clients
- Who modified workspace settings
- Who invited users

## Current Limitations

- No explicit `is_superuser` flag - relying on Mealie's `admin` flag
- No role-based permissions within workspaces
- Users belong to only one group/workspace (`users.group_id`)
- No workspace creation UI (manual database operation)
- No workspace-level user invitations (admin creates users directly)

## Security Principles

1. **Default to workspace scoping**: All queries should filter by `group_id` unless explicitly platform-level
2. **Workspace isolation**: Never leak data between workspaces
3. **Least privilege**: Site clients have minimal read-only permissions
4. **Explicit authorization**: Check group membership before any operation
5. **Separate concerns**: Admin routes and publishing routes use different auth mechanisms

## Related Documentation

- `docs/marvin-platform-plan.md` - Platform architecture
- `docs/site-clients-and-publishing.md` - Publishing API security model
- `docs/platform-implementation-checklist.md` - Implementation phases

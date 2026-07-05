# Marvin Platform Implementation Checklist

Use this checklist to track the first platform sprint.

## Branch

```text
marvin-platform-plan
```

## Sprint 1: Documentation

- [x] Add Marvin platform architecture plan.
- [x] Add data model notes.
- [x] Add publishing API notes.
- [x] Add site client notes.
- [x] Add AI intake notes as a future phase.

## Sprint 2: Database Migration

Add one Alembic migration for the first platform data slice.

- [x] entry_types
- [x] entries
- [ ] collections
- [ ] entry_collections
- [ ] resources
- [ ] entry_resources
- [ ] assets
- [ ] entry_assets
- [ ] site_clients

Rules:

- [x] Use existing `groups` table as the workspace boundary.
- [x] Add `group_id` to all workspace-scoped tables.
- [x] Do not rename `groups` yet.
- [x] Do not create a separate `workspaces` table yet.

## Sprint 3: Backend Models

- [x] Add SQLAlchemy models.
- [x] Add Pydantic schemas.
- [x] Add repositories.
- [x] Follow existing Marvin patterns.

## Sprint 4: Authenticated APIs

Authenticated user routes:

- [x] `GET /api/entry-types`
- [x] `POST /api/entry-types`
- [x] `GET /api/entry-types/{id}`
- [x] `PATCH /api/entry-types/{id}`
- [x] `DELETE /api/entry-types/{id}`
- [x] `GET /api/entries`
- [x] `POST /api/entries`
- [x] `GET /api/entries/{id}`
- [x] `PATCH /api/entries/{id}`
- [x] `DELETE /api/entries/{id}`

Rules:

- [x] Scope all entry type and entry queries to the current user's `group_id`.
- [x] Keep entry type slugs unique within a group.
- [x] Keep entry slugs unique within a group.
- [x] Prevent deleting entry types that are used by entries.

## Sprint 4.5: Tests

- [ ] Add route/repository tests for entry types.
- [ ] Add route/repository tests for entries.
- [x] Document missing tests because the project currently has no clear route/repository test pattern beyond shared test setup.

## Sprint 5: Publishing API

Read-only publishing routes:

- [ ] `GET /api/publish/{group_slug}/collections`
- [ ] `GET /api/publish/{group_slug}/entries`
- [ ] `GET /api/publish/{group_slug}/entries/{slug}`
- [ ] `GET /api/publish/{group_slug}/assets`

Rules:

- [ ] Validate site client token.
- [ ] Match token to `group_id`.
- [ ] Return only published entries.
- [ ] Respect collection restrictions.
- [ ] Never expose draft/admin/private fields.

## Sprint 6: Astro Integration

- [ ] Document how Astro calls the publishing API.
- [ ] Return Markdown content and frontmatter metadata.
- [ ] Return asset URLs and alt text.
- [ ] Keep public sites separate from Marvin Admin.

## Implementation Status

| Sprint | Status | Notes |
|--------|--------|-------|
| 1 | ✅ Complete | All documentation added |
| 2 | ✅ Complete | Migration file created, ready to run |
| 3 | ✅ Complete | Entry Type and Entry models, schemas, and repos implemented |
| 4 | ✅ Complete | Authenticated user CRUD routes implemented |
| 4.5 | 🚧 In Progress | Tests documented as missing; no existing route/repository pattern yet |
| 5 | ⏳ Deferred | Publishing API is future work |
| 6 | ⏳ Deferred | Astro integration is future work |

## Next Steps

1. **Test Database Migration**
   ```bash
   task py
   # In Python shell:
   from marvin.db.db_setup import init_db
   init_db()
   ```

2. **Test Authenticated APIs**
   ```bash
   curl -H "Authorization: Bearer <token>" \
     -X POST http://localhost:8000/api/entry-types \
     -H "Content-Type: application/json" \
     -d '{"name": "Article", "slug": "article"}'
   ```

3. **Add Focused Tests**
   - Add repository tests for group scoping and slug uniqueness.
   - Add route tests for authenticated CRUD behavior.
   - Add delete-prevention coverage for entry types in use.

## Future Work

- Smart collection rules engine
- Collections
- Resources
- Assets
- Site clients
- Publishing API
- Astro integration
- Asset transformation pipeline (resize, format conversion)
- Advanced permission scoping
- Webhook system for publish events
- AI-assisted intake (see ai-intake-future.md)


## Future Phase: AI Intake

Do not implement this yet.

- [ ] Voice note intake.
- [ ] Image upload intake.
- [ ] AI-generated draft entries.
- [ ] Suggested titles, summaries, tags, and collections.
- [ ] Human review before publish.

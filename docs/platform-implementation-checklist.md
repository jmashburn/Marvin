# Marvin Platform Implementation Checklist

Use this checklist to track the first platform sprint.

## Branch

```text
marvin-platform-plan
```

## Sprint 1: Documentation

- [x] Add Marvin platform architecture plan.
- [ ] Add data model notes.
- [ ] Add publishing API notes.
- [ ] Add site client notes.
- [ ] Add AI intake notes as a future phase.

## Sprint 2: Database Migration

Add one Alembic migration for the first platform tables.

- [ ] collections
- [ ] entries
- [ ] entry_collections
- [ ] resources
- [ ] entry_resources
- [ ] assets
- [ ] entry_assets
- [ ] site_clients

Rules:

- [ ] Use existing `groups` table as the workspace boundary.
- [ ] Add `group_id` to all workspace-scoped tables.
- [ ] Do not rename `groups` yet.
- [ ] Do not create a separate `workspaces` table yet.

## Sprint 3: Backend Models

- [ ] Add SQLAlchemy models.
- [ ] Add Pydantic schemas.
- [ ] Add repositories.
- [ ] Follow existing Marvin patterns.

## Sprint 4: Admin APIs

Authenticated admin routes:

- [ ] `/api/collections`
- [ ] `/api/entries`
- [ ] `/api/resources`
- [ ] `/api/assets`
- [ ] `/api/site-clients`

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

## Future Phase: AI Intake

Do not implement this yet.

- [ ] Voice note intake.
- [ ] Image upload intake.
- [ ] AI-generated draft entries.
- [ ] Suggested titles, summaries, tags, and collections.
- [ ] Human review before publish.
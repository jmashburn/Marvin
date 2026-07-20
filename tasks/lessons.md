# Lessons

## Environment / tooling

- **Always run Python through the project venv in `Marvin/`.** Use `uv run python …`
  (or `uv run <tool>`) rather than bare `python`/`pip`. The repo is a uv project; bare
  `python` uses the system interpreter and misses installed deps. Correction from user
  2026-07-17.

## Database migrations

- **Never hand-write Alembic migration files.** Always generate them through Alembic's
  autogenerate process so revision IDs, `down_revision` chains, and schema diffs are correct.
  Use the repo task: `task py:migrate -- "message describing the change"`
  (wraps `uv run alembic --config src/marvin/alembic.ini revision --autogenerate -m "..."`).
  Review/adjust the generated file, but do not author migrations by hand. Correction from
  user 2026-07-17.
  - **Reinforced 2026-07-19** (repeated the mistake): even though `--autogenerate` is unreliable
    on the SQLite dev DB (memory `alembic-migrations-autogenerate` → hand-fill the body), you must
    STILL generate the skeleton via the command — `uv run alembic -c src/marvin/alembic.ini revision
    -m "..."` — so the revision id is unique and `down_revision` auto-resolves to the current head.
    Hand-*picking* a revision id collided with an existing one (`b1c2d3e4f5a6`) and produced an
    Alembic "cycle detected" that broke the whole test suite. Flow: `alembic revision` (skeleton) →
    hand-fill `upgrade`/`downgrade` → verify `alembic heads` shows ONE head.

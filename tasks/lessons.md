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

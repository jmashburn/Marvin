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
  - **Reinforced 2026-07-19** (repeated the mistake): always generate via the command so the
    revision id is unique and `down_revision` auto-resolves to the current head. Hand-*picking* a
    revision id collided with an existing one (`b1c2d3e4f5a6`) and produced an Alembic
    "cycle detected" that broke the whole test suite. Always verify `alembic heads` shows ONE head.
  - **CORRECTED 2026-07-20 — the "autogenerate is unreliable on SQLite" claim was FALSE.**
    I repeated it from memory and used it to justify hand-filling migration bodies; the user
    pushed back ("it's always worked for me") and was right. Autogenerate was never the problem:
    **six models used the Postgres-only `postgresql.JSONB` type**, which SQLite cannot compile, so
    every run died with `UnsupportedCompilationError`. Fixed at the source — those models now use
    `sa.JSON`, and `task py:migrate` runs clean against the SQLite dev DB.
    - **Rule: use `sa.JSON` for JSON fields, regardless.** Not `postgresql.JSONB`, and don't
      re-pitch `sa.JSON().with_variant(JSONB, "postgresql")` — that was raised and declined.
    - **Meta-lesson:** when a memory says a standard tool is "broken", verify it before repeating
      it, and prefer fixing the cause over enshrining the workaround. A stale workaround cost more
      than the one-line fix would have.

## Git in this repo

- **Never run `git stash` (or any committing git command) here.** Commit signing is enabled, so
  `git stash push` creates a signed commit → invokes GPG/pinentry to decrypt the user's `pass` key
  → hangs the non-interactive session (and pops an unexpected passphrase prompt at the user).
  This is the same trap already known for `git push` (memory `git-push-needs-gpg-unlock`), but it
  bites on *stash* too, which is easy to reach for.
  - **Instead**, to compare working-tree changes against committed state, use read-only plumbing:
    `git show HEAD:<path>` (diff it against the working file), `git diff`, or copy the HEAD version
    to a temp file. Never mutate the index/worktree to "test something and put it back".
  - Correction from user 2026-07-20: a `git stash push`/`pop` round-trip to check whether
    `astro check` errors were pre-existing triggered their GPG pinentry and wedged the shell for
    two tool calls. The same question was answerable with `git show HEAD:<file>`.

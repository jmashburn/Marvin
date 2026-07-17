# Lessons

## Environment / tooling

- **Always run Python through the project venv in `Marvin/`.** Use `uv run python …`
  (or `uv run <tool>`) rather than bare `python`/`pip`. The repo is a uv project; bare
  `python` uses the system interpreter and misses installed deps. Correction from user
  2026-07-17.

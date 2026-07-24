#!/usr/bin/env bash
# Run the backend API and the server-rendered frontend side by side in one container.
#
# The frontend is Astro with output: "server" (@astrojs/node standalone), so it needs a live Node
# process — it can't be served as static files from the API. We supervise both here: if either one
# exits, the whole container comes down with that status, so an orchestrator restarts a half-dead
# app instead of leaving it limping.
set -uo pipefail

shutdown() {
    trap - TERM INT
    kill -TERM "${backend_pid:-}" "${frontend_pid:-}" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap shutdown TERM INT

# Backend API (uvicorn via the console script; reads API_PORT/HOST from the environment).
marvin-server &
backend_pid=$!

# Frontend SSR server. The standalone adapter reads HOST/PORT at runtime; bind all interfaces on
# its own port so it doesn't collide with the API.
HOST=0.0.0.0 PORT="${FRONTEND_PORT:-4321}" node /app/frontend/dist/server/entry.mjs &
frontend_pid=$!

# Return as soon as either process exits, propagating its status.
wait -n
status=$?
shutdown
exit "$status"

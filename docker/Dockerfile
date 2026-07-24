ARG IMAGE="python"
ARG VARIENT="3.12-slim"
ARG UV_IMAGE="ghcr.io/astral-sh/uv"
ARG UV_VARIENT="python3.12-bookworm"
# node:*-slim is Debian bookworm, matching python:3.12-slim, so the node binary copied into the
# runtime below is ABI-compatible.
ARG NODE_IMAGE="node"
ARG NODE_VARIENT="22-slim"

##################################
# Builder Image - Frontend (Astro SSR)
##################################
# The frontend is output: "server" (@astrojs/node standalone): a Node program, not static files,
# so it is built here and run alongside the API in the production image.
FROM ${NODE_IMAGE}:${NODE_VARIENT} AS frontend-builder

WORKDIR /frontend

# Vite inlines import.meta.env.PUBLIC_* at build time, and the browser must reach the backend at
# this URL. Leave empty to fall back to http://localhost:8080 (fine for local/single-host); set
# --build-arg PUBLIC_MARVIN_API_URL=https://api.example.com for a real deployment.
ARG PUBLIC_MARVIN_API_URL=""
ENV PUBLIC_MARVIN_API_URL=${PUBLIC_MARVIN_API_URL}

# Install against the lockfile first so this layer caches on dependency changes only.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# Call `astro build` directly rather than the package script's `astro check && astro build`: the
# type check has a known error backlog and would fail the image without affecting the compiled
# output (astro strips types at build time regardless).
RUN npx astro build

##################################
# Builder Image - Python
##################################

FROM ${IMAGE}:${VARIENT} AS python-base

ENV MARVIN_HOME="/app"

RUN useradd -U -d $MARVIN_HOME -s /bin/bash app && \
    usermod -G users app && \
    mkdir $MARVIN_HOME

##################################
# Base Image - Packages
##################################

FROM python-base AS builder-base

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    build-essential \
    libsasl2-dev libldap2-dev libssl-dev \
    gnupg gnupg2 gnupg1 \
    && apt-get clean

##################################
# Base Image - uv
##################################
#FROM builder-base AS uv-base
FROM ${UV_IMAGE}:${UV_VARIENT} AS uv-base

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since its a mounted vol
ENV UV_LINK_MODE=copy

# Generate proper TOML lockfile first
RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv lock

# --group postgres bundles the psycopg2 driver so the image can run against Postgres
# (DB_ENGINE=postgres); without it the app is SQLite-only. Other backend groups (ldap, vault,
# bitwarden) stay opt-in — add --group <name> here if a deployment needs them.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev --no-editable --group postgres

# The, add the rest of the projects source code and install it
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-editable --group postgres

# Remove unnecessary files from the virtual env before copying
RUN find /app/.venv -name '__pycache__' -type d -exec rm -rf {} + && \
    find /app/.venv -name '*.pyc' -delete && \
    find /app/.venv -name '*.pyo' -delete && \
    echo "Cleaned .venv"


# ##################################
# Production Base Image
# ##################################
# Slim runtime: the venv is compiled in uv-base, so the runtime needs neither the build
# toolchain nor the LDAP/SASL dev libs — base on python-base and copy only the venv.
FROM python-base AS build-base

COPY --from=uv-base --chown=app:app /app/.venv /app/.venv
ENV BASE_DIR=$MARVIN_HOME

# ##################################
# Production Image
# ##################################
FROM build-base AS production

ENV PRODUCTION=True
ENV TESTING=False
ENV DATA_DIR="$MARVIN_HOME/data"
# create directory used for Docker Secrets
RUN mkdir -p /run/secrets

VOLUME [ "$MARVIN_HOME/data/" ]

# Node runtime for the server-rendered frontend. Copying just the binary from the matching Debian
# base keeps the image lean — no npm/toolchain at runtime, only `node dist/server/entry.mjs`.
COPY --from=frontend-builder /usr/local/bin/node /usr/local/bin/node
# The built SSR server plus its runtime node_modules. The standalone build does not fully bundle —
# entry.mjs imports cookie/send/unstorage/@astrojs/* from node_modules — so they ship too.
COPY --from=frontend-builder --chown=app:app /frontend/dist /app/frontend/dist
COPY --from=frontend-builder --chown=app:app /frontend/node_modules /app/frontend/node_modules

ENV API_PORT=8080
ENV FRONTEND_PORT=4321

# API and frontend, respectively.
EXPOSE ${API_PORT} ${FRONTEND_PORT}

ARG COMMIT
ENV GIT_COMMIT_HASH=${COMMIT}

ENV PATH="/app/.venv/bin:$PATH"

ENV HOST=0.0.0.0

# Liveness probe: the healthcheck script hits the public root /healthz endpoint. start-period
# covers first-boot migrations + seeding so the container isn't marked unhealthy while starting.
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -m marvin.scripts.healthcheck || exit 1

# Supervise the API and the frontend SSR server together; either exiting brings the container down.
COPY --chown=app:app docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh
ENTRYPOINT ["/app/start.sh"]



# # ##################################
# # Testing Image
# # ##################################
# FROM build-base AS test

# ENV PRODUCTION=false
# ENV TESTING=true

# ENV PATH="/app/.venv/bin:$PATH"

# CMD ["marvin"]


# ##################################
# Lambda Image
# ##################################
FROM production AS lambda

ARG FUNCTION_DIR="/function"

RUN pip install boto3
# Lambda is single-process and invokes the handler directly — it must not inherit the dual-process
# supervisor entrypoint from `production`. Reset it so the CMD handler is used as before.
ENTRYPOINT []
CMD ["marvin.app.handler"]

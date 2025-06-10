ARG IMAGE="python"
ARG VARIENT="3.12-slim"
ARG UV_IMAGE="ghcr.io/astral-sh/uv"
ARG UV_VARIENT="python3.12-bookworm"

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

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev --no-editable

# The, add the rest of the projects source code and install it
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-editable

# Remove unnecessary files from the virtual env before copying
RUN find /app/.venv -name '__pycache__' -type d -exec rm -rf {} + && \
    find /app/.venv -name '*.pyc' -delete && \
    find /app/.venv -name '*.pyo' -delete && \
    echo "Cleaned .venv"


# ##################################
# Production Base Image
# ##################################
FROM builder-base AS build-base

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

ENV API_PORT=8080

EXPOSE ${API_PORT}

ARG COMMIT
ENV GIT_COMMIT_HASH=${COMMIT}

ENV PATH="/app/.venv/bin:$PATH"

ENV HOST=0.0.0.0

#HEALTHCHECK CMD python -m marvin.scripts.healthcheck || exit 1

ENTRYPOINT ["marvin"]



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
FROM production-base AS lambda

ARG FUNCTION_DIR="/function"

RUN pip install boto3
CMD ["marvin.app.handler"]

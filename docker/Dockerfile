##################################
# Base Image - Python
##################################
ARG IMAGE="python"
ARG VARIENT="3.11"
FROM ${IMAGE}:${VARIENT} AS python-base


ENV MARVIN_HOME="/app"
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACH_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true  \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

RUN mkdir "$MARVIN_HOME"

##################################
# Builder Image - Python
##################################
FROM python-base AS builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    build-essential \
    libsasl2-dev libldap2-dev libssl-dev \
    gnupg gnupg2 gnupg1 \
    && apt-get clean \
    && pip install -U --no-cache-dir pip


# install poetry - respect  $POETRY_VERSION & $POETRY_HOME
ENV POETRY_VERSION=1.3.1
RUN curl -sSL https://install.python-poetry.org | python3 -

# copy project requirement files here to ensure they will be cached.
WORKDIR $PYSETUP_PATH
COPY ./README.md ./poetry.lock ./pyproject.toml ./

RUN poetry install --only main

# ##################################
# Production Base Image
# ##################################
FROM python-base AS production-base
ENV PRODUCTION=true
ENV TESTING=false

ARG COMMIT
ENV GIT_COMMIT_HASh=${COMMIT}

COPY --from=builder-base $POETRY_HOME $POETRY_HOME
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH

COPY ./marvin $MARVIN_HOME/marvin
COPY ./README.md ./poetry.lock ./pyproject.toml $MARVIN_HOME

WORKDIR $MARVIN_HOME
RUN . $VENV_PATH/bin/activate && poetry install --only main
WORKDIR /

# ##################################
# Production Image
# ##################################
FROM pre-prod AS production
COPY ./docker/entry.sh $MARVIN_HOME/run.sh

RUN chmod +x $MARVIN_HOME/run.sh
ENTRYPOINT ["/app/run.sh"]


# ##################################
# Lambda Image
# ##################################
FROM production-base AS lambda

ARG FUNCTION_DIR="/function"

RUN pip install boto3
CMD ["marvin.app.handler"]

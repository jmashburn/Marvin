# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.224.2/containers/python-3/.devcontainer/base.Dockerfile

# [Choice] Python version (use -bullseye variants on local arm64/Apple Silicon): 3, 3.10, 3.9, 3.8, 3.7, 3.6, 3-bullseye, 3.10-bullseye, 3.9-bullseye, 3.8-bullseye, 3.7-bullseye, 3.6-bullseye, 3-buster, 3.10-buster, 3.9-buster, 3.8-buster, 3.7-buster, 3.6-buster
ARG VARIANT="3.10-bullseye"
FROM mcr.microsoft.com/devcontainers/python:1-${VARIANT}


ARG NODE_VERSION="none"
RUN if [ "${NODE_VERSION}" != "none" ]; then su vscode -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; fi

ARG APT_PROXY="none"
RUN if [ "${APT_PROXY}" != "none" ]; then echo "'Acquire::http::Proxy \"${APT_PROXY}\";' | tee /etc/apt/apt.conf.d/01proxy"; fi

RUN echo "export PROMPT_COMMAND='history -a'" >> /home/vscode/.bashrc \
    && echo "export HISTFILE=~/commandhistory/.bash_history" \
    && chown vscode:vscode -R /home/vscode

ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    TASK_HOME="/opt/task"

ENV PATH="$TASK_HOME/bin:$POETRY_HOME/bin:$PATH"

RUN curl -sSL https://taskfile.dev/install.sh -- -d -b ${TASK_HOME} | sh
RUN curl -sSL https://install.python-poetry.org | python3 -


RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    build-essential \
    libpq-dev \
    libwebp-dev \
    libsasl2-dev libldap2-dev libssl-dev \
    gnupg gnupg2 gnupg1

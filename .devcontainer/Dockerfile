# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.224.2/containers/python-3/.devcontainer/base.Dockerfile

# [Choice] Python version (use -bullseye variants on local arm64/Apple Silicon): 3, 3.10, 3.9, 3.8, 3.7, 3.6, 3-bullseye, 3.10-bullseye, 3.9-bullseye, 3.8-bullseye, 3.7-bullseye, 3.6-bullseye, 3-buster, 3.10-buster, 3.9-buster, 3.8-buster, 3.7-buster, 3.6-buster
ARG VARIANT="3.12-bookworm"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}


# ARG APT_PROXY="none"
# RUN if [ "${APT_PROXY}" != "none" ]; then echo "Acquire::http::Proxy \"${APT_PROXY}\";" | tee /etc/apt/apt.conf.d/01proxy; fi

RUN echo "export PROMPT_COMMAND='history -a'" >> /home/vscode/.bashrc \
    && echo "export HISTFILE=~/commandhistory/.bash_history" \
    && chown vscode:vscode -R /home/vscode

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
       curl \
       gnupg \
       dirmngr \
       ca-certificates \
       build-essential \
       libpq-dev \
       libwebp-dev \
       libsasl2-dev libldap2-dev libssl-dev

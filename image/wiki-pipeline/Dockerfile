# Dockerfile - wiki-pipeline

# ARG instructions used in FROM must come before the FROM instruction
ARG PYTHON_VERSION="3.12"

# Use a Python base image that matches the desired Python version
# We use a slim Debian-based image for smaller size.
FROM python:${PYTHON_VERSION}-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    dnsutils \
    iproute2 \
    iputils-ping \
    inetutils-telnet \
    openssh-client \
    ssh-client \
    bash \
    git \
    curl \
    wget \
    tree \
    jq \
    git \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Setup ssh-agent socket for Jenkins
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

WORKDIR /app

## ref: https://github.com/pypa/pip/issues/11179#issuecomment-1152766374
ENV PIP_ROOT_USER_ACTION=ignore

RUN python -m pip install --disable-pip-version-check --upgrade pip

# Install Python dependencies
COPY requirements.txt .
RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

# Copy all scripts
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.py

# Create wrapper script
RUN printf '#!/bin/bash\nexec python3 /app/scripts/cli.py "$@"\n' > /usr/local/bin/wiki-pipeline && \
    chmod +x /usr/local/bin/wiki-pipeline

ENV PYTHONPATH=/app
ENV PATH="/app/scripts:${PATH}"

CMD ["--help"]

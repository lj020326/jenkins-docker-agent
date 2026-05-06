# ARG instructions used in FROM must come before the FROM instruction
ARG PYTHON_VERSION="3.12"

# Stage 1: Extraction
ARG UBUNTU_VERSION=24.04
FROM ubuntu:${UBUNTU_VERSION} AS builder
RUN apt-get update && apt-get install -y unzip tar

ENV YQ_VERSION=v4.53.2
ENV YQ_BINARY=yq_linux_amd64
ARG GOVC_VERSION=v0.53.1
ARG PACKER_VERSION=1.15.3

# Copy all local files into the builder
COPY files/${YQ_BINARY}_${YQ_VERSION}.tar.gz /tmp/
COPY files/govc_${GOVC_VERSION}_linux_x86_64.tar.gz /tmp/
COPY files/packer_${PACKER_VERSION}_linux_amd64.zip /tmp/

# Extract YQ
RUN mkdir -p /out/usr/local/bin && \
    tar -xzf /tmp/${YQ_BINARY}_${YQ_VERSION}.tar.gz -C /out/usr/local/bin/ --wildcards "*${YQ_BINARY}*" && \
    mv /out/usr/local/bin/${YQ_BINARY} /out/usr/local/bin/yq

# Extract GOVC
RUN tar -xzf /tmp/govc_${GOVC_VERSION}_linux_x86_64.tar.gz -C /out/usr/local/bin/ --wildcards "*govc*"

# Extract Packer
RUN unzip /tmp/packer_${PACKER_VERSION}_linux_amd64.zip -d /out/usr/local/bin/

# Ensure everything is executable
RUN chmod +x /out/usr/local/bin/*

# Use a Python base image that matches the desired Python version
# We use a slim Debian-based image for smaller size.
FROM python:${PYTHON_VERSION}-slim-bullseye
ARG PYTHON_VERSION="3.12"

ARG ANSIBLE_CORE_VERSION="latest"

LABEL maintainer="Lee Johnson <ljohnson@dettonville.org>"
LABEL description="Custom Jenkins agent Container for Python ${PYTHON_VERSION}"

ARG BUILD_DATE
ARG BUILD_ID=devel
LABEL build=$BUILD_ID

# Set environment variables
ENV container=docker
ENV DEBIAN_FRONTEND=noninteractive

# Set PIP_NO_CACHE_DIR to prevent pip from caching packages inside the image
ENV PIP_NO_CACHE_DIR=1

ENV PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/ansible/bin"
ENV PATH="/root/.local/bin:${PATH}"

## ref: https://octopus.com/blog/using-ubuntu-docker-image
RUN echo 'APT::Install-Suggests "0";' >> /etc/apt/apt.conf.d/00-docker
RUN echo 'APT::Install-Recommends "0";' >> /etc/apt/apt.conf.d/00-docker

# Update package lists and install necessary build tools and common dependencies.
# These are essential for compiling some Python packages and for general test execution.
# Add any other system-level dependencies your specific Ansible collections might require.
# For example, if your collections interact with AWS, Azure, databases, etc., you might need:
# apt-get install -y --no-install-recommends libssl-dev libffi-dev openssh-client

## 1. Core System Utilities & Locales
# These rarely change and provide the base for everything else
RUN apt-get update -qqy && \
    apt-get -qqy --no-install-recommends install \
      apt-transport-https apt-utils locales ca-certificates \
      software-properties-common bash tar zip unzip gnupg \
      netbase tzdata curl wget git git-lfs tree less nano jq rsync && \
    sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

## 2. Networking & Debugging Tools
RUN apt-get update -qqy && \
    apt-get -qqy --no-install-recommends install \
      dnsutils iproute2 openssh-client iputils-ping \
      inetutils-telnet ssh-askpass sshpass ssh-client shellcheck \
      groff rlwrap && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

## 3. Build Tools & Development Libraries
# Essential for compiling Python C-extensions or local builds
RUN apt-get update -qqy && \
    apt-get -qqy --no-install-recommends install \
      build-essential patch genisoimage dirmngr openssl \
      zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev \
      libpq-dev libmariadb-dev libsasl2-dev libldap2-dev \
      libssl-dev libsqlite3-dev libreadline-dev libffi-dev \
      libbz2-dev uuid-dev default-mysql-client && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Generate and set the locale
RUN sed -i 's/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen

## Ensure the following are set after running `locale-gen`
ENV LANGUAGE=en_US:en
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

## 4. Docker CLI (DinD Support)
# Kept separate so the Docker version can be updated independently
# --- Start Docker-in-Docker (DinD) support installation ---
# Install Docker CLI to enable running docker commands inside this container.
# This is crucial for scenarios like 'ansible-test units --docker' which
# require interacting with a Docker daemon.
# Modern Docker Repo Setup
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo \
        "deb [arch=\"$(dpkg --print-architecture)\" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
        $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      docker-ce-cli \
      docker-compose-plugin \
      docker-buildx-plugin && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
# --- End Docker-in-Docker (DinD) support installation ---

# 5. External Tools: Copy in from builder stage ---
# Copy the already-extracted binaries from the builder stage
COPY --from=builder /out/usr/local/bin/ /usr/local/bin/

#==========
# PIP - Install Python dependencies
#==========
## ref: https://github.com/pypa/pip/issues/11179#issuecomment-1152766374
ENV PIP_ROOT_USER_ACTION=ignore

RUN python -m pip install --upgrade pip

# Set the working user for the rest of the build and runtime to 'root'
# as your desired UID is 0.
USER root

COPY requirements.txt .

#RUN pip install --user -r requirements.txt
RUN pip install --disable-pip-version-check -r requirements.txt

# Create a working directory for jenkins project files
WORKDIR /jenkins_project

# 1. Define the version at the top
ARG JAVA_VERSION=21
ARG PYTHON_VERSION="3.13"

# 2. Name the JDK image as a stage
FROM eclipse-temurin:${JAVA_VERSION}-jdk AS jdk-source

#==========
# JAVA - Install java dependencies
#==========
## ref: https://www.howtoforge.com/how-to-install-java-openjdk-and-oracle-jdk-on-ubuntu-22-04/
ENV JAVA_HOME=/opt/java/openjdk
#ENV JAVA_HOME=/usr/lib/jvm/java-${JAVA_VERSION}-openjdk-amd64

## ref: https://stackoverflow.com/questions/43316935/change-java-securerandom-in-dockerfile
#RUN sed -i 's/securerandom\.source=file:\/dev\/random/securerandom\.source=file:\/dev\/urandom/' /etc/java-${JAVA_VERSION}-openjdk/security/java.security
RUN sed -i 's/securerandom\.source=file:\/dev\/random/securerandom\.source=file:\/dev\/urandom/' ${JAVA_HOME}/conf/security/java.security

# 3. builder stage
ARG PYTHON_VERSION="3.13"
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder
# Stage 1: Extraction
RUN apt-get update && apt-get install -y unzip tar

ENV YQ_VERSION=v4.53.2
ENV YQ_BINARY=yq_linux_amd64
ARG GOVC_VERSION=v0.53.1
ARG PACKER_VERSION=1.15.3
ARG INCLUSIVITY_VERSION=0.19.0

# Copy all local files into the builder
COPY files/${YQ_BINARY}_${YQ_VERSION}.tar.gz /tmp/
COPY files/govc_${GOVC_VERSION}_linux_x86_64.tar.gz /tmp/
COPY files/packer_${PACKER_VERSION}_linux_amd64.zip /tmp/
COPY files/inclusivity-${INCLUSIVITY_VERSION}-linux-amd64.tar.gz /tmp/

# Extract YQ
RUN mkdir -p /out/usr/local/bin && \
    tar -xzf /tmp/${YQ_BINARY}_${YQ_VERSION}.tar.gz -C /out/usr/local/bin/ --wildcards "*${YQ_BINARY}*" && \
    mv /out/usr/local/bin/${YQ_BINARY} /out/usr/local/bin/yq

# Extract GOVC
RUN tar -xzf /tmp/govc_${GOVC_VERSION}_linux_x86_64.tar.gz -C /out/usr/local/bin/ --wildcards "*govc*"

# Extract inclusivity
RUN tar -xzf /tmp/inclusivity-${INCLUSIVITY_VERSION}-linux-amd64.tar.gz -C /out/usr/local/bin/ --wildcards "*inclusivity*"

# Extract Packer
RUN unzip /tmp/packer_${PACKER_VERSION}_linux_amd64.zip packer -d /out/usr/local/bin/

# Copy the retry script into the image
COPY retry_command.sh /out/usr/local/bin/retry_command.sh

# Make the script executable
RUN chmod +x /out/usr/local/bin/retry_command.sh

# Ensure everything is executable
RUN chmod +x /out/usr/local/bin/*

# Use a Python base image that matches the desired Python version
# We use a slim Debian-based image for smaller size.
FROM python:${PYTHON_VERSION}-slim-bookworm
ARG PYTHON_VERSION="3.13"

ARG ANSIBLE_CORE_VERSION="latest"

LABEL maintainer="Lee Johnson <ljohnson@dettonville.org>"
LABEL description="Custom CICD Container for Python ${PYTHON_VERSION}"

ARG BUILD_DATE
ARG BUILD_ID=devel
LABEL build=$BUILD_ID

# Set environment variables
ENV container=docker
ENV DEBIAN_FRONTEND=noninteractive
ENV JAVA_VERSION=21

## Add this to your Dockerfile before the USER command
ARG user=jenkins
ARG group=jenkins
ARG uid=1001
ARG gid=${uid}
ARG DOCKER_GID=1102

ENV TZ=Etc/UTC

# Create Docker Group with GID
# Set default value of 497 if DOCKER_GID set to blank string by Docker compose
RUN groupadd -g ${DOCKER_GID} docker && \
    groupadd -g ${gid} ${group}

#========================================
# Add normal user with passwordless sudo
#========================================
#RUN useradd ${user} --shell /bin/bash --create-home \
RUN useradd -l -c "Jenkins user" --shell /bin/bash -d /home/"${user}" -u "${uid}" -g "${gid}" -m "${user}" \
  && usermod -aG sudo ${user} \
  && usermod -aG docker ${user} \
  && echo 'ALL ALL = (ALL) NOPASSWD: ALL' >> /etc/sudoers

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
      apt-transport-https apt-utils ca-certificates \
      bash tar zip unzip xorriso \
      curl wget git git-lfs \
      locales tzdata netbase \
      software-properties-common \
      tree less nano jq rsync && \
    sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

## 2. Networking & Debugging Tools
RUN apt-get update -qqy && \
    apt-get -qqy --no-install-recommends install \
      dnsutils iproute2 iputils-ping inetutils-telnet \
      openssh-client ssh-askpass sshpass \
      gpg gpg-agent gnupg2 \
      shellcheck groff rlwrap && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

## 3. Build Tools & Development Libraries
# Essential for compiling Python C-extensions or local builds
RUN apt-get update -qqy && \
    apt-get -qqy --no-install-recommends install \
      build-essential patch genisoimage dirmngr openssl \
      python3-dev libxml2-dev libxslt1-dev \
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
      docker-buildx-plugin \
      docker-model-plugin && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
# --- End Docker-in-Docker (DinD) support installation ---

# 5. External Tools: Copy in from builder stage ---
# Copy the already-extracted binaries from the builder stage
COPY --from=builder /out/usr/local/bin/ /usr/local/bin/
COPY --from=jdk-source /opt/java/openjdk /opt/java/openjdk

# Set Java Environment Variables
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Verify Java is working (Optional but recommended)
RUN java -version

#==========
# PIP - Install Python dependencies
#==========
ARG VSPHERE_AUTOMATION_SDK_VERSION=8.0.3.0

COPY requirements.txt .
COPY requirements.yml .
COPY files/vsphere_automation_sdk-${VSPHERE_AUTOMATION_SDK_VERSION}.tar.gz /var/tmp/vsphere_automation_sdk.tar.gz

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Upgrade core tools
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Install requirements.txt first
RUN pip install --no-cache-dir -r requirements.txt

# === VMware vSphere Automation SDK Installation ===
RUN mkdir -p /tmp/sdk-build && \
    tar -xzf /var/tmp/vsphere_automation_sdk.tar.gz -C /tmp/sdk-build --strip-components=1 && \
    cd /tmp/sdk-build && \
    # Install the pre-built wheels directly (this bypasses the broken metadata)
    pip install --no-cache-dir --no-deps \
        $(find . -name "*.whl") && \
    pip install --no-cache-dir --no-deps . && \
    cd / && \
    rm -rf /tmp/sdk-build


#COPY entrypoint.sh /opt/bin/entrypoint.sh
#COPY functions.sh /opt/bin/functions.sh
#RUN chmod +x /opt/bin/entrypoint.sh \
#  && chmod +x /opt/bin/functions.sh

# COPY entrypoint.sh /opt/bin/entrypoint.sh
# RUN chmod +x /opt/bin/entrypoint.sh

# Create the default Ansible collections directory to ensure
# `ansible-galaxy collection list` can run without errors.
# The `ansible-test` tool and other Ansible commands expect this path to exist.
RUN mkdir -p /root/.ansible/collections

#RUN ansible-galaxy collection install -r requirements.yml
## occasionally network related issues when running ansible-galaxy directly - so wrap with retry mechanism
# optionally can set environment variables to customize retries and delay
# ENV RETRY_MAX_ATTEMPTS=7
# ENV RETRY_SLEEP_SECONDS=15
RUN /usr/local/bin/retry_command.sh ansible-galaxy collection install -r requirements.yml

# Create a working directory for Ansible project files
WORKDIR /ansible_project

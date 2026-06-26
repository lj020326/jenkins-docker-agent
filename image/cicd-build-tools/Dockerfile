#=============================================================================
# 1. CORE BUILD CONFIGURATION
#=============================================================================
ARG JAVA_VERSION=21
ARG PYTHON_VERSION="3.13"
ARG DEBIAN_VERSION="bookworm"

# Cache JDK source stage to extract binaries cleanly later
FROM eclipse-temurin:${JAVA_VERSION}-jdk AS jdk-source

#=============================================================================
# 2. BUILDER STAGE (Decoupled Binary Ingestion)
#=============================================================================
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS builder
RUN apt-get update && apt-get install -y unzip tar curl --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV YQ_VERSION=v4.53.2
ENV YQ_BINARY=yq_linux_amd64
ARG GOVC_VERSION=v0.53.1
ARG PACKER_VERSION=1.15.3
ARG INCLUSIVITY_VERSION=0.19.0

RUN mkdir -p /out/usr/local/bin

# Copy all local files into the builder
COPY files/${YQ_BINARY}_${YQ_VERSION}.tar.gz /tmp/
COPY files/govc_${GOVC_VERSION}_linux_x86_64.tar.gz /tmp/
COPY files/packer_${PACKER_VERSION}_linux_amd64.zip /tmp/
COPY files/inclusivity-${INCLUSIVITY_VERSION}-linux-amd64.tar.gz /tmp/

# Extract YQ
RUN tar -xzf /tmp/${YQ_BINARY}_${YQ_VERSION}.tar.gz -C /out/usr/local/bin/ --wildcards "*${YQ_BINARY}*" && \
    mv /out/usr/local/bin/${YQ_BINARY} /out/usr/local/bin/yq

# Extract GOVC
RUN tar -xzf /tmp/govc_${GOVC_VERSION}_linux_x86_64.tar.gz -C /out/usr/local/bin/ --wildcards "*govc*"

# Extract Packer
RUN unzip /tmp/packer_${PACKER_VERSION}_linux_amd64.zip packer -d /out/usr/local/bin/

# Extract inclusivity
RUN tar -xzf /tmp/inclusivity-${INCLUSIVITY_VERSION}-linux-amd64.tar.gz -C /out/usr/local/bin/ --wildcards "*inclusivity*"

# Bring in external script foundations
COPY retry_command.sh /out/usr/local/bin/retry_command.sh
RUN chmod +x /out/usr/local/bin/*

#=============================================================================
# 3. CONSOLIDATED RUNTIME IMAGE
#=============================================================================
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION}
LABEL maintainer="Lee Johnson <ljohnson@dettonville.org>"
LABEL description="Optimized Enterprise Enterprise CICD Engine Baseline"

ARG BUILD_DATE
ARG BUILD_ID=devel
LABEL build=$BUILD_ID

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    container=docker \
    VIRTUAL_ENV=/opt/venv \
    JAVA_HOME=/opt/java/openjdk

# Inject performance path extensions
ENV PATH="${JAVA_HOME}/bin:${VIRTUAL_ENV}/bin:${PATH}"

# Define identities and group permissions
ARG user=jenkins
ARG group=jenkins
ARG uid=1001
ARG gid=1001
ARG DOCKER_GID=1102

# Standardize optimization configurations for APT packages
RUN echo 'APT::Install-Suggests "0";\nAPT::Install-Recommends "0";' > /etc/apt/apt.conf.d/00-docker

# Create Docker Group with GID
# Set default value of 497 if DOCKER_GID set to blank string by Docker compose
RUN groupadd -g ${DOCKER_GID} docker && \
    groupadd -g ${gid} ${group} && \
    useradd -l -c "Jenkins user" --shell /bin/bash -d /home/"${user}" -u "${uid}" -g "${gid}" -m "${user}" && \
    usermod -aG sudo,docker ${user} && \
    echo 'ALL ALL = (ALL) NOPASSWD: ALL' >> /etc/sudoers

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
      tree less nano jq rsync \
      dnsutils iproute2 iputils-ping inetutils-telnet \
      openssh-client ssh-askpass sshpass \
      gpg gpg-agent gnupg2 \
      ldap-utils \
      shellcheck groff rlwrap && \
    sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

## 2. Build Tools & Development Libraries
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

## Generate and set the locale
#RUN sed -i 's/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
#    && locale-gen

## 4. Docker CLI (DinD Support)
# Kept separate so the Docker version can be updated independently
# --- Start Docker-in-Docker (DinD) support installation ---
# Install Docker CLI to enable running docker commands inside this container.
# This is crucial for scenarios like 'ansible-test units --docker' which
# require interacting with a Docker daemon.
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=\"$(dpkg --print-architecture)\" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" > /etc/apt/sources.list.d/docker.list && \
    \
    apt-get update && apt-get install -y docker-ce-cli docker-compose-plugin docker-buildx-plugin docker-model-plugin && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
# --- End Docker-in-Docker (DinD) support installation ---

#=============================================================================
# 4. RUNTIME DEPENDENCY INGESTION
#=============================================================================
COPY --from=builder /out/usr/local/bin/ /usr/local/bin/
COPY --from=jdk-source /opt/java/openjdk /opt/java/openjdk

RUN if [ -f ${JAVA_HOME}/conf/security/java.security ]; then \
        sed -i 's/securerandom\.source=file:\/dev\/random/securerandom\.source=file:\/dev\/urandom/' ${JAVA_HOME}/conf/security/java.security; \
    fi

# Verify Java is working (Optional but recommended)
RUN java -version

#==========
# PIP - Install Python dependencies
#==========
# Configure a virtual environment for isolated Python modules
RUN python3 -m venv $VIRTUAL_ENV && pip install --no-cache-dir --upgrade pip wheel setuptools

COPY requirements.txt .
COPY requirements.yml .
ARG VSPHERE_AUTOMATION_SDK_VERSION=8.0.3.0
COPY files/vsphere_automation_sdk-${VSPHERE_AUTOMATION_SDK_VERSION}.tar.gz /var/tmp/vsphere_automation_sdk.tar.gz

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --no-cache-dir -r requirements.txt && \
    mkdir -p /tmp/sdk-build && \
    tar -xzf /var/tmp/vsphere_automation_sdk.tar.gz -C /tmp/sdk-build --strip-components=1 && \
    cd /tmp/sdk-build && \
    pip install --no-cache-dir --no-deps $(find . -name "*.whl") && \
    pip install --no-cache-dir --no-deps . && \
    cd / && rm -rf /tmp/sdk-build /var/tmp/vsphere_automation_sdk.tar.gz requirements.txt

#=============================================================================
# Configure Multiarch contexts with valid schema properties
#=============================================================================
RUN for user_home in /root /home/${user}; do \
        mkdir -p ${user_home}/.docker/buildx/instances && \
        echo '{"name":"multiarch-builder","driver":"docker-container","nodes":[{"name":"multiarch-builder0","endpoint":"unix:///var/run/docker.sock","platforms":null,"flags":[],"env":null,"driver-opts":null}]}' \
        > ${user_home}/.docker/buildx/instances/multiarch-builder && \
        mkdir -p ${user_home}/.docker && \
        echo '{"currentContext":"default"}' \
        > ${user_home}/.docker/config.json && \
        mkdir -p ${user_home}/.ansible/collections && \
        chown -R ${user}:${user} ${user_home}/.docker ${user_home}/.ansible || true; \
    done

# Safe, repeatable compilation context via resilient wrapper
RUN /usr/local/bin/retry_command.sh ansible-galaxy collection install -r requirements.yml && rm requirements.yml

# Create a working directory for jenkins project files
WORKDIR /jenkins_project

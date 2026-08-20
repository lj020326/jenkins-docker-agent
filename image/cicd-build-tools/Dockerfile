#=============================================================================
# 1. JDK CONFIGURATION
#=============================================================================
ARG JAVA_VERSION=21
ARG PYTHON_VERSION="3.13"
ARG DEBIAN_VERSION="bookworm"

FROM eclipse-temurin:${JAVA_VERSION}-jdk AS jdk-source

#=============================================================================
# 2. BUILDER STAGE (Decoupled Binary Ingestion)
#=============================================================================
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS builder

ENV YQ_VERSION=v4.53.2
ENV YQ_BINARY=yq_linux_amd64
ARG GOVC_VERSION=v0.53.1
ARG PACKER_VERSION=1.15.3
ARG INCLUSIVITY_VERSION=0.19.0

RUN apt-get update && apt-get install -y --no-install-recommends unzip tar curl \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /out/usr/local/bin

# ADD auto-extracts local archives, saving extract layers
ADD files/${YQ_BINARY}_${YQ_VERSION}.tar.gz /tmp/
ADD files/govc_${GOVC_VERSION}_linux_x86_64.tar.gz /tmp/
COPY files/packer_${PACKER_VERSION}_linux_amd64.zip /tmp/
ADD files/inclusivity-${INCLUSIVITY_VERSION}-linux-amd64.tar.gz /tmp/

RUN mv /tmp/${YQ_BINARY} /out/usr/local/bin/yq || mv /tmp/*${YQ_BINARY}* /out/usr/local/bin/yq && \
    mv /tmp/govc /out/usr/local/bin/govc || true && \
    unzip /tmp/packer_${PACKER_VERSION}_linux_amd64.zip packer -d /out/usr/local/bin/ && \
    mv /tmp/inclusivity /out/usr/local/bin/inclusivity || true

COPY retry_command.sh /out/usr/local/bin/retry_command.sh
RUN chmod +x /out/usr/local/bin/*

#=============================================================================
# 3. CONSOLIDATED RUNTIME IMAGE
#=============================================================================
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION}
LABEL maintainer="Lee Johnson <ljohnson@dettonville.org>"
LABEL description="Optimized CICD Engine Baseline"

ARG BUILD_DATE
ARG BUILD_ID=devel
LABEL build=$BUILD_ID

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    container=docker \
    VIRTUAL_ENV=/opt/venv \
    JAVA_HOME=/opt/java/openjdk \
    PIP_NO_CACHE_DIR=1

ENV PATH="${JAVA_HOME}/bin:${VIRTUAL_ENV}/bin:${PATH}"

ARG user=jenkins
ARG group=jenkins
ARG uid=1001
ARG gid=1001
ARG DOCKER_GID=1102

USER root

# Setup Docker Group, Jenkins User, and APT Configuration
RUN groupadd -g ${DOCKER_GID} docker && \
    groupadd -g ${gid} ${group} && \
    useradd -l -c "Jenkins user" --shell /bin/bash -d /home/"${user}" -u "${uid}" -g "${gid}" -m "${user}" && \
    usermod -aG sudo,docker ${user} && \
    echo 'APT::Install-Suggests "0";\nAPT::Install-Recommends "0";' > /etc/apt/apt.conf.d/00-docker

# Switch default shell to bash so pipefail is recognized
SHELL ["/bin/bash", "-c"]

# Combined APT Installation Layer
RUN set -o pipefail && \
    apt-get update -qqy && \
    apt-get -qqy --no-install-recommends install \
      apt-transport-https apt-utils ca-certificates \
      bash tar zip unzip xorriso \
      curl git git-lfs \
      locales tzdata netbase \
      tree less jq rsync \
      dnsutils iproute2 iputils-ping inetutils-telnet \
      openssh-client ssh-askpass sshpass \
      gpg gpg-agent gnupg2 \
      shellcheck groff rlwrap \
      build-essential patch genisoimage dirmngr openssl \
      libxml2-dev libxslt1-dev \
      zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev \
      libpq-dev libmariadb-dev libsasl2-dev libldap2-dev \
      libssl-dev libsqlite3-dev libreadline-dev libffi-dev \
      libbz2-dev uuid-dev default-mysql-client && \
    sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=\"$(dpkg --print-architecture)\" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin docker-buildx-plugin docker-model-plugin && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

#=============================================================================
# 4. RUNTIME DEPENDENCY INGESTION
#=============================================================================
COPY --from=builder /out/usr/local/bin/ /usr/local/bin/
COPY --from=jdk-source /opt/java/openjdk /opt/java/openjdk

RUN if [ -f ${JAVA_HOME}/conf/security/java.security ]; then \
        sed -i 's/securerandom\.source=file:\/dev\/random/securerandom\.source=file:\/dev\/urandom/' ${JAVA_HOME}/conf/security/java.security; \
    fi && java -version

# Setup Virtual Environment and Python packages
WORKDIR /tmp
RUN python3 -m venv $VIRTUAL_ENV && pip install --no-cache-dir --upgrade pip wheel setuptools

ARG VSPHERE_AUTOMATION_SDK_VERSION=8.0.3.0
COPY requirements.txt .
ADD files/vsphere_automation_sdk-${VSPHERE_AUTOMATION_SDK_VERSION}.tar.gz /tmp/sdk-build/

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --no-deps $(find . -name "*.whl") && \
    pip install --no-cache-dir --no-deps /tmp/sdk-build/* && \
    rm -rf /tmp/sdk-build requirements.txt

# =============================================================================
# Runtime user / HOME
# =============================================================================
#
# IMPORTANT – do NOT switch to USER jenkins (or any non-root user) at the end
# of this image.
#
# The Jenkins Docker Pipeline plugin always starts agent containers with:
#   docker run ... -u 0:0 ...
#
# When the image itself ends with `USER jenkins` + `ENV HOME=/home/jenkins`,
# two different home directories appear at runtime:
#   - $HOME          → /home/jenkins   (from the ENV)
#   - getpwuid(0)    → /root           (because the process is actually root)
#
# Ansible’s async wrapper is sensitive to this mismatch.  The job file is
# written under /home/jenkins/.ansible_async/… while async_status later
# looks under /root/.ansible_async/… and fails with “could not find job”.
#
# Keeping the image as root (HOME=/root) makes the two paths identical and
# eliminates the class of bugs.  The same root cause also affected SSH
# known_hosts / key-scan behaviour in downstream images that extended this one.
#
# The jenkins user is still created so the image can be run manually as
# non-root if desired, but the default (and the only supported mode under
# the Docker Pipeline plugin) is root.
#
# =============================================================================
ENV HOME=/root
WORKDIR "${HOME}"

# Ensure the directories Ansible (and other tools) expect exist
RUN mkdir -p ${HOME}/.ansible_async \
             ${HOME}/.ansible/collections \
             ${HOME}/.ssh \
             ${HOME}/.docker/buildx/instances && \
    # optional: still keep a jenkins home in case someone runs without -u 0:0
    mkdir -p /home/${user}/.ansible_async \
             /home/${user}/.ansible/collections \
             /home/${user}/.ssh \
             /home/${user}/.docker/buildx/instances && \
    chown -R ${user}:${group} /home/${user}

COPY requirements.yml .
RUN /usr/local/bin/retry_command.sh ansible-galaxy collection install -r requirements.yml && \
    rm -f requirements.yml

USER root
# Fallback default command
CMD ["/bin/bash"]

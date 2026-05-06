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
RUN unzip /tmp/packer_${PACKER_VERSION}_linux_amd64.zip packer -d /out/usr/local/bin/

# Ensure everything is executable
RUN chmod +x /out/usr/local/bin/*

## ref: https://github.com/jenkinsci/docker-agent/blob/master/17/bullseye/Dockerfile
## ref: https://github.com/jenkinsci/docker-inbound-agent
ARG UBUNTU_VERSION=24.04
FROM ubuntu:${UBUNTU_VERSION}
LABEL maintainer="Lee Johnson <ljohnson@dettonville.org>"

ARG BUILD_DATE
ARG BUILD_ID=devel
LABEL build=$BUILD_ID

# Derived from
## ref: https://github.com/jenkinsci/docker-agent/blob/master/17/bullseye/Dockerfile
## ref: https://github.com/jenkinsci/docker/blob/master/Dockerfile
## ref: https://github.com/cyrille-leclerc/java-build-tools-dockerfile
## ref: https://github.com/dettonville/java-build-tools-dockerfile
## ref: https://github.com/getintodevops/jenkins-withdocker (miiro@getintodevops.com)
ARG user=jenkins
ARG group=jenkins
ARG uid=1001
#ARG gid=1001
ARG gid=${uid}
ARG http_port=8080
ARG agent_port=50000
ARG DOCKER_GID=1102
ARG WORKDIR=/home/${user}

ARG INTERNAL_IMAGE_BUILD=YES

ARG JENKINS_AGENT_WORKDIR="${WORKDIR}"/agent

ENV TZ=Etc/UTC

## ref: https://serverfault.com/questions/618994/when-building-from-dockerfile-debian-ubuntu-package-install-debconf-noninteract
ENV container=docker
ENV DEBIAN_FRONTEND=noninteractive
ENV JAVA_VERSION=21

#################################################
# Inspired by
# https://github.com/cloudbees/jnlp-slave-with-java-build-tools-dockerfile
# https://github.com/cloudbees/java-build-tools-dockerfile/blob/master/Dockerfile
# https://github.com/SeleniumHQ/docker-selenium/blob/master/Base/Dockerfile
# https://github.com/bibinwilson/jenkins-docker-slave
# https://medium.com/@prashant.vats/jenkins-master-and-slave-with-docker-b993dd031cbd
#################################################

## ALREADY DONE IN PARENT IMAGE
#RUN groupadd -g "${gid}" "${group}" \
#  && useradd -l -c "Jenkins user" -d /home/"${user}" -u "${uid}" -g "${gid}" -m "${user}"

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
  && echo 'ALL ALL = (ALL) NOPASSWD: ALL' >> /etc/sudoers \
  && echo "${user}:secret" | chpasswd

##================================================
## Customize sources for apt-get to use the custom mirror
##================================================
# Define the mirror base URL
#ENV APT_MIRROR="http://archive.ubuntu.com"
#ENV APT_MIRROR_SECURITY="http://security.ubuntu.com"
ENV APT_MIRROR=http://mirrors.rit.edu
ENV APT_MIRROR_SECURITY=http://mirrors.rit.edu

## --- Dynamically generate the ubuntu.sources file ---
#RUN DISTRIB_CODENAME=$(grep "VERSION_CODENAME=" /etc/os-release | cut -d'=' -f2 | tr -d '"') && \
#    echo "DISTRIB_CODENAME=${DISTRIB_CODENAME}" && \
#    printf "Types: deb\n\ URIs: ${APT_MIRROR}/ubuntu/\n\ Suites: ${DISTRIB_CODENAME} ${DISTRIB_CODENAME}-updates ${DISTRIB_CODENAME}-backports\n\ Components: main universe restricted multiverse\n\ Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n\n\ Types: ${APT_MIRROR_SECURITY}/ubuntu/\n\ ${DISTRIB_CODENAME}-security\n\ /usr/share/keyrings/ubuntu-archive-keyring.gpg\n"> /etc/apt/sources.list.d/ubuntu.sources

RUN sed -i "s|http://archive.ubuntu.com|${APT_MIRROR}|g" /etc/apt/sources.list.d/ubuntu.sources && \
    sed -i "s|http://security.ubuntu.com|${APT_MIRROR_SECURITY}|g" /etc/apt/sources.list.d/ubuntu.sources

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
      locales software-properties-common bash tar zip unzip gnupg \
      netbase tzdata curl wget git git-lfs tree less nano jq rsync && \
    sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

## 2. Networking & Debugging Tools
RUN apt-get update -qqy && \
    apt-get -qqy --no-install-recommends install \
      dnsutils iproute2 openssh-client iputils-ping \
      inetutils-telnet ssh-askpass sshpass ssh-client shellcheck && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

## 3. Runtimes: Java & Python
# These are the heaviest layers; separating them ensures changes to one don't invalidate the other
RUN apt-get update -qqy && \
    apt-get -qqy --no-install-recommends install \
      openjdk-21-jdk \
      python3 python3-pip python3-apt python3-virtualenv python3-venv groff rlwrap && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

## 4. Build Tools & Development Libraries
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

## 5. Docker CLI (DinD Support)
# Kept separate so the Docker version can be updated independently
# --- Start Docker-in-Docker (DinD) support installation ---
# Install Docker CLI to enable running docker commands inside this container.
# This is crucial for scenarios like 'ansible-test units --docker' which
# require interacting with a Docker daemon.
# Modern Docker Repo Setup
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/trusted.gpg.d/docker.asc && \
    add-apt-repository "deb [arch=$(dpkg --print-architecture)] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      docker-ce-cli \
      docker-compose-plugin \
      docker-buildx-plugin \
      docker-model-plugin && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
# --- End Docker-in-Docker (DinD) support installation ---

# 6. External Tools: Copy in from builder stage ---
# Copy the already-extracted binaries from the builder stage
COPY --from=builder /out/usr/local/bin/ /usr/local/bin/

#==========
# PIP - Install Python dependencies
#==========
COPY requirements.txt .
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip wheel setuptools && \
    pip install -r requirements.txt

RUN mkdir -p ${WORKDIR}/.ansible \
  && chown -R ${user}:${group} ${WORKDIR}/.ansible

#==========
# JAVA - Install java dependencies
#==========
## ref: https://stackoverflow.com/questions/43316935/change-java-securerandom-in-dockerfile
RUN sed -i 's/securerandom\.source=file:\/dev\/random/securerandom\.source=file:\/dev\/urandom/' /etc/java-${JAVA_VERSION}-openjdk/security/java.security

## ref: https://www.howtoforge.com/how-to-install-java-openjdk-and-oracle-jdk-on-ubuntu-22-04/
#ENV JAVA_HOME=/opt/java/openjdk
ENV JAVA_HOME=/usr/lib/jvm/java-${JAVA_VERSION}-openjdk-amd64

#COPY entrypoint.sh /opt/bin/entrypoint.sh
#COPY functions.sh /opt/bin/functions.sh
#RUN chmod +x /opt/bin/entrypoint.sh \
#  && chmod +x /opt/bin/functions.sh

# COPY entrypoint.sh /opt/bin/entrypoint.sh
# RUN chmod +x /opt/bin/entrypoint.sh

# drop back to the regular jenkins user - good practice
#USER jenkins
USER ${user}

## Add jenkins plugin
#COPY plugins.txt /usr/share/jenkins/plugins.txt
#RUN /usr/local/bin/install-plugins.sh < /usr/share/jenkins/plugins.txt

# for dev purpose
# USER root

# ENTRYPOINT ["/opt/bin/entrypoint.sh"]
#
# EXPOSE 4444

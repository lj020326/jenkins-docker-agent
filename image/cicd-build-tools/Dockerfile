## ref: https://github.com/jenkinsci/docker-agent/blob/master/17/bullseye/Dockerfile
## ref: https://github.com/jenkinsci/docker-inbound-agent
FROM ubuntu:24.04
LABEL maintainer="Lee Johnson <ljohnson@dettonville.org>"

ARG BUILD_ID=devel
ARG BUILD_DATE="2024-05-01"
LABEL build_date=$BUILD_DATE
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
ARG DOCKER_GID=991
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

# Create Docker Group with GID
# Set default value of 497 if DOCKER_GID set to blank string by Docker compose
RUN groupadd -g ${DOCKER_GID} docker && \
    groupadd -g ${gid} ${group}

## ALREADY DONE IN PARENT IMAGE
#RUN groupadd -g "${gid}" "${group}" \
#  && useradd -l -c "Jenkins user" -d /home/"${user}" -u "${uid}" -g "${gid}" -m "${user}"

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
## Customize sources for apt-get (only use if DISTRO version is old/archived - <=20.04)
##================================================
#RUN DISTRIB_CODENAME=$(cat /etc/*release* | grep DISTRIB_CODENAME | cut -f2 -d'=') \
#    && echo "deb http://archive.ubuntu.com/ubuntu ${DISTRIB_CODENAME} main universe\n" > /etc/apt/sources.list \
#    && echo "deb http://archive.ubuntu.com/ubuntu ${DISTRIB_CODENAME}-updates main universe\n" >> /etc/apt/sources.list \
#    && echo "deb http://security.ubuntu.com/ubuntu ${DISTRIB_CODENAME}-security main universe\n" >> /etc/apt/sources.list

## ref: https://octopus.com/blog/using-ubuntu-docker-image
RUN echo 'APT::Install-Suggests "0";' >> /etc/apt/apt.conf.d/00-docker
RUN echo 'APT::Install-Recommends "0";' >> /etc/apt/apt.conf.d/00-docker

RUN apt-get update -qqy && \
    apt-get -qqy --no-install-recommends install \
      apt-transport-https \
      apt-utils \
      locales \
      ca-certificates \
      software-properties-common \
      dnsutils \
      iproute2 \
      openssh-client \
      iputils-ping \
      inetutils-telnet \
      ssh-askpass sshpass \
      netbase \
      patch \
      tzdata \
      gpg gpg-agent \
      openjdk-21-jdk \
      openssl \
      tar zip unzip \
      wget curl \
      git \
      git-lfs \
      build-essential \
      less nano tree \
      jq \
      python3 \
      python3-pip \
      python3-apt \
      python3-virtualenv \
      python3-venv \
      groff \
      rlwrap \
      rsync \
      genisoimage \
      zlib1g-dev \
      libncurses5-dev \
      libgdbm-dev \
      libnss3-dev \
      libssl-dev \
      libsqlite3-dev \
      libreadline-dev \
      libffi-dev \
      libbz2-dev \
      tk-dev \
      uuid-dev \
      default-mysql-client && \
    sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    # Modern Docker Repo Setup
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/trusted.gpg.d/docker.asc && \
    add-apt-repository "deb [arch=$(dpkg --print-architecture)] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce docker-buildx-plugin && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

## Ensure the following are set after running `locale-gen`
ENV LANGUAGE=en_US:en
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

## ref: https://stackoverflow.com/questions/43316935/change-java-securerandom-in-dockerfile
RUN sed -i 's/securerandom\.source=file:\/dev\/random/securerandom\.source=file:\/dev\/urandom/' /etc/java-${JAVA_VERSION}-openjdk/security/java.security

## ref: https://www.howtoforge.com/how-to-install-java-openjdk-and-oracle-jdk-on-ubuntu-22-04/
#ENV JAVA_HOME=/opt/java/openjdk
ENV JAVA_HOME=/usr/lib/jvm/java-${JAVA_VERSION}-openjdk-amd64

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

##==========
## VMWARE govc CLI
## refs:
##    https://github.com/matt-l-welch/docker-govc/blob/master/Dockerfile
##    https://www.msystechnologies.com/blog/learn-how-to-install-configure-and-test-govc/
##    https://stackoverflow.com/questions/61571511/using-the-govc-container-in-jenkins
##==========
#RUN curl -fsSL $(curl -s https://api.github.com/repos/vmware/govmomi/releases/latest | \
#    grep browser_download_url | grep -i govc_linux_x86_64 | cut -d '"' -f 4) | \
#    tar -C /usr/local/bin -zxf -
RUN mkdir /var/tmp/govmomi && \
    curl -fsSL $(curl -s https://api.github.com/repos/vmware/govmomi/releases/latest | \
    grep browser_download_url | grep -i govc_linux_x86_64 | cut -d '"' -f 4) | \
    tar xzf - -C /var/tmp/govmomi && \
    mv /var/tmp/govmomi/govc /usr/local/bin && \
    rm -rf /var/tmp/govmomi

##==========
## PACKER CLI
## refs:
##   https://stackoverflow.com/questions/53147975/install-packer-in-jenkins-slave-using-dockerfile
##==========
#RUN add-apt-repository \
#        "deb [arch=$(dpkg --print-architecture)] https://apt.releases.hashicorp.com $(lsb_release -cs) main" && \
#    apt-get update && \
#    apt-get -y --no-install-recommends install packer

ARG PACKER_VERSION=1.9.5
##RUN PACKER_VERSION=$(wget -q -O -  https://releases.hashicorp.com/packer/ | grep packer_ | sed 's/.*packer_\(.*\)\<.*/\1/' | uniq | head -1) \
##RUN PACKER_VERSION=$(curl -fsSL https://releases.hashicorp.com/packer/ | grep packer_ | sed 's/.*packer_\(.*\)\<.*/\1/' | uniq | head -1) \
#RUN curl -fsSL https://releases.hashicorp.com/packer/${PACKER_VERSION}/packer_${PACKER_VERSION}_linux_amd64.zip | \
#    gunzip > /usr/local/bin/packer && \
#    chmod +x /usr/local/bin/packer
##RUN wget https://releases.hashicorp.com/packer/1.3.2/packer_1.6.2_linux_amd64.zip
##RUN unzip packer_1.3.2_linux_amd64.zip -d packer

COPY files/packer_${PACKER_VERSION}_linux_amd64.zip /var/tmp
RUN unzip /var/tmp/packer_${PACKER_VERSION}_linux_amd64.zip -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/packer \
    && rm /var/tmp/packer_${PACKER_VERSION}_linux_amd64.zip

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

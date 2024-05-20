## ref: https://hourperday.wordpress.com/2017/05/17/how-to-cicd-with-chef-cookbooks-and-jenkins-part-three/
## ref: https://schneide.blog/2019/10/21/using-parameterized-docker-builds/
ARG IMAGE_REGISTRY=lj020326
ARG BASE_IMAGE_LABEL=cicd-build-tools
ARG BUILD_ID=devel
ARG BUILD_DATE="2024-05-01"

FROM $IMAGE_REGISTRY/$BASE_IMAGE_LABEL:latest
LABEL maintainer="Lee Johnson <ljohnson@dettonville.org>"
LABEL build_date=$BUILD_DATE
LABEL build=$BUILD_ID

USER root

RUN apt-get update -qq && apt-get install -qqy \
    apt-transport-https \
    ca-certificates \
    curl \
    lxc \
    iptables

## docker already in base image
# Install Docker from Docker Inc. repositories.
#RUN curl -sSL https://get.docker.com/ | sh

# Install the magic wrapper.
ADD ./wrapdocker.sh /usr/local/bin/wrapdocker
RUN chmod +x /usr/local/bin/wrapdocker

#ARG SWARM_CLIENT_VERSION=2.0
ARG SWARM_CLIENT_VERSION=3.25
#ARG DOCKER_COMPOSE_VERSION=1.3.3

## This is done in the base CICD tools image
# Install necessary packages
#RUN apt-get update && apt-get install -y curl zip openjdk-7-jre-headless supervisor && rm -rf /var/lib/apt/lists/*
#RUN curl -fsSL https://omnitruck.chef.io/install.sh | sudo bash -s -- -P inspec

RUN apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

# Install Jenkins Swarm Client
#ADD https://repo.jenkins-ci.org/releases/org/jenkins-ci/plugins/swarm-client/3.3/swarm-client-3.3.jar /home/jenkins/
#ADD https://repo.jenkins-ci.org/releases/org/jenkins-ci/plugins/swarm-client/${SWARM_CLIENT_VERSION}/swarm-client-${SWARM_CLIENT_VERSION}.jar /home/jenkins/
RUN curl --connect-timeout 20 --max-time 60 -o /home/jenkins/swarm-client.jar \
    https://repo.jenkins-ci.org/releases/org/jenkins-ci/plugins/swarm-client/${SWARM_CLIENT_VERSION}/swarm-client-${SWARM_CLIENT_VERSION}.jar

RUN chown jenkins:jenkins /home/jenkins/swarm-client.jar

ADD supervisord.conf /etc/supervisor/conf.d/supervisord.conf

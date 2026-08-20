# ARG instructions used in FROM must come before the FROM instruction
ARG IMAGE_REGISTRY=docker.io
ARG BASE_IMAGE_LABEL=lj020326/cicd-build-tools:latest
FROM $IMAGE_REGISTRY/$BASE_IMAGE_LABEL

ARG user=jenkins
ARG group=jenkins

USER root
#ENV HOME=/home/${user}
ENV HOME=/root

#==========
# PIP - Install Python dependencies
#==========
COPY requirements.txt .
RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

ARG JENKINS_AGENT_WORKDIR="${HOME}/agent"

## drop back to the regular jenkins user - good practice
#USER ${user}

## Create a working directory for jenkins project files
#WORKDIR /jenkins_project
# Create a working directory for Ansible project files
WORKDIR ${HOME}

# ARG instructions used in FROM must come before the FROM instruction
ARG IMAGE_REGISTRY=docker.io
ARG BASE_IMAGE_LABEL=lj020326/cicd-build-tools:latest
FROM $IMAGE_REGISTRY/$BASE_IMAGE_LABEL

ARG user=jenkins
ARG group=jenkins

USER root

#==========
# PIP - Install Python dependencies
#==========
## ref: https://github.com/pypa/pip/issues/11179#issuecomment-1152766374
ENV PIP_ROOT_USER_ACTION=ignore

COPY requirements.txt .
RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

ARG WORKDIR=/home/${user}
ARG JENKINS_AGENT_WORKDIR="${WORKDIR}"/agent

# drop back to the regular jenkins user - good practice
USER ${user}

## Create a working directory for jenkins project files
#WORKDIR /jenkins_project
# Create a working directory for Ansible project files
WORKDIR ${WORKDIR}

## ref: https://schneide.blog/2019/10/21/using-parameterized-docker-builds/
ARG IMAGE_REGISTRY=docker.io
ARG BASE_IMAGE_LABEL=lj020326/cicd-build-tools
FROM $IMAGE_REGISTRY/$BASE_IMAGE_LABEL
ARG BUILD_ID=devel
ARG BUILD_DATE="2024-05-01"

## refs:
##   https://github.com/cloudbees/jnlp-slave-with-java-build-tools-dockerfile/blob/master/Dockerfile
##   https://github.com/cloudbees/java-build-tools-dockerfile/blob/master/Dockerfile
##
#FROM jenkins/inbound-agent as builder
FROM jenkins/agent as builder

FROM $IMAGE_REGISTRY/$BASE_IMAGE_LABEL:latest
LABEL maintainer="Lee Johnson <ljohnson@dettonville.org>"
LABEL build_date=$BUILD_DATE
LABEL build=$BUILD_ID

#################################################
# Inspired by
# https://github.com/cloudbees/jnlp-slave-with-java-build-tools-dockerfile
# https://github.com/cloudbees/java-build-tools-dockerfile/blob/master/Dockerfile
# https://github.com/SeleniumHQ/docker-selenium/blob/master/Base/Dockerfile
# https://github.com/bibinwilson/jenkins-docker-slave
# https://medium.com/@prashant.vats/jenkins-master-and-slave-with-docker-b993dd031cbd
#################################################

USER root

## ref: https://issues.jenkins-ci.org/browse/JENKINS-60343
ARG user=jenkins
ARG group=${user}
ARG uid=1000
ARG gid=${uid}
ENV HOME=/home/${user}

#COPY --from=builder /usr/local/bin/jenkins-slave /usr/local/bin/jenkins-agent
COPY jenkins-agent /usr/local/bin/jenkins-agent
COPY --from=builder /usr/share/jenkins/agent.jar /usr/share/jenkins/agent.jar

RUN chmod +x /usr/local/bin/jenkins-agent &&\
    ln -s /usr/local/bin/jenkins-agent /usr/local/bin/jenkins-slave
RUN chmod 644 /usr/share/jenkins/agent.jar &&\
    ln -sf /usr/share/jenkins/agent.jar /usr/share/jenkins/slave.jar

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

#USER ${user}

#ENTRYPOINT ["/usr/local/bin/jenkins-agent"]
ENTRYPOINT ["/entrypoint.sh"]

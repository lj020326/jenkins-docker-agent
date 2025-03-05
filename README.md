[![Docker images build](https://github.com/lj020326/jenkins-docker-agent/actions/workflows/build-images.yml/badge.svg)](https://github.com/lj020326/jenkins-docker-agent/actions/workflows/build-images.yml)
[![License](https://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat)](LICENSE)

# jenkins-docker-agent

The jenkins-agent enabled docker images defined here can be found on [dockerhub](https://hub.docker.com/repositories/lj020326?search=jenkins).  

Docker CICD builder agent for Jenkins.

Inspired by:
- https://wiki.tds.tieto.com/display/TDSKB/Executing+Jenkins+jobs+when+only+one+way+network+connection+exists
- https://support.cloudbees.com/hc/en-us/articles/115001771692-How-to-Create-Permanent-Agents-with-Docker#jnlpconnection
- https://github.com/cyrille-leclerc/java-build-tools-dockerfile
- https://github.com/dettonville/java-build-tools-dockerfile
- https://github.com/cloudbees/jnlp-slave-with-java-build-tools-dockerfile
- https://github.com/cloudbees/java-build-tools-dockerfile/blob/master/Dockerfile
- https://github.com/SeleniumHQ/docker-selenium/blob/master/Base/Dockerfile
- https://medium.com/@prashant.vats/jenkins-master-and-slave-with-docker-b993dd031cbd
- https://devopscube.com/docker-containers-as-build-slaves-jenkins/
- https://github.com/bibinwilson/jenkins-docker-slave


## Description

It can be used as a Jenkins inbound agent, for use with Jenkins Cloud plugins.

## Status

[![GitHub issues](https://img.shields.io/github/issues/lj020326/jenkins-docker-agent.svg?style=flat)](https://github.com/lj020326/jenkins-docker-agent/issues)
[![GitHub stars](https://img.shields.io/github/stars/lj020326/jenkins-docker-agent.svg?style=flat)](https://github.com/lj020326/jenkins-docker-agent/stargazers)
[![Docker Pulls - cicd-build-tools](https://img.shields.io/docker/pulls/lj020326/cicd-build-tools.svg?style=flat)](https://hub.docker.com/repository/docker/lj020326/cicd-build-tools/)
[![Docker Pulls - jenkins-docker-cicd-agent](https://img.shields.io/docker/pulls/lj020326/jenkins-docker-cicd-agent.svg?style=flat)](https://hub.docker.com/repository/docker/lj020326/jenkins-docker-cicd-agent/)
[![Docker Pulls - cicd-docker-in-docker](https://img.shields.io/docker/pulls/lj020326/cicd-docker-in-docker.svg?style=flat)](https://hub.docker.com/repository/docker/lj020326/cicd-docker-in-docker/)
[![Docker Pulls - jenkins-dind-agent](https://img.shields.io/docker/pulls/lj020326/jenkins-dind-agent.svg?style=flat)](https://hub.docker.com/repository/docker/lj020326/jenkins-dind-agent/)
[![Docker Pulls - jenkins-swarm-agent](https://img.shields.io/docker/pulls/lj020326/jenkins-swarm-agent.svg?style=flat)](https://hub.docker.com/repository/docker/lj020326/jenkins-swarm-agent/)

## How to use this Docker image

This Docker image is intended to be used in conjunction with a Docker container orchestration service such as
-   Kubernetes (see [Jenkins Kubernetes Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Kubernetes+Plugin))
-   Mesos (see [Jenkins Mesos Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Mesos+Plugin))
-   Amazon EC2 Container Service

It can also be used as a "static" Jenkins agent connected to a Jenkins master by manually launching the Docker container.

### Java

Sample with the Jenkins [Pipeline Maven Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Pipeline+Maven+Plugin).

```
node ("cicd-docker-agent") { 

    git "https://github.com/cloudbees-community/game-of-life"
    withMaven(mavenSettingsConfig:'my-maven-settings') {
       sh "mvn clean deploy"
    }
}
```

### Selenium

The docker image enables Selenium tests bundling Firefox and starting selenium-server-standalone (listening on the default port 4444).

#### Selenium Sample with Java

```
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.remote.DesiredCapabilities;
import org.openqa.selenium.remote.RemoteWebDriver;

WebDriver webDriver = new RemoteWebDriver(DesiredCapabilities.firefox());
webDriver.get("http://www.python.org");
webDriver.getTitle();
```

### Selenium Sample with Python

```
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

driver = webdriver.Remote(
   command_executor='http://127.0.0.1:4444/wd/hub',
   desired_capabilities=DesiredCapabilities.FIREFOX)

driver.get('http://python.org')
```

## Running

To run a Docker container

    docker run cicd-docker-agent -url http://jenkins-server:port <secret> <agent name>

optional environment variables:

* `JENKINS_URL`: url for the Jenkins server, can be used as a replacement to `-url` option, or to set alternate jenkins URL
* `JENKINS_TUNNEL`: (`HOST:PORT`) connect to this agent host and port instead of Jenkins server, assuming this one do route TCP traffic to Jenkins master. Useful when when Jenkins runs behind a load balancer, reverse proxy, etc.


## Contact

[![Linkedin](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/leejjohnson/)

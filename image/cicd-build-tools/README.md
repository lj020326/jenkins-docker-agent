
# Description

Docker image with all the commonly used tools to build Java applications on Jenkins agents.

We have decided to bundle many tools in the same image to cover as many Java use cases as possible. In a second iteration, we plan to offer granularity in the tools installed on the image, maybe using a `Dockerfile` generator.

## Supported tags and respective `Dockerfile` links

-   [`latest` (*latest/Dockerfile*)](https://github.com/cloudbees/java-build-tools-dockerfile/blob/master/Dockerfile)

## How to use this Docker image

This Docker image is intended to be used with the [Jenkins Docker Pipeline Plugin](https://wiki.jenkins-ci.org/display/JENKINS/CloudBees+Docker+Pipeline+Plugin).

## Java

Sample with Maven and the Jenkins [Docker Pipeline Plugin](https://wiki.jenkins-ci.org/display/JENKINS/CloudBees+Docker+Pipeline+Plugin) and [Pipeline Maven Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Pipeline+Maven+Plugin).

```
node ("docker"){
    git "https://github.com/lj020326/game-of-life"
    docker.image("lj020326/java-build-tools").inside {
        withMaven(mavenSettingsConfig:'my-maven-settings') {
           sh "mvn clean deploy"
        }
    }
}
```

## Selenium

The docker image enables Selenium tests bundling Firefox and starting selenium-server-standalone (listening on the default port 4444).

### Selenium Sample with Java

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

# Version latest
-   OS: Ubuntu 20.04
-   Common tools: openssh-client, unzip, wget, curl, git, jq, rsync
-   Ant 1.10.8
-   AWS CLI: aws-cli/1.18.108
-   Azure CLI (`az`): 2.0.81
-   Yarn 1.22.4
-   Cloud Foundry CLI (latest) at `/usr/local/bin/cf`: 6.51.0
-   Firefox at `/usr/bin/firefox`: 68.1.0esr
-   Firefox Geckodriver at `/usr/bin/geckodriver`: v0.26.0
-   gcc (latest): 9.3.0
-   Grunt CLI: 1.3.2
-   Gulp: 4.0.2
-   Java: OpenJDK 8 (latest): 1.8.0_252-8u252
-   JMeter (5.3.1) located in `/opt/jmeter/`
-   Kubernetes CLI at `/usr/local/bin/kubectl`: 1.16.1
-   Make (latest): 4.2.1
-   Maven located in `/usr/share/maven/`: 3.6.3
-   MySQL Client: 8.0.21
-   Node.js at `/usr/bin/nodejs`: 10.22.0
-   Npm at `/usr/bin/npm`: 6.14.6
-   Open Shift V3 CLI at `/usr/local/bin/oc`: 3.11.0
-   Python/3.8.2
-   Selenium at `/opt/selenium/selenium-server-standalone.jar`: 3.141.59
-   XVFB: 2:1.20.8

# Version 2.5.1
-   OS: Ubuntu 16.04
-   Common tools: openssh-client, unzip, wget, curl, git, jq, rsync
-   Ant 1.10.7
-   AWS CLI: aws-cli/1.16.257
-   Azure CLI (`az`): 2.0.74
-   Bower: 1.8.4
-   Cloud Foundry CLI (latest) at `/usr/local/bin/cf`: 6.46.1
-   Firefox at `/usr/bin/firefox`: 68.1.0esr
-   Firefox Geckodriver at `/usr/bin/geckodriver`: v0.25.0
-   gcc (latest): 5.4.0
-   Grunt CLI: 1.3.1
-   Gulp: 4.0.0
-   Java: OpenJDK 8 (latest): 1.8.0_222
-   JMeter (5.1.1) located in `/opt/jmeter/`
-   Kubernetes CLI at `/usr/local/bin/kubectl`: 1.16.1
-   Make (latest): 4.1
-   Maven located in `/usr/share/maven/`: 3.6.2
-   MySQL Client: Ver 14.14 Distrib 5.7.27
-   Node.js at `/usr/bin/nodejs`: 10.16.3
-   Npm at `/usr/bin/npm`: 6.9.0
-   Open Shift V3 CLI at `/usr/local/bin/oc`: 3.11.0
-   Python/2.7.12
-   Selenium at `/opt/selenium/selenium-server-standalone.jar`: 3.141.59
-   XVFB: 2:1.18.4

## About this repository

The automated build is on the [Docker Hub](https://hub.docker.com/lj020326/java-build-tools/).

## Reference

- https://github.com/lden/cloudbees--java-build-tools-dockerfile
- https://github.com/cyrille-leclerc/java-build-tools-dockerfile
- https://github.com/dettonville/java-build-tools-dockerfile

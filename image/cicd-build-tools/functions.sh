#!/bin/bash

# source: https://github.com/cloudbees/java-build-tools-dockerfile/blob/master/functions.sh
# source: https://github.com/SeleniumHQ/docker-selenium/blob/3.0.1-erbium/NodeBase/functions.sh

# https://github.com/SeleniumHQ/docker-selenium/issues/184
function get_server_num() {
  echo $(echo $DISPLAY | sed -r -e 's/([^:]+)?:([0-9]+)(\.[0-9]+)?/\2/')
}

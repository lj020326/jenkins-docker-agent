#!/bin/bash

# source: https://github.com/cloudbees/java-build-tools-dockerfile/blob/master/entry_point.sh

function shutdown {
  kill -s SIGTERM $NODE_PID
  wait $NODE_PID
}

trap shutdown SIGTERM SIGINT

# cloudbees specific: use 'exec "$@"' and not 'wait $NODE_PID'
exec "$@"

#!/bin/bash
#
# This entrypoint is dedicated to start Docker Engine (in Docker)
# For CloudBees Jenkins Enterprise 1.x Agent Templates
# Cf. https://support.cloudbees.com/hc/en-us/articles/115001626487-Customize-entrypoint-on-CJE-Agent-Docker-images

set -e

if [ $# -gt 0 ]
then
  ## Default Docker flag. It can be overwritten by an environment variable
  DOCKER_OPTS="${DOCKER_OPTS:-"--bip=192.168.0.1/24"}"

  if [ "${AUTOCONFIGURE_DOCKER_STORAGE}" = "true" ]
  then
    # Default settings: we let the script autodetect the "best"
    # storage driver for Docker based on the host kernel features
    if [ -f "/proc/filesystems" ]
    then
      ## Best case: we can use overlayFS 2 (overlay2 for Docker)
      if [ "$(grep overlay /proc/filesystems)" ]
      then
        STORAGE_DRIVER="overlay2"
      elif [ "$(grep aufs /proc/filesystems)" ]
      # overlay not available: let's try aufs, the Docker "original" layer FS
      then
        STORAGE_DRIVER="aufs"
      else
        # Other drivers exists: btrfs, zfs, but they need advanced configuration
        # Check https://docs.docker.com/storage/storagedriver/select-storage-driver/
        # We fallback to the worst case, "vfs": slow but works everywhere
#        STORAGE_DRIVER="vfs"
        STORAGE_DRIVER="devicemapper"
      fi
      DOCKER_OPTS+=" --storage-driver ${STORAGE_DRIVER}"
    fi
  fi

  echo "== Starting Docker Engine with the following options: ${DOCKER_OPTS}"
  /usr/local/bin/dockerd-entrypoint.sh ${DOCKER_OPTS} >/docker.log 2>&1 &

  # Wait for Docker to start by checking the TCP socket locally
  ## Wait 1 second to let all process and file handle being created
  echo "== Waiting for Docker Engine process to start"
  sleep 1

  ## Try reaching the unix socket 6 times, waiting 5s between tries
  curl -XGET -sS -o /dev/null --fail \
    --retry 6 --retry-delay 5 \
    --unix-socket /var/run/docker.sock \
    http://DOCKER/_ping || (cat /docker.log && exit 1)

  ## Last check: the _ping endpoint should send "OK" on stdout
  [ "$(curl -sS -X GET --unix-socket /var/run/docker.sock http:/images/_ping)" == "OK" ]

  echo "== Docker Engine started and ready"

  # Load any "tar-gzipped" Docker image from the local cache
  if [ -n "${DOCKER_IMAGE_CACHE_DIR}" ] && [ -d "${DOCKER_IMAGE_CACHE_DIR}" ]
  then
    echo "== Variable 'DOCKER_IMAGE_CACHE_DIR' found and pointing to an existing Directory"
    echo "== Loading following .tar files in Docker:"
    find "${DOCKER_IMAGE_CACHE_DIR}" -type f -name "*.gz" -print \
      -exec sh -c 'gunzip --stdout "$1" | docker load' -- {} \;
  fi

  # second argument is the java command line generated by CJE (passed as a single arg)
  shift
  echo "== Launching the following user-provided command: ${*}"
  exec /bin/sh -c "$@"
fi

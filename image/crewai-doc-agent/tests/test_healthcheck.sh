#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="lj020326/crewai-doc-agent:local-test"
CONTAINER_WORKSPACE="/workspace"

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#SCRIPT_NAME="$(basename "$0")"
DOCKER_BUILD_DIR="$(dirname "${TEST_DIR}")"

HOST_CONFIG="${TEST_DIR}/.crewai-config.yml"
#WORKSPACE_DIR="$(pwd)"

echo "=== Building local test Docker image ==="
#docker build -t "${IMAGE_NAME}" .
#docker build --no-cache -t "${IMAGE_NAME}" "${DOCKER_BUILD_DIR}"
docker build -t "${IMAGE_NAME}" "${DOCKER_BUILD_DIR}"

echo ""
echo "=== Running container healthcheck against local .crewai-config.yml ==="
DOCKER_COMMAND="docker run --rm \
  -v ${HOST_CONFIG}:${CONTAINER_WORKSPACE}/.crewai-config.yml \
  -v /etc/ssl/certs/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt:ro \
  -w ${CONTAINER_WORKSPACE} \
  -e LLM_API_KEY=${LLM_API_KEY:-dummy-key} \
  -e LITELLM_LOCAL_MODEL_COST_MAP=True \
  -e LITELLM_SKIP_MODEL_INFO_QUERY=True \
  -e REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
  -e SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
  ${IMAGE_NAME} crewai-doc-agent -v healthcheck --config .crewai-config.yml"

# Apply standard header redactions to printable log output
DOCKER_COMMAND_MASKED=$(echo "${DOCKER_COMMAND}" | sed -E -e 's/LLM_API_KEY=[^ '\''"]+/LLM_API_KEY=[REDACTED]/g')

echo "${DOCKER_COMMAND_MASKED}"

eval "${DOCKER_COMMAND}"

echo "=== Test completed successfully! ==="

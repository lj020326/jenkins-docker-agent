# Dockerfile - crewai-doc-agent

ARG IMAGE_REGISTRY=docker.io
ARG BASE_IMAGE_LABEL=lj020326/cicd-build-tools:latest
FROM $IMAGE_REGISTRY/$BASE_IMAGE_LABEL

USER root
WORKDIR /app

ENV PIP_ROOT_USER_ACTION=ignore \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

ENV PATH="${VIRTUAL_ENV}/bin:/usr/local/bin:${PATH}"

COPY requirements.txt .
RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

# Install the package itself
COPY crewai_doc_agent/ /app/crewai_doc_agent/
RUN chmod +x /app/crewai_doc_agent/*.py

# Thin wrapper that invokes the package as a module (correct sys.path & __name__)
RUN printf '#!/bin/bash\nexec python3 -u -m crewai_doc_agent.cli "$@"\n' \
        > /usr/local/bin/crewai-doc-agent && \
    chmod +x /usr/local/bin/crewai-doc-agent

ENV PYTHONPATH=/app \
    CREWAI_DISABLE_TELEMETRY=true \
    CREWAI_TELEMETRY_OPT_OUT=true \
    OTEL_SDK_DISABLED=true \
    ANONYMIZED_TELEMETRY=false

# Default working directory for the container image,
# can be overridden via docker run -w /workspace
WORKDIR /workspace

CMD ["--help"]

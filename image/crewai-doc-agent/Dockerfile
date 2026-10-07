# Dockerfile - crewai-doc-agent

ARG IMAGE_REGISTRY=docker.io
ARG BASE_IMAGE_LABEL=lj020326/cicd-build-tools:latest
FROM $IMAGE_REGISTRY/$BASE_IMAGE_LABEL

USER root
WORKDIR /app

ENV PIP_ROOT_USER_ACTION=ignore

COPY requirements.txt .
RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.py

RUN printf '#!/bin/bash\nexec python3 -u /app/scripts/cli.py "$@"\n' > /usr/local/bin/crewai-doc-agent && \
    chmod +x /usr/local/bin/crewai-doc-agent

ENV PYTHONPATH=/app
ENV PATH="/app/scripts:${PATH}"

CMD ["--help"]

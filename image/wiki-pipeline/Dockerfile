# Dockerfile - wiki-pipeline

ARG IMAGE_REGISTRY=docker.io
ARG BASE_IMAGE_LABEL=lj020326/cicd-build-tools:latest
FROM $IMAGE_REGISTRY/$BASE_IMAGE_LABEL

ARG user=jenkins
ARG group=jenkins

USER root

# 2. Setup Application
WORKDIR /app

#==========
# PIP - Install Python dependencies
#==========
## ref: https://github.com/pypa/pip/issues/11179#issuecomment-1152766374
ENV PIP_ROOT_USER_ACTION=ignore

COPY requirements.txt .
RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

# 3. Copy scripts and entrypoint
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.py

# Create wrapper script
RUN printf '#!/bin/bash\nexec python3 -u /app/scripts/cli.py "$@"\n' > /usr/local/bin/wiki-pipeline && \
    chmod +x /usr/local/bin/wiki-pipeline

ENV PYTHONPATH=/app
ENV PATH="/app/scripts:${PATH}"

# drop back to the regular jenkins user - good practice
USER ${user}

CMD ["--help"]

# Testing Guide

This repository provides containerized builds for `ansible-runner`, target across multiple Python and Ansible-core version matrices. This document outlines the testing workflow, linting rules, and local validation steps required to ensure build consistency and container health.

---

## 🛠️ Prerequisites

Before running tests locally, ensure you have the following tools installed on your host machine:

* **Docker** (or Docker Desktop with Buildx enabled)
* **Python 3.10+**
* **pre-commit** (`pip install pre-commit`)
* **hadolint** (Dockerfile linter)
* **shellcheck** (Bash script linter)
* **yamllint** (YAML syntax & structure linter)

---

## 🚀 Quick Start (Local Pre-Commit Checks)

We use `pre-commit` hooks to enforce static code analysis, syntax checking, and security scans across Python, Shell scripts, Dockerfiles, and Ansible metadata.

1. Install git hooks:
   ```bash
   pre-commit install
   ```
2. Run all checks manually across the repository:
   ```bash
   pre-commit run --all-files
   ```

---

## 🔍 Static Code Analysis & Linting

### 1. Dockerfile Linting
To check `image/Dockerfile` against Docker best practices (multi-stage verification, package pinning, layer reduction):

```bash
hadolint image/Dockerfile
```

### 2. Shell Script Validation
All `.sh` helper scripts (e.g., `image/retry_command.sh` and `build-push-images.sh`) are linted with `shellcheck`:

```bash
shellcheck image/retry_command.sh build-push-images.sh
```

### 3. YAML Syntax & Ansible Galaxy Requirements
Validate configuration syntax for `.continue/config.yaml`, `.jenkins/docker-build-config.yml`, and `image/requirements.yml`:

```bash
yamllint .
ansible-lint image/requirements.yml
```

---

## 🐳 Container Build Verification

### Local Single Image Build Test
To test a build locally using default arguments:

```bash
docker build \
  --build-arg ANSIBLE_CORE_VERSION="2.16" \
  --build-arg PYTHON_VERSION="3.12" \
  -t local/ansible-runner:test \
  image/
```

### In-Container Runtime Functional Tests
Once built, verify that critical tools and Python modules (such as the VMware vSphere Automation SDK and Ansible Galaxy collection installations) are present and functional:

```bash
# 1. Verify Python & Ansible versions
docker run --rm local/ansible-runner:test ansible --version

# 2. Verify VMware SDK import
docker run --rm local/ansible-runner:test python3 -c "import com.vmware.vapi.std.errors_client; print('SDK Import Successful')"

# 3. Verify installed Ansible collections
docker run --rm local/ansible-runner:test ansible-galaxy collection list

# 4. Execute included pytest / molecule test utilities
docker run --rm local/ansible-runner:test pytest --version
```

---

## ⚙️ Automated Continuous Integration (CI)

### GitHub Actions Pipeline
The GitHub Actions workflow (`.github/workflows/build-images.yml`) automatically executes on pull requests and pushes to `main`. It builds a test matrix across multiple Python (`3.10`, `3.11`, `3.12`, `3.13`, `3.14`) and Ansible (`2.16` through `2.21`, `latest`) version pairs.

Matrix verification includes:
* Automated multi-arch build capability checks using `QEMU` and `Buildx`.
* Tag generation and image layer caching.

### Jenkins Build Automation
Internal verification runs via `Jenkinsfile` utilizing the shared library (`pipelineAutomationLib`) against `.jenkins/docker-build-config.yml` configuration targets.

---
name: Docker Build Automation
globs: ["**/*.{sh,yml,yaml,github/workflows/**}"]
alwaysApply: true
description: Standards for build scripts and CI
---

# Docker Build Automation Standards

- Make build scripts idempotent and robust
- Support build arguments for flexibility
- Include proper tagging and labeling strategy
- Integrate security scanning (Trivy, Hadolint, etc.)
- Ensure reproducible builds
- Document build process clearly

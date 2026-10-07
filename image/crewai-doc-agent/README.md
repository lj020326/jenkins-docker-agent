# CrewAI Documentation Agent (`crewai-doc-agent`)

Automated, AI-driven documentation and repository analysis agent powered by **CrewAI**, **LiteLLM**, and a robust shared `LLMClient` supporting enterprise proxies, endpoint health checks, and flexible authentication models.

## Architecture & Workflow

The `crewai-doc-agent` packages repository source files into a token-optimized context structure (`save/repository_context.yaml`), performs automated pre-flight connection validation, and delegates technical documentation tasks to specialized CrewAI agents.

```
                      ┌──────────────────────────────────────────────┐
                      │    Repository Source Files (.py, .yml, etc.) │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Stage 1: REPOSITORY PACKAGING                                                            │
│  - Scans workspace, respects .gitignore patterns, ignores binary files, and packages    │
│    clean codebase content into `save/repository_context.yaml`.                           │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Stage 2: LLMCLIENT PRE-FLIGHT & HEALTH CHECK                                             │
│  - Verifies connection against Ollama/vLLM endpoints (/models or /api/tags).             │
│  - Automatically resolves custom CA bundle paths and handles Basic vs Bearer auth.       │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Stage 3: CREWAI EXECUTION PIPELINE                                                       │
│  - Instantiates Principal Technical Documentation Engineer agent with CrewAI LLM wrapper. │
│  - Executes sequential tasks analyzing repository context to generate updated markdown.  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure & Layout

```text
crewai-doc-agent/
├── save/
│   └── repository_context.yaml   <-- Token-optimized packaged repository context
├── scripts/
│   ├── cli.py                    <-- Main CLI entrypoint and Crew orchestration
│   ├── utils.py                  <-- Shared LLMClient, configuration, and health checks
│   └── package_dir.py            <-- Repository tree scanner and YAML packager
├── .crewai-config.yml            <-- Agent and LLM backend configuration
└── Dockerfile
```

## Features

* **Pre-flight Endpoint Health Check:** Automatically pings the LLM provider (`/models` or `/api/tags`) upon startup to fail fast if unreachable.
* **Flexible Authentication Support:** Supports both standard Bearer tokens and HTTP Basic Authentication (with Base64 encoding forwarded via LiteLLM `extra_headers`).
* **Automated CA Bundle Resolution:** Detects corporate container CA certificate bundles (`/etc/ssl/certs/ca-certificates.crt`, etc.) automatically.
* **Token-Optimized Context Packaging:** Scans the codebase while respecting `.gitignore` and generates structured YAML inputs for the agent.

## Available Pipeline Commands

| Command | Description | Key Flags |
| :--- | :--- | :--- |
| `package` | Scans workspace and compiles repository files into context YAML. | `--output` |
| `run` | Executes the pre-flight health check and launches the CrewAI doc workflow. | `--config`, `--verbose` (-v) |

## Quick Start & Usage Example

```bash
# 1. Create configuration file
cp .crewai-config.example.yml .crewai-config.yml

# 2. Package repository context and run agent workflow inside Docker
docker run --rm -v $(pwd):/workspace -w /workspace \
  lj020326/crewai-doc-agent:latest \
    python3 scripts/package_dir.py --output save/repository_context.yaml && \
    python3 scripts/cli.py run --verbose
```

## Docker Image

```bash
lj020326/crewai-doc-agent:latest
```

Built with:
- Python 3.12-slim
- CrewAI + LiteLLM + Ollama support
- Secure containerized networking and cert store integration

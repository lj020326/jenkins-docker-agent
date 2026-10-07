# CrewAI Documentation Agent (`crewai-doc-agent`)

Automated, AI-driven documentation and repository analysis agent powered by **CrewAI**, **LiteLLM**, and a robust shared `LLMClient` supporting enterprise proxies, endpoint health checks, and flexible authentication models.

## Architecture & Workflow

The `crewai-doc-agent` uses specialized multi-agent crews (`crew.py`) driven by a CLI entrypoint (`cli.py`). Agents utilize custom tools like the repository packaging utility (`package_dir.py`) to generate token-optimized context files (`.package_dir.context.yml`) complete with rich execution metadata before performing documentation and architectural code reviews.

```
                      ┌──────────────────────────────────────────────┐
                      │    Repository Source Files (.py, .yml, etc.) │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Stage 1: LLMCLIENT PRE-FLIGHT & HEALTH CHECK                                             │
│  - Verifies connection against Ollama/vLLM endpoints (/models or /api/tags).             │
│  - Automatically resolves custom CA bundle paths and handles Basic vs Bearer auth.       │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Stage 2: MULTI-AGENT CREW EXECUTION                                                      │
│  - Repository Context Analyst agent packages code via tool into .package_dir.context.yml │
│  - Senior Code Reviewer agent analyzes structure and generates documentation/reports.    │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Stage 3: DOCUMENTATION & REPORTING                                                       │
│  - Outputs structured Markdown documentation and architectural review reports.           │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure & Layout

```text
crewai-doc-agent/
├── .package_dir.context.yml      <-- Token-optimized packaged repository context & metadata
├── scripts/
│   ├── agents/
│   │   └── package_tool.py       <-- CrewAI tool wrapper for package_dir.py
│   ├── cli.py                    <-- Main CLI entrypoint & LLMClient health check
│   ├── crew.py                   <-- Modular multi-agent crew definition (run_crew)
│   ├── package_dir.py            <-- Repository tree scanner & YAML packager
│   └── utils.py                  <-- Shared LLMClient, configuration, and health checks
├── .crewai-config.yml            <-- Agent and LLM backend configuration
└── Dockerfile
```

## Features

* **Pre-flight Endpoint Health Check:** Automatically pings the LLM provider (`/models` or `/api/tags`) upon startup to fail fast if unreachable.
* **Flexible Authentication Support:** Supports both standard Bearer tokens and HTTP Basic Authentication (with Base64 encoding forwarded via LiteLLM `extra_headers`).
* **Modular Multi-Agent Architecture:** Clean separation of concerns with `cli.py` managing configuration/health checks and `crew.py` exposing a modular `run_crew()` function.
* **Tool-Driven Repository Packaging:** Custom CrewAI tools execute `package_dir.py` to generate `.package_dir.context.yml` locally with embedded git commit hashes, branch info, execution PWD, and directory trees.

## Available Pipeline Commands

| Command | Description | Key Flags |
| :--- | :--- | :--- |
| `run` | Executes the pre-flight health check and launches the CrewAI multi-agent crew workflow. | `--config`, `--verbose` (-v) |

## Quick Start & Usage Example

```bash
# 1. Create configuration file
cp .crewai-config.example.yml .crewai-config.yml

# 2. Run agent workflow inside Docker container
docker run --rm -v $(pwd):/workspace -w /workspace \
  lj020326/crewai-doc-agent:latest \
    crewai-doc-agent run --verbose
```

## Docker Image

```bash
lj020326/crewai-doc-agent:latest
```

Built with:
- Python 3.12-slim
- CrewAI + LiteLLM + Ollama support
- Secure containerized networking and cert store integration

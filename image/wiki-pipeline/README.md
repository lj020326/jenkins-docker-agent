# Wiki Pipeline - LLM-Powered Documentation Generator

Automated, high-quality Markdown wiki generation for Ansible repositories using Ollama + LiteLLM.

## Features

- Harvests legacy Markdown files (`docs/`, `README.md`, `TESTING.md`, etc.)
- Smart ingestion of Ansible YAML files (`roles/`, `playbooks/`, etc.) → one professional page per role
- Configurable LLM prompts, temperature, max_tokens, timeout
- Respects `.gitignore` and custom `roles_ignore`
- Priority roles and categorized index in top-level `wiki/README.md`
- `--changed-only` mode for fast incremental runs
- Fully configurable via `.wiki-config.yml`

## Quick Start

```bash
# 1. Create config file (copy from example below)
cp .wiki-config.example.yml .wiki-config.yml

# 2. Run the pipeline
docker run --rm -v $(pwd):/workspace -w /workspace \
  lj020326/wiki-pipeline:latest \
  wiki-pipeline ingest --verbose
```

## Configuration (.wiki-config.yml)

```YAML
wiki:
  output_dir: "wiki"
  title: "Ansible Datacenter Wiki"
  subtitle: "Central documentation for all roles and automation"

  roles_ignore:
    - bootstrap_aibrix
    - bootstrap_solr_cloud

  priority_roles:
    - bootstrap_docker
    - bootstrap_linux_core
    - bootstrap_kubernetes
    - deploy_vm

  llm:
    temperature: 0.25
    max_tokens: 4096
    timeout: 600

  role_prompt:
    prefix: |
      You are an expert Ansible architect...
    suffix: |
      Important notes:
      - Double-underscore variables are internal only.

  compile_prompt: { ... }
  lint_prompt: { ... }
  qa_prompt: { ... }
```

## Available Commands

| Command          | Description                               | Key Flags                 |
|------------------|-------------------------------------------|---------------------------|
| harvest          | Copy legacy .md files to raw/legacy-docs/ | "--output, --verbose"     |
| ingest           | Generate role documentation from YAML     | "--limit, --changed-only" |
| compile          | Improve raw Markdown → wiki/              | --verbose                 |
| lint             | LLM-powered quality check + report        | "--fix, --verbose"        |
| index            | Generate top-level wiki/README.md index   | --verbose                 |
| qa               | Generate FAQ section                      | --verbose                 |
| generate-outputs | Placeholder for slides/charts             | --verbose                 |

## Full Pipeline Example (Recommended)

```Bash
wiki-pipeline harvest --verbose
wiki-pipeline ingest --changed-only --verbose
wiki-pipeline compile --verbose
wiki-pipeline lint --fix --verbose
wiki-pipeline index --verbose
```

## Jenkins Integration

See [`.jenkins/runWikiPipeline.groovy`](https://github.com/lj020326/pipeline-automation-lib/blob/main/vars/runWikiPipeline.groovy) for the full CI/CD pipeline that:

- Runs inside the Docker container 
- Uses --changed-only for speed 
- Commits changes with [skip ci]
- Respects internal LLM endpoint

## Docker Image

```Bash
lj020326/wiki-pipeline:latest
```

Built with:

- Python 3.12-slim 
- LiteLLM + Ollama support 
- Git, graphviz, ssh-agent 
- All scripts included

## Example .wiki-config

In your ansible git repository root:
```shell
cp .wiki-config.example.yml .wiki-config.yml
```

Then edit .wiki-config.yml to match your preferred roles_ignore / priority_roles

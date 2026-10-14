#!/usr/bin/env python3
# scripts/ingest_ansible_yaml.py
"""
Single-Pass Ansible Role Ingestion.
Extracts role source code, integrates index insights, and generates production-ready wiki pages.
"""

import argparse
import litellm
import logging
import pathspec
from pathlib import Path

from .index import generate_wiki_index
from .utils import (
    IndexHelper,
    LLMClient,
    ensure_dir,
    get_content_fingerprint,
    get_effective_paths,
    is_ignored,
    load_config,
    load_state,
    render_yaml_prompt,
    save_state,
    setup_logging,
    strip_code_fences,
)

# Create a module-level logger
log = logging.getLogger(__name__)


def get_role_name(yaml_path: Path) -> str:
    parts = yaml_path.parts
    if "roles" in parts:
        idx = parts.index("roles")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return yaml_path.parent.name


def summarize_role(
    llm_client: LLMClient,
    role_dir: Path,
    repo_root: Path,
    config: dict,
    index_helper: IndexHelper,
) -> dict:
    role_name = get_role_name(role_dir)
    rel_role_path = role_dir.relative_to(repo_root)
    wiki_config = config.get("wiki", {})
    wiki_dir = wiki_config.get("wiki_dir", "wiki")

    # llm_config = wiki_config.get("llm", {})
    role_prompt = wiki_config.get("role_prompt", {})

    files_content = {}
    # characters per file to avoid huge prompts
    max_file_size = 2500

    # for subdir in ["defaults", "vars", "tasks", "meta", "handlers", "templates", "files"]:
    for subdir in ["defaults", "tasks", "meta", "handlers"]:
        sub_path = role_dir / subdir
        if not sub_path.exists():
            continue
        for yml_file in sorted(sub_path.rglob("*.yml")) + sorted(
            sub_path.rglob("*.yaml")
        ):
            try:
                # content = yml_file.read_text(encoding="utf-8")
                lines = [
                    line
                    for line in yml_file.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.strip().startswith("#")
                ]
                content = "\n".join(lines)

                # Truncate very large files (especially tasks/main.yml)
                if len(content) > max_file_size * 2:
                    content = (
                        content[:max_file_size] + "\n... [truncated - large file] ..."
                    )
                files_content[f"{subdir}/{yml_file.relative_to(sub_path)}"] = content
            except Exception as e:
                log.debug(f"Could not read {yml_file}: {e}")

    files_section = "\n\n".join(
        [
            f"### {fname}\n```yaml\n{content}\n```"
            for fname, content in files_content.items()
        ]
    )

    # Check for and read an existing role README.md file
    readme_path = role_dir / "README.md"
    readme_section = ""
    if readme_path.exists():
        try:
            readme_content = readme_path.read_text(encoding="utf-8")
            if len(readme_content) > max_file_size * 2:
                readme_content = (
                    readme_content[: max_file_size * 2]
                    + "\n... [truncated - large README] ..."
                )
            readme_section = (
                f"\n\n### Existing README.md\n````markdown\n{readme_content}\n````"
            )
        except Exception as e:
            log.debug(f"Could not read README.md for {role_name}: {e}")

    # Use Indexer to find actual usages across repository
    usages = index_helper.find_role_dependents(role_name)
    usage_section = ""
    if usages:
        usage_section = (
            "\n\n### Discovered Repos/Playbooks Using This Role:\n"
            + "\n".join([f"- `{u}`" for u in usages[:10]])
        )

    messages = render_yaml_prompt(
        role_prompt,
        rel_role_path=rel_role_path,
        role_name=role_name,
        files_section=files_section,
        readme_section=readme_section,
        usage_section=usage_section,
    )

    log.info(
        f"   Generating documentation for role: {role_name} ({len(files_content)} files)"
    )

    try:
        md_content = llm_client.get_response(messages)

        # Strip outer markdown code fences if the LLM wrapped the response
        md_content = strip_code_fences(md_content)

        # Ensure frontmatter exists
        if not md_content.strip().startswith("---"):
            frontmatter = f"""---
title: "{role_name.replace('_', ' ').title()} Role"
role: {rel_role_path}
category: Roles
type: ansible-role
tags: [ansible, role, {role_name}]
---

"""
            md_content = frontmatter + md_content

        target_path = f"{wiki_dir}/roles/{role_name}.md"
        return {
            "content": md_content,
            "target_path": target_path,
            "role_name": role_name,
        }

    except Exception as e:
        log.error(f"LLM Error: {type(e).__name__}: {e}")
        raise


def ingest_ansible_yaml(
    llm_client: LLMClient,
    repo_root: Path,
    limit: int = None,
    changed_only: bool = False,
    config_path: str = ".wiki-config.yml",
):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    paths = get_effective_paths(wiki_config)

    # 1. Standardized directory resolution
    effective_wiki_dir = paths["wiki_dir"]
    state_path = paths["state_file"]

    # 2. Safety: Ensure role output dir exists before processing
    role_output_dir = repo_root / effective_wiki_dir / "roles"
    ensure_dir(role_output_dir)

    index_helper = IndexHelper(repo_root)

    state = load_state(state_path)
    if "ingest" not in state:
        state["ingest"] = {}

    ingest_ignore = wiki_config.get("ingest_ignore", [])
    log.debug(f"ingest_ignore={ingest_ignore}")

    # Pre-compile the ignore patterns for performance
    ignore_spec = (
        pathspec.PathSpec.from_lines("gitwildmatch", ingest_ignore)
        if ingest_ignore
        else None
    )

    # Discovery logic remains focused on the roles/ directory
    all_roles = sorted((repo_root / "roles").glob("*/"))
    processed = 0

    log.info("🔍 Analyzing roles for documentation updates...")

    for role_path in all_roles:
        if limit and processed >= limit:
            log.info(f"   ⏭️  Processed file limit hit => {processed}")
            break

        role_id = role_path.name

        # POLISH: Replaced redundant is_dir() check with a single clean trace
        log.debug(f"Inspecting role: {role_id}")

        # 3. Filter check
        if is_ignored(role_path, ingest_ignore, spec=ignore_spec):
            log.debug(f"   ⏭️  Skipping ignored role: {role_id}")
            continue

        # 4. Fingerprinting
        current_hash = get_content_fingerprint(role_path, ignore_patterns=ingest_ignore)
        state_hash = state["ingest"].get(role_id)

        if changed_only and state_hash == current_hash:
            log.debug(f"   ⏭️  Skipping {role_id} (unchanged)")
            continue

        log.info(f"   📝 Processing: {role_id}")

        try:
            # 5. Summarization logic
            result = summarize_role(
                llm_client, role_path, repo_root, config, index_helper
            )

            # 6. Polished File Writing: Use the established paths
            target_md = role_output_dir / f"{result['role_name']}.md"
            target_md.write_text(result["content"], encoding="utf-8")

            # Update state with the clean fingerprint
            state["ingest"][role_id] = current_hash

            log.debug(f"   ✓ Generated {target_md.relative_to(repo_root)}")
            processed += 1
        except litellm.InternalServerError as e:
            log.error(f"   💥 Fatal LLM Internal Server Error for {role_id}: {e}")
            raise
        except (ConnectionError, TimeoutError) as e:
            log.error(f"   💥 Fatal Connection/Timeout Error for {role_id}: {e}")
            raise
        except Exception as e:
            log.error(f"   ❌ Failed to process {role_id}: {e}")
            continue

    # 7. Post-process
    if processed > 0:
        generate_wiki_index(repo_root, config_path=config_path)
        save_state(state_path, state)

    log.info(f"✅ Successfully processed {processed} Ansible roles.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Ansible YAML files into wiki")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument("--debug-llm", action="store_true")
    parser.add_argument("--changed-only", action="store_true")
    parser.add_argument("--config", default=".wiki-config.yml")
    args = parser.parse_args()

    # Initialize the global logging config once
    setup_logging(args.verbose, debug_llm=args.debug_llm)

    # Instantiate LLM setup/config once upon startup
    llm_client = LLMClient(
        config_path=args.config,
        overrides={
            "debug_llm": args.debug_llm,
        },
    )

    ingest_ansible_yaml(
        llm_client, Path("."), limit=args.limit, changed_only=args.changed_only
    )

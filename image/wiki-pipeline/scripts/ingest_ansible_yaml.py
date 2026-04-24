#!/usr/bin/env python3
# scripts/ingest_yaml.py
"""
Smart YAML ingestion for Ansible repositories.
Creates one high-quality Markdown file per role.
Supports --changed-only mode.
"""

import argparse
import json
import logging
from pathlib import Path

from .index import generate_wiki_index
from .utils import ensure_dir, get_role_fingerprint, load_config, is_ignored, LLMClient


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
        verbose: int = 0
) -> dict:
    role_name = get_role_name(role_dir)
    rel_role_path = role_dir.relative_to(repo_root)
    wiki_config = config.get("wiki", {})
    # llm_config = wiki_config.get("llm", {})
    role_prompt = wiki_config.get("role_prompt", {})

    files_content = {}
    max_file_size = 2500  # characters per file to avoid huge prompts

    # for subdir in ["defaults", "vars", "tasks", "meta", "handlers", "templates", "files"]:
    for subdir in ["defaults", "tasks", "meta", "handlers"]:
        sub_path = role_dir / subdir
        if not sub_path.exists():
            continue
        for yml_file in sorted(sub_path.rglob("*.yml")) + sorted(sub_path.rglob("*.yaml")):
            try:
                # content = yml_file.read_text(encoding="utf-8")
                lines = [l for l in yml_file.read_text().splitlines()
                         if l.strip() and not l.strip().startswith("#")]
                content = "\n".join(lines)

                # Truncate very large files (especially tasks/main.yml)
                if len(content) > max_file_size * 2:
                    content = content[:max_file_size] + "\n... [truncated - large file] ..."
                files_content[f"{subdir}/{yml_file.name}"] = content
            except Exception:
                pass

    files_section = "\n\n".join([f"### {fname}\n```yaml\n{content}\n```"
                               for fname, content in files_content.items()])

    prompt = (
        (role_prompt.get("prefix", "") or "") +
        f"\nRole Path: {rel_role_path}\n\n{files_section}\n\n" +
        (role_prompt.get("suffix", "") or "")
    )

    print(f"   Generating documentation for role: {role_name} ({len(files_content)} files)")

    try:
        md_content = llm_client.get_response(prompt)

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

        output_dir = wiki_config.get("output_dir", "wiki")
        target_path = f"{output_dir}/roles/{role_name}.md"

        return {
            "content": md_content,
            "target_path": target_path,
            "role_name": role_name
        }

    except Exception as e:
        # Log it if you want, but re-raise so the caller knows it failed
        logging.error(f"LLM Error: {type(e).__name__}: {e}")
        raise


def ingest_ansible_yaml(
        llm_client: LLMClient,
        repo_root: Path,
        limit: int = None,
        changed_only: bool = False,
        verbose: int = 0,
        config_path: str = ".wiki-config.yml"
):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    output_dir = wiki_config.get("output_dir", "wiki")
    ingest_ignore = wiki_config.get("ingest_ignore", [])

    ensure_dir(repo_root / output_dir / "roles")

    fingerprint_file = Path(llm_client.config['wiki']['output_dir']) / ".hashes.json"

    # Load existing hashes
    old_hashes = {}
    if fingerprint_file.exists():
        old_hashes = json.loads(fingerprint_file.read_text())

    print(f"   ⏭️  Updating role fingerprints: {fingerprint_file}")

    new_hashes = {}
    roles_to_process = []
    all_roles = sorted((repo_root / "roles").glob("*/"))

    for role_path in all_roles:
        if role_path.is_dir():
            if verbose >= 2:
                print(f"DEBUG: Inspecting role: {role_path.name}", flush=True)

        # if should_ignore_path(role_path, ingest_ignore):
        if is_ignored(role_path, ingest_ignore):
            if verbose >= 2:
                print(f"   ⏭️  Skipping ignored path: {role_path.name}")
            continue

        current_hash = get_role_fingerprint(role_path)
        new_hashes[role_path.name] = current_hash

        if changed_only:
            if old_hashes.get(role_path.name) != current_hash:
                roles_to_process.append(role_path)
        else:
            roles_to_process.append(role_path)

    print("Ingesting roles...")

    processed = 0
    for role_dir in roles_to_process:
        if limit and processed >= limit:
            break

        if verbose:
            print(f"   ⏭️  Ingesting role path: {role_dir.name}")

        try:
            result = summarize_role(
                llm_client,
                role_dir,
                repo_root,
                config,
                verbose=verbose
            )

            target_md = repo_root / result["target_path"]
            ensure_dir(target_md.parent)

            target_md.write_text(result["content"], encoding="utf-8")
            print(f"   ✓ Generated {target_md.relative_to(repo_root)}")
            processed += 1
        except Exception as e:
            print(f"   Skipping {role_dir} due to error: {e}")
            # Optionally continue to the next file
            continue

    # Always regenerate the top-level index after ingest
    generate_wiki_index(repo_root, verbose=verbose, config_path=config_path)

    # Save updated hashes after successful run
    fingerprint_file.write_text(json.dumps(new_hashes, indent=2))

    print(f"\n✅ Successfully processed {processed} Ansible roles into {output_dir}/roles/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Ansible YAML files into wiki")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument("--debug-llm", action="store_true")
    parser.add_argument("--changed-only", action="store_true")
    parser.add_argument("--config", default=".wiki-config.yml")
    args = parser.parse_args()

    # Instantiate LLM setup/config once upon startup
    llm_client = LLMClient(
        config_path=args.config,
        overrides={
            "model": args.model,
            "api_base": args.api_base,
            "provider": args.provider,
            "debug_llm": args.debug_llm
        }
    )

    ingest_ansible_yaml(
        llm_client,
        Path("."),
        limit=args.limit,
        verbose=args.verbose,
        changed_only=args.changed_only
    )

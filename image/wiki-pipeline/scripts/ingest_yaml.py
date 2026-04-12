#!/usr/bin/env python3
# scripts/ingest_yaml.py
"""
Smart YAML ingestion for Ansible repositories.
Creates one high-quality Markdown file per role.
Supports --changed-only mode.
"""

import argparse
import subprocess
from pathlib import Path
import yaml
from scripts.utils import get_llm_response, ensure_dir, is_ignored_by_git, load_config
from scripts.index import generate_wiki_index


def get_changed_roles(repo_root: Path):
    """Return list of role directories that have changed YAML files"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--", "roles/*/"],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        changed_paths = [Path(f) for f in result.stdout.strip().splitlines() if f]

        changed_roles = set()
        for p in changed_paths:
            if "roles" in p.parts:
                idx = p.parts.index("roles")
                if idx + 1 < len(p.parts):
                    changed_roles.add(p.parts[idx + 1])

        return list(changed_roles)
    except Exception as e:
        print(f"Warning: Could not detect changed roles: {e}")
        return []


def get_role_name(yaml_path: Path) -> str:
    parts = yaml_path.parts
    if "roles" in parts:
        idx = parts.index("roles")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return yaml_path.parent.name


def summarize_role(
        role_dir: Path,
        repo_root: Path,
        config: dict,
        verbose: bool = False,
        model: str = None,
        api_base: str = None,
        api_key: str = None
) -> dict:
    role_name = get_role_name(role_dir)
    rel_role_path = role_dir.relative_to(repo_root)
    wiki_config = config.get("wiki", {})
    llm_config = wiki_config.get("llm", {})
    role_prompt = wiki_config.get("role_prompt", {})

    files_content = {}
    for subdir in ["defaults", "vars", "tasks", "meta", "handlers", "templates", "files"]:
        sub_path = role_dir / subdir
        if sub_path.exists():
            for yml_file in sorted(sub_path.rglob("*.yml")) + sorted(sub_path.rglob("*.yaml")):
                try:
                    content = yml_file.read_text(encoding="utf-8")[:3000]
                    files_content[f"{subdir}/{yml_file.name}"] = content
                except Exception:
                    pass

    files_section = "\n\n".join([f"### {fname}\n```yaml\n{content}\n```" for fname, content in files_content.items()])

    prompt = (
        (role_prompt.get("prefix", "") or "") +
        f"\nRole Path: {rel_role_path}\n\n{files_section}\n\n" +
        (role_prompt.get("suffix", "") or "")
    )

    if verbose:
        print(f"   Generating documentation for role: {role_name}")

    md_content = get_llm_response(
        prompt,
        model=model,
        api_base=api_base,
        api_key=api_key,
        temperature=llm_config.get("temperature"),
        max_tokens=llm_config.get("max_tokens"),
        timeout=llm_config.get("timeout"),
        verbose=verbose
    )

    # Ensure frontmatter exists
    if not md_content.strip().startswith("---"):
        frontmatter = f"""---
title: "{role_name.replace('_', ' ').title()} Role"
original_role: {rel_role_path}
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


def ingest_ansible_yaml(
        repo_root: Path,
        limit: int = None,
        verbose: bool = False,
        model: str = None,
        api_base: str = None,
        api_key: str = None,
        changed_only: bool = False,
        config_path: str = ".wiki-config.yml"
):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    output_dir = wiki_config.get("output_dir", "wiki")
    roles_ignore = wiki_config.get("roles_ignore", [])

    ensure_dir(repo_root / output_dir / "roles")

    if changed_only:
        changed_role_names = get_changed_roles(repo_root)
        if verbose:
            print(f"Changed-only mode: Found {len(changed_role_names)} changed roles")
        role_dirs = [repo_root / "roles" / name for name in changed_role_names if (repo_root / "roles" / name).exists()]
    else:
        role_dirs = []
        for role_dir in sorted((repo_root / "roles").glob("*/")):
            if role_dir.is_dir() and not role_dir.name.startswith("."):
                role_dirs.append(role_dir)

    processed = 0
    for role_dir in role_dirs:
        if role_dir.name in roles_ignore:
            if verbose:
                print(f"   ⏭️  Skipping ignored role: {role_dir.name}")
            continue

        if limit and processed >= limit:
            break

        result = summarize_role(
            role_dir,
            repo_root,
            config,
            verbose=verbose,
            model=model,
            api_base=api_base,
            api_key=api_key)

        target_md = repo_root / result["target_path"]
        ensure_dir(target_md.parent)

        target_md.write_text(result["content"], encoding="utf-8")
        print(f"   ✓ Generated {target_md.relative_to(repo_root)}")
        processed += 1

    # Always regenerate the top-level index after ingest
    generate_wiki_index(repo_root, verbose=verbose, config_path=config_path)

    print(f"\n✅ Successfully processed {processed} Ansible roles into {output_dir}/roles/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Ansible YAML files into wiki")
    parser.add_argument("--limit", type=int, help="Limit number of roles to process")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--changed-only", action="store_true")
    parser.add_argument("--config", default=".wiki-config.yml")
    args = parser.parse_args()

    ingest_ansible_yaml(
        Path("."),
        limit=args.limit,
        verbose=args.verbose,
        changed_only=args.changed_only,
        config_path=args.config
    )

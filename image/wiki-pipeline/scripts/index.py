#!/usr/bin/env python3
# scripts/index.py
"""
Builds the top-level wiki/README.md using .wiki-config.yml
"""

import argparse
from pathlib import Path
import yaml
from collections import defaultdict
from scripts.utils import ensure_dir


def load_config(config_path: str = ".wiki-config.yml"):
    path = Path(config_path)
    if not path.exists():
        print(f"Warning: {config_path} not found. Using defaults.")
        return {"wiki": {"output_dir": "wiki"}}
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Could not load {config_path}: {e}")
        return {"wiki": {"output_dir": "wiki"}}


def generate_wiki_index(repo_root: Path, verbose: bool = False, config_path: str = ".wiki-config.yml"):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    wiki_dir = repo_root / wiki_config.get("output_dir", "wiki")
    ensure_dir(wiki_dir)

    role_files = sorted((wiki_dir / "roles").glob("*.md"))

    index_content = f"# {wiki_config.get('title', 'Ansible Wiki')}\n\n"
    index_content += f"{wiki_config.get('subtitle', '')}\n\n"
    index_content += f"{wiki_config.get('description', '')}\n\n"

    # Priority roles
    priority_roles = wiki_config.get("priority_roles", [])
    index_content += "## Priority Roles\n\n"
    for role_md in role_files:
        role_name = role_md.stem
        if role_name in priority_roles:
            rel_link = role_md.relative_to(wiki_dir)
            index_content += f"- **[{role_name}]({rel_link})** — Core role\n"

    index_content += "\n## All Roles by Category\n\n"

    # Categories
    categories = defaultdict(list)
    if "categories" in wiki_config:
        for cat_name, cat_data in wiki_config["categories"].items():
            for role_name in cat_data.get("roles", []):
                categories[cat_name].append(role_name)

    # Remaining roles
    default_cat = wiki_config.get("default_category", "other")
    for role_md in role_files:
        role_name = role_md.stem
        found = any(role_name in lst for lst in categories.values())
        if not found:
            categories[default_cat].append(role_name)

    # Render categories
    for cat_name, role_list in sorted(categories.items()):
        title = wiki_config.get("default_category_title", "Other Roles") if cat_name == default_cat else \
                wiki_config.get("categories", {}).get(cat_name, {}).get("title", cat_name.title())
        index_content += f"### {title}\n\n"
        for role_name in sorted(role_list):
            role_md = wiki_dir / "roles" / f"{role_name}.md"
            if role_md.exists():
                rel_link = role_md.relative_to(wiki_dir)
                index_content += f"- [{role_name}]({rel_link})\n"
        index_content += "\n"

    # Write the main index
    (wiki_dir / "README.md").write_text(index_content, encoding="utf-8")
    (wiki_dir / "index.md").write_text(index_content, encoding="utf-8")

    print(f"✅ Generated {wiki_dir}/README.md with {len(role_files)} roles")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--config", default=".wiki-config.yml")
    args = parser.parse_args()
    generate_wiki_index(Path("."), verbose=args.verbose, config_path=args.config)

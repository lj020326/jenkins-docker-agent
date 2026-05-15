#!/usr/bin/env python3
# scripts/index.py
"""
Builds the top-level wiki/README.md and index.md using .wiki-config.yml.
Final convergence point for Structural and Contextual documentation streams.
"""

import argparse
import logging
from pathlib import Path
from collections import defaultdict

from .utils import ensure_dir, load_config, setup_logging, get_effective_paths

# Create a module-level logger
log = logging.getLogger(__name__)


def generate_wiki_index(
        repo_root: Path,
        config_path: str = ".wiki-config.yml"
):
    # 1. Setup paths and config using the standardized utility
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    paths = get_effective_paths(wiki_config)

    wiki_dir = repo_root / paths["wiki_dir"]
    roles_dir = wiki_dir / "roles"
    ensure_dir(wiki_dir)

    # 2. Identify all generated role documentation files
    role_files = sorted(roles_dir.glob("*.md"))
    active_role_names = {f.stem for f in role_files}

    # Initialize content with header information
    index_content = f"# {wiki_config.get('title', 'Ansible Wiki')}\n\n"
    index_content += f"{wiki_config.get('subtitle', '')}\n\n"
    index_content += f"{wiki_config.get('description', '')}\n\n"

    # 3. Handle Priority Roles Section
    log.debug("   ⏭️  Processing Priority roles")
    priority_roles = wiki_config.get("priority_roles", [])
    if priority_roles:
        index_content += "## Priority Roles\n\n"
        for role_name in priority_roles:
            role_md = roles_dir / f"{role_name}.md"
            if role_md.exists():
                rel_link = role_md.relative_to(wiki_dir)
                index_content += f"- **[{role_name}]({rel_link})** — Core role\n"
        index_content += "\n"

    index_content += "## All Roles by Category\n\n"

    # 4. Categorization Logic
    categories = defaultdict(list)
    assigned_roles = set()

    # Map roles based on config categories
    if "categories" in wiki_config:
        log.debug("   ⏭️  Mapping roles to defined categories")
        for cat_name, cat_data in wiki_config["categories"].items():
            for role_name in cat_data.get("roles", []):
                if role_name in active_role_names:
                    categories[cat_name].append(role_name)
                    assigned_roles.add(role_name)

    # 5. Handle Remaining Roles (Default Category)
    log.debug("   ⏭️  Assigning remaining roles to default category")
    default_cat = wiki_config.get("default_category", "other")
    for role_name in active_role_names:
        if role_name not in assigned_roles:
            categories[default_cat].append(role_name)

    # 6. Render Categories Section
    log.debug("   ⏭️  Rendering categories to index")
    for cat_name in sorted(categories.keys()):
        role_list = categories[cat_name]
        if not role_list:
            continue

        # Get category title from config or format the slug
        title = wiki_config.get("default_category_title", "Other Roles") if cat_name == default_cat else \
            wiki_config.get("categories", {}).get(cat_name, {}).get("title", cat_name.replace('_', ' ').title())

        index_content += f"### {title}\n"

        # Add category description if available
        cat_desc = wiki_config.get("categories", {}).get(cat_name, {}).get("description", "")
        if cat_desc:
            index_content += f"*{cat_desc}*\n\n"
        else:
            index_content += "\n"

        for role_name in sorted(role_list):
            role_md = roles_dir / f"{role_name}.md"
            rel_link = role_md.relative_to(wiki_dir)
            index_content += f"- [{role_name}]({rel_link})\n"
        index_content += "\n"

    # 7. Write final artifacts
    (wiki_dir / "README.md").write_text(index_content, encoding="utf-8")
    (wiki_dir / "index.md").write_text(index_content, encoding="utf-8")

    log.info(f"✅ Generated convergence index at {wiki_dir}/README.md with {len(active_role_names)} roles")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument("--config", default=".wiki-config.yml")
    args = parser.parse_args()

    # Initialize the global logging config once
    setup_logging(args.verbose)

    generate_wiki_index(
        Path("."),
        config_path=args.config
    )

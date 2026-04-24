#!/usr/bin/env python3
# scripts/harvest_legacy.py
import argparse
from pathlib import Path
import shutil
from datetime import datetime
from .utils import add_frontmatter, ensure_dir, is_ignored_by_git, load_config, is_ignored


def harvest_legacy(
        root_dir: Path,
        verbose: int = 0,
        config_path: str = ".wiki-config.yml"
):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})

    # Config override with proper Path conversion
    output_dir_name = wiki_config.get("output_dir", "wiki")
    harvest_dir_name = wiki_config.get("harvest_dir", "raw/legacy-docs")

    final_harvest_dir = Path(harvest_dir_name)
    harvest_ignore = wiki_config.get("harvest_ignore", [])

    if verbose >= 1:
        print(f"   Harvesting into: {final_harvest_dir}")

    ensure_dir(final_harvest_dir)
    md_count = 0

    for md_file in sorted(root_dir.rglob("*.md")):
        # 1. Prevent self-harvesting:
        # Check if the current file is inside the output directory
        if final_harvest_dir in md_file.parents or md_file.name == final_harvest_dir.name:
            if verbose >= 2:
                print(f"  Skipping output directory: {md_file}")
            continue

        # 2. ignore logic
        # Skip common temp and output dirs
        if any(exclude in md_file.parts for exclude in
               [".git", str(final_harvest_dir), output_dir_name, "outputs", "__pycache__"]):
            continue

        # Skip configured ignore dirs
        # Get path relative to the harvest root
        rel_path = md_file.relative_to(root_dir)
        if is_ignored(rel_path, harvest_ignore):
            if verbose >= 2:
                print(f"   ⏭️  Ignored by harvest_ignore: {md_file.relative_to(root_dir)}")
            continue

        # Respect .gitignore
        if is_ignored_by_git(md_file, root_dir):
            if verbose >= 2:
                print(f"   ⏭️  Ignored by .gitignore: {md_file.relative_to(root_dir)}")
            continue

        relative = md_file.relative_to(root_dir)
        target = final_harvest_dir / relative
        ensure_dir(target.parent)

        # Copy file
        shutil.copy2(md_file, target)

        # Add frontmatter
        content = target.read_text(encoding="utf-8")
        metadata = {
            "original_path": str(relative),
            "harvested_date": datetime.utcnow().isoformat(),
            "source_type": "legacy_markdown"
        }
        target.write_text(add_frontmatter(content, metadata), encoding="utf-8")
        md_count += 1

        if verbose >= 1:
            print(f"   Harvested: {relative}")

    print(f"✅ Harvested {md_count} markdown files into {final_harvest_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument("--config", default=".wiki-config.yml")
    args = parser.parse_args()

    harvest_legacy(
        args.root,
        verbose=args.verbose,
        config_path=args.config
    )

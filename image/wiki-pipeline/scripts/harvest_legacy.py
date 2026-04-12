#!/usr/bin/env python3
# scripts/harvest_legacy.py
import argparse
from pathlib import Path
import shutil
from datetime import datetime
from scripts.utils import add_frontmatter, ensure_dir, is_ignored_by_git


def harvest_legacy(root_dir: Path, raw_legacy_dir: Path, verbose: bool = False):
    ensure_dir(raw_legacy_dir)
    md_count = 0

    for md_file in sorted(root_dir.rglob("*.md")):
        # Skip common temp dirs
        if any(exclude in md_file.parts for exclude in [".git", "raw", "wiki", "outputs", "__pycache__"]):
            continue

        # Respect .gitignore
        if is_ignored_by_git(md_file, root_dir):
            if verbose:
                print(f"   ⏭️  Ignored by .gitignore: {md_file.relative_to(root_dir)}")
            continue

        relative = md_file.relative_to(root_dir)
        target = raw_legacy_dir / relative
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

        if verbose:
            print(f"   Harvested: {relative}")

    print(f"✅ Harvested {md_count} markdown files into {raw_legacy_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument("--output", default="raw/legacy-docs", type=Path)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    harvest_legacy(args.root, args.output, verbose=args.verbose)

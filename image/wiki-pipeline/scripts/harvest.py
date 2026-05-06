#!/usr/bin/env python3
# scripts/harvest.py
import argparse
import logging
import os
import pathspec
import shutil
from pathlib import Path
from datetime import datetime, timezone

from .utils import (
    add_frontmatter,
    ensure_dir,
    get_content_fingerprint,
    get_effective_paths,
    is_ignored,
    is_ignored_by_git,
    load_config,
    load_state,
    save_state,
    setup_logging
)

# Create a module-level logger
log = logging.getLogger(__name__)


def harvest(
        root_dir: Path,
        limit: int = None,
        changed_only=False,
        config_path: str = ".wiki-config.yml"
):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    paths = get_effective_paths(config.get("wiki", {}))
    effective_wiki_dir = paths["wiki_dir"]
    effective_state_dir = paths["state_dir"]
    effective_raw_dir = paths["raw_dir"]
    state_path = paths["state_file"]

    harvest_ignore = wiki_config.get("harvest_ignore", [])
    log.debug(f"harvest_ignore={harvest_ignore}")

    # Pre-compile the ignore patterns for performance
    ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', harvest_ignore) if harvest_ignore else None

    # Get targeted patterns
    rglob_patterns = wiki_config.get("harvest_rglob_patterns", ["**/*.md"])

    state = load_state(state_path)
    if "harvest" not in state:
        state["harvest"] = {}

    ensure_dir(effective_raw_dir)

    # --- STEP 1: CLEANUP PHASE ---
    # Remove files in raw_dir that should now be ignored
    log.info(f"🧹 Checking for stale files in {effective_raw_dir}...")

    removed_count = 0
    for harvested_file in list(effective_raw_dir.rglob("*.md")):
        # Reconstruct the original relative path to check against ignore rules
        # Note: harvest adds 'original_path' to frontmatter, but for
        # cleanup we can usually infer it from the structure within raw_dir.
        rel_path = harvested_file.relative_to(effective_raw_dir)

        # Check if the path is now ignored by config or git
        if is_ignored(rel_path, harvest_ignore, spec=ignore_spec) or is_ignored_by_git(rel_path, root_dir):
            log.trace(f"   Removing stale file: {rel_path}")
            os.remove(harvested_file)
            removed_count += 1

            # Clean up empty parent directories
            parent = harvested_file.parent
            while parent != effective_raw_dir and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent

    if removed_count > 0:
        log.info(f"✅ Cleaned up {removed_count} stale files from harvest directory.")

    # --- STEP 2: HARVEST PHASE ---
    log.info(f"📥 Harvesting into: {effective_raw_dir}")
    all_found_files = set()
    for pattern in rglob_patterns:
        log.debug(f"Scanning for pattern: {pattern}")
        # root_dir is typically Path(".")
        all_found_files.update(root_dir.rglob(pattern))

        # Convert back to sorted list for deterministic processing
    sorted_files = sorted(list(all_found_files))

    processed = 0
    for md_file in sorted_files:
        if limit and processed >= limit:
            log.debug(f"   Processed file limit hit => {processed}")
            break

        # 1. Consolidated Safety Check:
        # Skip if file is inside the .wiki state dir OR the final wiki dir
        if any(p == effective_state_dir or p == effective_wiki_dir for p in md_file.parents):
            log.trace(f"  Skipping internal/output directory tree: {md_file}")
            continue

        # 2. String-based Part Check:
        # Catch matches where the directory name exists in the path segments
        if any(exclude in md_file.parts for exclude in
               [str(effective_state_dir), str(effective_wiki_dir)]):
            log.trace(f"  Skipping restricted parts: {md_file}")
            continue

        # 3. Skip configured ignore dirs
        rel_path = md_file.relative_to(root_dir)
        if is_ignored(rel_path, harvest_ignore, spec=ignore_spec):
            log.trace(f"   ⏭️  Ignored by harvest_ignore: {rel_path}")
            continue

        # 4. Respect .gitignore
        if is_ignored_by_git(md_file, root_dir):
            log.trace(f"   ⏭️  Ignored by .gitignore: {rel_path}")
            continue

        file_id = str(md_file.relative_to(root_dir))

        # 1. Get the hash of the CLEAN source file
        current_hash = get_content_fingerprint(md_file)
        state_hash = state["harvest"].get(file_id)

        if changed_only and state_hash == current_hash:
            log.debug(f"   Skipping harvest for {file_id} (unchanged)")
            continue

        log.trace(f"   compile({file_id}): (changed)")
        log.trace(f"     state_hash   => [{state_hash}]")
        log.trace(f"     current_hash => [{current_hash}]")

        target = effective_raw_dir / rel_path
        ensure_dir(target.parent)

        # 2. Copy and add frontmatter (this changes the file on disk)
        shutil.copy2(md_file, target)

        # Add frontmatter
        content = target.read_text(encoding="utf-8")
        metadata = {
            "original_path": str(rel_path),
            "harvested_date": datetime.now(timezone.utc).isoformat(),
            "source_type": "legacy_markdown"
        }
        target.write_text(add_frontmatter(content, metadata), encoding="utf-8")

        # 3. Update the state file using the CLEAN source hash
        state["harvest"][str(rel_path)] = current_hash

        processed += 1

        log.debug(f"   Harvested: {rel_path}")

    save_state(state_path, state)

    log.info(f"✅ Harvested {processed} markdown files into {effective_raw_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument("--changed-only", action="store_true")
    parser.add_argument("--config", default=".wiki-config.yml")
    args = parser.parse_args()

    # Initialize the global logging config once
    setup_logging(args.verbose)

    harvest(
        args.root,
        limit=args.limit,
        changed_only=args.changed_only,
        config_path=args.config
    )

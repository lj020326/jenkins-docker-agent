#!/usr/bin/env python3
# scripts/compile.py
"""
Uses LLM to polish and standardize files in the raw storage into the wiki.
"""

import argparse
import json
import logging
from pathlib import Path

from .utils import (
    ensure_dir,
    get_content_fingerprint,
    get_effective_paths,
    load_config,
    load_state,
    save_state,
    setup_logging,
    LLMClient
)

# Create a module-level logger
log = logging.getLogger(__name__)


def compile_raw_to_wiki(
    llm_client: LLMClient,
    limit: int = None,
    changed_only=False,
    config_path: str = ".wiki-config.yml"
):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    paths = get_effective_paths(config.get("wiki", {}))
    effective_raw_dir = paths["raw_dir"]
    effective_wiki_dir = paths["wiki_dir"]
    state_path = paths["state_file"]

    compile_prompt = wiki_config.get("compile_prompt", {})
    max_file_size = 6000  # characters per file to avoid huge prompts

    state = load_state(state_path)
    if "compile" not in state:
        state["compile"] = {}

    log.info(f"Compiling markdown...")
    ensure_dir(effective_wiki_dir)
    processed = 0
    for md_file in sorted(effective_raw_dir.rglob("*.md")):
        if limit and processed >= limit:
            log.debug(f"   ⏭️  Processed file limit hit => {processed}")
            break

        # Skip internal index files if they exist in raw
        if md_file.name == "index.md":
            continue

        file_id = str(md_file.relative_to(effective_raw_dir))
        current_hash = get_content_fingerprint(md_file)
        state_hash = state["compile"].get(file_id)

        if changed_only and state_hash == current_hash:
            log.debug(f"   ⏭️  Skipping compile for {file_id} (unchanged)")
            continue

        log.trace(f"   harvest({file_id}): (changed)")
        log.trace(f"     state_hash   => [{state_hash}]")
        log.trace(f"     current_hash => [{current_hash}]")

        log.debug(f"   ⏭️  Compiling {md_file.relative_to(effective_raw_dir)}")

        content = md_file.read_text(encoding="utf-8")

        # Truncate very large files (especially tasks/main.yml)
        if len(content) > max_file_size * 2:
            content = content[:max_file_size] + "\n... [truncated - large file] ..."

        prompt = (
            (compile_prompt.get("prefix", "") or "") +
            f"\n\nOriginal content:\n{content}\n\n" +
            (compile_prompt.get("suffix", "") or "")
        )

        try:
            improved = llm_client.get_response(prompt)

            target = effective_wiki_dir / md_file.relative_to(effective_raw_dir)
            ensure_dir(target.parent)
            target.write_text(improved, encoding="utf-8")
            log.info(f"   Compiled → {target.relative_to(Path('.'))}")

            state["compile"][file_id] = current_hash
            processed += 1

        except Exception as e:
            log.error(f"   ⏭️  Skipping {md_file.name} due to error: {e}")
            # Optionally continue to the next file
            continue

    save_state(state_path, state)

    log.info(f"\n✅ Successfully compiled {processed} markdown files into {effective_wiki_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
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
            "model": args.model,
            "api_base": args.api_base,
            "provider": args.provider,
            "debug_llm": args.debug_llm
        }
    )

    compile_raw_to_wiki(
        llm_client,
        limit=args.limit,
        changed_only=args.changed_only,
        config_path=args.config
    )

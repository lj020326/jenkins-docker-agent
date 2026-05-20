#!/usr/bin/env python3
# scripts/lint.py
"""
LLM-powered linting: finds inconsistencies, missing data, suggests improvements,
and creates a lint report.
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


def lint_wiki(
    llm_client: LLMClient,
    limit: int = None,
    changed_only=False,
    config_path: str = ".wiki-config.yml"
):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    paths = get_effective_paths(config.get("wiki", {}))

    # llm_config = wiki_config.get("llm", {})
    lint_prompt = wiki_config.get("lint_prompt", {})
    max_file_size = 6000  # characters per file to avoid huge prompts

    effective_wiki_dir = paths["wiki_dir"]
    effective_state_dir = paths["state_dir"]
    state_path = paths["state_file"]
    lint_report = effective_state_dir / "lint-report.md"

    issues = []

    state = load_state(state_path)
    if "lint" not in state:
        state["lint"] = {}

    log.info("Running wiki linting...")

    processed = 0
    for md_file in sorted(effective_wiki_dir.rglob("*.md")):
        if limit and processed >= limit:
            log.debug(f"   ⏭️  Processed file limit hit => {processed}")
            break

        if md_file.name == "lint-report.md":
            continue

        file_id = str(md_file.relative_to(effective_wiki_dir))
        current_hash = get_content_fingerprint(md_file)
        state_hash = state["lint"].get(file_id)

        if changed_only and state_hash == current_hash:
            log.debug(f"   ⏭️  Skipping lint for {file_id} (unchanged)")
            continue

        log.trace(f"   lint({file_id}): (changed)")
        log.trace(f"     state_hash   => [{state_hash}]")
        log.trace(f"     current_hash => [{current_hash}]")

        log.debug(f"   ⏭️  Linting {md_file.relative_to(effective_wiki_dir)}")

        content = md_file.read_text(encoding="utf-8")

        # Truncate very large files (especially tasks/main.yml)
        if len(content) > max_file_size * 2:
            content = content[:max_file_size] + "\n... [truncated - large file] ..."

        prompt = (
            (lint_prompt.get("prefix", "") or "") +
            f"\n\nFile: {md_file.relative_to(effective_wiki_dir.parent)}\n\nContent:\n{content}\n\n" +
            (lint_prompt.get("suffix", "") or "")
        )

        try:
            result = llm_client.get_response(prompt)

            if "issue" in result.lower() or "missing" in result.lower() or "suggest" in result.lower():
                issues.append(result)

            log.info(f"   ⏭️  Linted {md_file.name}")

            state["lint"][file_id] = current_hash
            processed += 1

        except Exception as e:
            log.error(f"   ⏭️  Skipping {md_file.name} due to error: {e}")
            # Optionally continue to the next file
            continue

    save_state(state_path, state)

    report = "# Wiki Lint Report\n\n" + "\n\n".join(issues) if issues else "# Wiki Lint Report\n\nNo major issues found."
    lint_report.write_text(report, encoding="utf-8")
    log.info(f"\n✅ Successfully linted {processed} markdown files. Lint report saved to {lint_report}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true")
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

    lint_wiki(
        llm_client,
        limit=args.limit,
        changed_only=args.changed_only,
        config_path=args.config
    )

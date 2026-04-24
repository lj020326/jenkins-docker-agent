#!/usr/bin/env python3
# scripts/lint.py
"""
LLM-powered linting: finds inconsistencies, missing data, suggests improvements,
and creates a lint report.
"""

import argparse
from pathlib import Path
from .utils import ensure_dir, load_config, LLMClient


def lint_wiki(
        llm_client: LLMClient,
        limit: int = None,
        verbose: int = 0,
        config_path: str = ".wiki-config.yml"
):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    # llm_config = wiki_config.get("llm", {})
    lint_prompt = wiki_config.get("lint_prompt", {})
    max_file_size = 6000  # characters per file to avoid huge prompts

    effective_wiki_dir = Path(wiki_config.get("output_dir", "wiki"))

    ensure_dir(effective_wiki_dir)
    lint_report = effective_wiki_dir / "lint-report.md"
    issues = []

    print("Running wiki linting...")

    processed = 0
    for md_file in sorted(effective_wiki_dir.rglob("*.md")):
        if md_file.name == "lint-report.md":
            continue

        if limit and processed >= limit:
            break

        if verbose >= 1:
            print(f"   Linting {md_file.relative_to(effective_wiki_dir)}")

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

            if verbose:
                print(f"   Linted {md_file.name}")
            processed += 1

        except Exception as e:
            print(f"   Skipping {md_file.name} due to error: {e}")
            # Optionally continue to the next file
            continue

    report = "# Wiki Lint Report\n\n" + "\n\n".join(issues) if issues else "# Wiki Lint Report\n\nNo major issues found."
    lint_report.write_text(report, encoding="utf-8")
    print(f"✅ Lint complete. Report saved to {lint_report}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument("--debug-llm", action="store_true")
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

    lint_wiki(
        llm_client,
        verbose=args.verbose,
        config_path=args.config
    )

#!/usr/bin/env python3
# scripts/lint.py
"""
LLM-powered linting: finds inconsistencies, missing data, suggests improvements,
and creates a lint report.
"""

import argparse
from pathlib import Path
from scripts.utils import get_llm_response, ensure_dir, load_config


def lint_wiki(wiki_dir: Path,
              model: str = None,
              api_base: str = None,
              api_key: str = None,
              verbose: bool = False,
              config_path: str = ".wiki-config.yml"):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    llm_config = wiki_config.get("llm", {})
    lint_prompt = wiki_config.get("lint_prompt", {})

    ensure_dir(wiki_dir)
    lint_report = wiki_dir / "lint-report.md"
    issues = []

    print("Running wiki linting...")

    for md_file in sorted(wiki_dir.rglob("*.md")):
        if md_file.name == "lint-report.md":
            continue

        if verbose:
            print(f"   Linting {md_file.relative_to(wiki_dir)}")

        content = md_file.read_text(encoding="utf-8")

        prompt = (
            (lint_prompt.get("prefix", "") or "") +
            f"\n\nFile: {md_file.relative_to(wiki_dir.parent)}\n\nContent:\n{content[:6000]}\n\n" +
            (lint_prompt.get("suffix", "") or "")
        )

        result = get_llm_response(
            prompt,
            model=model,
            api_base=api_base,
            api_key=api_key,
            temperature=llm_config.get("temperature", 0.2),
            max_tokens=llm_config.get("max_tokens"),
            timeout=llm_config.get("timeout"),
            verbose=verbose
        )

        if "issue" in result.lower() or "missing" in result.lower() or "suggest" in result.lower():
            issues.append(result)

    report = "# Wiki Lint Report\n\n" + "\n\n".join(issues) if issues else "# Wiki Lint Report\n\nNo major issues found."
    lint_report.write_text(report, encoding="utf-8")
    print(f"✅ Lint complete. Report saved to {lint_report}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--config", default=".wiki-config.yml")
    args = parser.parse_args()
    lint_wiki(Path("wiki"), verbose=args.verbose, config_path=args.config)

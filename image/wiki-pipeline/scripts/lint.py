#!/usr/bin/env python3
# scripts/lint.py
"""
Hybrid Wiki Linting Pipeline:
1. Fast, deterministic AST/Regex checks run locally (0s LLM overhead).
2. Optional LLM-powered semantic analysis for nuanced formatting, quality QA, or auto-fixing.
"""

import argparse
import litellm
import logging
import re
from pathlib import Path

from .utils import (
    LLMClient,
    get_content_fingerprint,
    get_effective_paths,
    load_config,
    load_state,
    render_yaml_prompt,
    save_state,
    setup_logging,
    strip_code_fences,
)

# Create a module-level logger
log = logging.getLogger(__name__)


def run_deterministic_lint(file_path: Path, content: str) -> list[str]:
    """
    Executes fast, zero-cost deterministic checks on Markdown structure and frontmatter.
    Returns a list of human-readable issues found.
    """
    issues = []
    rel_path = file_path.name

    # Check 1: YAML Frontmatter existence and validity
    if not content.startswith("---"):
        issues.append(
            f"[{rel_path}] Missing YAML frontmatter header (must start with '---')."
        )
    else:
        # Check basic YAML frontmatter keys
        frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not frontmatter_match:
            issues.append(f"[{rel_path}] Unclosed YAML frontmatter header.")
        else:
            fm_text = frontmatter_match.group(1)
            required_keys = ["title:", "category:"]
            for key in required_keys:
                if key not in fm_text:
                    issues.append(
                        f"[{rel_path}] Frontmatter missing required key: `{key}`."
                    )

    # Check 2: Heading hierarchy check
    if not re.search(r"^#\s+", content, re.MULTILINE):
        issues.append(f"[{rel_path}] Missing H1 title heading (`# Document Title`).")

    # Check 3: Check for empty code fences or broken blocks
    if content.count("```") % 2 != 0:
        issues.append(
            f"[{rel_path}] Unmatched or unclosed Markdown code block fences (` ``` `)."
        )

    # Check 4: Check for unresolved placeholder text
    placeholders = ["TODO", "FIXME", "[insert", "<insert"]
    for ph in placeholders:
        if ph in content:
            issues.append(
                f"[{rel_path}] Contains unresolved placeholder or marker: `{ph}`."
            )

    return issues


def lint_wiki(
    llm_client: LLMClient = None,
    fix: bool = False,
    limit: int = None,
    changed_only: bool = False,
    use_llm: bool = True,
    config_path: str = ".wiki-config.yml",
):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    paths = get_effective_paths(wiki_config)

    lint_prompt = wiki_config.get("lint_prompt", {})
    # Character threshold for prompt truncation
    max_file_size = 6000

    effective_wiki_dir = paths["wiki_dir"]
    effective_state_dir = paths["state_dir"]
    state_path = paths["state_file"]
    lint_report = effective_state_dir / "lint-report.md"

    issues_report = []

    state = load_state(state_path)
    if "lint" not in state:
        state["lint"] = {}

    log.info(
        f"Running wiki linting (Deterministic Check | LLM Mode: {use_llm} | Fix: {fix})..."
    )

    processed = 0
    for md_file in sorted(effective_wiki_dir.rglob("*.md")):
        if limit and processed >= limit:
            log.debug(f"   ⏭️  Processed file limit hit => {processed}")
            break

        if md_file.name in ["lint-report.md", "index.md", "README.md"]:
            continue

        file_id = str(md_file.relative_to(effective_wiki_dir))
        current_hash = get_content_fingerprint(md_file)
        state_hash = state["lint"].get(file_id)

        if changed_only and state_hash == current_hash:
            log.debug(f"   ⏭️  Skipping lint for {file_id} (unchanged)")
            continue

        log.debug(f"   🔍 Linting {file_id}")
        content = md_file.read_text(encoding="utf-8")

        # Stage 1: Deterministic Lint Pass (Instant)
        file_issues = run_deterministic_lint(md_file, content)
        if file_issues:
            issues_report.append(
                f"### {file_id} (Deterministic Validation)\n"
                + "\n".join(f"- {i}" for i in file_issues)
            )

        # Stage 2: Optional LLM Semantic Pass
        if use_llm and llm_client:
            truncated_content = content
            if len(content) > max_file_size * 2:
                truncated_content = (
                    content[:max_file_size] + "\n... [truncated - large file] ..."
                )

            messages = render_yaml_prompt(
                lint_prompt, file_id=file_id, truncated_content=truncated_content
            )

            if fix:
                # Append instructions or handle fix requirement cleanly in messages
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "If there are any errors or formatting inconsistencies that are readily fixable, "
                            "please provide the complete corrected markdown content for the file at the end of your response "
                            "under a heading named '### Fixed Content' enclosed in a code block."
                        ),
                    }
                )

            try:
                result = llm_client.get_response(messages)

                if fix and "### Fixed Content" in result:
                    parts = result.split("### Fixed Content", 1)
                    report_part = parts[0].strip()
                    fixed_content_raw = parts[1].strip()

                    # Extract clean content from potential code fences in the fixed section
                    fixed_content = strip_code_fences(fixed_content_raw)

                    if fixed_content:
                        md_file.write_text(fixed_content, encoding="utf-8")
                        current_hash = get_content_fingerprint(md_file)
                        log.info(f"   🛠️ Fixed and updated {md_file.name}")
                        report_part += f"\n\n*Status: Automatically fixed and applied changes to {md_file.name}.*"

                    if report_part:
                        issues_report.append(
                            f"### {file_id} (Semantic Analysis)\n{report_part}"
                        )
                else:
                    if any(
                        w in result.lower()
                        for w in ["issue", "missing", "suggest", "error"]
                    ):
                        issues_report.append(
                            f"### {file_id} (Semantic Analysis)\n{result}"
                        )
            except litellm.InternalServerError as e:
                log.error(
                    f"   💥 Fatal LLM Internal Server Error for {md_file.name}: {e}"
                )
                raise
            except (ConnectionError, TimeoutError) as e:
                log.error(
                    f"   💥 Fatal Connection/Timeout Error for {md_file.name}: {e}"
                )
                raise
            except Exception as e:
                log.error(
                    f"   ⚠️ Skipping LLM pass for {md_file.name} due to error: {e}"
                )

        state["lint"][file_id] = current_hash
        processed += 1

    save_state(state_path, state)

    report_content = (
        "# Wiki Lint Report\n\n" + "\n\n---\n\n".join(issues_report)
        if issues_report
        else "# Wiki Lint Report\n\nNo issues or formatting warnings found."
    )
    lint_report.write_text(report_content, encoding="utf-8")
    log.info(
        f"\n✅ Linting completed across {processed} files. Report saved to {lint_report}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lint Wiki Markdown files.")
    parser.add_argument(
        "--fix", action="store_true", help="Automatically apply LLM fix recommendations"
    )
    parser.add_argument("--limit", type=int, help="Limit number of files processed")
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument("--debug-llm", action="store_true")
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="Only lint changed files based on state fingerprint",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Run deterministic checks only (skip LLM pass)",
    )
    parser.add_argument("--config", default=".wiki-config.yml")
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-base", default=None)
    parser.add_argument("--provider", default=None)
    args = parser.parse_args()

    setup_logging(args.verbose, debug_llm=args.debug_llm)

    llm_client = None
    if not args.no_llm:
        llm_client = LLMClient(
            config_path=args.config,
            overrides={
                "model": args.model,
                "api_base": args.api_base,
                "provider": args.provider,
                "debug_llm": args.debug_llm,
            },
        )

    lint_wiki(
        llm_client=llm_client,
        fix=args.fix,
        limit=args.limit,
        changed_only=args.changed_only,
        use_llm=not args.no_llm,
        config_path=args.config,
    )

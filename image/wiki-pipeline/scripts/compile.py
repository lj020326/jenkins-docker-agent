#!/usr/bin/env python3
# scripts/compile.py
"""
Uses LLM to polish and standardize files in the raw storage into the wiki.
"""

import argparse
from pathlib import Path
from .utils import ensure_dir, load_config, LLMClient


def compile_raw_to_wiki(
        llm_client: LLMClient,
        limit: int = None,
        verbose: int = 0,
        config_path: str = ".wiki-config.yml"
):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    compile_prompt = wiki_config.get("compile_prompt", {})
    max_file_size = 6000  # characters per file to avoid huge prompts

    effective_wiki_dir = Path(wiki_config.get("output_dir", "wiki"))
    effective_raw_dir = Path(wiki_config.get("harvest_dir", "raw/legacy-docs"))

    print(f"Compiling markdown...")
    ensure_dir(effective_wiki_dir)
    processed = 0
    for md_file in sorted(effective_raw_dir.rglob("*.md")):
        # Skip internal index files if they exist in raw
        if md_file.name == "index.md": continue

        if limit and processed >= limit:
            break

        if verbose >= 1:
            print(f"   Compiling {md_file.relative_to(effective_raw_dir)}")

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
            if verbose:
                print(f"   Compiled → {target.relative_to(Path('.'))}")
            processed += 1

        except Exception as e:
            print(f"   Skipping {md_file.name} due to error: {e}")
            # Optionally continue to the next file
            continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", default="raw", type=Path)
    parser.add_argument("--wiki-dir", default="wiki", type=Path)
    parser.add_argument("--limit", type=int)
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

    compile_raw_to_wiki(
        llm_client,
        limit=args.limit,
        verbose=args.verbose,
        config_path=args.config
    )

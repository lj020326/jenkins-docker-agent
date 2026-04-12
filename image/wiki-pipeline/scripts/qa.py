#!/usr/bin/env python3
# scripts/qa.py
"""
Research-style Q&A generation - can be called by lint or manually.
"""

import argparse
from pathlib import Path
from scripts.utils import get_llm_response, ensure_dir, load_config


def generate_qa(wiki_dir: Path,
                model: str = None,
                api_base: str = None,
                api_key: str = None,
                verbose: bool = False,
                config_path: str = ".wiki-config.yml"):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    llm_config = wiki_config.get("llm", {})

    ensure_dir(wiki_dir)
    qa_file = wiki_dir / "qa.md"

    if verbose:
        print("Generating Q&A section...")

    qa_prompt = wiki_config.get("qa_prompt", "Generate important Q&A pairs...")

    qa_content = get_llm_response(
        qa_prompt,
        model=model,
        api_base=api_base,
        api_key=api_key,
        temperature=llm_config.get("temperature", 0.3),
        max_tokens=llm_config.get("max_tokens"),
        timeout=llm_config.get("timeout"),
        verbose=verbose
    )

    full_content = f"# Frequently Asked Questions\n\n{qa_content}\n"
    qa_file.write_text(full_content, encoding="utf-8")
    print(f"✅ QA section generated at {qa_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki-dir", default="wiki", type=Path)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--config", default=".wiki-config.yml")
    args = parser.parse_args()
    generate_qa(args.wiki_dir, verbose=args.verbose, config_path=args.config)

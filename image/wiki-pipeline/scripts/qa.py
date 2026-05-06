#!/usr/bin/env python3
# scripts/qa.py
"""
Research-style Q&A generation - can be called by lint or manually.
"""

import argparse
import logging
from pathlib import Path

from .utils import ensure_dir, load_config, setup_logging, LLMClient

# Create a module-level logger
log = logging.getLogger(__name__)


def generate_qa(
        llm_client: LLMClient,
        config_path: str = ".wiki-config.yml"
):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    # llm_config = wiki_config.get("llm", {})

    effective_wiki_dir = Path(wiki_config.get("wiki_dir"))

    ensure_dir(effective_wiki_dir)
    qa_file = effective_wiki_dir / "qa.md"

    log.info("Generating Q&A section...")

    qa_prompt = wiki_config.get("qa_prompt", "Generate important Q&A pairs...")

    qa_content = llm_client.get_response(qa_prompt)

    full_content = f"# Frequently Asked Questions\n\n{qa_content}\n"
    qa_file.write_text(full_content, encoding="utf-8")
    log.info(f"✅ QA section generated at {qa_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument("--debug-llm", action="store_true")
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

    generate_qa(
        llm_client,
        config_path=args.config
    )

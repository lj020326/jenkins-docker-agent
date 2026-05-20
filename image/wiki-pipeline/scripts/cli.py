#!/usr/bin/env python3
# scripts/cli.py
"""
Unified CLI for the wiki pipeline with configurable LLM endpoint.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path so we can import scripts.* properly
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils import setup_logging, LLMClient
from scripts.harvest import harvest
from scripts.ingest_ansible_yaml import ingest_ansible_yaml
from scripts.compile import compile_raw_to_wiki
from scripts.lint import lint_wiki
from scripts.index import generate_wiki_index
from scripts.qa import generate_qa
from scripts.generate_media import generate_media


def main():
    # Common parser for global arguments
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--config", default=".wiki-config.yml",
                               help="Path to .wiki-config.yml (default: .wiki-config.yml)")
    parent_parser.add_argument("-v", "--verbose", action="count", default=0,
                               help="Verbosity level: -v, -vv, -vvv")
    parent_parser.add_argument("-d", "--debug-llm", action="store_true",
                               help="Enable LiteLLM debug mode (very verbose)")
    parent_parser.add_argument("--api-base", default=None,
                               help="Override LLM API base URL")
    parent_parser.add_argument("--api-key", default=None,
                               help="Override LLM API key")
    parent_parser.add_argument("--model", default=None,
                               help="Override LLM model name")
    parent_parser.add_argument("--provider", default=None,
                               help="Override LLM provider (openai/ollama)")
    # Add --changed-only to the parent_parser so it's available to all commands
    parent_parser.add_argument("--changed-only", action="store_true", help="Only process files that have changed")
    parent_parser.add_argument("--limit", type=int, default=None)

    parser = argparse.ArgumentParser(description="Wiki Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # harvest (no LLM)
    p = subparsers.add_parser("harvest", parents=[parent_parser])

    # ingest (uses LLM)
    p = subparsers.add_parser("ingest", parents=[parent_parser], help="Ingest Ansible YAML")

    # compile (uses LLM)
    p = subparsers.add_parser("compile", parents=[parent_parser], help="Compile raw to wiki")

    # lint (uses LLM)
    p = subparsers.add_parser("lint", parents=[parent_parser], help="Run linting")
    p.add_argument("--fix", action="store_true")

    # index (no LLM)
    p = subparsers.add_parser("index", parents=[parent_parser], help="Build index and backlinks")

    # qa (uses LLM)
    p = subparsers.add_parser("qa", parents=[parent_parser], help="Generate Q&A")

    # generate-media (no LLM)
    p = subparsers.add_parser(
        "generate-media",
        parents=[parent_parser],
        help="Generate slides and charts and other derived media content")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize the global logging config once
    setup_logging(args.verbose, debug_llm=args.debug_llm)

    # Common kwargs for LLM functions
    common_kwargs = {
        "limit": args.limit,
        "changed_only": args.changed_only,
        "config_path": args.config
    }

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

    if args.command == "harvest":
        harvest(Path("."), **common_kwargs)
    elif args.command == "ingest":
        ingest_ansible_yaml(llm_client, Path("."), **common_kwargs)
    elif args.command == "compile":
        compile_raw_to_wiki(llm_client, **common_kwargs)
    elif args.command == "lint":
        lint_wiki(llm_client, **common_kwargs)
    elif args.command == "index":
        generate_wiki_index(Path("."), args.config)
    elif args.command == "qa":
        generate_qa(llm_client, args.config)
    elif args.command == "generate-media":
        generate_media(llm_client, args.config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# scripts/cli.py
"""
Unified CLI for the wiki pipeline with configurable LLM endpoint.
"""

import argparse
from pathlib import Path
import sys

# Add parent directory to path so we can import scripts.* properly
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.harvest_legacy import harvest_legacy
from scripts.ingest_yaml import ingest_ansible_yaml
from scripts.compile import compile_raw_to_wiki
from scripts.lint import lint_wiki
from scripts.index import generate_wiki_index
from scripts.qa import generate_qa
from scripts.generate_outputs import generate_outputs


def main():
    # Common parser for global arguments
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--config", default=".wiki-config.yml",
                               help="Path to .wiki-config.yml (default: .wiki-config.yml)")
    parent_parser.add_argument("--verbose", "-v", action="store_true")
    parent_parser.add_argument("--api-base", default="http://gpu02.johnson.int:11434/v1")
    parent_parser.add_argument("--api-key", default=None)
    parent_parser.add_argument("--model", default="qwen2.5-coder:32b")

    parser = argparse.ArgumentParser(description="Wiki Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # harvest (no LLM)
    p = subparsers.add_parser("harvest", parents=[parent_parser])
    p.add_argument("--output", default="raw/legacy-docs", type=Path)

    # ingest (uses LLM)
    p = subparsers.add_parser("ingest", parents=[parent_parser], help="Ingest Ansible YAML")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--changed-only", action="store_true")

    # compile (uses LLM)
    p = subparsers.add_parser("compile", parents=[parent_parser], help="Compile raw to wiki")

    # lint (uses LLM)
    p = subparsers.add_parser("lint", parents=[parent_parser], help="Run linting")
    p.add_argument("--fix", action="store_true")

    # index (no LLM)
    p = subparsers.add_parser("index", parents=[parent_parser], help="Build index and backlinks")

    # qa (uses LLM)
    p = subparsers.add_parser("qa", parents=[parent_parser], help="Generate Q&A")

    # generate-outputs (no LLM)
    p = subparsers.add_parser("generate-outputs", parents=[parent_parser], help="Generate slides and charts")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Common kwargs for LLM functions
    common_kwargs = {
        "verbose": args.verbose,
        "api_base": args.api_base,
        "api_key": args.api_key,
        "model": args.model,
        "config_path": args.config
    }

    if args.command == "harvest":
        harvest_legacy(Path("."), args.output, verbose=args.verbose)
    elif args.command == "ingest":
        ingest_ansible_yaml(Path("."), limit=args.limit, changed_only=args.changed_only, **common_kwargs)
    elif args.command == "compile":
        compile_raw_to_wiki(Path("raw"), Path("wiki"), **common_kwargs)
    elif args.command == "lint":
        lint_wiki(Path("wiki"), **common_kwargs)
    elif args.command == "index":
        generate_wiki_index(Path("."), verbose=args.verbose, config_path=args.config)
    elif args.command == "qa":
        generate_qa(Path("wiki"), **common_kwargs)
    elif args.command == "generate-outputs":
        generate_outputs(Path("wiki"), Path("outputs"), verbose=args.verbose)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

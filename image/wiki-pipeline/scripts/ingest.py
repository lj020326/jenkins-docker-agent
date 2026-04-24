#!/usr/bin/env python3
# scripts/ingest.py
import argparse
from pathlib import Path
from .ingest_ansible_yaml import ingest_ansible_yaml

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument("--ansible", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--changed-only", action="store_true")
    args = parser.parse_args()

    if args.ansible:
        ingest_ansible_yaml(
            Path("."),
            limit=args.limit,
            changed_only=args.changed_only,
            verbose=args.verbose
        )
    else:
        print("General ingest not yet implemented - use --ansible for now")

#!/usr/bin/env python3
# scripts/generate_outputs.py
"""
Generates Marp slides and Matplotlib charts, then embeds links back into wiki.
"""

import argparse
from pathlib import Path
from scripts.utils import ensure_dir


def generate_outputs(wiki_dir: Path, outputs_dir: Path, verbose: bool = False):
    ensure_dir(outputs_dir)
    ensure_dir(outputs_dir / "slides")
    ensure_dir(outputs_dir / "charts")

    if verbose:
        print("Generating outputs (slides & charts)...")

    # Placeholder - expand with actual Marp + matplotlib logic later
    # Example: create a simple index
    index = "# Generated Outputs\n\n## Slides\n\n## Charts\n"
    (outputs_dir / "index.md").write_text(index, encoding="utf-8")

    if verbose:
        print(f"✅ Outputs generated in {outputs_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki-dir", default="wiki", type=Path)
    parser.add_argument("--outputs-dir", default="outputs", type=Path)
    args = parser.parse_args()
    generate_outputs(args.wiki_dir, args.outputs_dir)

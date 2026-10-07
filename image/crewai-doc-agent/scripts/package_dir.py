#!/usr/bin/env python3
import os
import sys
import argparse
import pathspec
import yaml
from pathlib import Path

# Default patterns to ignore during repository packaging
DEFAULT_IGNORES = [
    ".git",
    ".github",
    ".code_index",
    ".agent_state",
    "save",
    "node_modules",
    "__pycache__",
    "*.pyc",
    "*.tar.gz",
    "*.zip",
    ".DS_Store",
]


def load_ignore_spec(repo_root: Path) -> pathspec.PathSpec:
    patterns = list(DEFAULT_IGNORES)
    gitignore_path = repo_root / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            patterns.extend(
                [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]
            )
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def is_binary_file(file_path: Path, chunk_size: int = 1024) -> bool:
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(chunk_size)
            if b"\0" in chunk:
                return True
    except Exception:
        return True
    return False


def format_yaml_literal(text: str, indent: int = 2) -> str:
    # Helper to format multiline strings cleanly in YAML output
    return yaml.scalar_representer.ScalarRepresenter.represent_scalar(
        yaml.representer.SafeRepresenter(), "tag:yaml.org,2002:str", text, style="|"
    )


def build_tree(repo_root: Path, ignore_spec: pathspec.PathSpec) -> dict:
    file_dict = {}
    for root, dirs, files in os.walk(repo_root):
        rel_root = Path(root).relative_to(repo_root)

        # Filter directories in-place
        dirs[:] = [
            d
            for d in dirs
            if not ignore_spec.match_file(str(rel_root / d)) and d != "."
        ]

        for file in files:
            rel_path = rel_root / file if rel_root != Path(".") else Path(file)
            if ignore_spec.match_file(str(rel_path)):
                continue

            full_path = repo_root / rel_path
            if full_path.is_file() and not is_binary_file(full_path):
                try:
                    file_dict[str(rel_path)] = full_path.read_text(
                        encoding="utf-8", errors="ignore"
                    )
                except Exception as e:
                    print(f"⚠️ Warning: Could not read {rel_path}: {e}", file=sys.stderr)
    return file_dict


def main():
    parser = argparse.ArgumentParser(
        description="Package repository files into a token-optimized YAML context file."
    )
    parser.add_argument(
        "repo_dir", nargs="?", default=".", help="Path to repository root"
    )
    parser.add_argument("--output", required=True, help="Path to output YAML file")
    args = parser.parse_args()

    repo_root = Path(args.repo_dir).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"📦 Scanning repository at {repo_root}...")
    ignore_spec = load_ignore_spec(repo_root)
    file_data = build_tree(repo_root, ignore_spec)

    print(f"📝 Writing {len(file_data)} files to context bundle: {output_path}")

    # Custom representer for neat multiline strings
    yaml.add_representer(
        str,
        lambda dumper, data: dumper.represent_scalar(
            "tag:yaml.org,2002:str", data, style="|" if "\n" in data else None
        ),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(
            file_data, f, default_flow_style=False, sort_keys=True, allow_unicode=True
        )

    print("✅ Repository context packaging completed successfully.")


if __name__ == "__main__":
    main()

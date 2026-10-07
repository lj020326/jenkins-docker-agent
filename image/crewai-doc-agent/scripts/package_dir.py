#!/usr/bin/env python3
"""
Repository Directory Packaging Tool
Packages source code within a directory into a unified, token-optimized YAML file
for AI/LLM context interactions.
"""

import argparse
import datetime
import logging
import os
import re
import subprocess
import sys
import yaml
from argparse import RawTextHelpFormatter
from pathlib import Path

# Script metadata matching template structure
__scriptName__ = os.path.basename(sys.argv[0])
__version__ = "2026.10.07"
__updated__ = "7 October 2026"

log = logging.getLogger(__scriptName__)


def setup_logging(loglevel_str="INFO"):
    """Sets up the script logger and applies the requested logging level."""
    loglevel = getattr(logging, loglevel_str.upper(), logging.INFO)
    log.setLevel(loglevel)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not log.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        log.addHandler(handler)
    else:
        log.handlers[0].setLevel(loglevel)


# Custom PyYAML Dumper to format multiline strings using block scalar '|'
class LiteralBlockYamlDumper(yaml.SafeDumper):
    pass


def _represent_multiline_str(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


LiteralBlockYamlDumper.add_representer(str, _represent_multiline_str)


# --- Configuration Defaults ---
BASE_EXCLUDE_DIRS = (
    r"(\.git|\.idea|\.DS_Store|\.test|\.tmp|vault|\.vault|__pycache__|"
    r"output|save|assets|build|releases|archive|old)"
)
FILE_EXT_EXCLUDES = r"\.(svg|png|jpg|jpeg|gif|ico|webp|pdf|zip|tar|gz|7z)$"
DEFAULT_OUTPUT_FILENAME = ".package_dir.context.yml"


# --- Code Stripping / Compression Helpers ---
def strip_comments_and_blanks(
    content: str, ext: str, strip_comments: bool, strip_blanks: bool
) -> str:
    """Strips comments and/or blank lines based on file extension."""
    if not content.strip():
        return content

    cleaned = content

    if strip_comments:
        # Python, Bash, Shell, YAML, TOML, Dockerfile
        if ext in {
            ".py",
            ".sh",
            ".bash",
            ".yaml",
            ".yml",
            ".toml",
            ".dockerfile",
            ".r",
            ".pl",
        }:
            cleaned = re.sub(r"^\s*#.*$", "", cleaned, flags=re.MULTILINE)
        # C, C++, Java, JS, TS, Go, Rust, PHP, C#
        elif ext in {
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".cs",
            ".go",
            ".rs",
            ".php",
            ".swift",
            ".kt",
        }:
            cleaned = re.sub(r"/\*[\s\S]*?\*/", "", cleaned)  # Block comments
            cleaned = re.sub(
                r"^\s*//.*$", "", cleaned, flags=re.MULTILINE
            )  # Line comments
        # HTML, XML
        elif ext in {".html", ".xml", ".htm"}:
            cleaned = re.sub(r"<!--[\s\S]*?-->", "", cleaned)

    if strip_blanks:
        lines = [line for line in cleaned.splitlines() if line.strip()]
        cleaned = "\n".join(lines)

    return cleaned


def is_binary_file(file_path: Path, chunk_size: int = 1024) -> bool:
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(chunk_size)
            if b"\0" in chunk:
                return True
    except Exception:
        return True
    return False


def build_tree(files: list[str]) -> str:
    """Generates a text-based ASCII directory tree summary."""
    tree = {}
    for path in sorted(files):
        parts = path.split("/")
        curr = tree
        for part in parts:
            curr = curr.setdefault(part, {})

    def render_tree(d: dict, prefix: str = "") -> list[str]:
        lines = []
        keys = sorted(d.keys())
        for i, key in enumerate(keys):
            is_last = i == len(keys) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{key}")
            if d[key]:
                extension = "    " if is_last else "│   "
                lines.extend(render_tree(d[key], prefix + extension))
        return lines

    return "\n".join(["."] + render_tree(tree))


def get_git_commit_info(dir_path: Path) -> tuple[str, str]:
    """Retrieves current Git commit hash and active branch if in a Git repo."""
    commit_hash = "N/A"
    branch_name = "N/A"
    try:
        res = subprocess.run(
            ["git", "-C", str(dir_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            commit_hash = res.stdout.strip()

        res_branch = subprocess.run(
            ["git", "-C", str(dir_path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res_branch.returncode == 0:
            branch_name = res_branch.stdout.strip()
    except Exception:
        pass

    return commit_hash, branch_name


def main():
    prog_usage = f"""
Examples of use:
  {__scriptName__} my_project
  {__scriptName__} -s 15 my_project
  {__scriptName__} -n my_project node_modules .venv
  {__scriptName__} -L DEBUG my_project
  {__scriptName__} --strip-comments --strip-blank-lines my_project
  {__scriptName__} -o /tmp/custom_context.yaml my_project
"""

    parser = argparse.ArgumentParser(
        formatter_class=RawTextHelpFormatter,
        description="Repository Directory Packaging Tool\nPackages source code into a YAML file optimized for AI/LLM interactions.",
        epilog=prog_usage,
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__} ({__updated__})",
    )
    parser.add_argument(
        "-L",
        "--loglevel",
        choices=["DEBUG", "INFO", "WARN", "ERROR"],
        default="INFO",
        help="Set log level (default: INFO)",
    )

    parser.add_argument("directory_path", help="Path to the directory to package")
    parser.add_argument(
        "custom_ignores",
        nargs="*",
        help="Additional directory or file patterns to ignore",
    )
    parser.add_argument(
        "-o", "--output", dest="output_file_custom", help="Custom output file path"
    )
    parser.add_argument(
        "-s",
        "--size-threshold",
        dest="size_threshold_mb",
        type=int,
        default=10,
        help="File size threshold warning in MB (default: 10)",
    )
    parser.add_argument(
        "-n",
        "--no-git",
        dest="no_git",
        action="store_true",
        help="Disable Git integration. Forces standard file search",
    )

    # Optimization options
    parser.add_argument(
        "--strip-comments",
        action="store_true",
        help="Remove code comments to save tokens",
    )
    parser.add_argument(
        "--strip-blank-lines",
        action="store_true",
        help="Remove empty lines to save tokens",
    )
    parser.add_argument(
        "--max-file-size-kb",
        type=int,
        default=500,
        help="Skip individual files exceeding this size in KB (default: 500)",
    )

    args = parser.parse_args()

    setup_logging(args.loglevel)

    log.debug("Starting directory packaging process")

    execution_pwd = os.getcwd()
    requested_target_dir = args.directory_path

    dir_path = Path(args.directory_path).resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        log.error(
            f"Directory path '{args.directory_path}' does not exist or is not a directory."
        )
        sys.exit(1)

    directory_name = dir_path.name

    # Target directory path for file output
    if args.output_file_custom:
        output_file = Path(args.output_file_custom).resolve()
    else:
        output_file = dir_path / DEFAULT_OUTPUT_FILENAME

    log.info(f"Target output path: {output_file}")

    # Build regex exclusions
    custom_regex_parts = [re.escape(arg) for arg in args.custom_ignores]
    if custom_regex_parts:
        all_dir_excludes = f"{BASE_EXCLUDE_DIRS}|({'|'.join(custom_regex_parts)})"
    else:
        all_dir_excludes = BASE_EXCLUDE_DIRS

    git_dir_exclude_regex = re.compile(rf"(^|/)({all_dir_excludes})(/|$)")
    file_ext_exclude_regex = re.compile(FILE_EXT_EXCLUDES)

    use_git = not args.no_git
    is_git_repo = False

    if use_git:
        try:
            res = subprocess.run(
                ["git", "-C", str(dir_path), "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and "true" in res.stdout.strip():
                is_git_repo = True
        except Exception as e:
            log.debug(f"Git execution failed during repository detection: {e}")
            is_git_repo = False

    log.info(f"Packaging directory: {directory_name}")

    candidate_paths: list[str] = []

    if is_git_repo:
        log.info("Strategy: Git tracking (observing .gitignore rules)")
        log.info(
            f"Excluding directory patterns matching: {git_dir_exclude_regex.pattern}"
        )
        log.info(f"Excluding file extensions matching: {FILE_EXT_EXCLUDES}")
        log.info("Filtering out non-text files...")
        log.info("---")

        try:
            res = subprocess.run(
                [
                    "git",
                    "-C",
                    str(dir_path),
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            candidate_paths = [
                line.strip() for line in res.stdout.splitlines() if line.strip()
            ]
        except Exception as e:
            log.error(f"Error executing git ls-files: {e}")
            sys.exit(1)
    else:
        log.info("Strategy: Standard file search (ignoring Git tracking)")
        log.info(
            f"Excluding directory patterns matching: {git_dir_exclude_regex.pattern}"
        )
        log.info("Filtering out non-text files...")
        log.info("---")

        for root, dirs, files in os.walk(dir_path):
            rel_root = os.path.relpath(root, dir_path)
            if rel_root == ".":
                rel_root = ""

            # Prune excluded directories in-place
            dirs[:] = [
                d
                for d in dirs
                if not git_dir_exclude_regex.search(
                    os.path.join(rel_root, d) if rel_root else d
                )
            ]

            for file in files:
                rel_file_path = os.path.join(rel_root, file) if rel_root else file
                candidate_paths.append(rel_file_path)

    processed_files = {}
    file_list = []
    total_lines = 0

    for rel_path in sorted(candidate_paths):
        full_path = dir_path / rel_path

        # Ignore output context dotfiles (e.g., .package_dir.context.yml)
        if full_path.name.startswith(".package_dir"):
            log.debug(f"Skipping package context file: {rel_path}")
            continue

        # Ignore directory matching patterns
        if git_dir_exclude_regex.search(rel_path):
            log.debug(f"Skipping excluded pattern: {rel_path}")
            continue

        # Ignore extensions
        if file_ext_exclude_regex.search(rel_path):
            log.debug(f"Skipping excluded extension: {rel_path}")
            continue

        # Prevent packaging the output file itself
        if full_path.resolve() == output_file.resolve():
            log.debug(f"Skipping output target file: {rel_path}")
            continue

        if not full_path.is_file():
            continue

        # Skip oversized files
        if full_path.stat().st_size > (args.max_file_size_kb * 1024):
            log.warning(
                f"Skipping file exceeding size limit ({args.max_file_size_kb} KB): {rel_path}"
            )
            continue

        # Skip binary files
        if is_binary_file(full_path):
            log.warning(f"Skipping binary: {rel_path}")
            continue

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            ext = full_path.suffix.lower()
            cleaned_content = strip_comments_and_blanks(
                content, ext, args.strip_comments, args.strip_blank_lines
            )

            processed_files[rel_path] = cleaned_content
            file_list.append(rel_path)
            total_lines += len(cleaned_content.splitlines())
            log.debug(f"Processed file: {rel_path}")

        except Exception as e:
            log.error(f"Error reading file {rel_path}: {e}")

    git_commit_hash, git_branch = (
        get_git_commit_info(dir_path) if is_git_repo else ("N/A", "N/A")
    )

    # Build rich metadata for LLM contextual awareness
    yaml_data = {
        "__meta__": {
            "package_name": directory_name,
            "requested_target_dir": requested_target_dir,
            "absolute_target_dir": str(dir_path),
            "execution_pwd": execution_pwd,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "git_commit_hash": git_commit_hash,
            "git_branch": git_branch,
            "python_version": sys.version.split()[0],
            "total_files": len(file_list),
            "total_lines": total_lines,
            "directory_tree": build_tree(file_list),
        },
        "files": processed_files,
    }

    # --- Write YAML Output ---
    try:
        with open(output_file, "w", encoding="utf-8") as out:
            out.write("# ==========================================================\n")
            out.write(f"# Repository Package: {directory_name}\n")
            out.write("# Format: YAML 1.2 (LLM Source Context)\n")
            out.write(
                "# ==========================================================\n\n"
            )

            yaml.dump(
                yaml_data,
                out,
                Dumper=LiteralBlockYamlDumper,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

    except Exception as e:
        log.error(f"Failed to write output file '{output_file}': {e}")
        sys.exit(1)

    log.info("---")
    log.info(f"Packaging complete! Saved in '{output_file}'.")

    # --- File Size Check ---
    output_bytes = output_file.stat().st_size
    threshold_bytes = args.size_threshold_mb * 1024 * 1024
    output_mb = output_bytes / (1024 * 1024)

    if output_bytes > threshold_bytes:
        log.warning(
            f"Output file size ({output_mb:.2f} MB) exceeds the threshold limit of {args.size_threshold_mb} MB!"
        )


if __name__ == "__main__":
    main()

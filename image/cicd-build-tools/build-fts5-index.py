#!/usr/bin/env python3
import os
import argparse
import pathlib
import sqlite3
import fnmatch

try:
    import yaml
except ImportError:
    yaml = None


DEFAULT_INDEX_DIR = ".code_index"
DEFAULT_USE_GITIGNORE = True
DEFAULT_GITIGNORE_FILE = ".gitignore"
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".code_index",
}
DEFAULT_ALLOWED_EXTS = {
    ".py",
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".groovy",
    ".sh",
    ".js",
    ".ts",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".h",
}


def load_gitignore_patterns(
    workspace_dir: pathlib.Path, gitignore_filename: str
) -> set:
    """Read gitignore patterns matching the logic from worker daemon/agent core."""
    patterns = set()
    gitignore_path = workspace_dir / gitignore_filename

    if gitignore_path.exists():
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("!"):
                        patterns.add(line)
        except Exception as e:
            print(f"⚠️  Failed to parse {gitignore_path.name}: {e}")
    return patterns


def load_config(config_path: pathlib.Path):
    """Load configuration options from .fts5-indexer.yml if available."""
    index_dir = DEFAULT_INDEX_DIR
    use_gitignore = DEFAULT_USE_GITIGNORE
    gitignore_file = DEFAULT_GITIGNORE_FILE
    excluded_dirs = set(DEFAULT_EXCLUDED_DIRS)
    allowed_exts = set(DEFAULT_ALLOWED_EXTS)

    if config_path.is_file():
        if yaml is None:
            print("⚠️  PyYAML is not installed. Using default indexer settings.")
            return index_dir, use_gitignore, gitignore_file, excluded_dirs, allowed_exts

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                # noinspection unresolved-references
                indexer_cfg = yaml.safe_load(f) or {}

            if "index_dir" in indexer_cfg:
                index_dir = indexer_cfg["index_dir"]

            if "use_gitignore" in indexer_cfg:
                use_gitignore = bool(indexer_cfg["use_gitignore"])

            if "gitignore" in indexer_cfg:
                gitignore_file = str(indexer_cfg["gitignore"])

            if "excluded_dirs" in indexer_cfg:
                excluded_dirs = set(indexer_cfg["excluded_dirs"])

            if "allowed_exts" in indexer_cfg:
                # Ensure extensions start with a dot
                allowed_exts = {
                    ext if ext.startswith(".") else f".{ext}"
                    for ext in indexer_cfg["allowed_exts"]
                }

            print(f"⚙️  Loaded indexer configuration from {config_path}")
        except Exception as e:
            print(f"⚠️  Failed to parse {config_path} ({e}). Falling back to defaults.")
    else:
        print(f"ℹ️  No config file found at {config_path}. Using default settings.")

    # Ensure the index directory itself is excluded from file walking
    excluded_dirs.add(index_dir)

    return index_dir, use_gitignore, gitignore_file, excluded_dirs, allowed_exts


def build_fts5_index(workspace_dir: pathlib.Path, config_file: str):
    config_path = workspace_dir / config_file
    (
        index_dir_name,
        use_gitignore,
        gitignore_file,
        excluded_dirs,
        allowed_exts,
    ) = load_config(config_path)

    gitignore_patterns = set()
    if use_gitignore:
        gitignore_patterns = load_gitignore_patterns(workspace_dir, gitignore_file)

    index_dir = workspace_dir / index_dir_name
    index_dir.mkdir(parents=True, exist_ok=True)
    db_path = index_dir / "code_search.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode = DELETE;")
    cursor.execute("PRAGMA synchronous = NORMAL;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_meta (
            filepath TEXT PRIMARY KEY,
            mtime REAL
        )
    """)

    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS code_fts USING fts5(
            filepath UNINDEXED,
            filename,
            content,
            tokenize='trigram'
        )
    """)

    for root, dirs, files in os.walk(workspace_dir):
        # 1. Prune excluded directories (both default excluded_dirs and gitignore patterns)
        dirs[:] = [
            d
            for d in dirs
            if d not in excluded_dirs
            and not any(
                fnmatch.fnmatch(d, pat.rstrip("/"))
                or fnmatch.fnmatch(
                    os.path.relpath(os.path.join(root, d), workspace_dir),
                    pat.rstrip("/"),
                )
                for pat in gitignore_patterns
            )
        ]

        for file in files:
            p = pathlib.Path(root) / file
            if p.suffix.lower() in allowed_exts:
                rel_path = str(p.relative_to(workspace_dir))

                # 2. Filter out files matching gitignore patterns
                if gitignore_patterns and any(
                    fnmatch.fnmatch(rel_path, pat)
                    or fnmatch.fnmatch(rel_path, pat + "/**")
                    or fnmatch.fnmatch(file, pat)
                    for pat in gitignore_patterns
                ):
                    continue

                mtime = p.stat().st_mtime

                cursor.execute(
                    "SELECT mtime FROM file_meta WHERE filepath = ?", (rel_path,)
                )
                row = cursor.fetchone()

                if row is None or row[0] < mtime:
                    try:
                        with open(p, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        cursor.execute(
                            "DELETE FROM code_fts WHERE filepath = ?", (rel_path,)
                        )
                        cursor.execute(
                            "INSERT OR REPLACE INTO file_meta VALUES (?, ?)",
                            (rel_path, mtime),
                        )
                        cursor.execute(
                            "INSERT INTO code_fts (filepath, filename, content) VALUES (?, ?, ?)",
                            (rel_path, p.name, content),
                        )
                    except Exception as e:
                        print(f"Skipping {rel_path}: {e}")

    conn.commit()
    cursor.execute("VACUUM;")
    conn.close()
    print("✅ SQLite FTS5 index update complete.")


def main():
    parser = argparse.ArgumentParser(description="Build SQLite FTS5 Code Index")
    parser.add_argument(
        "--config",
        default=".fts5-indexer.yml",
        help="Path to YAML configuration file (default: .fts5-indexer.yml)",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Path to workspace root directory (default: current directory)",
    )

    args = parser.parse_args()
    workspace_dir = pathlib.Path(args.workspace).resolve()

    build_fts5_index(workspace_dir, args.config)


if __name__ == "__main__":
    main()

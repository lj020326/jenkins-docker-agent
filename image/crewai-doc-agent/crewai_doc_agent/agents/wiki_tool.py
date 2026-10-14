# crewai_doc_agent/agents/wiki_tool.py
"""Safe wiki markdown writer — only under wiki/ in the workspace."""

from pathlib import Path
from crewai.tools import tool

_WIKI_ROOT = "wiki"
_FORBIDDEN = ("..",)


@tool("Write Wiki Document")
def write_wiki_document(
    relative_path: str,
    content: str,
) -> str:
    """
    Write a markdown documentation file under the repository wiki/ tree.

    Args:
        relative_path: Path relative to wiki/, e.g. "roles/my-role.md"
            or "architecture/overview.md". Do NOT include a leading "wiki/".
        content: Full markdown body to write.
    """
    rel = (relative_path or "").strip().lstrip("/")
    if not rel:
        return "ERROR: relative_path is empty"

    # Normalize and block path traversal
    for bad in _FORBIDDEN:
        if bad in Path(rel).parts or bad in rel:
            return f"ERROR: invalid path component in '{relative_path}'"

    # Force under wiki/
    if rel.startswith(f"{_WIKI_ROOT}/"):
        rel = rel[len(_WIKI_ROOT) + 1 :]

    target = Path(_WIKI_ROOT) / rel
    # Ensure .md extension for doc pages
    if target.suffix.lower() not in (".md", ".markdown"):
        target = target.with_suffix(".md")

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {target.resolve()} ({len(content)} bytes)"
    except OSError as e:
        return f"ERROR writing {target}: {e}"

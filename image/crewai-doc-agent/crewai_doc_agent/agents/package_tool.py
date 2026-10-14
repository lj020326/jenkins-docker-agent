# crewai_doc_agent/agents/package_tool.py
import subprocess
import sys
from pathlib import Path
from crewai.tools import tool


@tool("Package Directory Context")
def package_directory_tool(
    directory_path: str = ".",
    strip_comments: bool = True,
    strip_blank_lines: bool = False,
) -> str:
    """
    Runs the package_dir module on a specified target directory to generate
    a token-optimized .package_dir.<directory_name>.yml file containing source code and rich metadata.

    Args:
        directory_path (str): The path to the directory to package.
            Use "." for the current workspace (Jenkins workspace / CWD).
            Do NOT invent paths like "./target-repo".
        strip_comments (bool): Whether to strip code comments to save tokens.
        strip_blank_lines (bool): Whether to remove blank lines.
    """
    # Prefer running as a module so it works regardless of CWD / PYTHONPATH
    cmd = [sys.executable, "-m", "crewai_doc_agent.package_dir"]
    if strip_comments:
        cmd.append("--strip-comments")
    if strip_blank_lines:
        cmd.append("--strip-blank-lines")
    cmd.append(directory_path)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        target_dir = Path(directory_path).resolve()
        dir_name = target_dir.name if target_dir.name else "root"
        output_file = target_dir / f".package_dir.{dir_name}.yml"

        return (
            f"Successfully packaged directory '{directory_path}'.\n"
            f"Output generated at: {output_file}\n"
            f"Command Output:\n{result.stdout.strip()}"
        )
    except subprocess.CalledProcessError as e:
        return (
            f"Failed to package directory '{directory_path}'.\n"
            f"stdout:\n{e.stdout.strip() if e.stdout else ''}\n"
            f"stderr:\n{e.stderr.strip() if e.stderr else ''}"
        )
    except FileNotFoundError as e:
        return f"Failed to package directory '{directory_path}': {e}"

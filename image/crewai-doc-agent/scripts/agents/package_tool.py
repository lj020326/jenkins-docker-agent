# agents/package_tool.py
import subprocess
from pathlib import Path
from crewai.tools import tool


@tool("Package Directory Context")
def package_directory_tool(
    directory_path: str, strip_comments: bool = False, strip_blank_lines: bool = False
) -> str:
    """
    Runs the package_dir.py script on a specified target directory to generate
    a token-optimized .package_dir.context.yml file containing source code and rich metadata.

    Args:
        directory_path (str): The path to the directory to package.
        strip_comments (bool): Whether to strip code comments to save tokens.
        strip_blank_lines (bool): Whether to remove blank lines.
    """
    script_path = Path("package_dir.py").resolve()
    if not script_path.exists():
        return f"Error: package_dir.py script not found at {script_path}"

    cmd = ["python3", str(script_path)]
    if strip_comments:
        cmd.append("--strip-comments")
    if strip_blank_lines:
        cmd.append("--strip-blank-lines")
    cmd.append(directory_path)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        target_dir = Path(directory_path).resolve()
        output_file = target_dir / ".package_dir.context.yml"

        return (
            f"Successfully packaged directory '{directory_path}'.\n"
            f"Output generated at: {output_file}\n"
            f"Command Output:\n{result.stdout.strip()}"
        )
    except subprocess.CalledProcessError as e:
        return f"Failed to package directory. Error:\n{e.stderr.strip()}"

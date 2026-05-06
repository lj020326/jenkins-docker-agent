#!/usr/bin/env python3
# scripts/generate_media.py
"""
Generates Marp slides and Matplotlib charts, then embeds links back into wiki.
"""

# scripts/generate_media.py
import argparse
import logging
from pathlib import Path

from .utils import ensure_dir, load_config, setup_logging, LLMClient

# Create a module-level logger
log = logging.getLogger(__name__)


def embed_media_links(wiki_dir: Path, media_dir: Path):
    """Scan generated media and add references to the main Wiki Index."""
    index_file = wiki_dir / "index.md"
    if not index_file.exists():
        return

    # Create a list of relative links for the media found
    media_links = ["\n## 📊 System Visuals & Charts\n"]
    for asset in media_dir.rglob("*.png"):
        rel_link = asset.relative_to(wiki_dir)
        media_links.append(f"- [{asset.stem}]({rel_link})")

    # Append to the end of the index
    with open(index_file, "a") as f:
        f.write("\n".join(media_links))


def generate_media(
    llm_client: LLMClient,
    config_path: str = ".wiki-config.yml"
):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})

    effective_wiki_dir = Path(wiki_config.get("wiki_dir"))

    # Place media inside the wiki directory to keep the structure clean
    media_dir = effective_wiki_dir / "media"
    ensure_dir(media_dir)
    ensure_dir(media_dir / "charts")

    log.debug(f"Generating media assets in {media_dir}...")

    # Placeholder - expand with actual Marp + matplotlib logic later
    # Example: create a simple index
    index = "# Generated Outputs\n\n## Slides\n\n## Charts\n"
    (media_dir / "index.md").write_text(index, encoding="utf-8")

    # Logic to generate artifacts (Matplotlib/Marp) goes here
    chart_path = media_dir / "charts" / "infrastructure_overview.png"
    # (Example: plt.savefig(chart_path))

    log.debug(f"✅ Outputs generated in {media_dir}")

    embed_media_links(effective_wiki_dir, media_dir)
    return media_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument("--debug-llm", action="store_true")
    parser.add_argument("--config", default=".wiki-config.yml")
    args = parser.parse_args()

    # Initialize the global logging config once
    setup_logging(args.verbose, debug_llm=args.debug_llm)

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

    generate_media(
        llm_client,
        config_path=args.config
    )

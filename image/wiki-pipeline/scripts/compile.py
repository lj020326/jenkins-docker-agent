#!/usr/bin/env python3
# scripts/compile.py
import argparse
from pathlib import Path
from scripts.utils import get_llm_response, ensure_dir, load_config


def compile_raw_to_wiki(raw_dir: Path,
                        wiki_dir: Path,
                        model: str = None,
                        api_base: str = None,
                        api_key: str = None,
                        verbose: bool = False,
                        config_path: str = ".wiki-config.yml"):
    config = load_config(config_path)
    wiki_config = config.get("wiki", {})
    llm_config = wiki_config.get("llm", {})
    compile_prompt = wiki_config.get("compile_prompt", {})

    ensure_dir(wiki_dir)
    for md_file in sorted(raw_dir.rglob("*.md")):
        if verbose:
            print(f"   Compiling {md_file.relative_to(raw_dir)}")

        content = md_file.read_text(encoding="utf-8")

        prompt = (
            (compile_prompt.get("prefix", "") or "") +
            f"\n\nOriginal content:\n{content[:6500]}\n\n" +
            (compile_prompt.get("suffix", "") or "")
        )

        improved = get_llm_response(
            prompt,
            model=model,
            api_base=api_base,
            api_key=api_key,
            temperature=llm_config.get("temperature"),
            max_tokens=llm_config.get("max_tokens"),
            timeout=llm_config.get("timeout"),
            verbose=verbose
        )

        target = wiki_dir / md_file.relative_to(raw_dir)
        ensure_dir(target.parent)
        target.write_text(improved, encoding="utf-8")
        print(f"   Compiled → {target.relative_to(Path('.'))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", default="raw", type=Path)
    parser.add_argument("--wiki-dir", default="wiki", type=Path)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--config", default=".wiki-config.yml")
    args = parser.parse_args()
    compile_raw_to_wiki(args.raw_dir, args.wiki_dir, verbose=args.verbose, config_path=args.config)

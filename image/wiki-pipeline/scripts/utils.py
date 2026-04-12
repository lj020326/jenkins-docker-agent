# scripts/utils.py
import os
import subprocess
import yaml
import frontmatter
from datetime import datetime
from pathlib import Path
import litellm


def get_default_config():
    """Internal defaults if .wiki-config.yml is missing"""
    return {
        "wiki": {
            "output_dir": "wiki",
            "title": "Ansible Datacenter Wiki",
            "llm": {
                "temperature": 0.25,
                "max_tokens": 4096,
                "timeout": 600
            },
            "role_prompt": {
                "prefix": "You are an expert Ansible architect and excellent technical writer.\nCreate a comprehensive, high-quality, professional documentation page.",
                "suffix": "Important notes:\n- Double-underscore variables are internal only.\n- Do not invent Related Roles.\n- Use only standard GitHub Markdown."
            },
            "compile_prompt": {
                "prefix": "You are an expert technical writer.\nImprove and standardize this documentation page for GitHub rendering.",
                "suffix": "Keep all original information. Add proper YAML frontmatter, categories, and a Backlinks section if missing.\nOutput only the improved Markdown."
            },
            "lint_prompt": {
                "prefix": "You are a strict technical documentation reviewer.\nAnalyze this documentation page for issues.",
                "suffix": "Return findings in this exact format:\n### {filename}\n**Issues:**\n- issue 1\n**Suggestions:**\n- suggestion 1"
            },
            "qa_prompt": "You are a helpful technical support engineer.\nGenerate 8-12 important Q&A pairs based on the wiki content.",
            "roles_ignore": [],
            "priority_roles": []
        }
    }


def load_config(config_path: str = ".wiki-config.yml"):
    path = Path(config_path)
    if not path.exists():
        print(f"Warning: {config_path} not found. Using internal defaults.")
        return get_default_config()

    try:
        with open(path, encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
            default = get_default_config()
            # Deep merge user config over defaults
            default["wiki"].update(user_config.get("wiki", {}))
            return default
    except Exception as e:
        print(f"Warning: Could not load {config_path}: {e}. Using defaults.")
        return get_default_config()


def get_llm_response(
        prompt: str,
        model: str = None,
        api_base: str = None,
        api_key: str = None,
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        verbose: bool = False
) -> str:
    model = model or os.getenv("LLM_MODEL", "qwen2.5-coder:32b")
    api_base = api_base or os.getenv("OPENAI_API_BASE", "http://gpu02.johnson.int:11434/v1")

    # Determine if we're talking to Ollama
    is_ollama = api_base and ("11434" in api_base or "ollama" in str(api_base).lower())

    if is_ollama:
        if not model.startswith("ollama/") and not model.startswith("openai/"):
            model = f"openai/{model}"

        # These two lines are critical
        litellm.custom_llm_provider = "openai"
        litellm.api_base = api_base

        # litellm.suppress_debug_info = True
        litellm.use_client = True

        # Ollama uses "ollama" as the dummy key for OpenAI-compatible endpoint
        effective_api_key = api_key or "ollama"
    else:
        effective_api_key = api_key or os.getenv("OPENAI_API_KEY", "dummy-key")

    # This line prevents LiteLLM from trying to pull the remote JSON file at
    # https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json
    litellm.set_callbacks = []

    if verbose:
        print(f"DEBUG: Using model = '{model}' | api_base = '{api_base}' | api_key = '{effective_api_key}'")
        # print(f"DEBUG: prompt='{prompt}'")  # ← helpful for debugging

    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            api_base=api_base,
            api_key=effective_api_key,
            temperature=temperature or 0.25,
            max_tokens=max_tokens or 4096,
            timeout=timeout or 600,
        )
        content = response.choices[0].message.content.strip()
        if verbose:
            print(f"DEBUG: Success - Received {len(content)} characters")
        return content
    except Exception as e:
        print(f"ERROR calling LLM: {type(e).__name__}: {e}")
        raise


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def add_frontmatter(md_content: str, metadata: dict) -> str:
    post = frontmatter.Post(md_content, **metadata)
    return frontmatter.dumps(post)


def relative_link(target: str, from_path: Path) -> str:
    return os.path.relpath(target, start=from_path.parent)


def is_ignored_by_git(path: Path, repo_root: Path) -> bool:
    """Return True if path is ignored by .gitignore"""
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", str(path.relative_to(repo_root))],
            cwd=repo_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception:
        return False

# scripts/utils.py
import fnmatch
import hashlib
import logging
import os
import subprocess
import time
from pathlib import Path

import frontmatter
import litellm
import yaml

# Module-level cache for configuration (loaded once per process)
_config_cache = None


class LLMClient:
    def __init__(self, config_path=".wiki-config.yml", overrides=None):
        # 1. Load configuration once
        self.config = self._load_config(config_path)
        llm_cfg = self.config.get("wiki", {}).get("llm", {})
        overrides = overrides or {}

        # 2. Set core connection parameters
        self.model = overrides.get("model") or llm_cfg.get("model")
        self.api_base = overrides.get("api_base") or llm_cfg.get("api_base")
        self.api_key = overrides.get("api_key") or llm_cfg.get("api_key", "dummy-key")
        self.provider = overrides.get("provider") or llm_cfg.get("provider", "openai")

        # 3. Apply LiteLLM SDK initializations
        self._initialize_litellm(llm_cfg, overrides.get("debug_llm"))

        # 4. Set default generation parameters
        self.default_params = {
            "temperature": llm_cfg.get("temperature", 0.25),
            "max_tokens": llm_cfg.get("max_tokens", 4096),
            "timeout": llm_cfg.get("timeout", 900)
        }

    @staticmethod
    def get_default_config():
        """Internal defaults if .wiki-config.yml is missing"""
        return {
            "wiki": {
                "output_dir": "wiki",
                "title": "Ansible Datacenter Wiki",
                "llm": {
                    "model": "qwen2.5-coder:32b",
                    "api_base": "http://gpu02.johnson.int:11434/v1",
                    "api_key": "dummy-key",
                    "provider": "openai",
                    "temperature": 0.25,
                    "max_tokens": 4096,
                    "timeout": 1200
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

    def _load_config(self, path):
        if not Path(path).exists():
            return self.get_default_config()
            return {"wiki": {"llm": {}}}  # Fallback to defaults
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}

    def _initialize_litellm(self, cfg, debug_override):
        """Perform one-time SDK setup """
        litellm.skip_model_info_query = cfg.get("skip_model_info_query", True)
        litellm.use_local_model_cost_map = cfg.get("use_local_model_cost_map", True)
        litellm.suppress_helper_warnings = cfg.get("suppress_helper_warnings", True)

        if debug_override or cfg.get("debug_llm"):
            litellm._turn_on_debug()

        litellm.api_base = self.api_base

        model_cost_map_default = {
            "qwen2.5-coder:32b": {
                "max_tokens": 32768,
                "input_cost_per_token": 0,
                "output_cost_per_token": 0,
                "lite_llm_model_name": "qwen2.5-coder:32b",
                "model_name": "qwen2.5-coder:32b"
            }
        }
        model_cost_map = cfg.get("model_cost_map", model_cost_map_default)
        # If using custom models, it's often best to provide a dummy map to stop the search
        # litellm.model_cost_map = model_cost_map
        litellm.register_model(model_cost_map)

        # Register custom model if provider prefix is missing
        if self.provider and not self.model.startswith(f"{self.provider}/"):
            self.model = f"{self.provider}/{self.model}"

    def get_response(self, prompt, **kwargs):
        """Refactored class method for LLM calls """
        params = {**self.default_params, **kwargs}
        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.api_key,
                **params
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            # Log it if you want, but re-raise so the caller knows it failed
            logging.error(f"LLM Error: {type(e).__name__}: {e}")
            raise


def load_config(config_path: str = ".wiki-config.yml", force_reload: bool = False):
    """Load config with module-level caching"""
    global _config_cache

    if _config_cache is not None and not force_reload:
        return _config_cache

    path = Path(config_path)
    if not path.exists():
        print(f"Warning: {config_path} not found. Using internal defaults.")
        _config_cache = LLMClient.get_default_config()
        return _config_cache

    try:
        with open(path, encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
            default = LLMClient.get_default_config()
            default["wiki"].update(user_config.get("wiki", {}))
            _config_cache = default
            return _config_cache
    except Exception as e:
        print(f"Warning: Could not load {config_path}: {e}. Using defaults.")
        _config_cache = LLMClient.get_default_config()
        return _config_cache


def get_role_fingerprint(role_path):
    """Creates a MD5 hash of the functional parts of a role."""
    relevant_files = ["tasks/main.yml", "defaults/main.yml", "meta/main.yml"]
    combined_content = ""

    for file_name in relevant_files:
        p = role_path / file_name
        if p.exists():
            # Use the compaction logic here: strip comments/whitespace
            lines = [l.strip() for l in p.read_text().splitlines()
                     if l.strip() and not l.strip().startswith("#")]
            combined_content += "".join(lines)

    return hashlib.md5(combined_content.encode()).hexdigest()


# Rest of utility functions remain unchanged
def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def add_frontmatter(md_content: str, metadata: dict) -> str:
    post = frontmatter.Post(md_content, **metadata)
    return frontmatter.dumps(post)


def relative_link(target: str, from_path: Path) -> str:
    return os.path.relpath(target, start=from_path.parent)


def should_ignore_path(path: Path, ignore_patterns: list) -> bool:
    path_str = str(path)
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(path_str, pattern) or pattern in path_str:
            return True
    return False


def is_ignored(path, ignore_patterns):
    """
    Checks if a path should be ignored based on glob patterns.
    Works with both string paths and pathlib.Path objects.
    """
    # Convert pathlib object to string for pattern matching
    path_str = str(path)
    path_parts = Path(path).parts  # Provides a tuple of directory segments

    for pattern in ignore_patterns:
        # 1. Direct glob matching (e.g., **/vault.yml)
        if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(os.path.basename(path_str), pattern):
            return True

        # 2. Directory-specific matching (e.g., 'docs/')
        if pattern.endswith('/'):
            clean_pattern = pattern.strip('/')
            if clean_pattern in path_parts:
                return True

    return False


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

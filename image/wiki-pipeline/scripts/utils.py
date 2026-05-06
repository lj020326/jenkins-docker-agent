# scripts/utils.py
import fnmatch
import hashlib
import json
import logging
import os
import pathspec
import pprint
import subprocess
import sys
from pathlib import Path

import frontmatter
import litellm
import yaml

# Module-level cache for configuration (loaded once per process)
_config_cache = None
# Define TRACE level (lower than DEBUG)
TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


def trace(self, message, *args, **kws):
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, message, args, **kws)


logging.Logger.trace = trace

# Create a module-level logger
log = logging.getLogger(__name__)


def setup_logging(verbose_level: int, debug_llm: bool = False):
    """
    verbose_level:
        Maps CLI verbosity to standard logging levels.
        0: INFO (Done..., Error...)
        1: DEBUG (-v)
        2+: TRACE (-vv)
    debug_llm:
        If True, sets litellm to DEBUG.
        If False, keeps litellm at WARNING.
    """

    # Configure the root logger
    logging.basicConfig(
        level=logging.WARNING,
        format='[%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # logging.basicConfig(
    #     level=logging.WARNING,
    #     format="%(asctime)s [%(levelname)s] %(message)s",
    #     datefmt="%Y-%m-%d %H:%M:%S",
    #     handlers=[
    #         logging.StreamHandler(sys.stdout)
    #     ]
    # )

    # 2. Define the level for OUR scripts
    if verbose_level >= 2:
        level = TRACE_LEVEL
    elif verbose_level == 1:
        level = logging.DEBUG
    else:
        level = logging.INFO

    log.debug(f"debug_llm={debug_llm}")

    # 3. Configure the 'scripts' parent logger
    # Every file that starts with 'from .utils import log' or
    # 'logging.getLogger(__name__)' will now inherit this level.
    pipeline_logger = logging.getLogger("scripts")
    pipeline_logger.setLevel(level)

    # List of noisy external loggers to control
    llm_loggers = ["litellm", "openai", "httpcore", "httpx"]

    for logger_name in llm_loggers:
        external_logger = logging.getLogger(logger_name)
        if debug_llm:
            log.debug(f"logger({logger_name}).setLevel=logging.DEBUG")
            external_logger.setLevel(logging.DEBUG)
            external_logger.propagate = True
        else:
            log.trace(f"logger({logger_name}).setLevel=logging.WARNING")
            external_logger.setLevel(logging.WARNING)
            # Prevent these from sending their debug logs up to your DEBUG root logger
            external_logger.propagate = False

    # Log the status of your internal debug flag
    log.debug(f"Logging initialized: level={level}, debug_llm={debug_llm}")

    # # Some versions of LiteLLM also use a 'LiteLLM' logger (capitalized)
    # logging.getLogger("LiteLLM").setLevel(logging.WARNING)


def get_default_config():
    """Internal defaults if .wiki-config.yml is missing"""
    log.trace("getting default configs")
    return {
        "wiki": {
            "wiki_dir": "wiki",
            "wiki_state_dir": ".wiki",
            "harvest_rglob_patterns": [
                "./*.md",
                "**/docs/**/*.md",
                "**/playbooks/**/*.md",
                "**/roles/**/*.md",
                "**/vars/**/*.md"
            ],
            "harvest_ignore": [
                ".continue/", "archive/", "inventory/",
                "molecule/", "plugins/", "save/", "tests/"
            ],
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
        self._initialize_litellm(llm_cfg, overrides.get("debug_llm", False))

        # 4. Set default generation parameters
        self.default_params = {
            "temperature": llm_cfg.get("temperature", 0.25),
            "max_tokens": llm_cfg.get("max_tokens", 4096),
            "timeout": llm_cfg.get("timeout", 900)
        }

    def _load_config(self, config_path):
        return load_config(config_path)

    def _initialize_litellm(self, cfg, debug_override=False):
        """Perform one-time SDK setup """
        litellm.skip_model_info_query = cfg.get("skip_model_info_query", True)
        litellm.use_local_model_cost_map = cfg.get("use_local_model_cost_map", True)
        litellm.suppress_helper_warnings = cfg.get("suppress_helper_warnings", True)

        turn_on_debug = debug_override or cfg.get("debug_llm", False)
        # log.debug(f"debug_override={debug_override}")
        # log.debug(f"cfg.get('debug_llm', False)={cfg.get('debug_llm', False)}")
        # log.debug(f"turn_on_debug={turn_on_debug}")

        if turn_on_debug:
            log.debug(f"turning on litellm debug")
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

    wiki_config = get_default_config()

    log.debug(f"config_path={config_path}")
    path = Path(config_path)
    if not path.exists():
        log.warning(f"{config_path} not found. Using internal defaults.")

    if os.path.exists(config_path):
        with open(path, encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
            # Deep merge user_config into defaults
            # (Ensuring 'wiki' sub-keys are handled)
            wiki_config["wiki"].update(user_config.get("wiki"))

    _config_cache = wiki_config
    # log.debug("_config_cache=\n" + pprint.pformat(_config_cache))

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


def get_content_fingerprint(target_path: Path, ignore_patterns: list = None) -> str:
    """
    Generates a deterministic hash for a file or a directory.
    If directory: hashes filenames and contents of all non-ignored files.
    """
    hash_obj = hashlib.sha256()

    if not target_path.exists():
        return ""

    if target_path.is_file():
        hash_obj.update(target_path.read_bytes())
    else:
        # For directories (like Ansible roles), walk and hash contents
        # Sort to ensure the hash is deterministic
        files = sorted([f for f in target_path.rglob("*") if f.is_file()])
        for file in files:
            if ignore_patterns and is_ignored(file, ignore_patterns):
                continue
            # Hash path relative to target and the content
            hash_obj.update(str(file.relative_to(target_path)).encode())
            hash_obj.update(file.read_bytes())

    return hash_obj.hexdigest()


def get_effective_paths(wiki_config: dict):
    """
    Helper to resolve the directory structure.
    """
    state_dir = Path(wiki_config.get("wiki_state_dir", ".wiki"))
    ensure_dir(state_dir)
    return {
        "wiki_dir": Path(wiki_config.get("wiki_dir", "wiki")),
        "state_dir": state_dir,
        "raw_dir": state_dir / "raw",
        "state_file": state_dir / ".wiki-state.json"
    }


def load_state(file_path: Path) -> dict:
    if file_path.exists():
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state_path: Path, state: dict):
    """Saves the state dictionary to the defined path."""
    ensure_dir(state_path.parent)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


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


def is_ignored(path, ignore_patterns, spec=None):
    """
    Checks if a path should be ignored using git-style wildmatch patterns.
    Optimized to use a pre-compiled pathspec object.
    """
    if not ignore_patterns and spec is None:
        return False

    path_str = str(path)
    path_obj = Path(path)

    # 1. Primary Logic: Use pre-compiled spec or compile on the fly
    if spec:
        if spec.match_file(path_str):
            return True
    else:
        # Fallback for single-use calls
        temp_spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
        if temp_spec.match_file(path_str):
            return True

    # 2. Legacy/Fallback Logic for specific filename matches
    # This ensures consistency with existing Ansible/DevOps governance[cite: 1, 5]
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(os.path.basename(path_str), pattern):
            return True
        if path_obj.match(pattern):
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

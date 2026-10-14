# scripts/utils.py
import fnmatch
import frontmatter
import hashlib
import json
import litellm
import logging
import os
import pathspec
import pprint
import re
import requests
import sqlite3
import subprocess
import sys
import yaml
from pathlib import Path
from requests.auth import HTTPBasicAuth

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
        format="[%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # 2. Define the level for OUR scripts
    if verbose_level >= 2:
        level = TRACE_LEVEL
    elif verbose_level == 1:
        level = logging.DEBUG
    else:
        level = logging.INFO

    # 3. Configure the 'scripts' parent logger
    pipeline_logger = logging.getLogger("scripts")
    pipeline_logger.setLevel(level)

    log.debug(f"debug_llm={debug_llm}")

    # List of noisy external loggers to control
    llm_loggers = ["litellm", "openai", "httpcore", "httpx"]

    for logger_name in llm_loggers:
        external_logger = logging.getLogger(logger_name)
        if debug_llm:
            log.debug(f"logger({logger_name}).setLevel=logging.DEBUG")
            external_logger.setLevel(logging.DEBUG)
            external_logger.propagate = True
        else:
            # noinspection PyUnresolvedReferences
            log.trace(f"logger({logger_name}).setLevel=logging.WARNING")
            external_logger.setLevel(logging.WARNING)
            # Prevent these from sending their debug logs up to your DEBUG root logger
            external_logger.propagate = False

    # Log the status of your internal debug flag
    log.debug(f"Logging initialized: level={level}, debug_llm={debug_llm}")


def get_default_config():
    """Internal defaults if .wiki-config.yml is missing"""
    # noinspection PyUnresolvedReferences
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
                "**/vars/**/*.md",
            ],
            "harvest_ignore": [
                ".continue/",
                "archive/",
                "docs/",
                "inventory/",
                "molecule/",
                "plugins/",
                "save/",
                "tests/",
                "venv/",
            ],
            "ingest_ignore": ["**/vars/vault.yml", "venv/", "molecule/"],
            "title": "Ansible Datacenter Wiki",
            "llm": {
                "model": "qwen2.5-coder:32b",
                "api_base": "http://gpu02.example.int:11434/v1",
                "api_key": "dummy-key",
                "provider": "openai",
                "temperature": 0.25,
                "max_tokens": 4096,
                "timeout": 1200,
            },
            "role_prompt": {
                "system": "You are an expert Ansible architect and excellent technical writer.\nYour task is to create a comprehensive, high-quality, professional documentation page for an Ansible role.\nFollow GitHub Markdown specifications strictly (no Obsidian syntax).\n",
                "user": "Role Path: {rel_role_path}\n\n### Role Source Files:\n{files_section}\n\n{readme_section}\n\n{usage_section}\n\nRequirements:\n- Start with clean YAML frontmatter (title, role, category, type, tags).\n- Provide a one-paragraph summary of the role's purpose.\n- Include sections: Variables, Usage, Dependencies, Tags, Best Practices, and Molecule Tests (if any).\n- Include a '## Backlinks' section with relative paths back to original role files (e.g., `../../roles/{role_name}/defaults/main.yml`).\n- Never document double-underscore variables (e.g., `__internal_var`) as user-configurable.\n- Do not invent related roles that do not exist in the repository.\n",
            },
            "compile_prompt": {
                "system": "You are an expert technical writer specializing in documentation standardization.\nImprove and standardize documentation pages for GitHub rendering while preserving all original information and meaning.\n",
                "user": 'Original content:\n{content}\n\nInstructions:\n- Add or improve YAML frontmatter (title, original_path, category, tags).\n- Ensure clear structure, proper headings, and a "Backlinks" section if missing.\n- Output only the improved Markdown.\n',
            },
            "lint_prompt": {
                "system": "You are a strict technical documentation reviewer analyzing Markdown files for quality, consistency, and completeness.\n",
                "user": "File: {file_id}\n\nContent:\n{truncated_content}\n\nAnalyze the document and return findings in this exact format only:\n### {file_id}\n**Issues:**\n- issue 1\n- issue 2\n**Suggestions:**\n- suggestion 1\n- suggestion 2\n",
            },
            "qa_prompt": {
                "system": "You are a helpful technical support engineer for this Ansible datacenter repository.\n",
                "user": "Generate 8-12 important, frequently asked Q&A pairs based on the content of this wiki.\nFocus on common user questions, troubleshooting steps, best practices, and gotchas.\nFormat as a clean Q&A list using Markdown.\n",
            },
        }
    }


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
    # noinspection PyUnresolvedReferences
    log.trace("_config_cache=\n" + pprint.pformat(_config_cache))

    return _config_cache


def render_yaml_prompt(prompt_config, **kwargs) -> list[dict]:
    """
    Renders a YAML-based prompt structure (containing system and user sections)
    into standard OpenAI/LiteLLM chat messages format: [{'role': 'system', ...}, {'role': 'user', ...}]
    """
    messages = []
    if not isinstance(prompt_config, dict):
        # Fallback if a plain string was provided in legacy configs
        return [{"role": "user", "content": str(prompt_config).format(**kwargs)}]

    system_tmpl = prompt_config.get("system", "")
    if system_tmpl:
        system_content = system_tmpl.format(**kwargs)
        messages.append({"role": "system", "content": system_content.strip()})

    user_tmpl = prompt_config.get("user", "")
    if user_tmpl:
        user_content = user_tmpl.format(**kwargs)
        messages.append({"role": "user", "content": user_content.strip()})
    elif not messages:
        # Fallback if neither system nor user keys exist but it's a dict
        messages.append(
            {"role": "user", "content": str(prompt_config).format(**kwargs)}
        )

    return messages


class IndexHelper:
    """Interface for querying the sqlite3 FTS5 index generated by runIndexerPipeline.groovy."""

    def __init__(self, repo_root: Path, index_dir: str = ".code_index"):
        self.db_path = repo_root / index_dir / "code_search.db"
        self.enabled = self.db_path.exists()

    def search_code(self, query_term: str, limit: int = 10) -> list:
        if not self.enabled:
            return []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT filepath, snippet(code_fts, 2, '<b>', '</b>', '...', 10)
                FROM code_fts
                WHERE code_fts MATCH ?
                LIMIT ?
                """,
                (query_term, limit),
            )
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            logging.debug(f"Index query failed for '{query_term}': {e}")
            return []

    def find_role_dependents(self, role_name: str) -> list:
        """Find playbooks or roles referencing this role via include_role/import_role."""
        if not self.enabled:
            return []
        query = f'"role: {role_name}" OR "{role_name}"'
        matches = self.search_code(query, limit=20)
        return [m[0] for m in matches if m[0].endswith((".yml", ".yaml"))]


class LLMClient:
    def __init__(self, config_path=".wiki-config.yml", overrides=None):
        # 1. Load configuration once
        self.config = self._load_config(config_path)
        llm_cfg = self.config.get("wiki", {}).get("llm", {})
        overrides = overrides or {}

        # 2. Set core connection parameters
        self.model = overrides.get("model") or llm_cfg.get("model")
        self.provider = overrides.get("provider") or llm_cfg.get("provider", "openai")
        self.api_base = overrides.get("api_base") or llm_cfg.get("api_base")

        # Capture auth_type configuration (supports "basic" or standard/bearer)
        self.auth_type = (
            overrides.get("auth_type") or llm_cfg.get("auth_type") or "bearer"
        ).lower()

        # Resolve API Key from cfg -> env vars -> fallback for local backends
        self.api_key = (
            overrides.get("api_key")
            or llm_cfg.get("api_key")
            or os.getenv("LLM_API_KEY")
            or os.getenv("VLLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("LITELLM_API_KEY")
            or ""
        )

        # 3. Setup system CA bundle paths for requests & SSL verification
        self.verify_cert = self._resolve_ca_bundle()

        # 4. Apply LiteLLM SDK initializations
        self._initialize_litellm(llm_cfg, overrides.get("debug_llm", False))

        # 5. Set default generation parameters
        self.default_params = {
            "temperature": llm_cfg.get("temperature", 0.25),
            "max_tokens": llm_cfg.get("max_tokens", 4096),
            "timeout": llm_cfg.get("timeout", 900),
        }

        # 6. Perform health check on initialization to fail fast if unreachable
        self._check_health()

    @staticmethod
    def _load_config(config_path):
        return load_config(config_path)

    def _resolve_ca_bundle(self):
        """
        Determines the appropriate CA bundle path from system locations
        or environment overrides so that Python 'requests' and 'litellm' trust
        custom/corporate root certificates mounted in containers.
        """
        # If explicitly provided via environment variables, respect them first
        env_bundle = os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("SSL_CERT_FILE")
        if env_bundle and os.path.exists(env_bundle):
            log.debug(f"Using CA bundle from environment: {env_bundle}")
            return env_bundle

        # Common Linux container system CA bundle locations
        candidate_paths = [
            "/etc/ssl/certs/ca-certificates.crt",  # Debian / Ubuntu / Alpine
            "/etc/pki/tls/certs/ca-bundle.crt",  # RHEL / CentOS / Fedora
            "/etc/ssl/cert.pem",  # General OpenSSL
        ]

        for path in candidate_paths:
            if os.path.exists(path):
                log.debug(f"Found system CA bundle at: {path}")
                # Export environment variables so underlying libraries (like httpx/certifi/requests) use it too
                os.environ.setdefault("REQUESTS_CA_BUNDLE", path)
                os.environ.setdefault("SSL_CERT_FILE", path)
                return path

        # Fallback to True (default certifi store) if no system bundle is explicitly found
        log.warning(
            "No standard system CA bundle found in common paths. Falling back to default certifi bundle."
        )
        return True

    def _check_health(self):
        """
        Performs a health check against the LLM/Ollama endpoint mirroring curl probes.
        Sends a GET request to /api/tags with Basic or Bearer Authentication as configured.
        """
        base_url = self.api_base.rstrip("/")

        # Determine tags endpoint based on common Ollama/vLLM structures
        if base_url.endswith("/v1"):
            # OpenAI compatible API
            tags_url = f"{base_url}/models"
            root_url = base_url[:-3]
        elif base_url.endswith("/api"):
            tags_url = f"{base_url}/tags"
            root_url = base_url[:-4]
        else:
            tags_url = f"{base_url}/api/tags"
            root_url = base_url

        headers = {}
        auth = None

        if self.api_key:
            if self.auth_type == "basic":
                if ":" in self.api_key:
                    user, pwd = self.api_key.split(":", 1)
                    auth = HTTPBasicAuth(user, pwd)
                else:
                    headers["Authorization"] = f"Basic {self.api_key}"
            else:
                headers["Authorization"] = f"Bearer {self.api_key}"

        log.info(f"🔍 Verifying connection to LLM endpoint: {tags_url}")
        try:
            response = requests.get(
                tags_url,
                headers=headers,
                auth=auth,
                timeout=min(self.default_params.get("timeout", 10), 10),
                verify=self.verify_cert,
            )
            response.raise_for_status()

            log.info(f"✅ Successfully connected to LLM endpoint: {root_url}")
            # Parse and log available models at DEBUG level
            data = response.json()
            models = []

            if "models" in data:  # Ollama native /api/tags format
                models = [m.get("name") for m in data.get("models", [])]
            elif "data" in data:  # OpenAI /v1/models format
                models = [m.get("id") for m in data.get("data", [])]

            if models:
                log.debug(
                    f"📋 Available models at endpoint ({len(models)}): {', '.join(models)}"
                )
            else:
                log.debug(
                    "📋 Connected successfully, but no models were returned or unrecognized format."
                )
        except requests.exceptions.RequestException as e:
            log.error(
                f"💥 Connection error or SSL validation failure to LLM endpoint [{tags_url}]: {e}"
            )
            raise ConnectionError(
                f"Connection error/SSL validation failure to LLM endpoint at {tags_url}: {e}"
            ) from e

    def _initialize_litellm(self, cfg: dict, debug_override: bool = False):
        """Perform one-time SDK setup"""
        litellm.skip_model_info_query = cfg.get("skip_model_info_query", True)
        litellm.use_local_model_cost_map = cfg.get("use_local_model_cost_map", True)
        litellm.suppress_helper_warnings = cfg.get("suppress_helper_warnings", True)
        litellm.suppress_debug_info = cfg.get("suppress_debug_info", True)

        turn_on_debug = debug_override or cfg.get("debug_llm", False)

        if turn_on_debug:
            log.debug("turning on litellm debug")
            # noinspection protected-member
            litellm._turn_on_debug()

        # Set API base URL
        log.info(f"api_base={self.api_base}")
        litellm.api_base = self.api_base

        # Assign unified api_key to LiteLLM and environment
        log.debug(f"api_key={self.api_key}")
        litellm.api_key = self.api_key

        # Flexible local cost map supporting both GPU host endpoints
        model_cost_map_default = {
            "devstral:24b": {
                "max_tokens": 16384,
                "cache_creation_input_token_cost": 0,
                "cache_read_input_token_cost": 0,
                "input_cost_per_token": 0,
                "output_cost_per_token": 0,
            },
            "deepseek-r1:14b": {
                "max_tokens": 16384,
                "cache_creation_input_token_cost": 0,
                "cache_read_input_token_cost": 0,
                "input_cost_per_token": 0,
                "output_cost_per_token": 0,
            },
            "qwen2.5-coder:7b": {
                "max_tokens": 16384,
                "cache_creation_input_token_cost": 0,
                "cache_read_input_token_cost": 0,
                "input_cost_per_token": 0,
                "output_cost_per_token": 0,
            },
            "qwen2.5-coder:32b": {
                "max_tokens": 16384,
                "cache_creation_input_token_cost": 0,
                "cache_read_input_token_cost": 0,
                "input_cost_per_token": 0,
                "output_cost_per_token": 0,
            },
            "qwen3.5:27b": {
                "max_tokens": 16384,
                "cache_creation_input_token_cost": 0,
                "cache_read_input_token_cost": 0,
                "input_cost_per_token": 0,
                "output_cost_per_token": 0,
            },
            "llama3.1:8b": {
                "max_tokens": 8192,
                "cache_creation_input_token_cost": 0,
                "cache_read_input_token_cost": 0,
                "input_cost_per_token": 0,
                "output_cost_per_token": 0,
            },
        }

        # Merge user config map into defaults if present
        model_cost_map = model_cost_map_default.copy()
        user_cost_map = cfg.get("model_cost_map", {})
        if user_cost_map:
            model_cost_map.update(user_cost_map)

        # Register custom model if provider prefix is missing
        if self.provider and not self.model.startswith(f"{self.provider}/"):
            # Ensure prefixed model variant is also in LiteLLM cost map
            prefixed_model = f"{self.provider}/{self.model}"
            if self.model in model_cost_map and prefixed_model not in model_cost_map:
                model_cost_map[prefixed_model] = model_cost_map[self.model].copy()
                model_cost_map[prefixed_model]["model_name"] = prefixed_model
            self.model = prefixed_model

        litellm.register_model(model_cost_map)

    def get_response(self, prompt_or_messages, **kwargs):
        """Refactored class method for LLM calls accepting strings or message lists"""
        params = {**self.default_params, **kwargs}
        extra_headers = kwargs.pop("extra_headers", {})

        if self.auth_type == "basic" and self.api_key:
            if ":" in self.api_key:
                import base64

                encoded_bytes = base64.b64encode(self.api_key.encode("utf-8"))
                extra_headers["Authorization"] = (
                    f"Basic {encoded_bytes.decode('utf-8')}"
                )
            else:
                extra_headers["Authorization"] = f"Basic {self.api_key}"

        # Support passing either raw messages list or a single prompt string
        if isinstance(prompt_or_messages, list):
            messages = prompt_or_messages
        else:
            messages = [{"role": "user", "content": prompt_or_messages}]

        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                api_key=self.api_key if self.auth_type != "basic" else None,
                extra_headers=extra_headers if extra_headers else None,
                **params,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"LLM Error: {type(e).__name__}: {e}")
            raise


def get_role_fingerprint(role_path):
    """Creates a MD5 hash of the functional parts of a role."""
    relevant_files = ["tasks/main.yml", "defaults/main.yml", "meta/main.yml"]
    combined_content = ""

    for file_name in relevant_files:
        p = role_path / file_name
        if p.exists():
            # Use the compaction logic here: strip comments/whitespace
            lines = [
                line.strip()
                for line in p.read_text().splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
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
        "state_file": state_dir / ".wiki-state.json",
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


def strip_code_fences(text: str) -> str:
    """Eliminates unnecessary top-level markdown code fences from LLM responses."""
    text = text.strip()
    match = re.match(r"^```[a-zA-Z0-9_-]*\n([\s\S]*?)\n```$", text)
    if match:
        return match.group(1).strip()
    return text


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
        temp_spec = pathspec.PathSpec.from_lines("gitwildmatch", ignore_patterns)
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
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False

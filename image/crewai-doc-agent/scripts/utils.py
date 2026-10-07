import os
import logging
import requests
import yaml
from pathlib import Path
from requests.auth import HTTPBasicAuth
import litellm

log = logging.getLogger(__name__)


def load_config(config_path: str = ".crewai-config.yml") -> dict:
    path = Path(config_path)
    if not path.exists():
        log.warning(f"⚠️ Config file not found at {config_path}. Using defaults.")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class LLMClient:
    def __init__(self, config_path=".crewai-config.yml", overrides=None):
        self.config = load_config(config_path)
        llm_cfg = self.config.get("llm", {})
        overrides = overrides or {}

        self.model = overrides.get("model") or llm_cfg.get("model", "qwen2.5-coder:32b")
        self.provider = overrides.get("provider") or llm_cfg.get("provider", "openai")
        self.api_base = overrides.get("api_base") or llm_cfg.get(
            "api_base", "http://localhost:11434/v1"
        )
        self.auth_type = (
            overrides.get("auth_type") or llm_cfg.get("auth_type") or "bearer"
        ).lower()

        self.api_key = (
            overrides.get("api_key")
            or llm_cfg.get("api_key")
            or os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "dummy-key"
        )

        self.verify_cert = self._resolve_ca_bundle()
        self._initialize_litellm(llm_cfg)
        self._check_health()

    def _resolve_ca_bundle(self):
        env_bundle = os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("SSL_CERT_FILE")
        if env_bundle and os.path.exists(env_bundle):
            return env_bundle

        candidate_paths = [
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/pki/tls/certs/ca-bundle.crt",
            "/etc/ssl/cert.pem",
        ]
        for path in candidate_paths:
            if os.path.exists(path):
                os.environ.setdefault("REQUESTS_CA_BUNDLE", path)
                os.environ.setdefault("SSL_CERT_FILE", path)
                return path
        return True

    def _check_health(self):
        base_url = self.api_base.rstrip("/")
        if base_url.endswith("/v1"):
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

        log.info(
            f"🔍 Verifying connection to LLM endpoint: {tags_url} (Auth: {self.auth_type})"
        )
        try:
            response = requests.get(
                tags_url,
                headers=headers,
                auth=auth,
                timeout=10,
                verify=self.verify_cert,
            )
            response.raise_for_status()
            log.info(f"✅ Successfully connected to LLM endpoint: {root_url}")
        except requests.exceptions.RequestException as e:
            log.error(
                f"💥 Connection error or SSL validation failure to LLM endpoint [{tags_url}]: {e}"
            )
            raise ConnectionError(
                f"Connection error/SSL validation failure to LLM endpoint at {tags_url}: {e}"
            ) from e

    def _initialize_litellm(self, cfg: dict):
        litellm.skip_model_info_query = cfg.get("skip_model_info_query", True)
        litellm.use_local_model_cost_map = cfg.get("use_local_model_cost_map", True)
        litellm.suppress_helper_warnings = True
        litellm.suppress_debug_info = True

        litellm.api_base = self.api_base
        litellm.api_key = self.api_key

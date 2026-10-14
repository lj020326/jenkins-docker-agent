# crewai_doc_agent/crew.py
import os
import subprocess
from pathlib import Path

from crewai import Agent, Crew, Process, Task
from crewai_doc_agent.agents.package_tool import package_directory_tool
from crewai_doc_agent.agents.wiki_tool import write_wiki_document

# Workspace-local storage for LanceDB / CrewAI memory (must be writable in CI).
# Override with CREWAI_STORAGE_DIR in the environment if needed.
_DEFAULT_STORAGE = Path(".agent_state") / "crewai"
# Prefer an embedding model you already host (from healthcheck model list)
_DEFAULT_EMBED_MODEL = "nomic-embed-text"

# Ansible-oriented defaults; override via env
_PRIORITY_PARENTS = ("roles", "inventory", "playbooks", "collections")


def _ensure_memory_storage() -> Path:
    """Resolve and create the CrewAI/LanceDB storage directory."""
    storage_root = Path(
        os.environ.get("CREWAI_STORAGE_DIR", str(_DEFAULT_STORAGE))
    ).resolve()
    storage_root.mkdir(parents=True, exist_ok=True)
    # Ensure env is set so LanceDBStorage picks it up ($CREWAI_STORAGE_DIR/memory)
    os.environ["CREWAI_STORAGE_DIR"] = str(storage_root)
    return storage_root


def _build_embedder(api_base: str, api_key: str, embed_model: str) -> dict:
    """
    Point memory embeddings at the same OpenAI-compatible Ollama endpoint
    used for chat — NOT api.openai.com.

    Ollama serves embeddings at {api_base}/embeddings (e.g. .../v1/embeddings).
    """
    # CrewAI ollama provider wants the native embeddings URL in some versions;
    # openai provider works against Ollama's /v1-compatible API.
    return {
        "provider": "openai",
        "config": {
            "model_name": embed_model,
            "api_key": api_key or "dummy-key",
            "api_base": api_base.rstrip("/"),
        },
    }


def detect_repo_type(target_dir: Path) -> str:
    """
    Lightweight auto-detection of repository kind.
    Expand via TODO.md roadmap (python, java, rust, golang, …).
    """
    if (target_dir / "roles").is_dir() and (
        (target_dir / "playbooks").is_dir()
        or (target_dir / "ansible.cfg").is_file()
        or (target_dir / "inventory").is_dir()
    ):
        return "ansible-playbook"
    if (target_dir / "plugins").is_dir() and (
        (target_dir / "galaxy.yml").is_file() or (target_dir / "meta").is_dir()
    ):
        return "ansible-plugins"
    if (target_dir / "pyproject.toml").is_file() or (target_dir / "setup.py").is_file():
        return "python"
    if (target_dir / "pom.xml").is_file() or (target_dir / "build.gradle").is_file():
        return "java"
    if (target_dir / "Cargo.toml").is_file():
        return "rust"
    if (target_dir / "go.mod").is_file():
        return "golang"
    return "generic"


def _discover_role_dirs(target_dir: Path) -> list[str]:
    """Return relative paths roles/<name> for each role directory."""
    roles_root = target_dir / "roles"
    if not roles_root.is_dir():
        return []
    names = sorted(
        p.name
        for p in roles_root.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name != "__pycache__"
    )
    return [f"roles/{n}" for n in names]


def _discover_extra_dirs(target_dir: Path) -> list[str]:
    """inventory / playbooks / etc. as single package units (not every leaf)."""
    found = []
    for name in _PRIORITY_PARENTS:
        if name == "roles":
            continue
        if (target_dir / name).is_dir():
            found.append(name)
    return found


def _roles_touched_by_git(target_dir: Path, base_ref: str = "origin/main") -> set[str]:
    """
    Return role names (not full paths) touched between base_ref and HEAD.
    Falls back to empty set on git errors (caller decides full vs empty scan).
    """
    try:
        res = subprocess.run(
            [
                "git",
                "-C",
                str(target_dir),
                "diff",
                "--name-only",
                f"{base_ref}...HEAD",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            # try HEAD~1 if origin/main missing
            res = subprocess.run(
                ["git", "-C", str(target_dir), "diff", "--name-only", "HEAD~1"],
                capture_output=True,
                text=True,
                check=False,
            )
        touched: set[str] = set()
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line.startswith("roles/"):
                continue
            parts = Path(line).parts
            # roles/<role_name>/...
            if len(parts) >= 2:
                touched.add(parts[1])
        return touched
    except Exception:
        return set()


def run_crew(
    llm,
    verbose: bool = True,
    target_dir: str = ".",
    api_base: str | None = None,
    api_key: str | None = None,
    embed_model: str | None = None,
    enable_memory: bool = True,
    max_roles: int | None = None,
    changed_only: bool = False,
    git_base_ref: str = "origin/main",
):
    """
    Hierarchical documentation crew (ansible-oriented when roles/ present):

      1. Package + review (+ wiki write) each roles/<role>
      2. Package + review inventory / playbooks / collections
      3. Package + review root → wiki/architecture/overview.md

    changed_only: only roles touched in git diff vs git_base_ref.
    """
    storage_root = _ensure_memory_storage()
    base = Path(target_dir).resolve()
    repo_type = detect_repo_type(base)

    embed_model = embed_model or os.environ.get(
        "CREWAI_EMBED_MODEL", _DEFAULT_EMBED_MODEL
    )
    api_base = api_base or os.environ.get(
        "OPENAI_API_BASE", "http://localhost:11434/v1"
    )
    api_key = (
        api_key
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("LLM_API_KEY", "dummy-key")
    )
    if max_roles is None:
        env_cap = os.environ.get("CREWAI_MAX_ROLES")
        max_roles = int(env_cap) if env_cap and env_cap.isdigit() else None

    role_dirs = _discover_role_dirs(base)
    if changed_only and repo_type.startswith("ansible"):
        touched = _roles_touched_by_git(base, git_base_ref)
        if touched:
            role_dirs = [r for r in role_dirs if r.split("/", 1)[-1] in touched]
        elif verbose:
            print(
                "[crew] changed_only=true but no roles in git diff; "
                "falling back to max_roles / full role list"
            )
    if max_roles is not None:
        role_dirs = role_dirs[:max_roles]

    extra_dirs = _discover_extra_dirs(base)

    if verbose:
        # Logger may not be configured yet; print is fine for visibility in CI
        print(
            f"[crew] repo_type={repo_type} storage={storage_root} "
            f"memory={enable_memory} embed={embed_model} api_base={api_base} "
            f"changed_only={changed_only} roles={len(role_dirs)} "
            f"extras={extra_dirs} root={base}"
        )

    embedder = (
        _build_embedder(api_base, api_key, embed_model) if enable_memory else None
    )

    analyst = Agent(
        role="Repository Context Analyst",
        goal="Package directories with the Package Directory Context tool; report real tool output only.",
        backstory=(
            "You call tools and quote results. Never invent file trees. "
            "When a package summary marks a directory oversized, note the repackage_command."
        ),
        tools=[package_directory_tool],
        llm=llm,
        verbose=verbose,
        memory=enable_memory,
    )

    reviewer = Agent(
        role="Senior Documentation Reviewer",
        goal=(
            "Produce accurate documentation from real .package_dir.context.yml files "
            "and persist them under wiki/ using the Write Wiki Document tool."
        ),
        backstory=(
            "You specialize in structured technical docs. For Ansible repos you cover "
            "roles (tasks/defaults/handlers/templates/meta). You only document what "
            "exists in packaged context or memory. You always write final pages via the wiki tool."
        ),
        tools=[write_wiki_document],
        llm=llm,
        verbose=verbose,
        memory=enable_memory,
    )

    tasks: list[Task] = []

    def _package_task(rel: str, label: str) -> Task:
        return Task(
            description=(
                f"[{label}] Call 'Package Directory Context' once with "
                f"directory_path='{rel}', strip_comments=True. "
                f"Return the tool result VERBATIM. Do not invent YAML or file lists."
            ),
            expected_output=f"Exact tool output confirming packaging of '{rel}'.",
            agent=analyst,
        )

    def _get_context_filename(rel: str) -> str:
        """Helper to derive .package_dir.<name>.yml for a given relative path."""
        p = Path(rel).resolve()
        dname = p.name if p.name else "root"
        if rel == "." or rel == "":
            return f".package_dir.{dname}.yml"
        return f"{rel}/.package_dir.{dname}.yml"

    def _review_and_write_role(rel: str) -> Task:
        role_name = rel.split("/", 1)[-1]
        wiki_rel = f"roles/{role_name}.md"
        ctx = _get_context_filename(rel)
        return Task(
            description=(
                f"[role:{rel}] Analyze '{ctx}' on disk. "
                f"Write a concise markdown role document covering purpose, tasks, "
                f"defaults/vars, handlers, templates, and dependencies. "
                f"Then call 'Write Wiki Document' with relative_path='{wiki_rel}' "
                f"and the full markdown as content. "
                f"Do not invent files absent from the package YAML."
            ),
            expected_output=f"Confirmation that wiki/{wiki_rel} was written.",
            agent=reviewer,
        )

    def _review_unit(rel: str) -> Task:
        wiki_rel = f"{rel}/overview.md"
        ctx = _get_context_filename(rel)
        return Task(
            description=(
                f"[unit:{rel}] Analyze '{ctx}'. Write markdown overview for '{rel}', "
                f"then call 'Write Wiki Document' with relative_path='{wiki_rel}'."
            ),
            expected_output=f"Confirmation that wiki/{wiki_rel} was written.",
            agent=reviewer,
        )

    # Phase A — roles
    for rel in role_dirs:
        tasks.append(_package_task(rel, f"role:{rel}"))
        tasks.append(_review_and_write_role(rel))

    # Phase B — inventory / playbooks / collections
    for rel in extra_dirs:
        tasks.append(_package_task(rel, f"unit:{rel}"))
        tasks.append(_review_unit(rel))

    # Phase C — root
    root_ctx = _get_context_filename(".")
    tasks.append(_package_task(".", "root"))
    tasks.append(
        Task(
            description=(
                f"[root] Analyze '{root_ctx}'. "
                f"Repo type detected as '{repo_type}'. "
                "Use prior role/unit reviews from memory. "
                "If __meta__.oversized_directories lists paths not yet reviewed, list gaps. "
                "Write a top-level architecture overview, then call "
                "'Write Wiki Document' with relative_path='architecture/overview.md'."
            ),
            expected_output="Confirmation that wiki/architecture/overview.md was written.",
            agent=reviewer,
        )
    )

    crew_kwargs = dict(
        agents=[analyst, reviewer],
        tasks=tasks,
        process=Process.sequential,
        verbose=verbose,
        memory=enable_memory,
    )
    if enable_memory and embedder:
        crew_kwargs["embedder"] = embedder

    return Crew(**crew_kwargs).kickoff()

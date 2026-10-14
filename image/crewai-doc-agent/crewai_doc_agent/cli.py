#!/usr/bin/env python3
import os
import sys
import argparse
import base64
import logging
from pathlib import Path
from crewai import LLM
from crewai_doc_agent.utils import LLMClient, setup_logging
from crewai_doc_agent.crew import run_crew

log = logging.getLogger(__name__)


def _prepare_memory_storage(storage_dir: str | None = None) -> Path:
    """Point CrewAI/LanceDB at a writable workspace path before crew starts."""
    root = Path(
        storage_dir or os.environ.get("CREWAI_STORAGE_DIR", ".agent_state/crewai")
    )
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    os.environ["CREWAI_STORAGE_DIR"] = str(root)
    log.info(f"🧠 CrewAI memory storage: {root}  (LanceDB → {root}/memory)")
    return root


def run_agent_workflow(
    config_path: str,
    verbose: int,
    target_dir: str = ".",
    storage_dir: str | None = None,
    changed_only: bool = False,
):
    _prepare_memory_storage(storage_dir)

    log.info("initializing LLMClient and running endpoint health check...")
    llm_client = LLMClient(config_path=config_path)

    # Safeguard: Ensure LiteLLM/OpenAI provider sees a valid API key in environment
    if llm_client.api_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = llm_client.api_key

    os.environ.setdefault("OPENAI_API_BASE", llm_client.api_base)
    os.environ.setdefault("OPENAI_BASE_URL", llm_client.api_base)
    if llm_client.api_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = llm_client.api_key

    log.info(
        f"🤖 Configuring CrewAI LLM -> Model: {llm_client.model}, "
        f"Base: {llm_client.api_base}, Auth: {llm_client.auth_type}"
    )
    log.info(f"📁 Target directory for packaging: {target_dir}")

    # Build extra_headers for Basic Auth if configured
    extra_headers = {}
    if llm_client.auth_type == "basic" and llm_client.api_key:
        if ":" in llm_client.api_key:
            encoded_bytes = base64.b64encode(llm_client.api_key.encode("utf-8"))
            extra_headers["Authorization"] = f"Basic {encoded_bytes.decode('utf-8')}"
        else:
            extra_headers["Authorization"] = f"Basic {llm_client.api_key}"

    # Instantiate the authenticated LLM wrapper object
    llm = LLM(
        model=(
            f"{llm_client.provider}/{llm_client.model}"
            if not llm_client.model.startswith(f"{llm_client.provider}/")
            else llm_client.model
        ),
        base_url=llm_client.api_base,
        api_key=None if llm_client.auth_type == "basic" else llm_client.api_key,
        extra_headers=extra_headers if extra_headers else None,
        temperature=llm_client.config.get("agent", {}).get("temperature", 0.2),
    )

    log.info("🚀 Starting CrewAI multi-agent documentation and analysis crew...")
    # Pass the instantiated llm object directly into run_crew
    result = run_crew(
        llm=llm,
        verbose=(verbose > 0),
        target_dir=target_dir,
        api_base=llm_client.api_base,
        api_key=llm_client.api_key,
        embed_model=os.environ.get("CREWAI_EMBED_MODEL", "nomic-embed-text"),
        enable_memory=os.environ.get("CREWAI_ENABLE_MEMORY", "true").lower()
        in ("1", "true", "yes"),
        max_roles=(
            int(os.environ["CREWAI_MAX_ROLES"])
            if os.environ.get("CREWAI_MAX_ROLES", "").isdigit()
            else None
        ),
        changed_only=changed_only
        or os.environ.get("CREWAI_CHANGED_ONLY", "").lower() in ("1", "true", "yes"),
        git_base_ref=os.environ.get("CREWAI_GIT_BASE_REF", "origin/main"),
    )

    print("\n=== CrewAI Execution Result ===")
    print(result)
    print("===============================")


def main():
    parser = argparse.ArgumentParser(description="CrewAI Documentation Agent CLI")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbosity level: -v, -vv, -vvv",
    )
    parser.add_argument(
        "-d",
        "--debug-llm",
        action="store_true",
        help="Enable LiteLLM debug mode (very verbose)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Run subcommand
    run_parser = subparsers.add_parser(
        "run", help="Run the CrewAI documentation agent workflow"
    )
    run_parser.add_argument(
        "--config",
        default=".crewai-config.yml",
        help="Path to CrewAI configuration YAML file",
    )
    run_parser.add_argument(
        "--target-dir",
        default=".",
        help="Directory to package and review (default: '.')",
    )
    run_parser.add_argument(
        "--storage-dir",
        default=None,
        help="CrewAI/LanceDB storage root (default: .agent_state/crewai)",
    )
    run_parser.add_argument(
        "--changed-only",
        action="store_true",
        help="Only document roles touched in git diff (ansible repos)",
    )

    # Healthcheck subcommand
    healthcheck_parser = subparsers.add_parser(
        "healthcheck", help="Test config loading and LLM endpoint connectivity"
    )
    healthcheck_parser.add_argument(
        "--config",
        default=".crewai-config.yml",
        help="Path to CrewAI configuration YAML file",
    )

    args = parser.parse_args()

    # Initialize logging
    setup_logging(args.verbose, debug_llm=args.debug_llm)

    if args.command == "run":
        try:
            run_agent_workflow(
                args.config,
                verbose=args.verbose,
                target_dir=args.target_dir,
                storage_dir=args.storage_dir,
                changed_only=getattr(args, "changed_only", False),
            )
        except Exception as e:
            log.error(f"Pipeline execution failed: {e}")
            sys.exit(1)
    elif args.command == "healthcheck":
        try:
            log.info(f"Running health check with config: {args.config}")
            llm_client = LLMClient(config_path=args.config)
            print(
                f"\nSUCCESS: Configuration loaded and endpoint verified successfully!\n"
                f"  - Model: {llm_client.model}\n"
                f"  - Base URL: {llm_client.api_base}\n"
                f"  - Auth Type: {llm_client.auth_type}"
            )
        except Exception as e:
            log.error(f"Healthcheck failed: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

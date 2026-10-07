#!/usr/bin/env python3
import sys
import argparse
import base64
import logging
from crewai import LLM
from utils import LLMClient, setup_logging
from crew import run_crew

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("crewai-doc-agent")


def run_agent_workflow(config_path: str, verbose: int):
    log.info("initializing LLMClient and running endpoint health check...")
    llm_client = LLMClient(config_path=config_path)

    log.info(
        f"🤖 Configuring CrewAI LLM -> Model: {llm_client.model}, Base: {llm_client.api_base}, Auth: {llm_client.auth_type}"
    )

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
        model=f"{llm_client.provider}/{llm_client.model}"
        if not llm_client.model.startswith(f"{llm_client.provider}/")
        else llm_client.model,
        base_url=llm_client.api_base,
        api_key=None if llm_client.auth_type == "basic" else llm_client.api_key,
        extra_headers=extra_headers if extra_headers else None,
        temperature=llm_client.config.get("llm", {}).get("temperature", 0.2),
    )

    log.info("🚀 Starting CrewAI multi-agent documentation and analysis crew...")
    # Pass the instantiated llm object directly into run_crew
    result = run_crew(llm=llm, verbose=(verbose > 0))

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

    run_parser = subparsers.add_parser(
        "run", help="Run the CrewAI documentation agent workflow"
    )
    run_parser.add_argument(
        "--config",
        default=".crewai-config.yml",
        help="Path to CrewAI configuration YAML file",
    )
    # run_parser.add_argument(
    #     "--verbose", "-v", action="store_true", help="Enable verbose output"
    # )

    args = parser.parse_args()

    # Initialize the global logging config once
    setup_logging(args.verbose, debug_llm=args.debug_llm)

    if args.command == "run":
        try:
            run_agent_workflow(args.config, verbose=args.verbose)
        except Exception as e:
            log.error(f"Pipeline execution failed: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

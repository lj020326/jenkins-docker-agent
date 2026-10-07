#!/usr/bin/env python3
import sys
import argparse
import base64
import logging
from crewai import Agent, Crew, Process, Task, LLM
from utils import LLMClient

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("crewai-doc-agent")


def run_agent_workflow(config_path: str, verbose: bool):
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

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

    # Pass authenticated connection parameters and extra_headers to CrewAI's LLM wrapper
    llm = LLM(
        model=f"{llm_client.provider}/{llm_client.model}"
        if not llm_client.model.startswith(f"{llm_client.provider}/")
        else llm_client.model,
        base_url=llm_client.api_base,
        api_key=None if llm_client.auth_type == "basic" else llm_client.api_key,
        extra_headers=extra_headers if extra_headers else None,
        temperature=llm_client.config.get("llm", {}).get("temperature", 0.2),
    )

    doc_writer = Agent(
        role="Principal Technical Documentation Engineer",
        goal="Analyze repository codebase and generate accurate, clear, comprehensive documentation and release guides.",
        backstory="You are an elite developer advocacy agent with deep expertise in analyzing multi-container setups, infrastructure-as-code, and automated CI/CD pipelines.",
        verbose=verbose,
        llm=llm,
        allow_delegation=False,
    )

    analyze_task = Task(
        description="Review the packaged repository context in save/repository_context.yaml alongside code index insights, then generate structured and updated markdown documentation.",
        expected_output="Comprehensive updated markdown documentation files saved under the appropriate wiki or docs path.",
        agent=doc_writer,
    )

    crew = Crew(
        agents=[doc_writer],
        tasks=[analyze_task],
        process=Process.sequential,
        verbose=verbose,
    )

    log.info("🚀 Starting CrewAI documentation execution pipeline...")
    result = crew.kickoff()
    print("\n=== CrewAI Execution Result ===")
    print(result)
    print("===============================")


def main():
    parser = argparse.ArgumentParser(description="CrewAI Documentation Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run", help="Run the CrewAI documentation agent workflow"
    )
    run_parser.add_argument(
        "--config",
        default=".crewai-config.yml",
        help="Path to CrewAI configuration YAML file",
    )
    run_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

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

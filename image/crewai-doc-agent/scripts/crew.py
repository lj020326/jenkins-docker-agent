# scripts/crew.py
from crewai import Agent, Crew, Process, Task
from agents.package_tool import package_directory_tool


def run_crew(llm, verbose: bool = True):
    # 1. Define Agents using the explicit llm instance
    repo_analyst = Agent(
        role="Repository Context Analyst",
        goal="Package repository directories and extract deep architectural insights from the generated context file.",
        backstory=(
            "You are an expert systems architect skilled in reading packaged repository structures "
            "and identifying code patterns, dependencies, and potential bottlenecks using LLM context files."
        ),
        tools=[package_directory_tool],
        llm=llm,
        verbose=verbose,
        memory=True,
    )

    code_reviewer = Agent(
        role="Senior Code Reviewer",
        goal="Perform thorough code reviews and architectural audits based on the packaged repository context.",
        backstory=(
            "You analyze code standards, security practices, and structural layout from standardized "
            "YAML context files generated from target codebases."
        ),
        llm=llm,
        verbose=verbose,
    )

    # 2. Define Tasks
    package_task = Task(
        description=(
            "Package the target repository directory using the packaging tool. "
            "Ensure code comments are stripped to optimize tokens."
        ),
        expected_output="Confirmation that .package_dir.context.yml was successfully generated in the target directory with all metadata.",
        agent=repo_analyst,
    )

    review_task = Task(
        description=(
            "Read the generated '.package_dir.context.yml' file inside the targeted directory, "
            "analyze the code structure, check the embedded __meta__ details (such as git commit hash and total lines), "
            "and provide a comprehensive architecture and code quality review report."
        ),
        expected_output="A structured markdown report detailing the repository structure, code quality, and recommendations.",
        agent=code_reviewer,
    )

    # 3. Assemble Crew
    code_audit_crew = Crew(
        agents=[repo_analyst, code_reviewer],
        tasks=[package_task, review_task],
        process=Process.sequential,
        verbose=verbose,
    )

    return code_audit_crew.kickoff()

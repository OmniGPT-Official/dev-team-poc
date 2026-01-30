"""
Implementation Cycle Workflow

Flow: Dev → Code Review → Security Review → (loop if changes requested)

Each agent receives the previous agent's output as a string via step_input.previous_step_content.
All artifacts are stored in GitHub via MCP tools.
"""

import os
import sys
import asyncio
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Loop, Step, Workflow
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info, log_debug

from agents.software_engineer import software_engineer_agent
from agents.lead_engineer import lead_engineer_agent
from agents.security_engineer import security_engineer_agent


def _run_async(coro):
    """Run async coroutine from sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Simple iteration counter
_iteration = 0


def run_development(step_input: StepInput) -> StepOutput:
    """Software Engineer implements or revises code."""
    global _iteration
    _iteration += 1

    spec = step_input.input if isinstance(step_input.input, str) else ""
    feedback = step_input.previous_step_content or ""

    log_info(f"[STEP:development] Starting iteration {_iteration}")
    log_debug(f"[STEP:development] INPUT (spec):\n{spec[:500]}{'...' if len(spec) > 500 else ''}")
    log_debug(f"[STEP:development] INPUT (feedback):\n{feedback[:500]}{'...' if len(feedback) > 500 else ''}")

    if _iteration == 1:
        prompt = f"""<task>Implement the feature described in the specification below.</task>

<specification>
{spec}
</specification>

<instructions>
1. Write clean, production-ready code based on the specification
2. Save your code to GitHub:
   - Use create_or_update_file to save directly (do NOT create_repository first)
   - If you get "repository not found", THEN use create_repository and retry
   - If you get "name already exists", the repo exists - just use create_or_update_file
3. Respond with a summary of what you implemented
</instructions>"""
    else:
        prompt = f"""<task>Revise your code based on the review feedback below.</task>

<feedback>
{feedback}
</feedback>

<instructions>
1. Use GitHub MCP tools to read your current code
2. Address all issues raised in the feedback
3. Save the updated code to the repository
4. Respond with a summary of changes made
</instructions>"""

    log_info(f"[AGENT:software_engineer] Calling for {'implementation' if _iteration == 1 else 'revision'}")
    result = _run_async(software_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info(f"[STEP:development] Iteration {_iteration} complete")
    log_debug(f"[STEP:development] OUTPUT:\n{output[:500]}{'...' if len(output) > 500 else ''}")

    return StepOutput(content=output, success=True)


def run_code_review(step_input: StepInput) -> StepOutput:
    """Lead Engineer reviews code quality."""
    dev_output = step_input.previous_step_content or ""

    log_info("[STEP:code_review] Starting")
    log_debug(f"[STEP:code_review] INPUT:\n{dev_output[:500]}{'...' if len(dev_output) > 500 else ''}")

    prompt = f"""<task>Review the code implementation for quality and best practices.</task>

<context>
{dev_output}
</context>

<instructions>
1. Use GitHub MCP tools to read the implementation code
2. Check code quality, readability, and architecture alignment
3. Check error handling and best practices
4. Save your review to GitHub
5. End with exactly "APPROVED" or "CHANGES_REQUESTED"
</instructions>"""

    log_info("[AGENT:lead_engineer] Calling for code review")
    result = _run_async(lead_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:code_review] Complete")
    log_debug(f"[STEP:code_review] OUTPUT:\n{output[:500]}{'...' if len(output) > 500 else ''}")

    return StepOutput(content=output, success=True)


def run_security_review(step_input: StepInput) -> StepOutput:
    """Security Engineer reviews for vulnerabilities."""
    code_review = step_input.previous_step_content or ""

    log_info("[STEP:security_review] Starting")
    log_debug(f"[STEP:security_review] INPUT:\n{code_review[:500]}{'...' if len(code_review) > 500 else ''}")

    prompt = f"""<task>Review the code for security vulnerabilities.</task>

<previous_review>
{code_review}
</previous_review>

<instructions>
1. Use GitHub MCP tools to read the implementation code
2. Check for injection vulnerabilities, auth flaws, input validation issues
3. Check for OWASP Top 10 vulnerabilities
4. Save your review to GitHub
5. End with exactly "APPROVED" or "CHANGES_REQUIRED"
</instructions>"""

    log_info("[AGENT:security_engineer] Calling for security review")
    result = _run_async(security_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:security_review] Complete")
    log_debug(f"[STEP:security_review] OUTPUT:\n{output[:500]}{'...' if len(output) > 500 else ''}")

    # Combine both reviews for the next iteration's feedback
    combined = f"""<code_review>
{code_review}
</code_review>

<security_review>
{output}
</security_review>"""

    return StepOutput(content=combined, success=True)


def should_continue(outputs: List[StepOutput]) -> bool:
    """Return True to break loop when approved or max iterations reached."""
    global _iteration

    log_info(f"[LOOP] Checking end condition (iteration {_iteration})")

    if _iteration >= 3:
        log_info("[LOOP] Max iterations reached - ending loop")
        return True

    last_output = outputs[-1].content.lower() if outputs else ""
    code_ok = "approved" in last_output and "changes_requested" not in last_output
    security_ok = "approved" in last_output and "changes_required" not in last_output

    if code_ok and security_ok:
        log_info("[LOOP] All reviews approved - ending loop")
        return True

    log_info("[LOOP] Changes requested - continuing to next iteration")
    return False


def format_summary(step_input: StepInput) -> StepOutput:
    """Generate final summary."""
    global _iteration
    iterations = _iteration
    _iteration = 0  # Reset for next run

    log_info(f"[STEP:summary] Generating summary (completed in {iterations} iterations)")

    output = f"## Implementation Complete\n\n**Iterations:** {iterations}"
    log_debug(f"[STEP:summary] OUTPUT:\n{output}")

    return StepOutput(content=output, success=True)


# Workflow definition
implementation_cycle_workflow = Workflow(
    name="Implementation Cycle",
    stream=False,
    description="Dev → Code Review → Security Review loop",
    steps=[
        Loop(
            name="Review Loop",
            steps=[
                Step(name="development", executor=run_development),
                Step(name="code_review", executor=run_code_review),
                Step(name="security_review", executor=run_security_review),
            ],
            end_condition=should_continue,
            max_iterations=3,
        ),
        Step(name="summary", executor=format_summary),
    ]
)


def run_implementation_cycle(spec: str) -> dict:
    """Run the workflow with a specification string."""
    global _iteration
    _iteration = 0

    log_info("[WORKFLOW:implementation_cycle] ========================================")
    log_info("[WORKFLOW:implementation_cycle] ========== STARTING ==========")
    log_info("[WORKFLOW:implementation_cycle] ========================================")
    log_debug(f"[WORKFLOW:implementation_cycle] INPUT:\n{spec[:500]}{'...' if len(spec) > 500 else ''}")

    result = implementation_cycle_workflow.run(input=spec)
    output = result.content or ""

    log_info("[WORKFLOW:implementation_cycle] ========================================")
    log_info("[WORKFLOW:implementation_cycle] ========== COMPLETE ==========")
    log_info("[WORKFLOW:implementation_cycle] ========================================")
    log_debug(f"[WORKFLOW:implementation_cycle] OUTPUT:\n{output}")

    return {"success": True, "content": output}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--spec-file", required=True, help="Path to specification file")
    args = parser.parse_args()

    with open(args.spec_file) as f:
        spec = f.read()

    result = run_implementation_cycle(spec)
    print(result["content"])

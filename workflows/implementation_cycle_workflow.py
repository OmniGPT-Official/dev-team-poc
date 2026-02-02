"""
Implementation Cycle Workflow

Input: PRD + Technical Documentation
Flow: [Development -> Code Review + Security Review] loops until both approve

Uses Agno's Loop pattern with Parallel reviews.
State is managed through step outputs - no global variables.
"""

import os
import sys
import asyncio
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Loop, Parallel, Step, Workflow
from agno.workflow.step import StepInput, StepOutput

from agents.software_engineer import software_engineer_agent
from agents.lead_engineer import lead_engineer_agent
from agents.security_engineer import security_engineer_agent


MAX_ITERATIONS = 5


def _run_async(coro):
    """Run async coroutine from sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _extract_feedback_from_reviews(content: str) -> str:
    """Extract feedback from previous review outputs if changes were requested."""
    if not content:
        return ""
    # If the previous content contains review feedback markers, extract it
    if "CHANGES_REQUESTED" in content or "CHANGES_REQUIRED" in content:
        return content
    return ""


def development_executor(step_input: StepInput) -> StepOutput:
    """Development step: implement or revise code based on PRD, tech docs, and feedback."""
    # Get the original input (PRD + tech docs)
    spec = step_input.input if isinstance(step_input.input, str) else ""

    # Check if this is a revision (previous_step_content has review feedback)
    previous_content = step_input.previous_step_content or ""
    feedback = _extract_feedback_from_reviews(previous_content)
    is_first_iteration = not feedback

    iteration_label = "Initial" if is_first_iteration else "Revision"
    print(f"\n{'='*60}")
    print(f"[Development - {iteration_label}]")
    print(f"{'='*60}")

    if is_first_iteration:
        prompt = f"""Implement the code based on the following specifications:

{spec}

Instructions:
- Read the PRD and technical documentation carefully
- Implement the code according to the specifications
- Use GitHub MCP tools to create/update files in the repository

After implementation, output ONLY the following structured information:
```
GITHUB_INFO:
- owner: <repo owner>
- repo: <repo name>
- branch: <branch name>
- files_changed:
  - <file path 1>
  - <file path 2>
  ...
```"""
    else:
        prompt = f"""Revise the implementation based on review feedback.

Original specifications:
{spec}

Review feedback to address:
{feedback}

Instructions:
- Address the feedback by updating the code
- Use GitHub MCP tools to update the files

After implementation, output ONLY the following structured information:
```
GITHUB_INFO:
- owner: <repo owner>
- repo: <repo name>
- branch: <branch name>
- files_changed:
  - <file path 1>
  - <file path 2>
  ...
```"""

    result = _run_async(software_engineer_agent.arun(prompt))
    output = result.content or ""

    print(f"\n[Development - {iteration_label}] Complete")
    print(output)

    return StepOutput(content=output, success=True)


def code_review_executor(step_input: StepInput) -> StepOutput:
    """Code review step: review the implementation using GitHub MCP."""
    print(f"\n{'='*60}")
    print(f"[Code Review]")
    print(f"{'='*60}")

    spec = step_input.input if isinstance(step_input.input, str) else ""
    github_info = step_input.previous_step_content or ""

    prompt = f"""Review the implementation for the following specifications:

{spec}

## GitHub Repository Info (files to review)

{github_info}

Instructions:
- Use GitHub MCP tools to fetch and read the files listed above
- Check if the implementation matches the requirements in the spec
- Review code quality, structure, and best practices

End your response with exactly one of:
- APPROVED
- CHANGES_REQUESTED (followed by specific feedback)"""

    result = _run_async(lead_engineer_agent.arun(prompt))
    output = result.content or ""

    print(f"[Code Review Result]\n{output}")
    print(f"{'='*60}")

    return StepOutput(content=output, success=True)


def security_review_executor(step_input: StepInput) -> StepOutput:
    """Security review step: review the implementation for security issues."""
    print(f"\n{'='*60}")
    print(f"[Security Review]")
    print(f"{'='*60}")

    spec = step_input.input if isinstance(step_input.input, str) else ""
    github_info = step_input.previous_step_content or ""

    prompt = f"""Review the implementation for security issues:

{spec}

## GitHub Repository Info (files to review)

{github_info}

Instructions:
- Use GitHub MCP tools to fetch and read the files listed above
- Check for security vulnerabilities (OWASP top 10)
- Verify no sensitive data is exposed
- Check for proper input validation

End your response with exactly one of:
- APPROVED
- CHANGES_REQUIRED (followed by specific security concerns)"""

    result = _run_async(security_engineer_agent.arun(prompt))
    output = result.content or ""

    print(f"[Security Review Result]\n{output}")
    print(f"{'='*60}")

    return StepOutput(content=output, success=True)


# Create steps
development_step = Step(name="Development", executor=development_executor)
code_review_step = Step(name="Code Review", executor=code_review_executor)
security_review_step = Step(name="Security Review", executor=security_review_executor)


def check_approval(outputs: List[StepOutput]) -> bool:
    """
    End condition: check if both reviews approved.
    Returns True to EXIT the loop when both approve.
    Returns False to CONTINUE looping.
    """
    if len(outputs) < 2:
        return False

    # Get the last two outputs (code review and security review from Parallel)
    code_review_output = outputs[-2].content.lower() if outputs[-2].content else ""
    security_review_output = outputs[-1].content.lower() if outputs[-1].content else ""

    code_approved = "approved" in code_review_output and "changes_requested" not in code_review_output
    security_approved = "approved" in security_review_output and "changes_required" not in security_review_output

    if code_approved and security_approved:
        print(f"\n{'='*60}")
        print(f"[Loop] Both reviews APPROVED")
        print(f"{'='*60}")
        return True

    print(f"\n[Loop] Reviews requested changes - continuing to next iteration")
    return False


implementation_cycle_workflow = Workflow(
    name="Implementation Cycle",
    description="Development loop until code review + security review approve",
    steps=[
        Loop(
            name="Development Loop",
            steps=[
                development_step,
                Parallel(code_review_step, security_review_step, name="Reviews"),
            ],
            end_condition=check_approval,
            max_iterations=MAX_ITERATIONS,
        ),
    ],
)

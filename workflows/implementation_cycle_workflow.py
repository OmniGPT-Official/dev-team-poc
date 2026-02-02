"""
Implementation Cycle Workflow

Input: PRD + Technical Documentation
Flow: [Development -> Code Review + Security Review] loops until both approve

Uses Agno's Loop pattern with Parallel reviews.
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

# Store state for iterations
_review_feedback = ""
_iteration = 0


def _run_async(coro):
    """Run async coroutine from sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def development_executor(step_input: StepInput) -> StepOutput:
    """Development step: implement or revise code based on PRD, tech docs, and feedback."""
    global _iteration
    _iteration += 1

    print(f"\n{'='*60}")
    print(f"[Development - Iteration {_iteration}]")
    print(f"{'='*60}")

    # Get the original input (PRD + tech docs)
    spec = step_input.input if isinstance(step_input.input, str) else ""

    if _iteration == 1 or not _review_feedback:
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
{_review_feedback}

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

    print(f"\n[Development - Iteration {_iteration}] Complete")
    print(output)

    return StepOutput(content=output, success=True)


def code_review_executor(step_input: StepInput) -> StepOutput:
    """Code review step: review the implementation using GitHub MCP."""
    print(f"\n{'='*60}")
    print(f"[Code Review - Iteration {_iteration}]")
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

    print(f"\n[Code Review Prompt]\n{prompt}\n[End Code Review Prompt]\n")

    result = _run_async(lead_engineer_agent.arun(prompt))
    output = result.content or ""

    print(f"[Code Review Result]\n{output}")
    print(f"{'='*60}")

    return StepOutput(content=output, success=True)


def security_review_executor(step_input: StepInput) -> StepOutput:
    """Security review step: review the implementation for security issues."""
    print(f"\n{'='*60}")
    print(f"[Security Review - Iteration {_iteration}]")
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

    print(f"\n[Security Review Prompt]\n{prompt}\n[End Security Review Prompt]\n")

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
    global _review_feedback

    if len(outputs) < 3:
        return False

    # Get the last two outputs (code review and security review from Parallel)
    # In a loop iteration: [dev, code_review, security_review]
    code_review_output = outputs[-2].content.lower() if outputs[-2].content else ""
    security_review_output = outputs[-1].content.lower() if outputs[-1].content else ""

    code_approved = "approved" in code_review_output and "changes_requested" not in code_review_output
    security_approved = "approved" in security_review_output and "changes_required" not in security_review_output

    if code_approved and security_approved:
        print(f"\n{'='*60}")
        print(f"[Loop] Both reviews APPROVED after {_iteration} iteration(s)")
        print(f"{'='*60}")
        _review_feedback = ""
        return True

    # Collect feedback for next iteration
    feedback_parts = []
    if not code_approved:
        feedback_parts.append(f"Lead Engineer Feedback:\n{outputs[-2].content}")
    if not security_approved:
        feedback_parts.append(f"Security Engineer Feedback:\n{outputs[-1].content}")

    _review_feedback = "\n\n".join(feedback_parts)
    print(f"\n[Loop] Reviews requested changes - continuing to iteration {_iteration + 1}")
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


def run_implementation_cycle(prd: str, technical_docs: str) -> dict:
    """
    Run the implementation cycle workflow.

    Args:
        prd: Product Requirements Document
        technical_docs: Technical documentation/architecture

    Returns:
        dict with success status and content
    """
    global _review_feedback, _iteration
    _review_feedback = ""
    _iteration = 0

    input_spec = f"""## PRD (Product Requirements Document)

{prd}

## Technical Documentation

{technical_docs}
"""

    result = implementation_cycle_workflow.run(input=input_spec)
    output = result.content or ""

    return {"success": True, "content": output, "iterations": _iteration}

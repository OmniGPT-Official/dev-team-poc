"""
Implementation Cycle Workflow

Flow: Setup -> [Development -> Code Review -> Security Review] (loop until approved) -> Summary

The workflow loops until both lead engineer and security engineer approve the code.
Errors don't break the loop - they become feedback for the next iteration to self-correct.
All artifacts are stored in GitHub via MCP tools.
"""

import os
import sys
import json
import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.db.in_memory import InMemoryDb
from agno.workflow import Loop, Step, Workflow
from agno.workflow.types import StepInput, StepOutput

from agents.software_engineer import software_engineer_agent
from agents.lead_engineer import lead_engineer_agent
from agents.security_engineer import security_engineer_agent


# Logging setup
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

_log_file = None
_iteration = 0


def init_log():
    """Initialize log file with timestamp."""
    global _log_file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _log_file = LOG_DIR / f"workflow_run_{timestamp}.log"
    return _log_file


def log_entry(category: str, name: str, data: dict):
    """Append a log entry with timestamp, category, name, and data."""
    if _log_file is None:
        init_log()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "category": category,
        "name": name,
        "data": data
    }
    with open(_log_file, "a") as f:
        f.write(json.dumps(entry, indent=2) + "\n---\n")
    print(f"[{category}:{name}] logged")


# Hardcoded for testing - replace with actual values
OWNER = "OmniGPT-Official"
REPO = "test-demo-repo"


def _run_async(coro):
    """Run async coroutine from sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def step_setup(step_input: StepInput) -> StepOutput:
    """Setup step: Create repository if needed."""
    spec = step_input.input if isinstance(step_input.input, str) else ""

    prompt = f"""Create a GitHub repository named '{REPO}' under owner '{OWNER}'.

Instructions:
1. First check if the repository exists using `get_repository`
2. If it does NOT exist (404 error), create it with `create_repository`
3. If it already exists, skip creation
4. Confirm the repository is ready

Respond with a brief confirmation of what you did."""

    log_entry("step", "setup", {
        "input": spec[:500] if spec else "(no input)",
        "prompt": prompt
    })

    try:
        print(f"\n[Setup] Creating/verifying repository {OWNER}/{REPO}...")
        result = _run_async(software_engineer_agent.arun(prompt))
        output = result.content or ""

        log_entry("agent", "software_engineer", {
            "action": "setup",
            "output": output
        })

        print(f"[Setup] Complete")
        return StepOutput(content=output, success=True)

    except Exception as e:
        error_msg = f"Setup error: {str(e)}\n{traceback.format_exc()}"
        log_entry("error", "setup", {"error": error_msg})
        print(f"[Setup] Error: {str(e)}")
        # Return error as content - workflow continues, error becomes feedback
        return StepOutput(
            content=f"<error>Setup failed: {str(e)}. Please retry.</error>",
            success=False,
            error=str(e)
        )


def step_development(step_input: StepInput) -> StepOutput:
    """Development step: Implement or revise code based on feedback."""
    global _iteration
    _iteration += 1

    spec = step_input.input if isinstance(step_input.input, str) else ""
    feedback = step_input.previous_step_content or ""

    log_entry("step", "development", {
        "iteration": _iteration,
        "input": spec[:500] if spec else "(no input)",
        "feedback": feedback[:500] if feedback else "(no feedback)"
    })

    # Check if previous step had an error - include it in context
    has_error = "<error>" in feedback.lower()

    if _iteration == 1 and not has_error:
        # First iteration: implement the initial code
        prompt = f"""Create a README.md file in the repository {OWNER}/{REPO}.

The README should contain:
- Project title: Test Demo Repo
- A brief description saying this is a demo repository for testing the implementation workflow
- A simple "Getting Started" section

Use `create_or_update_file` to save the file with:
- owner: {OWNER}
- repo: {REPO}
- path: README.md
- message: "docs: add initial README"

Respond with a confirmation of what you created."""
    else:
        # Subsequent iterations OR error recovery: revise based on feedback
        prompt = f"""{"Fix the error and " if has_error else ""}Revise your code based on the feedback below.

<feedback>
{feedback}
</feedback>

Instructions:
1. {"First, understand what went wrong and fix it. " if has_error else ""}Read the current README.md from {OWNER}/{REPO} using `get_file_contents`
2. Address all issues raised in the feedback
3. Update the file using `create_or_update_file`
4. Respond with a summary of changes made

If you encounter any errors, describe them clearly so they can be addressed in the next iteration."""

    try:
        print(f"\n[Development - Iteration {_iteration}] {'Error recovery' if has_error else 'Implementing' if _iteration == 1 else 'Revising'}...")
        result = _run_async(software_engineer_agent.arun(prompt))
        output = result.content or ""

        log_entry("agent", "software_engineer", {
            "iteration": _iteration,
            "action": "error_recovery" if has_error else ("implement" if _iteration == 1 else "revise"),
            "output": output
        })

        print(f"[Development - Iteration {_iteration}] Complete")
        return StepOutput(content=output, success=True)

    except Exception as e:
        error_msg = f"Development error (iteration {_iteration}): {str(e)}\n{traceback.format_exc()}"
        log_entry("error", "development", {"iteration": _iteration, "error": error_msg})
        print(f"[Development - Iteration {_iteration}] Error: {str(e)}")
        # Return error as content - loop continues, error becomes feedback for next iteration
        return StepOutput(
            content=f"<error>Development failed (iteration {_iteration}): {str(e)}. Please analyze this error and fix it in the next iteration.</error>",
            success=False,
            error=str(e)
        )


def step_code_review(step_input: StepInput) -> StepOutput:
    """Code review step: Lead engineer reviews the code."""
    dev_output = step_input.previous_step_content or ""

    # Check if development had an error
    has_error = "<error>" in dev_output.lower()

    if has_error:
        # Pass through the error - don't try to review broken code
        log_entry("step", "code_review", {
            "iteration": _iteration,
            "skipped": True,
            "reason": "development had error"
        })
        print(f"\n[Code Review - Iteration {_iteration}] Skipped (development had error)")
        return StepOutput(
            content=f"{dev_output}\n\n<code_review>CHANGES_REQUESTED: Development step failed. Please fix the error first.</code_review>",
            success=True  # success=True so workflow continues
        )

    prompt = f"""Review the code implementation in {OWNER}/{REPO}.

Instructions:
1. Use `get_file_contents` to read README.md from the repository
2. Review the content for:
   - Clarity and completeness
   - Best practices
   - Any issues that need to be addressed
3. Provide your review verdict

End your response with exactly one of:
- APPROVED (if the code meets standards)
- CHANGES_REQUESTED (if improvements are needed, list what needs to change)"""

    log_entry("step", "code_review", {
        "iteration": _iteration,
        "input": dev_output[:500] if dev_output else "(no input)"
    })

    try:
        print(f"\n[Code Review - Iteration {_iteration}] Lead engineer reviewing...")
        result = _run_async(lead_engineer_agent.arun(prompt))
        output = result.content or ""

        log_entry("agent", "lead_engineer", {
            "iteration": _iteration,
            "output": output
        })

        print(f"[Code Review - Iteration {_iteration}] Complete")
        return StepOutput(content=output, success=True)

    except Exception as e:
        error_msg = f"Code review error (iteration {_iteration}): {str(e)}\n{traceback.format_exc()}"
        log_entry("error", "code_review", {"iteration": _iteration, "error": error_msg})
        print(f"[Code Review - Iteration {_iteration}] Error: {str(e)}")
        # Return error as feedback - loop continues
        return StepOutput(
            content=f"<error>Code review failed (iteration {_iteration}): {str(e)}. CHANGES_REQUESTED: Please retry.</error>",
            success=False,
            error=str(e)
        )


def step_security_review(step_input: StepInput) -> StepOutput:
    """Security review step: Security engineer reviews for vulnerabilities."""
    code_review = step_input.previous_step_content or ""

    # Check if previous steps had errors
    has_error = "<error>" in code_review.lower()

    if has_error:
        # Pass through the error - don't try to review broken code
        log_entry("step", "security_review", {
            "iteration": _iteration,
            "skipped": True,
            "reason": "previous step had error"
        })
        print(f"\n[Security Review - Iteration {_iteration}] Skipped (previous step had error)")
        # Combine for feedback
        combined = f"""<code_review>
{code_review}
</code_review>

<security_review>CHANGES_REQUIRED: Previous steps failed. Please fix errors first.</security_review>"""
        return StepOutput(content=combined, success=True)

    prompt = f"""Review the code in {OWNER}/{REPO} for security vulnerabilities.

Instructions:
1. Use `get_file_contents` to read README.md from the repository
2. Check for any security concerns:
   - Sensitive information exposure
   - Any security anti-patterns
3. Provide your security assessment

End your response with exactly one of:
- APPROVED (if no security issues found)
- CHANGES_REQUIRED (if security issues exist, list what needs to be fixed)"""

    log_entry("step", "security_review", {
        "iteration": _iteration,
        "input": code_review[:500] if code_review else "(no input)"
    })

    try:
        print(f"\n[Security Review - Iteration {_iteration}] Security engineer reviewing...")
        result = _run_async(security_engineer_agent.arun(prompt))
        output = result.content or ""

        # Combine code review and security review for feedback to next iteration
        combined = f"""<code_review>
{code_review}
</code_review>

<security_review>
{output}
</security_review>"""

        log_entry("agent", "security_engineer", {
            "iteration": _iteration,
            "output": output
        })

        print(f"[Security Review - Iteration {_iteration}] Complete")
        return StepOutput(content=combined, success=True)

    except Exception as e:
        error_msg = f"Security review error (iteration {_iteration}): {str(e)}\n{traceback.format_exc()}"
        log_entry("error", "security_review", {"iteration": _iteration, "error": error_msg})
        print(f"[Security Review - Iteration {_iteration}] Error: {str(e)}")
        # Return error as feedback - loop continues
        combined = f"""<code_review>
{code_review}
</code_review>

<security_review>
<error>Security review failed (iteration {_iteration}): {str(e)}. CHANGES_REQUIRED: Please retry.</error>
</security_review>"""
        return StepOutput(
            content=combined,
            success=False,
            error=str(e)
        )


def should_continue(outputs: List[StepOutput]) -> bool:
    """
    End condition for the loop.
    Returns True to EXIT the loop when both reviews are approved (and no errors).
    Returns False to CONTINUE looping.
    """
    if not outputs:
        return False  # Continue if no outputs yet

    last_output = outputs[-1].content.lower() if outputs else ""

    # Check for errors - if there are errors, continue looping to fix them
    if "<error>" in last_output:
        log_entry("loop", "end_condition", {
            "iteration": _iteration,
            "result": "ERROR DETECTED - continuing loop to self-correct"
        })
        print(f"\n[Loop] Error detected - continuing to iteration {_iteration + 1} to self-correct")
        return False  # Continue loop to fix error

    # Check for approval - both code review and security review must approve
    code_approved = "approved" in last_output and "changes_requested" not in last_output
    security_approved = "approved" in last_output and "changes_required" not in last_output

    if code_approved and security_approved:
        log_entry("loop", "end_condition", {
            "iteration": _iteration,
            "result": "APPROVED - exiting loop"
        })
        print(f"\n[Loop] Both reviews APPROVED - exiting loop after {_iteration} iteration(s)")
        return True  # Exit loop

    log_entry("loop", "end_condition", {
        "iteration": _iteration,
        "result": "CHANGES REQUESTED - continuing loop"
    })
    print(f"\n[Loop] Changes requested - continuing to iteration {_iteration + 1}")
    return False  # Continue loop


def step_summary(step_input: StepInput) -> StepOutput:
    """Generate final summary."""
    _ = step_input  # Available if needed for dynamic summary
    global _iteration
    iterations = _iteration
    _iteration = 0  # Reset for next run

    output = f"""## Implementation Complete

**Repository:** {OWNER}/{REPO}
**Iterations:** {iterations}

### Summary
- Repository created/verified
- Code implemented and reviewed
- Lead engineer: APPROVED
- Security engineer: APPROVED

All reviews passed. Implementation complete."""

    log_entry("step", "summary", {
        "iterations": iterations,
        "output": output
    })

    print(f"\n[Summary] Workflow complete in {iterations} iteration(s)")
    return StepOutput(content=output, success=True)


# In-memory database for workflow session history
workflow_db = InMemoryDb()

# Workflow definition with review loop (no max_iterations - loops until approved)
# Errors don't break the loop - they become feedback for self-correction
implementation_cycle_workflow = Workflow(
    name="Implementation Cycle",
    stream=False,
    description="Development -> Code Review -> Security Review loop until approved (self-correcting on errors)",
    db=workflow_db,
    add_workflow_history_to_steps=True,
    steps=[
        Step(name="setup", executor=step_setup),
        Loop(
            name="Review Loop",
            steps=[
                Step(name="development", executor=step_development),
                Step(name="code_review", executor=step_code_review),
                Step(name="security_review", executor=step_security_review),
            ],
            end_condition=should_continue,
            # No max_iterations - loops until both reviews approve
        ),
        Step(name="summary", executor=step_summary),
    ]
)


def run_implementation_cycle(spec: str = "") -> dict:
    """Run the workflow with an optional specification string."""
    global _iteration
    _iteration = 0

    log_file = init_log()

    log_entry("workflow", "start", {
        "input": spec[:500] if spec else "(no input)",
        "owner": OWNER,
        "repo": REPO
    })

    print("=" * 60)
    print("STARTING IMPLEMENTATION CYCLE WORKFLOW")
    print(f"Repository: {OWNER}/{REPO}")
    print(f"Log file: {log_file}")
    print("Loops until both Lead Engineer and Security Engineer approve")
    print("Errors trigger self-correction (loop continues)")
    print("=" * 60)

    result = implementation_cycle_workflow.run(input=spec)
    output = result.content or ""

    log_entry("workflow", "complete", {
        "output": output
    })

    print("=" * 60)
    print("WORKFLOW COMPLETE")
    print("=" * 60)
    print(output)

    return {"success": True, "content": output, "log_file": str(log_file)}


if __name__ == "__main__":
    result = run_implementation_cycle()
    print(f"\nLog file: {result['log_file']}")

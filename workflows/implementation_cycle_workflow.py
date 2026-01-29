"""
Implementation Cycle Workflow

A workflow that handles the implementation cycle with development, code review,
security review, and revision loop.

All communication between agents is file-based:
1. Development (Software Engineer) - Saves code to file → outputs file path
2. Code Review (Lead Engineer) - Reads code file → saves review to file → outputs file path
3. Security Review (Security Engineer) - Reads code file → saves review to file → outputs file path
4. Revision Loop - Software Engineer reads feedback files → updates code file

File Structure:
    output/
    ├── implementations/     # Code files from Software Engineer
    ├── code_reviews/        # Review files from Lead Engineer
    └── security_reviews/    # Review files from Security Engineer

Usage:
    from workflows.implementation_cycle_workflow import (
        implementation_cycle_workflow,
        ImplementationCycleInput
    )

    workflow_input = ImplementationCycleInput(
        technical_document="[Architecture content here]",
        product_name="AI Assistant",
        task_description="Implement user authentication module"
    )

    result = implementation_cycle_workflow.run(input=workflow_input)
"""

import os
import sys
from datetime import datetime
from typing import Optional, List
from loguru import logger
from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Loop, Step, Workflow
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_error, log_info

from agents.software_engineer import software_engineer_agent
from agents.lead_engineer import lead_engineer_agent
from agents.security_engineer import security_engineer_agent


# ============================================================================
# INPUT MODEL
# ============================================================================

class ImplementationCycleInput(BaseModel):
    """Input model for Implementation Cycle Workflow."""
    technical_document: str = Field(..., description="Technical architecture/specification document")
    product_name: str = Field(..., description="Name of the product/feature")
    task_description: str = Field(..., description="Specific task to implement")
    architecture_file_path: Optional[str] = Field(None, description="Path to architecture file")


# ============================================================================
# SESSION STATE FOR TRACKING FILES AND REVIEWS
# ============================================================================

class ImplementationState:
    """Tracks file paths and review statuses across the implementation cycle."""
    def __init__(self):
        self.iteration = 0
        self.code_file_path = ""
        self.code_review_file_path = ""
        self.security_review_file_path = ""
        self.code_review_status = "pending"
        self.security_review_status = "pending"
        self.approved = False

    def reset_reviews(self):
        """Reset review statuses for a new iteration."""
        self.code_review_status = "pending"
        self.security_review_status = "pending"
        self.code_review_file_path = ""
        self.security_review_file_path = ""


# Global state instance (per workflow run)
_state = ImplementationState()


# ============================================================================
# HELPER: Generate file paths (no versioning - same files get updated)
# ============================================================================

def _get_file_paths(product_name: str):
    """Generate consistent file paths (same files updated each iteration)."""
    safe_name = product_name.lower().replace(" ", "_").replace("/", "_")[:30]

    return {
        "code": f"implementations/software_engineer_{safe_name}.py",
        "code_review": f"code_reviews/lead_engineer_review_{safe_name}.md",
        "security_review": f"security_reviews/security_engineer_review_{safe_name}.md",
    }


# ============================================================================
# STEP 1: DEVELOPMENT (Software Engineer)
# ============================================================================

def run_development(step_input: StepInput) -> StepOutput:
    """Software Engineer implements code and saves to file."""
    global _state

    try:
        # Handle input types
        if isinstance(step_input.input, ImplementationCycleInput):
            workflow_input = step_input.input
        elif isinstance(step_input.input, dict):
            workflow_input = ImplementationCycleInput(**step_input.input)
        else:
            return StepOutput(content=f"Invalid input type: {type(step_input.input)}", success=False)

        _state.iteration += 1
        iteration = _state.iteration

        # Generate file paths (same files each iteration - no versioning)
        paths = _get_file_paths(workflow_input.product_name)
        _state.code_file_path = paths["code"]

        log_info(f"[DEVELOPMENT] Iteration {iteration} for: {workflow_input.product_name}")

        if iteration == 1:
            # First iteration - implement from scratch
            prompt = f"""You are the Software Engineer. Implement the following based on the technical architecture.

**Product/Feature:** {workflow_input.product_name}
**Task:** {workflow_input.task_description}

**Technical Architecture:**
{workflow_input.technical_document}

**Instructions:**
1. Write clean, production-ready Python code
2. Include proper error handling and input validation
3. Add docstrings and comments for complex logic
4. Follow security best practices

**IMPORTANT - Save your code:**
Use the `save_file` tool to save your implementation to: `{_state.code_file_path}`

After saving, confirm the file path in your response.
"""
        else:
            # Revision - read current code and feedback, update the same file
            prompt = f"""You are the Software Engineer. Revise your implementation based on review feedback.

**Product/Feature:** {workflow_input.product_name}
**Task:** {workflow_input.task_description}

**Instructions:**
1. Use `read_file` to read the current code from: `{_state.code_file_path}`
2. Use `read_file` to read code review feedback from: `{_state.code_review_file_path}`
3. Use `read_file` to read security review feedback from: `{_state.security_review_file_path}`
4. Address ALL feedback points from both reviews
5. Use `save_file` to save the revised code to: `{_state.code_file_path}` (overwrite the existing file)

After saving, confirm what changes you made.
"""

        result = software_engineer_agent.run(prompt)
        _state.reset_reviews()

        if result.content:
            log_info(f"[DEVELOPMENT] Completed - Code saved to: {_state.code_file_path}")
            return StepOutput(content=f"CODE_FILE:{_state.code_file_path}\n\n{result.content}", success=True)
        else:
            return StepOutput(content="Development failed - no output", success=False)

    except Exception as e:
        log_error(f"[DEVELOPMENT] Error: {str(e)}")
        return StepOutput(content=f"Development error: {str(e)}", success=False)


development_step = Step(
    name="development",
    description="Software Engineer implements code and saves to file",
    executor=run_development
)


# ============================================================================
# STEP 2: CODE REVIEW (Lead Engineer)
# ============================================================================

def run_code_review(step_input: StepInput) -> StepOutput:
    """Lead Engineer reads code file, reviews, and saves feedback to file."""
    global _state

    try:
        if isinstance(step_input.input, ImplementationCycleInput):
            workflow_input = step_input.input
        elif isinstance(step_input.input, dict):
            workflow_input = ImplementationCycleInput(**step_input.input)
        else:
            workflow_input = None

        # Generate review file path (same file each iteration)
        paths = _get_file_paths(workflow_input.product_name if workflow_input else "unknown")
        _state.code_review_file_path = paths["code_review"]

        log_info(f"[CODE REVIEW] Iteration {_state.iteration}")

        prompt = f"""You are the Lead Engineer. Review the code implementation for quality and architecture alignment.

**Instructions:**
1. Use `read_file` to read the code from: `{_state.code_file_path}`
2. Review against these criteria:
   - Code Quality: Clean, readable, well-structured?
   - Architecture Alignment: Follows the technical spec?
   - Best Practices: Coding standards followed?
   - Error Handling: Comprehensive?
   - Maintainability: Easy to maintain and extend?

3. Write your review with this format:
   - **Review Status**: APPROVED or CHANGES_REQUESTED
   - **Quality Score**: 1-10
   - **Strengths**: What's done well
   - **Issues Found**: Problems identified (if any)
   - **Required Changes**: Specific changes needed (if CHANGES_REQUESTED)

4. Use `save_file` to save your review to: `{_state.code_review_file_path}`

After saving, confirm the review status and file path.
"""

        result = lead_engineer_agent.run(prompt)

        if result.content:
            content_lower = result.content.lower()

            # Determine review status
            if "changes_requested" in content_lower or "changes requested" in content_lower:
                _state.code_review_status = "changes_requested"
            elif "approved" in content_lower:
                _state.code_review_status = "approved"
            else:
                _state.code_review_status = "changes_requested"

            log_info(f"[CODE REVIEW] Status: {_state.code_review_status} - Saved to: {_state.code_review_file_path}")
            return StepOutput(content=f"REVIEW_STATUS:{_state.code_review_status}\nREVIEW_FILE:{_state.code_review_file_path}\n\n{result.content}", success=True)
        else:
            return StepOutput(content="Code review failed", success=False)

    except Exception as e:
        log_error(f"[CODE REVIEW] Error: {str(e)}")
        return StepOutput(content=f"Code review error: {str(e)}", success=False)


code_review_step = Step(
    name="code_review",
    description="Lead Engineer reads code file, reviews, saves feedback to file",
    executor=run_code_review
)


# ============================================================================
# STEP 3: SECURITY REVIEW (Security Engineer)
# ============================================================================

def run_security_review(step_input: StepInput) -> StepOutput:
    """Security Engineer reads code file, reviews for vulnerabilities, saves feedback."""
    global _state

    try:
        if isinstance(step_input.input, ImplementationCycleInput):
            workflow_input = step_input.input
        elif isinstance(step_input.input, dict):
            workflow_input = ImplementationCycleInput(**step_input.input)
        else:
            workflow_input = None

        # Generate review file path (same file each iteration)
        paths = _get_file_paths(workflow_input.product_name if workflow_input else "unknown")
        _state.security_review_file_path = paths["security_review"]

        log_info(f"[SECURITY REVIEW] Iteration {_state.iteration}")

        prompt = f"""You are the Security Engineer. Review the code for security vulnerabilities.

**Instructions:**
1. Use `read_file` to read the code from: `{_state.code_file_path}`
2. Check for these security issues:
   - Injection vulnerabilities (SQL, XSS, command injection)
   - Authentication/Authorization flaws
   - Sensitive data exposure
   - Input validation issues
   - Insecure error handling
   - OWASP Top 10 vulnerabilities

3. Write your review with this format:
   - **Security Status**: APPROVED or CHANGES_REQUIRED
   - **Vulnerabilities Found**: List with severity (Critical/High/Medium/Low)
   - **Required Fixes**: Specific security fixes needed
   - **Recommendations**: Additional security improvements

4. Use `save_file` to save your review to: `{_state.security_review_file_path}`

After saving, confirm the security status and file path.
"""

        result = security_engineer_agent.run(prompt)

        if result.content:
            content_lower = result.content.lower()

            # Determine security status
            if "changes_required" in content_lower or "changes required" in content_lower:
                _state.security_review_status = "changes_required"
            elif "critical" in content_lower or ("high" in content_lower and "vulnerabilit" in content_lower):
                _state.security_review_status = "changes_required"
            elif "approved" in content_lower:
                _state.security_review_status = "approved"
            else:
                _state.security_review_status = "approved"

            log_info(f"[SECURITY REVIEW] Status: {_state.security_review_status} - Saved to: {_state.security_review_file_path}")
            return StepOutput(content=f"SECURITY_STATUS:{_state.security_review_status}\nREVIEW_FILE:{_state.security_review_file_path}\n\n{result.content}", success=True)
        else:
            return StepOutput(content="Security review failed", success=False)

    except Exception as e:
        log_error(f"[SECURITY REVIEW] Error: {str(e)}")
        return StepOutput(content=f"Security review error: {str(e)}", success=False)


security_review_step = Step(
    name="security_review",
    description="Security Engineer reads code file, reviews for vulnerabilities, saves feedback",
    executor=run_security_review
)


# ============================================================================
# LOOP END CONDITION
# ============================================================================

def reviews_passed(outputs: List[StepOutput]) -> bool:
    """Check if both reviews passed. Returns True to break loop."""
    global _state

    code_approved = _state.code_review_status == "approved"
    security_approved = _state.security_review_status == "approved"

    if code_approved and security_approved:
        _state.approved = True
        log_info("[LOOP] All reviews APPROVED - breaking loop")
        return True

    if _state.iteration >= 3:
        log_info("[LOOP] Max iterations (3) reached - breaking loop")
        return True

    log_info(f"[LOOP] Reviews not passed - Code: {_state.code_review_status}, Security: {_state.security_review_status}")
    return False


# ============================================================================
# FINAL OUTPUT
# ============================================================================

def format_final_output(step_input: StepInput) -> StepOutput:
    """Generate final summary."""
    global _state

    try:
        if isinstance(step_input.input, ImplementationCycleInput):
            workflow_input = step_input.input
        else:
            workflow_input = None

        status = "APPROVED" if _state.approved else "COMPLETED_WITH_NOTES"

        summary = f"""
## Implementation Cycle Complete

**Product/Feature**: {workflow_input.product_name if workflow_input else "Unknown"}
**Status**: `{status}`
**Iterations**: {_state.iteration}
**Code Review**: {_state.code_review_status}
**Security Review**: {_state.security_review_status}

### Output Files
- **Code**: `{_state.code_file_path}`
- **Code Review**: `{_state.code_review_file_path}`
- **Security Review**: `{_state.security_review_file_path}`
"""

        log_info(f"[COMPLETE] Status: {status}, Iterations: {_state.iteration}")

        # Reset state for next run
        final_code_path = _state.code_file_path
        _state.__init__()

        return StepOutput(content=summary, success=True)

    except Exception as e:
        log_error(f"[FINAL] Error: {str(e)}")
        return StepOutput(content=f"Output error: {str(e)}", success=False)


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

implementation_cycle_workflow = Workflow(
    name="Implementation Cycle Workflow",
    stream=False,
    description="""Implementation cycle with file-based agent communication:

    Loop (max 3 iterations):
    1. Development - Software Engineer saves/updates code file
    2. Code Review - Lead Engineer reads code, saves/updates review file
    3. Security Review - Security Engineer reads code, saves/updates review file

    On revision: Software Engineer reads feedback files, updates same code file

    Output Files (same files updated each iteration):
    - implementations/software_engineer_[name].py
    - code_reviews/lead_engineer_review_[name].md
    - security_reviews/security_engineer_review_[name].md""",
    steps=[
        Loop(
            name="Implementation Review Loop",
            steps=[development_step, code_review_step, security_review_step],
            end_condition=reviews_passed,
            max_iterations=3,
        ),
        format_final_output,
    ]
)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def run_implementation_cycle(
    technical_document: str,
    product_name: str,
    task_description: str,
    architecture_file_path: Optional[str] = None,
) -> dict:
    """Run the implementation cycle workflow."""
    global _state
    _state = ImplementationState()

    workflow_input = ImplementationCycleInput(
        technical_document=technical_document,
        product_name=product_name,
        task_description=task_description,
        architecture_file_path=architecture_file_path,
    )

    log_info(f"Starting implementation cycle: {product_name}")
    result = implementation_cycle_workflow.run(input=workflow_input)

    return {
        "success": result.success,
        "content": result.content,
        "code_file": _state.code_file_path,
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Implementation Cycle Workflow")
    parser.add_argument("--architecture-file", required=True)
    parser.add_argument("--product-name", required=True)
    parser.add_argument("--task", required=True)

    args = parser.parse_args()

    with open(args.architecture_file, "r") as f:
        architecture_content = f.read()

    result = run_implementation_cycle(
        technical_document=architecture_content,
        product_name=args.product_name,
        task_description=args.task,
        architecture_file_path=args.architecture_file,
    )

    print(result["content"])

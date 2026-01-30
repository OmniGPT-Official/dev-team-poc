"""
Implementation Cycle Workflow

A workflow that handles the implementation cycle with development, code review,
security review, and revision loop.

All communication between agents is GitHub-based:
1. Development (Software Engineer) - Creates/updates code file in GitHub repo
2. Code Review (Lead Engineer) - Reads code from GitHub → saves review to GitHub
3. Security Review (Security Engineer) - Reads code from GitHub → saves review to GitHub
4. Revision Loop - Software Engineer reads feedback from GitHub → updates code in GitHub

GitHub File Structure (in target repo):
    .dev-team/
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
        task_description="Implement user authentication module",
        project_context=ProjectContext(
            github_repo="my-app",
            github_owner="my-org"
        )
    )

    result = implementation_cycle_workflow.run(input=workflow_input)
"""

import os
import sys
import asyncio
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
# ASYNC HELPER - Run async agent calls from sync workflow steps
# ============================================================================

# Persistent event loop for running async code from sync context
_event_loop = None


def get_or_create_event_loop():
    """Get existing event loop or create a new one."""
    global _event_loop
    if _event_loop is None or _event_loop.is_closed():
        _event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_event_loop)
    return _event_loop


def run_async(coro):
    """
    Run an async coroutine from synchronous code.
    Uses a persistent event loop to avoid 'Event loop is closed' errors.
    """
    loop = get_or_create_event_loop()
    return loop.run_until_complete(coro)


# ============================================================================
# INPUT MODEL
# ============================================================================

class ProjectContext(BaseModel):
    """Context for external project integrations."""
    github_repo: str = Field(..., description="GitHub repository name (e.g., 'my-app')")
    github_owner: str = Field(..., description="GitHub owner/org (e.g., 'my-org')")
    vercel_project: Optional[str] = Field(None, description="Vercel project name")
    vercel_team: Optional[str] = Field(None, description="Vercel team/org slug")
    supabase_project: Optional[str] = Field(None, description="Supabase project name/ref")
    supabase_org: Optional[str] = Field(None, description="Supabase organization")


class ImplementationCycleInput(BaseModel):
    """Input model for Implementation Cycle Workflow."""
    technical_document: str = Field(..., description="Technical architecture/specification document")
    product_name: str = Field(..., description="Name of the product/feature")
    task_description: str = Field(..., description="Specific task to implement")
    architecture_file_path: Optional[str] = Field(None, description="Path to architecture file")
    project_context: Optional[ProjectContext] = Field(None, description="GitHub/Vercel/Supabase project context")


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
        # GitHub context
        self.github_repo = ""
        self.github_owner = ""
        self.vercel_project = ""
        self.vercel_team = ""
        self.supabase_project = ""
        self.supabase_org = ""

    def reset_reviews(self):
        """Reset review statuses for a new iteration."""
        self.code_review_status = "pending"
        self.security_review_status = "pending"
        self.code_review_file_path = ""
        self.security_review_file_path = ""

    def set_project_context(self, project_context: Optional[ProjectContext]):
        """Set project context from input."""
        if project_context:
            self.github_repo = project_context.github_repo
            self.github_owner = project_context.github_owner
            self.vercel_project = project_context.vercel_project or ""
            self.vercel_team = project_context.vercel_team or ""
            self.supabase_project = project_context.supabase_project or ""
            self.supabase_org = project_context.supabase_org or ""


# Global state instance (per workflow run)
_state = ImplementationState()


# ============================================================================
# HELPER: Generate GitHub file paths (stored in .dev-team/ directory)
# ============================================================================

def _get_github_file_paths(product_name: str):
    """Generate consistent GitHub file paths (stored in .dev-team/ directory)."""
    safe_name = product_name.lower().replace(" ", "_").replace("/", "_")[:30]

    return {
        "code": f".dev-team/implementations/software_engineer_{safe_name}.py",
        "code_review": f".dev-team/code_reviews/lead_engineer_review_{safe_name}.md",
        "security_review": f".dev-team/security_reviews/security_engineer_review_{safe_name}.md",
    }


# ============================================================================
# STEP 1: DEVELOPMENT (Software Engineer)
# ============================================================================

def run_development(step_input: StepInput) -> StepOutput:
    """Software Engineer implements code and saves to GitHub."""
    global _state

    try:
        # Handle input types
        if isinstance(step_input.input, ImplementationCycleInput):
            workflow_input = step_input.input
        elif isinstance(step_input.input, dict):
            workflow_input = ImplementationCycleInput(**step_input.input)
        else:
            return StepOutput(content=f"Invalid input type: {type(step_input.input)}", success=False)

        # Set project context on first iteration
        if _state.iteration == 0:
            _state.set_project_context(workflow_input.project_context)

        _state.iteration += 1
        iteration = _state.iteration

        # Generate GitHub file paths
        paths = _get_github_file_paths(workflow_input.product_name)
        _state.code_file_path = paths["code"]

        log_info(f"[DEVELOPMENT] Iteration {iteration} for: {workflow_input.product_name}")

        # Build GitHub context string for prompts
        github_context = ""
        if _state.github_repo and _state.github_owner:
            github_context = f"""
**GitHub Repository:** {_state.github_owner}/{_state.github_repo}
**Vercel Project:** {_state.vercel_project or 'N/A'} (Team: {_state.vercel_team or 'N/A'})
**Supabase Project:** {_state.supabase_project or 'N/A'} (Org: {_state.supabase_org or 'N/A'})
"""

        if iteration == 1:
            # First iteration - implement from scratch
            prompt = f"""You are the Software Engineer. Implement the following based on the technical architecture.

**Product/Feature:** {workflow_input.product_name}
**Task:** {workflow_input.task_description}
{github_context}
**Technical Architecture:**
{workflow_input.technical_document}

**Code Requirements:**
1. Write clean, production-ready Python code
2. Include proper error handling and input validation
3. Add docstrings and comments for complex logic
4. Follow security best practices

---

**CRITICAL INSTRUCTIONS - READ CAREFULLY:**

**STEP 1: CREATE THE REPOSITORY (call ONCE)**
Call `create_repository` with these parameters:
- name: "{_state.github_repo}"
- description: "Implementation for {workflow_input.product_name}"
- private: false

Wait for the result. If repo already exists (error 422), that's fine - proceed.

**STEP 2: SAVE YOUR CODE FILE (call ONCE)**
Call `create_or_update_file` with these parameters:
- owner: "{_state.github_owner}"
- repo: "{_state.github_repo}"
- path: "{_state.code_file_path}"
- content: [your Python code as a plain string]
- message: "feat: implement {workflow_input.product_name}"
- branch: "main"

**IMPORTANT RULES:**
- Call each tool EXACTLY ONCE - do NOT retry if you get a result back
- Do NOT call `get_file_contents` or `get_repository` in this step
- After `create_or_update_file` returns, STOP calling tools and write your response
- If a tool call fails with an error, report the error - do NOT retry

After the file is saved, respond with:
1. A brief summary of the code you implemented
2. Confirmation: "Saved to: {_state.github_owner}/{_state.github_repo}/{_state.code_file_path}"
"""
        else:
            # Revision - read current code and feedback from GitHub, update the file
            prompt = f"""You are the Software Engineer. Revise your implementation based on review feedback.

**Product/Feature:** {workflow_input.product_name}
**Task:** {workflow_input.task_description}
{github_context}

---

**CRITICAL INSTRUCTIONS - CALL EACH TOOL EXACTLY ONCE:**

**STEP 1: Read your current code** (call `get_file_contents` ONCE)
- owner: "{_state.github_owner}"
- repo: "{_state.github_repo}"
- path: "{_state.code_file_path}"

**STEP 2: Read code review feedback** (call `get_file_contents` ONCE)
- owner: "{_state.github_owner}"
- repo: "{_state.github_repo}"
- path: "{_state.code_review_file_path}"

**STEP 3: Read security review feedback** (call `get_file_contents` ONCE)
- owner: "{_state.github_owner}"
- repo: "{_state.github_repo}"
- path: "{_state.security_review_file_path}"

**STEP 4: Revise your code based on the feedback**

**STEP 5: Save the revised code** (call `create_or_update_file` ONCE)
- owner: "{_state.github_owner}"
- repo: "{_state.github_repo}"
- path: "{_state.code_file_path}"
- content: [your revised Python code as plain string]
- message: "fix: address review feedback for {workflow_input.product_name}"
- branch: "main"

**IMPORTANT RULES:**
- Call each tool EXACTLY ONCE - do NOT retry if you get a result back
- After `create_or_update_file` returns, STOP calling tools and write your response
- If a tool call fails with an error, report the error - do NOT retry

After saving, respond with a summary of changes made.
"""

        # Run async agent with MCP tools
        result = run_async(software_engineer_agent.arun(prompt))
        _state.reset_reviews()

        if result.content:
            log_info(f"[DEVELOPMENT] Completed - Code saved to GitHub: {_state.github_owner}/{_state.github_repo}/{_state.code_file_path}")
            return StepOutput(content=f"CODE_FILE:{_state.github_owner}/{_state.github_repo}/{_state.code_file_path}\n\n{result.content}", success=True)
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
    """Lead Engineer reads code from GitHub, reviews, and saves feedback to GitHub."""
    global _state

    try:
        if isinstance(step_input.input, ImplementationCycleInput):
            workflow_input = step_input.input
        elif isinstance(step_input.input, dict):
            workflow_input = ImplementationCycleInput(**step_input.input)
        else:
            workflow_input = None

        # Generate review file path (same file each iteration)
        paths = _get_github_file_paths(workflow_input.product_name if workflow_input else "unknown")
        _state.code_review_file_path = paths["code_review"]

        log_info(f"[CODE REVIEW] Iteration {_state.iteration}")

        prompt = f"""You are the Lead Engineer. Review the code implementation for quality and architecture alignment.

**CRITICAL INSTRUCTIONS - CALL EACH TOOL EXACTLY ONCE:**

**STEP 1: Read the code** (call `get_file_contents` ONCE)
- owner: "{_state.github_owner}"
- repo: "{_state.github_repo}"
- path: "{_state.code_file_path}"

**STEP 2: Review the code against these criteria:**
- Code Quality: Clean, readable, well-structured?
- Architecture Alignment: Follows the technical spec?
- Best Practices: Coding standards followed?
- Error Handling: Comprehensive?
- Maintainability: Easy to maintain and extend?

**STEP 3: Write your review with this format:**
- **Review Status**: APPROVED or CHANGES_REQUESTED
- **Quality Score**: 1-10
- **Strengths**: What's done well
- **Issues Found**: Problems identified (if any)
- **Required Changes**: Specific changes needed (if CHANGES_REQUESTED)

**STEP 4: Save your review** (call `create_or_update_file` ONCE)
- owner: "{_state.github_owner}"
- repo: "{_state.github_repo}"
- path: "{_state.code_review_file_path}"
- content: [your review in markdown format as plain string]
- message: "docs: add code review for iteration {_state.iteration}"
- branch: "main"

**IMPORTANT RULES:**
- Call each tool EXACTLY ONCE - do NOT retry if you get a result back
- After `create_or_update_file` returns, STOP calling tools and write your response
- If a tool call fails, report the error - do NOT retry

After saving, confirm: "Review Status: [APPROVED/CHANGES_REQUESTED]"
"""

        # Run async agent with MCP tools
        result = run_async(lead_engineer_agent.arun(prompt))

        if result.content:
            content_lower = result.content.lower()

            # Determine review status
            if "changes_requested" in content_lower or "changes requested" in content_lower:
                _state.code_review_status = "changes_requested"
            elif "approved" in content_lower:
                _state.code_review_status = "approved"
            else:
                _state.code_review_status = "changes_requested"

            log_info(f"[CODE REVIEW] Status: {_state.code_review_status} - Saved to GitHub: {_state.github_owner}/{_state.github_repo}/{_state.code_review_file_path}")
            return StepOutput(content=f"REVIEW_STATUS:{_state.code_review_status}\nREVIEW_FILE:{_state.github_owner}/{_state.github_repo}/{_state.code_review_file_path}\n\n{result.content}", success=True)
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
    """Security Engineer reads code from GitHub, reviews for vulnerabilities, saves feedback to GitHub."""
    global _state

    try:
        if isinstance(step_input.input, ImplementationCycleInput):
            workflow_input = step_input.input
        elif isinstance(step_input.input, dict):
            workflow_input = ImplementationCycleInput(**step_input.input)
        else:
            workflow_input = None

        # Generate review file path (same file each iteration)
        paths = _get_github_file_paths(workflow_input.product_name if workflow_input else "unknown")
        _state.security_review_file_path = paths["security_review"]

        log_info(f"[SECURITY REVIEW] Iteration {_state.iteration}")

        prompt = f"""You are the Security Engineer. Review the code for security vulnerabilities.

**CRITICAL INSTRUCTIONS - CALL EACH TOOL EXACTLY ONCE:**

**STEP 1: Read the code** (call `get_file_contents` ONCE)
- owner: "{_state.github_owner}"
- repo: "{_state.github_repo}"
- path: "{_state.code_file_path}"

**STEP 2: Check for these security issues:**
- Injection vulnerabilities (SQL, XSS, command injection)
- Authentication/Authorization flaws
- Sensitive data exposure
- Input validation issues
- Insecure error handling
- OWASP Top 10 vulnerabilities

**STEP 3: Write your review with this format:**
- **Security Status**: APPROVED or CHANGES_REQUIRED
- **Vulnerabilities Found**: List with severity (Critical/High/Medium/Low)
- **Required Fixes**: Specific security fixes needed
- **Recommendations**: Additional security improvements

**STEP 4: Save your review** (call `create_or_update_file` ONCE)
- owner: "{_state.github_owner}"
- repo: "{_state.github_repo}"
- path: "{_state.security_review_file_path}"
- content: [your security review in markdown format as plain string]
- message: "docs: add security review for iteration {_state.iteration}"
- branch: "main"

**IMPORTANT RULES:**
- Call each tool EXACTLY ONCE - do NOT retry if you get a result back
- After `create_or_update_file` returns, STOP calling tools and write your response
- If a tool call fails, report the error - do NOT retry

After saving, confirm: "Security Status: [APPROVED/CHANGES_REQUIRED]"
"""

        # Run async agent with MCP tools
        result = run_async(security_engineer_agent.arun(prompt))

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

            log_info(f"[SECURITY REVIEW] Status: {_state.security_review_status} - Saved to GitHub: {_state.github_owner}/{_state.github_repo}/{_state.security_review_file_path}")
            return StepOutput(content=f"SECURITY_STATUS:{_state.security_review_status}\nREVIEW_FILE:{_state.github_owner}/{_state.github_repo}/{_state.security_review_file_path}\n\n{result.content}", success=True)
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

        github_repo_url = f"https://github.com/{_state.github_owner}/{_state.github_repo}" if _state.github_owner and _state.github_repo else "N/A"

        summary = f"""
## Implementation Cycle Complete

**Product/Feature**: {workflow_input.product_name if workflow_input else "Unknown"}
**Status**: `{status}`
**Iterations**: {_state.iteration}
**Code Review**: {_state.code_review_status}
**Security Review**: {_state.security_review_status}

### GitHub Repository
- **Repository**: [{_state.github_owner}/{_state.github_repo}]({github_repo_url})

### Output Files (in GitHub)
- **Code**: `{_state.code_file_path}`
- **Code Review**: `{_state.code_review_file_path}`
- **Security Review**: `{_state.security_review_file_path}`
"""

        log_info(f"[COMPLETE] Status: {status}, Iterations: {_state.iteration}, Repo: {_state.github_owner}/{_state.github_repo}")

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
    description="""Implementation cycle with GitHub-based agent communication:

    Loop (max 3 iterations):
    1. Development - Software Engineer creates/updates code in GitHub repo
    2. Code Review - Lead Engineer reads code from GitHub, saves review to GitHub
    3. Security Review - Security Engineer reads code from GitHub, saves review to GitHub

    On revision: Software Engineer reads feedback from GitHub, updates code in GitHub

    Output Files (stored in GitHub repo under .dev-team/):
    - .dev-team/implementations/software_engineer_[name].py
    - .dev-team/code_reviews/lead_engineer_review_[name].md
    - .dev-team/security_reviews/security_engineer_review_[name].md""",
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
    github_repo: Optional[str] = None,
    github_owner: Optional[str] = None,
    vercel_project: Optional[str] = None,
    vercel_team: Optional[str] = None,
    supabase_project: Optional[str] = None,
    supabase_org: Optional[str] = None,
) -> dict:
    """Run the implementation cycle workflow."""
    global _state
    _state = ImplementationState()

    # Build project context if GitHub details provided
    project_ctx = None
    if github_repo and github_owner:
        project_ctx = ProjectContext(
            github_repo=github_repo,
            github_owner=github_owner,
            vercel_project=vercel_project,
            vercel_team=vercel_team,
            supabase_project=supabase_project,
            supabase_org=supabase_org,
        )

    workflow_input = ImplementationCycleInput(
        technical_document=technical_document,
        product_name=product_name,
        task_description=task_description,
        architecture_file_path=architecture_file_path,
        project_context=project_ctx,
    )

    log_info(f"Starting implementation cycle: {product_name} (GitHub: {github_owner}/{github_repo})")
    result = implementation_cycle_workflow.run(input=workflow_input)

    return {
        "success": result.success,
        "content": result.content,
        "code_file": f"{_state.github_owner}/{_state.github_repo}/{_state.code_file_path}" if _state.github_owner else _state.code_file_path,
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
    parser.add_argument("--github-repo", required=True, help="GitHub repository name")
    parser.add_argument("--github-owner", required=True, help="GitHub owner/organization")
    parser.add_argument("--vercel-project", help="Vercel project name")
    parser.add_argument("--vercel-team", help="Vercel team/org slug")
    parser.add_argument("--supabase-project", help="Supabase project name/ref")
    parser.add_argument("--supabase-org", help="Supabase organization")

    args = parser.parse_args()

    with open(args.architecture_file, "r") as f:
        architecture_content = f.read()

    result = run_implementation_cycle(
        technical_document=architecture_content,
        product_name=args.product_name,
        task_description=args.task,
        architecture_file_path=args.architecture_file,
        github_repo=args.github_repo,
        github_owner=args.github_owner,
        vercel_project=args.vercel_project,
        vercel_team=args.vercel_team,
        supabase_project=args.supabase_project,
        supabase_org=args.supabase_org,
    )

    print(result["content"])

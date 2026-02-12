"""
Product Requirements Workflow

Flow:
1. Create PRD (new project) or Feature Spec (existing project) → Save to Google Docs
2. Create simple Architecture Document → Save to Google Docs
3. Return BOTH document URLs

Input: PROJECT_TYPE, PROJECT_NAME, DESCRIPTION
Output: 2 Google Docs URLs (PRD/FS + Architecture)
"""

import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Step, Workflow
from agno.workflow.condition import Condition
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _log(emoji: str, step: str, msg: str, data: dict = None):
    """Concise logging."""
    print(f"{emoji} [{step}] {msg}")
    log_info(f"[{step}] {msg}")


def get_product_lead_agent():
    from agents.product_lead import product_lead_agent
    return product_lead_agent


def get_lead_engineer_agent():
    from agents.lead_engineer import lead_engineer_agent
    return lead_engineer_agent


# ============================================================================
# CONDITION EVALUATORS
# ============================================================================

def is_new_project(step_input: StepInput) -> bool:
    """Check if this is a new project."""
    content = str(step_input.input).lower()
    if "project_type: new" in content or "project_type:new" in content:
        _log("📋", "CONDITION", "Detected: NEW project")
        return True
    if any(kw in content for kw in ["new project", "from scratch", "build a new", "create a new"]):
        _log("📋", "CONDITION", "Detected: NEW project (keyword)")
        return True
    return False


def is_existing_project(step_input: StepInput) -> bool:
    """Check if this is an existing project."""
    content = str(step_input.input).lower()
    if "project_type: existing" in content or "project_type:existing" in content:
        _log("📋", "CONDITION", "Detected: EXISTING project")
        return True
    if any(kw in content for kw in ["existing product", "add feature", "enhance", "update"]):
        _log("📋", "CONDITION", "Detected: EXISTING project (keyword)")
        return True
    return False


# ============================================================================
# SIMPLE EXECUTOR WRAPPERS
# ============================================================================

def create_prd_executor(step_input: StepInput) -> StepOutput:
    """Simple wrapper to call product_lead with user_id from workflow."""
    from agno.workflow.types import StepOutput

    # Get user_id from workflow session
    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    description = """You MUST create a PRD and save it to Google Docs.

**CRITICAL: USE ONLY THE INFORMATION PROVIDED IN THE INPUT BELOW. DO NOT ADD EXAMPLES, DO NOT HALLUCINATE, DO NOT USE PLACEHOLDER CONTENT LIKE "REACT PRO" OR "TASK MANAGER". USE THE ACTUAL PROJECT DETAILS FROM THE INPUT.**

**STEP 1: Write the PRD content with these exact sections:**

1. OVERVIEW - What is this product? (USE ONLY INFO FROM INPUT)
2. GOALS - What problem does it solve? (USE ONLY INFO FROM INPUT)
3. TARGET USERS - Who will use it? (USE ONLY INFO FROM INPUT)
4. FEATURES - List of features (USE ONLY FEATURES FROM INPUT - if none provided, write "To be defined")
5. SUCCESS METRICS - How do we measure success? (USE ONLY INFO FROM INPUT - if none provided, write "To be defined")

**FORMATTING RULES:**
- Use PLAIN TEXT only (no markdown symbols like **, __, ##, `, [])
- Use "====" under section headings
- Use simple bullet points with "•" or "-"

**STEP 2: YOU MUST call the create_prd_document tool**

Call it NOW with:
- title: "PRD: [EXACT project name from input - DO NOT CHANGE IT]"
- content: (the PRD content you wrote above using ONLY the input data)
- project_name: "[EXACT project name from input]"

**STEP 3: Return the Google Docs URL**

The tool will return a URL like https://docs.google.com/document/d/XXXXX/edit
You MUST include this complete URL in your response.

CRITICAL: DO NOT HALLUCINATE. USE ONLY THE INPUT DATA. DO NOT ADD EXAMPLES."""

    # Call agent with user_id
    import asyncio
    result = asyncio.run(get_product_lead_agent().arun(description + f"\n\nInput: {step_input.input}", user_id=user_id))
    return StepOutput(content=result.content, success=True)


def create_feature_spec_executor(step_input: StepInput) -> StepOutput:
    """Simple wrapper to call product_lead with user_id from workflow."""
    from agno.workflow.types import StepOutput

    # Get user_id from workflow session
    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    description = """Create a Feature Specification for this existing product.

**CRITICAL: USE ONLY THE INFORMATION PROVIDED IN THE INPUT BELOW. DO NOT ADD EXAMPLES, DO NOT HALLUCINATE, DO NOT USE PLACEHOLDER CONTENT.**

Create a concise Feature Spec with:
1. Feature Overview - What does this feature do? (USE ONLY INFO FROM INPUT)
2. User Stories - Who needs it and why? (USE ONLY INFO FROM INPUT)
3. Requirements - What it must do (USE ONLY INFO FROM INPUT - if details missing, write "To be defined")
4. Acceptance Criteria - How we know it's done (USE ONLY INFO FROM INPUT - if details missing, write "To be defined")

**FORMATTING RULES:**
- Use PLAIN TEXT only (no markdown symbols like **, __, ##, `, [])
- Use "====" under section headings
- Keep it simple and actionable

**Save to Google Docs:**
Use create_feature_spec_document tool with:
- title: "Feature: [EXACT feature name from input]"
- content: [your spec using ONLY the input data]
- feature_name: "[EXACT feature name from input]"
- project_name: "[EXACT project name from input]"

Return the Google Docs URL.

CRITICAL: DO NOT HALLUCINATE. USE ONLY THE INPUT DATA."""

    # Call agent with user_id
    import asyncio
    result = asyncio.run(get_product_lead_agent().arun(description + f"\n\nInput: {step_input.input}", user_id=user_id))
    return StepOutput(content=result.content, success=True)


def create_architecture_executor(step_input: StepInput) -> StepOutput:
    """Simple wrapper to call lead_engineer with user_id from workflow."""
    from agno.workflow.types import StepOutput

    # Get user_id from workflow session
    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    description = """Create a SIMPLE architecture document.

**CRITICAL: READ THE PRD/FEATURE SPEC FROM THE PREVIOUS STEP. USE ONLY WHAT'S MENTIONED THERE. DO NOT ADD EXTRA FEATURES, DO NOT HALLUCINATE, DO NOT USE EXAMPLES FROM OTHER PROJECTS.**

Read the PRD/Feature Spec from the previous step, then create architecture.

**Create a SHORT architecture document with:**

1. **What We're Building** (2-3 sentences - BASED ONLY ON THE PRD)
2. **Tech Stack** (MATCH EXACTLY TO REQUIREMENTS - if PRD says static HTML, use that! If no tech specified, choose minimal stack for the requirements)
3. **Main Components** (bullet list - ONLY what's needed for the features in the PRD)
4. **Implementation Steps** (3-5 steps - ONLY for the features mentioned)
5. **Folder Structure** (MANDATORY - every file with exact path - ONLY files needed for the PRD features)
6. **File Cross-References** (MANDATORY - what each file imports/links)

**CRITICAL RULES:**
- RESPECT THE PRD SCOPE - don't add features not mentioned in the PRD
- Simple requirements = Simple architecture
- If PRD is 5 bullets → architecture should be 1 page
- DO NOT add features like "user authentication", "admin dashboard", etc. unless they're in the PRD

**FORMATTING RULES:**
- Use PLAIN TEXT only (no markdown symbols like **, __, ##, `, [])

**Save to Google Docs:**
Use create_document tool:
- title: "Architecture: [EXACT project name from PRD]"
- content: [your architecture using ONLY the PRD requirements]

Return the Google Docs URL.

CRITICAL: DO NOT HALLUCINATE FEATURES. MATCH THE PRD EXACTLY."""

    prev_content = step_input.previous_step_content or ""
    # Call agent with user_id
    import asyncio
    result = asyncio.run(get_lead_engineer_agent().arun(description + f"\n\nPrevious step output:\n{prev_content}", user_id=user_id))
    return StepOutput(content=result.content, success=True)


def create_summary_executor(step_input: StepInput) -> StepOutput:
    """Simple wrapper to call product_lead with user_id from workflow."""
    from agno.workflow.types import StepOutput

    # Get user_id from workflow session
    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    description = """Extract and present both Google Docs URLs from the previous steps.

Look at the previous step outputs and find:
1. The PRD or Feature Spec URL (from step 1)
2. The Architecture URL (from step 2)

Present them in this format:

## ✅ Documents Created!

**Project:** [project name]

### 📄 Document 1: [PRD or Feature Spec]
[URL from previous step]

### 🏗️ Document 2: Architecture
[URL from previous step]

---
**Next step:** Would you like me to implement this? Just say "yes" or "implement this".

CRITICAL: Find and include the ACTUAL URLs from the previous steps. Do not say "Not available"."""

    prev_content = step_input.get_all_previous_content()
    # Call agent with user_id
    import asyncio
    result = asyncio.run(get_product_lead_agent().arun(description + f"\n\nPrevious steps output:\n{prev_content}", user_id=user_id))
    return StepOutput(content=result.content, success=True)


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

product_requirements_workflow = Workflow(
    name="Product Requirements Workflow",
    stream=False,
    description="Create PRD/Feature Spec + Architecture documents",
    steps=[
        # Conditional: New Project → PRD
        Condition(
            name="new_project_path",
            description="Create PRD for new projects",
            evaluator=is_new_project,
            steps=[
                Step(
                    name="create_prd",
                    executor=create_prd_executor,
                    description="""Create PRD and save to Google Docs."""
                )
            ],
        ),
        # Conditional: Existing Project → Feature Spec
        Condition(
            name="existing_project_path",
            description="Create Feature Spec for existing projects",
            evaluator=is_existing_project,
            steps=[
                Step(
                    name="create_feature_spec",
                    executor=create_feature_spec_executor,
                    description="""Create Feature Spec and save to Google Docs."""
                )
            ],
        ),
        # Architecture (always runs)
        Step(
            name="create_architecture",
            executor=create_architecture_executor,
            description="""Create architecture document and save to Google Docs."""
        ),
        # Summary with both URLs
        Step(
            name="summary",
            executor=create_summary_executor,
            description="""Extract and present both document URLs."""
        ),
    ]
)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def run_product_requirements(
    request: str,
    project_type: Optional[str] = None,
    project_name: Optional[str] = None,
    feature_name: Optional[str] = None,
    github_repo_url: Optional[str] = None,
) -> dict:
    """Run the product requirements workflow."""
    _log("🚀", "WORKFLOW", "Starting Product Requirements Workflow")

    parts = [f"DESCRIPTION: {request}"]
    if project_type:
        parts.append(f"PROJECT_TYPE: {project_type}")
    if project_name:
        parts.append(f"PROJECT_NAME: {project_name}")
    if feature_name:
        parts.append(f"FEATURE_NAME: {feature_name}")
    if github_repo_url:
        parts.append(f"GITHUB_REPO_URL: {github_repo_url}")

    full_input = "\n".join(parts)
    result = product_requirements_workflow.run(input=full_input)

    _log("✅", "WORKFLOW", "Complete")
    return {"success": True, "content": result.content or ""}

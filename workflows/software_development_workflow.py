"""
Software Development Workflow - End to End

This is the main orchestration workflow that runs the complete development cycle:

Flow:
1. Product Requirements -> PRD or Feature Spec (conditional based on new/existing)
2. Architecture Design -> Technical Architecture (uses Lead Engineer agent directly)
3. Implementation -> Code written and saved (uses Software Engineer agent directly)
4. Summary -> Final report

Input: Request string with optional parameters
Output: Implementation summary with Google Docs link
"""

import os
import sys
import re
import asyncio
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Step, Workflow
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info, log_debug

from workflows.product_requirements_workflow import run_product_requirements


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _run_async(coro):
    """Run async coroutine from sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def parse_input_params(input_str: str) -> dict:
    """
    Parse input string for parameters.

    Looks for:
    - REQUEST: <text>
    - PROJECT_TYPE: new|existing
    - PROJECT_NAME: <name>
    - FEATURE_NAME: <name>
    """
    params = {
        "request": input_str,
        "project_type": None,
        "project_name": None,
        "feature_name": None,
    }

    type_match = re.search(r'PROJECT_TYPE:\s*(new|existing)', input_str, re.I)
    if type_match:
        params["project_type"] = type_match.group(1).lower()

    name_match = re.search(r'PROJECT_NAME:\s*([^\n]+)', input_str, re.I)
    if name_match:
        params["project_name"] = name_match.group(1).strip()

    feature_match = re.search(r'FEATURE_NAME:\s*([^\n]+)', input_str, re.I)
    if feature_match:
        params["feature_name"] = feature_match.group(1).strip()

    return params


# ============================================================================
# WORKFLOW STEP FUNCTIONS
# ============================================================================

def run_product_discovery(step_input: StepInput) -> StepOutput:
    """
    Step 1: Product Requirements

    Creates PRD (for new projects) or Feature Spec (for existing products).
    Uses the Product Requirements Workflow which handles:
    - Project classification (new vs existing)
    - Requirements gathering
    - Knowledge base storage
    - Google Doc creation
    """
    request = step_input.input if isinstance(step_input.input, str) else ""

    log_info("[STEP:product_requirements] Starting")
    log_debug(f"[STEP:product_requirements] INPUT:\n{request}")

    params = parse_input_params(request)

    log_info(f"[STEP:product_requirements] Parsed params: type={params['project_type']}, name={params['project_name']}")

    result = run_product_requirements(
        request=params["request"],
        project_type=params["project_type"],
        project_name=params["project_name"],
        feature_name=params["feature_name"],
    )
    output = result.get("content", "")

    log_info("[STEP:product_requirements] Complete")
    return StepOutput(content=output, success=True)


def run_architecture(step_input: StepInput) -> StepOutput:
    """
    Step 2: Architecture Design

    Lead Engineer creates technical architecture based on PRD/Feature Spec.
    Uses the lead_engineer_agent directly (inlined from deleted architecture_design_workflow).
    """
    prd = step_input.previous_step_content or ""
    original_input = step_input.input if isinstance(step_input.input, str) else ""

    log_info("[STEP:architecture_design] Starting")
    log_debug(f"[STEP:architecture_design] INPUT:\n{prd[:500]}")

    # Import agent directly
    from agents.lead_engineer import lead_engineer_agent

    prompt = f"""Based on the following product requirements, design the technical architecture.

<requirements>
{prd}
</requirements>

<original_request>
{original_input}
</original_request>

Create a comprehensive technical architecture document including:
1. System Overview
2. Component Architecture
3. Data Model
4. API Design
5. Technology Stack Recommendations
6. Implementation Plan with task breakdown
7. Security Considerations

Be thorough but only use information from the requirements above. Mark unknowns as open questions.
"""

    log_info("[AGENT:lead_engineer] Designing architecture")
    result = _run_async(lead_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:architecture_design] Complete")
    return StepOutput(content=output, success=True)


def run_implementation(step_input: StepInput) -> StepOutput:
    """
    Step 3: Implementation

    Software Engineer implements code based on the architecture.
    Uses the software_engineer_agent directly (inlined from deleted implementation_cycle_workflow).
    """
    original_request = step_input.input if isinstance(step_input.input, str) else ""
    architecture = step_input.previous_step_content or ""

    log_info("[STEP:implementation] Starting")
    log_debug(f"[STEP:implementation] INPUT (architecture):\n{architecture[:500]}")

    # Import agent directly
    from agents.software_engineer import software_engineer_agent

    prompt = f"""Based on the following architecture, implement the code.

<original_request>
{original_request}
</original_request>

<architecture>
{architecture}
</architecture>

Implement the code following the architecture above:
1. Write clean, production-ready code
2. Follow best practices and coding standards
3. Include error handling
4. Write key tests
5. Save all files using GitHub tools if available

Be thorough and implement all core components described in the architecture.
"""

    log_info("[AGENT:software_engineer] Implementing")
    result = _run_async(software_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:implementation] Complete")
    return StepOutput(content=output, success=True)


def format_final_summary(step_input: StepInput) -> StepOutput:
    """
    Final step: Create a comprehensive summary of the entire workflow.
    """
    implementation_output = step_input.previous_step_content or ""
    original_input = step_input.input if isinstance(step_input.input, str) else ""

    log_info("[STEP:summary] Generating final summary")

    # Determine project type
    is_prd = "prd_complete" in implementation_output.lower() or "prd:" in implementation_output.lower()
    doc_type = "PRD" if is_prd else "Feature Spec"

    # Try to extract Google Docs URL
    doc_url_match = re.search(r'https://docs\.google\.com/document/d/[^\s)]+', implementation_output)
    doc_url = doc_url_match.group(0) if doc_url_match else None

    summary = f"""
## Development Workflow Complete

### Summary
- **Document Type:** {doc_type}

### Workflow Completed
1. Product Requirements - {doc_type} created
2. Architecture Design - Technical specification created
3. Implementation - Code written and reviewed
"""

    if doc_url:
        summary += f"""
### Document Link
**Google Docs:** {doc_url}
"""

    summary += f"""
### Next Steps
1. Review the implementation
2. Run automated tests
3. Deploy to staging environment
4. Conduct user acceptance testing

---
{implementation_output}
"""

    log_info("[STEP:summary] Complete")
    return StepOutput(content=summary, success=True)


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

software_development_workflow = Workflow(
    name="Software Development",
    stream=False,
    description="""Complete end-to-end development workflow:
    1. Product Requirements (PRD/Feature Spec + Google Doc)
    2. Architecture Design (Lead Engineer)
    3. Implementation (Software Engineer)
    4. Final Summary""",
    steps=[
        Step(name="product_requirements", executor=run_product_discovery),
        Step(name="architecture_design", executor=run_architecture),
        Step(name="implementation", executor=run_implementation),
        Step(name="summary", executor=format_final_summary),
    ]
)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def run_software_development(
    request: str,
    project_type: Optional[str] = None,
    project_name: Optional[str] = None,
    feature_name: Optional[str] = None,
) -> dict:
    """
    Run the complete software development workflow.

    Args:
        request: User's product/feature request
        project_type: "new" for new project, "existing" for existing product
        project_name: Name of the project
        feature_name: Name of the feature (for existing products)

    Returns:
        Dict with success status and content
    """
    log_info("[WORKFLOW:software_development] Starting")

    # Build input with parameters
    input_parts = [request]
    if project_type:
        input_parts.append(f"PROJECT_TYPE: {project_type}")
    if project_name:
        input_parts.append(f"PROJECT_NAME: {project_name}")
    if feature_name:
        input_parts.append(f"FEATURE_NAME: {feature_name}")

    full_input = "\n".join(input_parts)
    log_debug(f"[WORKFLOW:software_development] INPUT:\n{full_input}")

    result = software_development_workflow.run(input=full_input)
    output = result.content or ""

    log_info("[WORKFLOW:software_development] Complete")

    return {"success": True, "content": output}

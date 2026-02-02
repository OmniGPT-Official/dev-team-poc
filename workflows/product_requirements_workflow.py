"""
Product Requirements Workflow

This workflow handles product requirements through the Product Lead.
It behaves differently based on whether it's a NEW project or an EXISTING product.

NEW PROJECT: Create full PRD → Store & create Google Doc
EXISTING PRODUCT: Create Feature Spec → Store & create Google Doc

The workflow is triggered by the Product Lead after asking questions.
Parameters are passed as a string that includes PROJECT_TYPE: new|existing
"""

import os
import sys
import asyncio
import json
import re
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.workflow import Step, Workflow
from agno.workflow.condition import Condition
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info, log_debug

# Knowledge base is handled automatically by Agno when attached to team/agent


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


def extract_param(text: str, param: str) -> Optional[str]:
    """Extract a parameter value from text."""
    pattern = rf'{param}:\s*([^\n]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


# ============================================================================
# AGENTS FOR PRD AND FEATURE SPEC CREATION
# ============================================================================

prd_creation_agent = Agent(
    name="PRD Creator",
    model=Claude(id="claude-sonnet-4-20250514"),
    markdown=True,
    instructions="""You create Product Requirements Documents (PRDs) for NEW projects.

**Your Task**: Create a comprehensive PRD based on the provided context.

**IMPORTANT - GOOGLE DOCS FORMATTING**:
- This will be inserted into Google Docs, so use PLAIN TEXT formatting only
- Use headings with proper spacing (not markdown # symbols)
- Use simple bullet points with "•" or "-"
- For tables, use plain text with clear spacing or bullet lists
- NO MARKDOWN syntax (no **, __, ##, `, [], etc.)
- Use line breaks and spacing for structure

**PRD Structure**:

PRD: [Product Name]

1. Executive Summary
Brief description of what we're building and why (2-3 sentences).

2. Problem Statement
The specific problem this product solves.

3. Target Users
Who will use this product and their key characteristics.

4. Goals & Success Metrics
Goal 1: [Metric] - [Target]
Goal 2: [Metric] - [Target]
Goal 3: [Metric] - [Target]

5. Feature Requirements

P0 - Must Have (MVP):
• Feature 1
  User Story: As a [user], I want [action] so that [benefit]
  Acceptance Criteria:
    - Criterion 1
    - Criterion 2

• Feature 2
  User Story: As a [user], I want [action] so that [benefit]
  Acceptance Criteria:
    - Criterion 1
    - Criterion 2

P1 - Should Have:
• Feature 1
  User Story: As a [user], I want [action] so that [benefit]
  Acceptance Criteria:
    - Criterion 1

6. Technical Considerations
• Technology stack preferences
• Integration requirements
• Constraints

7. Out of Scope (v1)
What this version will NOT include.

8. Open Questions
Any unknowns that need resolution.

---
CRITICAL: NO HALLUCINATION
• Only use information explicitly provided
• Mark unknowns as "Open Questions"
• Never invent features or requirements
• Use PLAIN TEXT formatting (no markdown)

End with: PRD_COMPLETE: true
""",
)

feature_spec_agent = Agent(
    name="Feature Spec Creator",
    model=Claude(id="claude-sonnet-4-20250514"),
    markdown=True,
    instructions="""You create Feature Specifications for EXISTING products.

**Your Task**: Create a focused Feature Spec based on the provided context.

**IMPORTANT - GOOGLE DOCS FORMATTING**:
- This will be inserted into Google Docs, so use PLAIN TEXT formatting only
- Use headings with proper spacing (not markdown # symbols)
- Use simple bullet points with "•" or "-"
- For tables, use plain text with clear spacing or bullet lists
- NO MARKDOWN syntax (no **, __, ##, `, [], etc.)
- Use line breaks and spacing for structure

**Feature Spec Structure**:

Feature Spec: [Feature Name]

1. Overview
What this feature does (2-3 sentences).

2. Background
Why this feature is needed and what triggered the request.

3. User Story
As a [user type], I want [capability], so that [benefit].

4. Functional Requirements
FR-1: [Requirement]
  Priority: P0
  Acceptance Criteria:
    - Criterion 1
    - Criterion 2

FR-2: [Requirement]
  Priority: P1
  Acceptance Criteria:
    - Criterion 1

5. Non-Functional Requirements
• Performance: ...
• Security: ...
• Scalability: ...

6. Affected Components
Which parts of the existing system this touches.

7. Dependencies
What this feature depends on.

8. Edge Cases
Scenarios to handle.

9. Out of Scope
What this feature will NOT do.

10. Open Questions
Any unknowns.

---
CRITICAL: NO HALLUCINATION
• Only use information explicitly provided
• Don't assume existing product architecture
• Mark unknowns as "Open Questions"
• Use PLAIN TEXT formatting (no markdown)

End with: FEATURE_SPEC_COMPLETE: true
""",
)


# ============================================================================
# WORKFLOW STEP FUNCTIONS
# ============================================================================

def create_prd(step_input: StepInput) -> StepOutput:
    """
    Create a PRD for a NEW project.
    """
    context = step_input.input if isinstance(step_input.input, str) else ""

    log_info("[STEP:create_prd] Creating PRD for new project")
    log_debug(f"[STEP:create_prd] INPUT:\n{context[:500]}")

    # Extract key info
    project_name = extract_param(context, "PROJECT_NAME") or "Unnamed Project"
    description = extract_param(context, "DESCRIPTION") or context

    prompt = f"""Create a PRD for this NEW project:

**Project Name**: {project_name}

**Context & Requirements**:
{description}

Create a comprehensive PRD now. Use only the information provided above.
"""

    log_info("[AGENT:prd_creator] Creating PRD")
    result = _run_async(prd_creation_agent.arun(prompt))
    output = result.content or ""

    # Add metadata
    output += f"\n\n<metadata>\nPROJECT_TYPE: new\nPROJECT_NAME: {project_name}\n</metadata>"

    log_info("[STEP:create_prd] Complete")
    return StepOutput(content=output, success=True)


def create_feature_spec(step_input: StepInput) -> StepOutput:
    """
    Create a Feature Spec for an EXISTING product.
    """
    context = step_input.input if isinstance(step_input.input, str) else ""

    log_info("[STEP:create_feature_spec] Creating Feature Spec for existing product")
    log_debug(f"[STEP:create_feature_spec] INPUT:\n{context[:500]}")

    # Extract key info
    project_name = extract_param(context, "PROJECT_NAME") or "Existing Product"
    feature_name = extract_param(context, "FEATURE_NAME") or "New Feature"
    description = extract_param(context, "DESCRIPTION") or context

    # Note: Existing project context is automatically provided by Agno's Knowledge system
    # when the team has knowledge base attached

    prompt = f"""Create a Feature Specification for this EXISTING product:

**Project Name**: {project_name}
**Feature Name**: {feature_name}

**Feature Request**:
{description}

Create a focused Feature Spec now. Use only the information provided above.
"""

    log_info("[AGENT:feature_spec_creator] Creating Feature Spec")
    result = _run_async(feature_spec_agent.arun(prompt))
    output = result.content or ""

    # Add metadata
    output += f"\n\n<metadata>\nPROJECT_TYPE: existing\nPROJECT_NAME: {project_name}\nFEATURE_NAME: {feature_name}\n</metadata>"

    log_info("[STEP:create_feature_spec] Complete")
    return StepOutput(content=output, success=True)


def store_and_create_doc(step_input: StepInput) -> StepOutput:
    """
    Create Google Doc (knowledge base storage is automatic via Agno).
    """
    content = step_input.previous_step_content or ""

    log_info("[STEP:store_and_create_doc] Creating document")

    # Extract metadata
    project_type = "new" if "project_type: new" in content.lower() else "existing"
    project_name = extract_param(content, "PROJECT_NAME") or "Unnamed"

    # Note: Content is automatically stored in Agno's Knowledge base
    # when the team has knowledge=get_knowledge_base() attached

    # Create Google Doc
    from tools.google_docs_tools import GoogleDocsTools
    docs_tool = GoogleDocsTools()

    if project_type == "new":
        doc_result_str = docs_tool.create_prd_document(
            title=f"PRD: {project_name}",
            content=content,
            project_name=project_name,
        )
    else:
        feature_name = extract_param(content, "FEATURE_NAME") or "New Feature"
        doc_result_str = docs_tool.create_feature_spec_document(
            title=f"Feature: {feature_name}",
            content=content,
            feature_name=feature_name,
            project_name=project_name,
        )

    # Parse the result to get the URL
    doc_url = None
    try:
        doc_result = json.loads(doc_result_str)
        if doc_result.get("success"):
            doc_url = doc_result.get("document_url", "")
    except (json.JSONDecodeError, TypeError):
        doc_url = None

    # Prepare output with document link prominently displayed
    doc_type = "PRD" if project_type == "new" else "Feature Spec"

    output = f"""{content}

---
## Document Created

- **Type:** {doc_type}
- **Project:** {project_name}
"""

    if doc_url:
        output += f"""- **Google Docs URL:** {doc_url}

**Your document is ready:** {doc_url}
"""
    else:
        output += """
**Note:** Google Doc creation failed. The document content is saved in the knowledge base.
To enable Google Docs, run: `python tests/google_docs/oauth_server.py` and authorize.
"""

    log_info("[STEP:store_and_create_doc] Complete")
    return StepOutput(content=output, success=True)


# ============================================================================
# CONDITION EVALUATORS
# ============================================================================

def is_new_project(step_input: StepInput) -> bool:
    """Check if this is a new project."""
    content = step_input.input if isinstance(step_input.input, str) else ""
    content_lower = content.lower()

    # Check explicit marker
    if "project_type: new" in content_lower or "project_type:new" in content_lower:
        log_info("[CONDITION] Detected: NEW project")
        return True

    # Check keywords
    new_keywords = ["new project", "from scratch", "build a new", "create a new", "start a new"]
    if any(kw in content_lower for kw in new_keywords):
        log_info("[CONDITION] Detected: NEW project (by keywords)")
        return True

    log_info("[CONDITION] Not a new project")
    return False


def is_existing_project(step_input: StepInput) -> bool:
    """Check if this is an existing project."""
    content = step_input.input if isinstance(step_input.input, str) else ""
    content_lower = content.lower()

    # Check explicit marker
    if "project_type: existing" in content_lower or "project_type:existing" in content_lower:
        log_info("[CONDITION] Detected: EXISTING project")
        return True

    # Check keywords
    existing_keywords = ["existing", "add feature", "add to", "enhance", "update", "modify"]
    if any(kw in content_lower for kw in existing_keywords):
        log_info("[CONDITION] Detected: EXISTING project (by keywords)")
        return True

    log_info("[CONDITION] Not an existing project")
    return False


# ============================================================================
# WORKFLOW DEFINITION WITH CONDITIONS
# ============================================================================

product_requirements_workflow = Workflow(
    name="Product Requirements Workflow",
    stream=False,
    description="""Conditional workflow for product requirements:
    - NEW project: Create PRD
    - EXISTING product: Create Feature Spec
    Then stores in knowledge base and creates Google Doc.""",
    steps=[
        # Conditional: New Project Path
        Condition(
            name="new_project_path",
            description="Create PRD for new projects",
            evaluator=is_new_project,
            steps=[
                Step(name="create_prd", executor=create_prd),
            ],
        ),
        # Conditional: Existing Project Path
        Condition(
            name="existing_project_path",
            description="Create Feature Spec for existing products",
            evaluator=is_existing_project,
            steps=[
                Step(name="create_feature_spec", executor=create_feature_spec),
            ],
        ),
        # Always run: Store and create document
        Step(name="store_and_create_doc", executor=store_and_create_doc),
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
) -> dict:
    """
    Run the product requirements workflow.

    Args:
        request: The user's description/requirements
        project_type: "new" or "existing"
        project_name: Name of the project
        feature_name: Name of the feature (for existing projects)

    Returns:
        Dict with success and content
    """
    log_info("[WORKFLOW:product_requirements] Starting")

    # Build input string with all parameters
    parts = [f"DESCRIPTION: {request}"]

    if project_type:
        parts.append(f"PROJECT_TYPE: {project_type}")
    if project_name:
        parts.append(f"PROJECT_NAME: {project_name}")
    if feature_name:
        parts.append(f"FEATURE_NAME: {feature_name}")

    full_input = "\n".join(parts)
    log_debug(f"[WORKFLOW:product_requirements] INPUT:\n{full_input}")

    result = product_requirements_workflow.run(input=full_input)
    output = result.content or ""

    log_info("[WORKFLOW:product_requirements] Complete")

    return {"success": True, "content": output}

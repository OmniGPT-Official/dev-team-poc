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
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)  # DO NOT close the loop


def extract_param(text: str, param: str) -> Optional[str]:
    """Extract a parameter value from text."""
    pattern = rf'{param}:\s*([^\n]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def clean_workflow_content(content: str) -> str:
    """
    Remove workflow debug messages and system noise from content.
    Only keeps the actual PRD/Feature Spec content.
    """
    if not content:
        return ""

    # Remove ONLY lines that start with workflow debug patterns (more precise)
    lines_to_remove_prefix = [
        "[debug",
        "[info",
        "[step:",
        "[condition]",
        "[agent:",
        "[workflow:",
        "info ",
        "debug ",
        "error ",
        "warning ",
    ]

    # Remove lines that are ONLY workflow status messages
    exact_patterns = [
        "condition",
        "not met",
        "skipped",
    ]

    cleaned_lines = []
    for line in content.split('\n'):
        line_stripped = line.strip()
        line_lower = line_stripped.lower()

        # Skip empty lines
        if not line_stripped:
            cleaned_lines.append(line)
            continue

        # Skip if line starts with debug prefix
        if any(line_lower.startswith(pattern) for pattern in lines_to_remove_prefix):
            continue

        # Skip if line is ONLY a workflow status message (all patterns in one line and short)
        if len(line_stripped) < 100 and all(pattern in line_lower for pattern in exact_patterns):
            continue

        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines).strip()


# ============================================================================
# AGENTS FOR PRD AND FEATURE SPEC CREATION
# ============================================================================

prd_creation_agent = Agent(
    name="PRD Creator",
    model=Claude(id="claude-sonnet-4-20250514"),
    markdown=True,
    instructions="""You are a Product Requirements Document (PRD) creator for NEW projects.

Your role is to transform business requirements into a comprehensive, structured PRD that engineers can implement.

## FORMATTING REQUIREMENTS (CRITICAL)

This PRD will be inserted into Google Docs, so:
• Use PLAIN TEXT formatting only (no markdown)
• Use "====" under section headings for emphasis
• Use simple bullet points with "•" or "-"
• Use blank lines for spacing between sections
• NO MARKDOWN syntax (no **, __, ##, `, [], etc.)
• Number lists as "1.", "2.", etc.

## PRD STRUCTURE (FOLLOW EXACTLY)

Create a complete PRD with these sections:

---

PRD: [Product Name]
====================================

1. EXECUTIVE SUMMARY
   Brief overview (2-3 sentences) of what we're building and why it matters.

2. PROBLEM STATEMENT
   The specific problem this product solves.
   • Who has this problem
   • Why existing solutions don't work
   • Impact of not solving this problem

3. TARGET USERS
   Who will use this product:
   • Primary user persona
   • User characteristics
   • User needs and pain points

4. PRODUCT VISION & SOLUTION
   What we're building:
   • High-level product description
   • How it solves the problem
   • What makes it different/better

5. GOALS & SUCCESS METRICS
   How we'll measure success:
   • Goal 1: [Specific metric] - [Target/benchmark]
   • Goal 2: [Specific metric] - [Target/benchmark]
   • Goal 3: [Specific metric] - [Target/benchmark]

6. FEATURE REQUIREMENTS

   P0 - MUST HAVE (MVP):
   Critical features for launch:

   • Feature 1: [Name]
     Description: [What it does]
     User Story: As a [user type], I want [action/capability] so that [benefit]
     Acceptance Criteria:
       - Criterion 1
       - Criterion 2
       - Criterion 3

   • Feature 2: [Name]
     Description: [What it does]
     User Story: As a [user type], I want [action/capability] so that [benefit]
     Acceptance Criteria:
       - Criterion 1
       - Criterion 2

   P1 - SHOULD HAVE:
   Important but not critical for MVP:

   • Feature 1: [Name]
     Description: [What it does]
     User Story: As a [user type], I want [action/capability] so that [benefit]

   P2 - NICE TO HAVE:
   Future enhancements:

   • Feature 1: [Name]
     Description: [What it does]

7. USER FLOW
   High-level user journey:
   1. User lands on [entry point]
   2. User [action]
   3. System [response]
   4. User achieves [outcome]

8. TECHNICAL CONSIDERATIONS
   • Preferred technology stack (if specified)
   • Performance requirements
   • Security requirements
   • Scalability considerations
   • Integration needs
   • Browser/device support

9. OUT OF SCOPE (V1)
   What this version will NOT include:
   • Feature/capability 1 - [reason]
   • Feature/capability 2 - [reason]

10. ASSUMPTIONS & CONSTRAINTS
    Assumptions:
    • Assumption 1
    • Assumption 2

    Constraints:
    • Constraint 1 (budget, timeline, technical, etc.)
    • Constraint 2

11. RISKS & MITIGATION
    • Risk 1: [Description] - Mitigation: [Strategy]
    • Risk 2: [Description] - Mitigation: [Strategy]

12. OPEN QUESTIONS
    Unknowns that need resolution:
    • Question 1: [What needs to be determined]
    • Question 2: [What needs to be determined]

13. TIMELINE & MILESTONES
    • Phase 1: [Milestone] - [Timeframe if known, or "TBD"]
    • Phase 2: [Milestone] - [Timeframe if known, or "TBD"]

---

## CRITICAL RULES

1. NO HALLUCINATION:
   • Only use information explicitly provided in the context
   • If information is missing, mark it in "Open Questions"
   • Never invent features, metrics, or requirements
   • Don't assume technical details unless specified

2. COMPLETENESS:
   • Fill out ALL sections above
   • If a section has no information, write "To be determined" or add to Open Questions
   • Infer reasonable user stories and acceptance criteria from provided context

3. CLARITY:
   • Be specific and actionable
   • Use clear, simple language
   • Avoid jargon unless necessary
   • Each requirement should be testable/measurable

4. USER-FOCUSED:
   • Frame everything around user value
   • Every feature should have a clear user benefit
   • Prioritize based on user needs

5. PLAIN TEXT ONLY:
   • Remember: this goes into Google Docs
   • Use spacing and simple formatting
   • NO markdown symbols

End your PRD with:

PRD_COMPLETE: true
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
    # Handle both string and dict inputs
    if isinstance(step_input.input, dict):
        context = str(step_input.input)
        project_name = step_input.input.get("PROJECT_NAME", "Unnamed Project")
        description = step_input.input.get("DESCRIPTION", context)
    elif isinstance(step_input.input, str):
        context = step_input.input
        project_name = extract_param(context, "PROJECT_NAME") or "Unnamed Project"
        description = extract_param(context, "DESCRIPTION") or context
    else:
        context = str(step_input.input)
        project_name = extract_param(context, "PROJECT_NAME") or "Unnamed Project"
        description = extract_param(context, "DESCRIPTION") or context

    print(f"\n[DEBUG:create_prd] STEP STARTED")
    print(f"[DEBUG:create_prd] Input type: {type(step_input.input)}")
    print(f"[DEBUG:create_prd] Project name: {project_name}")
    print(f"[DEBUG:create_prd] Description length: {len(description)}\n")

    log_info("[STEP:create_prd] Creating PRD for new project")
    log_debug(f"[STEP:create_prd] INPUT:\n{context[:500]}")

    prompt = f"""Create a PRD for this NEW project:

**Project Name**: {project_name}

**Context & Requirements**:
{description}

Create a comprehensive PRD now. Use only the information provided above.
"""

    print(f"[DEBUG:create_prd] Calling PRD creation agent...")
    log_info("[AGENT:prd_creator] Creating PRD")
    result = _run_async(prd_creation_agent.arun(prompt))
    output = result.content or ""
    print(f"[DEBUG:create_prd] Agent returned {len(output)} characters\n")

    # Add metadata
    output += f"\n\n<metadata>\nPROJECT_TYPE: new\nPROJECT_NAME: {project_name}\n</metadata>"

    print(f"[DEBUG:create_prd] STEP COMPLETE - output length: {len(output)}\n")
    log_info("[STEP:create_prd] Complete")
    return StepOutput(content=output, success=True)


def create_feature_spec(step_input: StepInput) -> StepOutput:
    """
    Create a Feature Spec for an EXISTING product.
    """
    # Handle both string and dict inputs
    if isinstance(step_input.input, dict):
        context = str(step_input.input)
        project_name = step_input.input.get("PROJECT_NAME", "Existing Product")
        feature_name = step_input.input.get("FEATURE_NAME", "New Feature")
        description = step_input.input.get("DESCRIPTION", context)
    elif isinstance(step_input.input, str):
        context = step_input.input
        project_name = extract_param(context, "PROJECT_NAME") or "Existing Product"
        feature_name = extract_param(context, "FEATURE_NAME") or "New Feature"
        description = extract_param(context, "DESCRIPTION") or context
    else:
        context = str(step_input.input)
        project_name = extract_param(context, "PROJECT_NAME") or "Existing Product"
        feature_name = extract_param(context, "FEATURE_NAME") or "New Feature"
        description = extract_param(context, "DESCRIPTION") or context

    log_info("[STEP:create_feature_spec] Creating Feature Spec for existing product")
    log_debug(f"[STEP:create_feature_spec] INPUT:\n{context[:500]}")

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
    # DEBUG: Show all available attributes on step_input
    print(f"\n[DEBUG:store_and_create_doc] StepInput attributes: {dir(step_input)}\n")

    # Get PRD/Feature Spec content from workflow run results
    # Since create_prd/create_feature_spec are inside Condition steps,
    # we need to access the workflow run to get their actual output
    content = ""

    # Try to get content from workflow run step results
    if hasattr(step_input, 'workflow_run') and step_input.workflow_run:
        print(f"[DEBUG:store_and_create_doc] workflow_run exists, type: {type(step_input.workflow_run)}")
        print(f"[DEBUG:store_and_create_doc] workflow_run attributes: {dir(step_input.workflow_run)}\n")

        if hasattr(step_input.workflow_run, 'step_results'):
            print(f"[DEBUG:store_and_create_doc] step_results exists, length: {len(step_input.workflow_run.step_results)}\n")
            for i, step_result in enumerate(step_input.workflow_run.step_results):
                print(f"[DEBUG:store_and_create_doc] step_result[{i}]: {type(step_result)}")
                print(f"[DEBUG:store_and_create_doc] step_result[{i}] attributes: {dir(step_result)}")
                if hasattr(step_result, 'step_name'):
                    print(f"[DEBUG:store_and_create_doc] step_result[{i}] step_name: {step_result.step_name}")
                if hasattr(step_result, 'content'):
                    print(f"[DEBUG:store_and_create_doc] step_result[{i}] content length: {len(step_result.content or '')}")

                # Look for Condition steps that contain create_prd or create_feature_spec
                if hasattr(step_result, 'steps') and step_result.steps:
                    print(f"[DEBUG:store_and_create_doc] step_result[{i}] has inner steps: {len(step_result.steps)}")
                    for j, inner_step in enumerate(step_result.steps):
                        print(f"[DEBUG:store_and_create_doc]   inner_step[{j}] name: {getattr(inner_step, 'step_name', 'N/A')}")
                        if hasattr(inner_step, 'step_name') and inner_step.step_name in ['create_prd', 'create_feature_spec']:
                            content = inner_step.content or ""
                            print(f"[DEBUG:store_and_create_doc]   ✓ Found {inner_step.step_name} output: {len(content)} chars\n")
                            break
                print()
                if content:
                    break
    else:
        print(f"[DEBUG:store_and_create_doc] workflow_run NOT available\n")

    # Fallback to previous_step_content if workflow_run not available
    if not content:
        content = step_input.previous_step_content or ""
        print(f"[DEBUG:store_and_create_doc] Using previous_step_content: {len(content)} chars\n")

    # Handle both string and dict inputs
    if isinstance(step_input.input, dict):
        original_input = str(step_input.input)
        input_dict = step_input.input
    elif isinstance(step_input.input, str):
        original_input = step_input.input
        input_dict = None
    else:
        original_input = str(step_input.input)
        input_dict = None

    log_info("[STEP:store_and_create_doc] Creating document")

    # DEBUG: show what we received
    print(f"\n[DEBUG:store_and_create_doc] Input type: {type(step_input.input)}")
    print(f"[DEBUG:store_and_create_doc] PRD/FS content length: {len(content)}")
    print(f"[DEBUG:store_and_create_doc] original_input length: {len(original_input)}")
    print(f"[DEBUG:store_and_create_doc] original_input preview: {original_input[:300]}\n")

    # Determine project type — check dict first, then string formats
    project_type = None
    if input_dict and "PROJECT_TYPE" in input_dict:
        project_type = input_dict["PROJECT_TYPE"].lower()
        print(f"[DEBUG:store_and_create_doc] Found PROJECT_TYPE in dict: {project_type}\n")
    else:
        # Check BOTH previous step content AND original input
        combined = (content + "\n" + original_input).lower()
        if any(marker in combined for marker in ["project_type: new", "project_type:new", "'project_type': 'new'", '"project_type": "new"']):
            project_type = "new"
        elif any(marker in combined for marker in ["project_type: existing", "project_type:existing", "'project_type': 'existing'", '"project_type": "existing"']):
            project_type = "existing"
        else:
            # Fallback: keyword check on original input
            new_keywords = ["new project", "from scratch", "build a new", "create a new", "start a new"]
            if any(kw in original_input.lower() for kw in new_keywords):
                project_type = "new"
            else:
                project_type = "existing"

    print(f"[DEBUG:store_and_create_doc] Determined project_type: {project_type}\n")

    # If no PRD/FS was created by conditions (both failed), create content now
    if not content.strip():
        print("[DEBUG:store_and_create_doc] No previous step content — creating document from original input\n")
        content = original_input

    # Extract project name from dict or string
    if input_dict and "PROJECT_NAME" in input_dict:
        project_name = input_dict["PROJECT_NAME"]
    else:
        project_name = extract_param(content, "PROJECT_NAME") or extract_param(original_input, "PROJECT_NAME") or "Unnamed"

    # CLEAN CONTENT: Remove workflow debug messages before creating Google Doc
    cleaned_content = clean_workflow_content(content)
    print(f"[DEBUG:store_and_create_doc] Content cleaned - before: {len(content)} chars, after: {len(cleaned_content)} chars\n")

    # FALLBACK: If cleaning removed everything (PRD/FS didn't generate), use original input
    if not cleaned_content.strip() and original_input.strip():
        print("[DEBUG:store_and_create_doc] Cleaned content empty - using original input as document content\n")
        cleaned_content = original_input

    # Validate we have content to create document
    if not cleaned_content.strip():
        print("[ERROR:store_and_create_doc] No content available to create document!\n")
        return StepOutput(
            content="ERROR: No content generated for document. Both PRD/Feature Spec creation and original input are empty.",
            success=False
        )

    # Note: Content is automatically stored in Agno's Knowledge base
    # when the team has knowledge=get_knowledge_base() attached

    # Create Google Doc
    from tools.google_docs_tools import GoogleDocsTools
    docs_tool = GoogleDocsTools()

    if project_type == "new":
        doc_result_str = docs_tool.create_prd_document(
            title=f"PRD: {project_name}",
            content=cleaned_content,
            project_name=project_name,
        )
    else:
        # Extract feature name from dict or string
        if input_dict and "FEATURE_NAME" in input_dict:
            feature_name = input_dict["FEATURE_NAME"]
        else:
            feature_name = extract_param(content, "FEATURE_NAME") or extract_param(original_input, "FEATURE_NAME") or "New Feature"
        doc_result_str = docs_tool.create_feature_spec_document(
            title=f"Feature: {feature_name}",
            content=cleaned_content,
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

    output = f"""{cleaned_content}

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
    # Handle both string and dict inputs
    if isinstance(step_input.input, dict):
        content = str(step_input.input)
        # Also check dict keys directly
        project_type = step_input.input.get("PROJECT_TYPE", "").lower()
        if project_type == "new":
            log_info("[CONDITION] ✓ Detected: NEW project (dict key)")
            return True
    elif isinstance(step_input.input, str):
        content = step_input.input
    else:
        content = str(step_input.input)

    content_lower = content.lower()

    # DEBUG LOGGING
    print(f"\n[DEBUG:is_new_project] Input type: {type(step_input.input)}")
    print(f"[DEBUG:is_new_project] Input content (first 500 chars): {content[:500]}")
    print(f"[DEBUG:is_new_project] Checking for 'new' project markers...\n")

    # Check explicit marker (multiple formats)
    if any(marker in content_lower for marker in [
        "project_type: new",
        "project_type:new",
        "project type: new",
        "project type:new",
        "type: new",
        "type:new",
        "'project_type': 'new'",
        '"project_type": "new"'
    ]):
        log_info("[CONDITION] ✓ Detected: NEW project (explicit marker)")
        return True

    # Check keywords
    new_keywords = ["new project", "from scratch", "build a new", "create a new", "start a new", "starting a new"]
    for kw in new_keywords:
        if kw in content_lower:
            log_info(f"[CONDITION] ✓ Detected: NEW project (keyword: '{kw}')")
            return True

    log_info("[CONDITION] ✗ Not a new project")
    return False


def is_existing_project(step_input: StepInput) -> bool:
    """Check if this is an existing project."""
    # Handle both string and dict inputs
    if isinstance(step_input.input, dict):
        content = str(step_input.input)
        # Also check dict keys directly
        project_type = step_input.input.get("PROJECT_TYPE", "").lower()
        if project_type == "existing":
            log_info("[CONDITION] ✓ Detected: EXISTING project (dict key)")
            return True
    elif isinstance(step_input.input, str):
        content = step_input.input
    else:
        content = str(step_input.input)

    content_lower = content.lower()

    # DEBUG LOGGING
    print(f"\n[DEBUG:is_existing_project] Input type: {type(step_input.input)}")
    print(f"[DEBUG:is_existing_project] Input content (first 500 chars): {content[:500]}")
    print(f"[DEBUG:is_existing_project] Checking for 'existing' project markers...\n")

    # Check explicit marker (multiple formats)
    if any(marker in content_lower for marker in [
        "project_type: existing",
        "project_type:existing",
        "project type: existing",
        "project type:existing",
        "type: existing",
        "type:existing",
        "'project_type': 'existing'",
        '"project_type": "existing"'
    ]):
        log_info("[CONDITION] ✓ Detected: EXISTING project (explicit marker)")
        return True

    # Check keywords
    existing_keywords = ["existing product", "existing project", "add feature", "add a feature", "add to", "enhance", "update", "modify", "improve existing"]
    for kw in existing_keywords:
        if kw in content_lower:
            log_info(f"[CONDITION] ✓ Detected: EXISTING project (keyword: '{kw}')")
            return True

    log_info("[CONDITION] ✗ Not an existing project")
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

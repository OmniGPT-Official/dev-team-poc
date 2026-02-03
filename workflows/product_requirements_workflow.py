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
# IMPORT AGENTS (Product Lead and Lead Engineer have Google Docs tools)
# ============================================================================

# Import agents - avoid circular imports by lazy loading
def get_product_lead_agent():
    from agents.product_lead import product_lead_agent
    return product_lead_agent

def get_lead_engineer_agent():
    from agents.lead_engineer import lead_engineer_agent
    return lead_engineer_agent




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

    prompt = f"""Create a comprehensive PRD for this NEW project:

**Project Name**: {project_name}

**Context & Requirements**:
{description}

**IMPORTANT**:
1. Create the COMPLETE PRD with all 13 sections
2. Use PLAIN TEXT formatting (no markdown)
3. Save it to Google Docs using create_prd_document tool
4. Return BOTH the full PRD content AND the Google Docs URL

Format your response as:
[FULL PRD CONTENT HERE]

---
Google Docs URL: [URL]
"""

    print(f"[DEBUG:create_prd] Calling Product Lead agent for PRD creation...")
    log_info("[AGENT:product_lead] Creating PRD")
    product_lead = get_product_lead_agent()
    result = _run_async(product_lead.arun(prompt))
    output = result.content or ""
    print(f"[DEBUG:create_prd] Product Lead agent returned {len(output)} characters\n")

    # Extract PRD content and URL
    prd_content = output
    doc_url = None
    if "Google Docs URL:" in output or "docs.google.com" in output:
        # Extract the URL
        import re
        url_match = re.search(r'https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+/edit', output)
        if url_match:
            doc_url = url_match.group(0)
            print(f"[DEBUG:create_prd] Extracted Google Docs URL: {doc_url}\n")

    # Add metadata (keep full content for next step)
    output_with_metadata = f"""{prd_content}

<metadata>
PROJECT_TYPE: new
PROJECT_NAME: {project_name}
DOC_URL: {doc_url or 'Not created'}
</metadata>"""

    print(f"[DEBUG:create_prd] STEP COMPLETE - output length: {len(output_with_metadata)}\n")
    log_info("[STEP:create_prd] Complete")
    return StepOutput(content=output_with_metadata, success=True)


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

    prompt = f"""Create a comprehensive Feature Specification for this EXISTING product:

**Project Name**: {project_name}
**Feature Name**: {feature_name}

**Feature Request**:
{description}

**IMPORTANT**:
1. Create the COMPLETE Feature Spec with all 10 sections
2. Use PLAIN TEXT formatting (no markdown)
3. Save it to Google Docs using create_feature_spec_document tool
4. Return BOTH the full Feature Spec content AND the Google Docs URL

Format your response as:
[FULL FEATURE SPEC CONTENT HERE]

---
Google Docs URL: [URL]
"""

    log_info("[AGENT:product_lead] Creating Feature Spec")
    product_lead = get_product_lead_agent()
    result = _run_async(product_lead.arun(prompt))
    output = result.content or ""

    # Extract Feature Spec content and URL
    fs_content = output
    doc_url = None
    if "Google Docs URL:" in output or "docs.google.com" in output:
        # Extract the URL
        import re
        url_match = re.search(r'https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+/edit', output)
        if url_match:
            doc_url = url_match.group(0)
            print(f"[DEBUG:create_feature_spec] Extracted Google Docs URL: {doc_url}\n")

    # Add metadata (keep full content for next step)
    output_with_metadata = f"""{fs_content}

<metadata>
PROJECT_TYPE: existing
PROJECT_NAME: {project_name}
FEATURE_NAME: {feature_name}
DOC_URL: {doc_url or 'Not created'}
</metadata>"""

    log_info("[STEP:create_feature_spec] Complete")
    return StepOutput(content=output_with_metadata, success=True)


def create_architecture_document(step_input: StepInput) -> StepOutput:
    """
    Create an Architecture Document using Lead Engineer agent.
    This step runs after PRD/Feature Spec creation.

    For NEW projects: Creates architecture based on PRD
    For EXISTING projects: Searches knowledge base for GitHub link, reads repo, creates architecture based on FS + existing code
    """
    # Get PRD/Feature Spec content - try multiple approaches
    prd_content = ""
    prd_doc_url = None

    # First, try to extract PRD URL from the original workflow input
    # The URL should have been included in the workflow execution context
    print(f"[DEBUG:create_architecture] Attempting to extract PRD URL from workflow context\n")

    # Try to get content from workflow run step results (Condition contains inner steps)
    if hasattr(step_input, 'workflow_run') and step_input.workflow_run:
        if hasattr(step_input.workflow_run, 'step_results'):
            print(f"[DEBUG:create_architecture] Searching {len(step_input.workflow_run.step_results)} step results for PRD/FS content\n")
            for i, step_result in enumerate(step_input.workflow_run.step_results):
                # Look for Condition steps that contain create_prd or create_feature_spec
                if hasattr(step_result, 'steps') and step_result.steps:
                    for inner_step in step_result.steps:
                        if hasattr(inner_step, 'step_name') and inner_step.step_name in ['create_prd', 'create_feature_spec']:
                            prd_content = inner_step.content or ""
                            print(f"[DEBUG:create_architecture] ✓ Found {inner_step.step_name} output: {len(prd_content)} chars\n")
                            # Extract URL from this content
                            if "docs.google.com" in prd_content:
                                import re
                                url_match = re.search(r'https://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)/edit', prd_content)
                                if url_match:
                                    prd_doc_url = url_match.group(0)
                                    print(f"[DEBUG:create_architecture] Extracted URL from content: {prd_doc_url}\n")
                            break
                if prd_content:
                    break

    # Fallback: try previous_step_content
    if not prd_content:
        prd_content = step_input.previous_step_content or ""
        print(f"[DEBUG:create_architecture] Using previous_step_content fallback: {len(prd_content)} chars\n")
        # Try to extract URL from fallback content
        if prd_content and "docs.google.com" in prd_content:
            import re
            url_match = re.search(r'https://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)/edit', prd_content)
            if url_match:
                prd_doc_url = url_match.group(0)
                print(f"[DEBUG:create_architecture] Extracted URL from fallback: {prd_doc_url}\n")

    # If we have a URL but not much content, READ the document from Google Docs
    if prd_doc_url and len(prd_content) < 1000:
        print(f"[DEBUG:create_architecture] PRD content too short ({len(prd_content)} chars), reading from Google Docs URL...\n")
        try:
            from tools.google_docs_tools import GoogleDocsTools
            docs_tool = GoogleDocsTools()
            # Extract document ID from URL
            import re
            doc_id_match = re.search(r'/document/d/([a-zA-Z0-9_-]+)/', prd_doc_url)
            if doc_id_match:
                doc_id = doc_id_match.group(1)
                print(f"[DEBUG:create_architecture] Reading Google Doc ID: {doc_id}\n")
                prd_content = docs_tool.read_document(doc_id)
                print(f"[DEBUG:create_architecture] ✓ Read {len(prd_content)} chars from Google Docs\n")
        except Exception as e:
            print(f"[DEBUG:create_architecture] Failed to read from Google Docs: {e}\n")
            # Continue with whatever content we have

    # Handle both string and dict inputs
    if isinstance(step_input.input, dict):
        original_input = str(step_input.input)
        project_name = step_input.input.get("PROJECT_NAME", "Unnamed Project")
        project_type = step_input.input.get("PROJECT_TYPE", "new")
    elif isinstance(step_input.input, str):
        original_input = step_input.input
        project_name = extract_param(original_input, "PROJECT_NAME") or "Unnamed Project"
        project_type_raw = extract_param(original_input, "PROJECT_TYPE")
        project_type = project_type_raw.lower() if project_type_raw else "new"
    else:
        original_input = str(step_input.input)
        project_name = "Unnamed Project"
        project_type = "new"

    print(f"\n[DEBUG:create_architecture] STEP STARTED")
    print(f"[DEBUG:create_architecture] Project: {project_name}")
    print(f"[DEBUG:create_architecture] Type: {project_type}")
    print(f"[DEBUG:create_architecture] PRD content length: {len(prd_content)}\n")

    log_info("[STEP:create_architecture] Creating Architecture Document")

    # Extract clean PRD/FS content (without metadata)
    clean_prd = prd_content.split("<metadata>")[0].strip() if "<metadata>" in prd_content else prd_content.strip()

    # If we still don't have a URL, try to extract from metadata
    if not prd_doc_url and "<metadata>" in prd_content:
        metadata_section = prd_content.split("<metadata>")[1].split("</metadata>")[0] if "</metadata>" in prd_content else ""
        if "DOC_URL:" in metadata_section:
            prd_doc_url = metadata_section.split("DOC_URL:")[1].strip().split("\n")[0].strip()
            if prd_doc_url and prd_doc_url != "Not created":
                print(f"[DEBUG:create_architecture] Found PRD/FS Doc URL in metadata: {prd_doc_url}\n")

    # Build prompt based on project type
    if project_type == "existing":
        # For EXISTING projects: Ask Lead Engineer to search knowledge base for GitHub link and read repo
        prompt = f"""You are creating an Architecture Document for an EXISTING product feature.

**Project Name**: {project_name}
**Type**: Existing Product Feature
**Feature Spec Google Docs URL**: {prd_doc_url or 'Not available'}

**Feature Spec Content**:
{clean_prd[:4000]}

**YOUR TASK**: Design how this new feature integrates with the existing codebase.

**STEPS**:

1. **Search Knowledge Base**: Search for the GitHub repository link for "{project_name}"
   - Find GitHub URL, repository information, or codebase location

2. **Analyze Existing Codebase**: Use your GitHub tools to:
   - Read the repository structure
   - Understand the current technology stack
   - Review existing code patterns and architecture
   - Identify affected components

3. **Design Feature Integration**: Based on Feature Spec AND existing codebase:
   - How this feature fits into current architecture
   - What components need modification
   - What new components are needed
   - Database changes if needed (prefer Supabase if already used)
   - API changes/additions required

**CREATE ARCHITECTURE DOCUMENT** with these sections:

1. **Current Architecture Summary**
   - Existing tech stack and patterns
   - Current project structure

2. **Feature Integration Plan**
   - Where this feature fits
   - Components to modify vs create new
   - How it follows existing patterns

3. **Technical Changes Required**
   - Code modifications needed
   - New files/components to create
   - Database schema changes (if any)
   - API endpoints (if any)

4. **Implementation Approach**
   - Step-by-step integration plan
   - Backward compatibility considerations
   - Testing strategy

5. **Deployment Considerations**
   - Must remain deployable to Vercel
   - Environment variables changes (if any)

**CRITICAL RULES**:
- Follow EXISTING architecture patterns - don't introduce new patterns without strong justification
- Use the SAME tech stack as the existing project
- Keep changes minimal and focused on the feature requirements
- Base ALL decisions on Feature Spec requirements

**FORMATTING**:
- Use PLAIN TEXT formatting (no markdown) as this will be saved to Google Docs

**SAVE TO GOOGLE DOCS**:
After creating the architecture document, save it using:
create_document(
    title="Architecture: {project_name} - [Feature Name]",
    content="[Your architecture document]"
)

Return the Google Docs URL in your response.
"""
    else:
        # For NEW projects: Create architecture based on PRD only
        prompt = f"""You are creating an Architecture Document for a NEW project.

**Project Name**: {project_name}
**Type**: New Project (starting from scratch)
**PRD Google Docs URL**: {prd_doc_url or 'Not available'}

**PRD (Product Requirements Document) Content**:
{clean_prd[:4000]}

**YOUR TASK**: Based ONLY on the PRD requirements, design the best architecture for this project.

**DEPLOYMENT REQUIREMENTS**:
- Must be deployable to Vercel
- If a database is needed, use Supabase
- Choose the simplest technology stack that meets the requirements (Next.js, React, static HTML/CSS, etc.)

**CREATE ARCHITECTURE DOCUMENT** with these sections:

1. **System Overview**
   - What this system does and how it works
   - Architecture pattern chosen and why (based on PRD requirements)

2. **Technology Stack Recommendation**
   - Choose technologies based on PRD requirements (simple HTML/CSS, React, Next.js, etc.)
   - Only include database (Supabase) if PRD requires data persistence
   - Justify each choice based on requirements

3. **Component Structure**
   - Main components/modules needed
   - How they work together
   - File/folder structure

4. **Data Architecture** (only if needed based on PRD)
   - Database schema if Supabase is needed
   - Data models and relationships
   - API structure if needed

5. **User Flow & Functionality**
   - How users interact with the system
   - Key features and how they're implemented

6. **Deployment Strategy**
   - Vercel deployment configuration
   - Environment variables needed
   - Build and deployment process

7. **Open Technical Questions**
   - Any clarifications needed for implementation

**CRITICAL RULES**:
- Base ALL decisions on the PRD requirements - don't add unnecessary complexity
- If the PRD describes a simple website → use simple HTML/CSS or static Next.js
- If the PRD needs interactivity → use React or Next.js
- If the PRD needs data storage → add Supabase
- DON'T suggest technologies not mentioned unless required by PRD
- Keep it as simple as possible while meeting requirements

**FORMATTING**:
- Use PLAIN TEXT formatting (no markdown) as this will be saved to Google Docs

**SAVE TO GOOGLE DOCS**:
After creating the architecture document, save it using:
create_document(
    title="Architecture: {project_name}",
    content="[Your architecture document]"
)

Return the Google Docs URL in your response.
"""

    print(f"[DEBUG:create_architecture] Calling Lead Engineer agent...")
    log_info("[AGENT:lead_engineer] Creating Architecture Document")
    lead_engineer = get_lead_engineer_agent()
    result = _run_async(lead_engineer.arun(prompt))
    output = result.content or ""
    print(f"[DEBUG:create_architecture] Lead Engineer returned {len(output)} characters\n")

    print(f"[DEBUG:create_architecture] STEP COMPLETE\n")
    log_info("[STEP:create_architecture] Complete")
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
    - NEW project: Product Lead creates PRD and saves to Google Docs
    - EXISTING product: Product Lead creates Feature Spec and saves to Google Docs
    - THEN: Lead Engineer creates Architecture Document and saves to Google Docs
    The workflow creates 2 documents total: PRD/FS + Architecture.""",
    steps=[
        # Conditional: New Project Path
        Condition(
            name="new_project_path",
            description="Create PRD for new projects and save to Google Docs",
            evaluator=is_new_project,
            steps=[
                Step(name="create_prd", executor=create_prd),
            ],
        ),
        # Conditional: Existing Project Path
        Condition(
            name="existing_project_path",
            description="Create Feature Spec for existing products and save to Google Docs",
            evaluator=is_existing_project,
            steps=[
                Step(name="create_feature_spec", executor=create_feature_spec),
            ],
        ),
        # Architecture Document (runs after PRD/FS creation)
        Step(
            name="create_architecture",
            description="Create Architecture Document using Lead Engineer",
            executor=create_architecture_document,
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

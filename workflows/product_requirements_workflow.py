"""
Product Requirements Workflow (Router + Steps Architecture)

Flow (Router-based):
- NEW PROJECT PATH → Create Project → PRD → Architecture → Supervisor → Summary
- EXISTING PROJECT PATH → Get Context → Validate GitHub → Feature Spec → Technical Doc → Supervisor → Summary

Input: PROJECT_TYPE, PROJECT_NAME, DESCRIPTION, PROJECT_ID (for existing), FEATURE_NAME (for existing)
Output: 2 Google Docs URLs (PRD/FS + Architecture/Tech Doc)
"""

import os
import sys
from typing import Union, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Step, Workflow, Steps
from agno.workflow.router import Router
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info
from services.project_context import set_current_project_id, get_current_project_id


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


def get_supervisor_agent():
    from agents.supervisor import supervisor_agent
    return supervisor_agent


# NOTE: Router selector function will be defined AFTER the Steps objects
# so it can return the actual Steps objects instead of strings


# ============================================================================
# EXECUTOR FUNCTIONS - NEW PROJECT PATH
# ============================================================================

def create_project_entry_executor(step_input: StepInput) -> StepOutput:
    """Create project entry in database at workflow start."""
    from tools.project_tools import create_project
    import re

    _log("🗂️", "PROJECT-CREATE", "Creating project entry at workflow start")

    # Extract project details from input
    project_name_match = re.search(r'PROJECT_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    project_desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?:PROJECT_TYPE:|$)', str(step_input.input), re.IGNORECASE | re.DOTALL)
    project_type_match = re.search(r'PROJECT_TYPE:\s*(.+)', str(step_input.input), re.IGNORECASE)

    project_name = project_name_match.group(1).strip() if project_name_match else "Unknown Project"
    project_description = project_desc_match.group(1).strip() if project_desc_match else "No description provided"
    project_type = project_type_match.group(1).strip() if project_type_match else "new"

    _log("🗂️", "PROJECT-CREATE", f"Project: {project_name}, Type: {project_type}")

    # Create project (this sets project_id in context)
    result = create_project(
        project_name=project_name,
        project_description=project_description,
        project_type=project_type
    )

    if result["success"]:
        _log("✅", "PROJECT-CREATE", f"Project created: {result['project_id']}")
        return StepOutput(
            content=f"Project created successfully: {project_name} (ID: {result['project_id']})",
            success=True
        )
    else:
        _log("❌", "PROJECT-CREATE", f"Failed: {result['message']}")
        return StepOutput(
            content=f"Failed to create project: {result['message']}",
            success=False
        )


def create_prd_executor(step_input: StepInput) -> StepOutput:
    """Simple wrapper to call product_lead with user_id from workflow."""
    from tools.project_tools import get_project
    import re
    import asyncio

    # Get user_id from workflow session
    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    # Get project_id from context
    project_id = get_current_project_id()

    # Extract project details
    project_name_match = re.search(r'PROJECT_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    project_desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?:PROJECT_TYPE:|$)', str(step_input.input), re.IGNORECASE | re.DOTALL)

    project_name = project_name_match.group(1).strip() if project_name_match else "Unknown Project"
    project_description = project_desc_match.group(1).strip() if project_desc_match else "No description provided"

    # Format project_id for filename (first 8 chars)
    project_id_short = project_id[:8] if project_id else "00000000"

    _log("📝", "PRD-CREATE", f"Starting PRD creation for user_id={user_id}, project_id={project_id}")

    description = f"""You MUST create a PRD and save it to Google Docs.

**CRITICAL: USE ONLY THE INFORMATION PROVIDED IN THE INPUT BELOW. DO NOT ADD EXAMPLES, DO NOT HALLUCINATE.**

**STEP 1: Write the PRD content starting with the DOCUMENT HEADER:**

DOCUMENT TYPE: Product Requirements Document (PRD)
PROJECT TYPE: New Project
PROJECT ID: {project_id}
PROJECT NAME: {project_name}
PROJECT DESCRIPTION: {project_description}

====================================================================================================

Then continue with all the PRD sections as per your instructions.

**STEP 2: YOU MUST call the create_prd_document tool**

CRITICAL - Document title format: PRD_{project_name.replace(' ', '')}_{project_id_short}

Call it with:
- title: "PRD_{project_name.replace(' ', '')}_{project_id_short}"
- content: (the PRD content with header)
- project_name: "{project_name}"

**STEP 3: Return the Google Docs URL AND the full PRD content**

Return in this format:
PRD Document URL: [URL]

PRD CONTENT:
[Full PRD text content]

CRITICAL: Include BOTH the URL and the FULL content in your response."""

    # Call agent with user_id
    _log("🤖", "PRD-CREATE", "Calling Product Lead agent...")
    result = asyncio.run(get_product_lead_agent().arun(description + f"\n\nInput: {step_input.input}", user_id=user_id))
    _log("✅", "PRD-CREATE", f"Product Lead completed. Result length: {len(result.content) if result and result.content else 0}")

    return StepOutput(content=result.content, success=True)


def create_architecture_executor(step_input: StepInput) -> StepOutput:
    """Simple wrapper to call lead_engineer with user_id from workflow."""
    import re
    import asyncio

    # Get user_id from workflow session
    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    # Get project_id from context
    project_id = get_current_project_id()

    # Extract PRD content from previous step
    prev_content = step_input.previous_step_content or ""

    # Extract project name from PRD content (try both formats: "PROJECT NAME:" and "PROJECT_NAME:")
    project_name_match = re.search(r'PROJECT[_ ]NAME:\s*(.+)', prev_content, re.IGNORECASE)
    if not project_name_match:
        # Fallback: extract from original input
        input_match = re.search(r'PROJECT_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
        project_name = input_match.group(1).strip() if input_match else "Unknown Project"
    else:
        project_name = project_name_match.group(1).strip()

    # Format project_id for filename (first 8 chars)
    project_id_short = project_id[:8] if project_id else "00000000"

    _log("🏗️", "ARCH-CREATE", f"Starting architecture creation for user_id={user_id}, project_id={project_id}")
    _log("🏗️", "ARCH-CREATE", f"Previous PRD content length: {len(prev_content)}")
    _log("🏗️", "ARCH-CREATE", f"Extracted project_name: {project_name}")

    description = f"""Create a SIMPLE architecture document based on the PRD content below.

**CRITICAL: READ THE PRD CONTENT BELOW. USE ONLY WHAT'S MENTIONED THERE.**

**STEP 1: Write the Architecture starting with the DOCUMENT HEADER:**

DOCUMENT TYPE: Technical Architecture Document
PROJECT TYPE: New Project
PROJECT ID: {project_id}
PROJECT NAME: {project_name}
TECH STACK: [Choose appropriate stack based on PRD requirements - e.g., "HTML5/CSS3/JavaScript" or "Next.js, TypeScript, Tailwind CSS"]

====================================================================================================

Then continue with all architecture sections as per your instructions.

**CRITICAL RULES:**
- RESPECT THE PRD SCOPE - don't add features not mentioned
- Simple requirements = Simple architecture
- Match tech stack to requirements (don't over-engineer)

**Save to Google Docs:**
CRITICAL - Document title format: Architecture_{project_name.replace(' ', '')}_{project_id_short}

Use create_document tool:
- title: "Architecture_{project_name.replace(' ', '')}_{project_id_short}"
- content: [your architecture with header]

**Return the Google Docs URL AND the full Architecture content**

Return in this format:
Architecture Document URL: [URL]

ARCHITECTURE CONTENT:
[Full architecture text content]

CRITICAL: Include BOTH the URL and the FULL content in your response."""

    # Call agent with user_id
    _log("🤖", "ARCH-CREATE", "Calling Lead Engineer agent...")
    result = asyncio.run(get_lead_engineer_agent().arun(description + f"\n\nPRD CONTENT:\n{prev_content}", user_id=user_id))
    _log("✅", "ARCH-CREATE", f"Lead Engineer completed. Result length: {len(result.content) if result and result.content else 0}")

    return StepOutput(content=result.content, success=True)


def supervisor_validation_executor(step_input: StepInput) -> StepOutput:
    """Supervisor validates documents and creates project in database."""
    import re
    import asyncio

    # Get user_id from workflow session
    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    _log("🔍", "SUPERVISOR", f"Starting supervisor validation for user_id={user_id}")

    # Access specific previous steps by name
    prd_content = step_input.get_step_content("create_prd") or ""
    arch_content = step_input.get_step_content("create_architecture") or ""

    _log("🔍", "SUPERVISOR", f"PRD content length: {len(prd_content)}")
    _log("🔍", "SUPERVISOR", f"Architecture content length: {len(arch_content)}")

    # Extract URLs from specific step outputs
    prd_url_match = re.search(r'PRD Document URL:\s*(https://docs\.google\.com/document/d/[^\s]+)', prd_content, re.IGNORECASE)
    arch_url_match = re.search(r'Architecture Document URL:\s*(https://docs\.google\.com/document/d/[^\s]+)', arch_content, re.IGNORECASE)

    prd_url = prd_url_match.group(1).strip() if prd_url_match else None
    arch_url = arch_url_match.group(1).strip() if arch_url_match else None

    _log("🔗", "SUPERVISOR", f"Extracted PRD URL: {prd_url}")
    _log("🔗", "SUPERVISOR", f"Extracted Architecture URL: {arch_url}")

    # Extract project name from input
    project_name_match = re.search(r'PROJECT_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    project_name = project_name_match.group(1).strip() if project_name_match else "Unknown Project"

    if not prd_url or not arch_url:
        _log("❌", "SUPERVISOR", "ERROR: Could not extract document URLs from previous steps")
        return StepOutput(
            content=f"ERROR: Could not extract document URLs. PRD URL: {prd_url}, Architecture URL: {arch_url}",
            success=False
        )

    description = f"""You are the Supervisor. Validate documents by READING THEM and update existing project.

**IMPORTANT:** A project was already created at workflow start. The project_id is available in context.

**DOCUMENT URLs (ALREADY EXTRACTED):**
- PRD Document URL: {prd_url}
- Architecture Document URL: {arch_url}

**Your tasks:**

1. **READ and Validate PRD**:
   - Call validate_prd_document("{prd_url}", "{project_name}")

2. **READ and Validate Architecture**:
   - Call validate_architecture_document("{arch_url}", "{project_name}")

3. **Update Project**: Get the project_id from context, then call:
   update_project(project_id, prd_doc_url="{prd_url}", architecture_doc_url="{arch_url}", status="in_development")

4. **Create Knowledge Base**: Call create_project_knowledge_base()

5. **Report**: Summarize validation results

**CRITICAL:**
- USE THE URLs PROVIDED ABOVE - DO NOT extract or hallucinate URLs
- READ the documents to validate content
- The project_id is already in context (from workflow start)
- Do NOT call create_project - project already exists
- Use status='in_development' when updating project"""

    _log("🤖", "SUPERVISOR", "Calling Supervisor agent...")
    result = asyncio.run(get_supervisor_agent().arun(description, user_id=user_id))
    _log("✅", "SUPERVISOR", f"Supervisor completed. Result length: {len(result.content) if result and result.content else 0}")

    return StepOutput(content=result.content, success=True)


def create_summary_executor(step_input: StepInput) -> StepOutput:
    """Build summary directly from previous step outputs (no agent call needed)."""
    import re

    project_id = get_current_project_id()

    _log("📊", "SUMMARY", f"Creating summary - project_id={project_id}")

    # Collect all previous step content
    prev_content = step_input.get_all_previous_content()

    # Extract all Google Docs URLs from previous steps
    doc_urls = re.findall(r'https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+(?:/edit)?', prev_content)
    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for url in doc_urls:
        normalized = url.rstrip('/edit').rstrip('/')
        if normalized not in seen:
            seen.add(normalized)
            unique_urls.append(url)

    # Extract project name from previous content
    project_name_match = re.search(r'PROJECT[_ ]NAME:\s*(.+)', prev_content, re.IGNORECASE)
    project_name = project_name_match.group(1).strip() if project_name_match else "Project"

    # Extract feature name (for existing projects)
    feature_name_match = re.search(r'FEATURE[_ ]NAME:\s*(.+)', prev_content, re.IGNORECASE)
    feature_name = feature_name_match.group(1).strip() if feature_name_match else None

    # Detect project type from content
    is_existing = "existing" in prev_content.lower()[:500] or feature_name is not None

    # Build summary from previous step outputs
    if is_existing:
        doc1_label = "Feature Specification"
        doc2_label = "Technical Document"
    else:
        doc1_label = "Product Requirements Document (PRD)"
        doc2_label = "Architecture Document"

    doc1_url = unique_urls[0] if len(unique_urls) > 0 else "Not found in previous steps"
    doc2_url = unique_urls[1] if len(unique_urls) > 1 else "Not found in previous steps"

    summary_parts = [
        "Documents Created Successfully!",
        f"Project: {project_name}",
    ]
    if feature_name:
        summary_parts.append(f"Feature: {feature_name}")

    summary_parts.extend([
        "",
        f"Document 1: {doc1_label}",
        f"URL: {doc1_url}",
        "",
        f"Document 2: {doc2_label}",
        f"URL: {doc2_url}",
        "",
        "Next step: Would you like me to implement this? Just say 'yes' or 'implement this'.",
    ])

    summary = "\n".join(summary_parts)

    _log("📊", "SUMMARY", f"Doc1: {doc1_url}")
    _log("📊", "SUMMARY", f"Doc2: {doc2_url}")

    # Append metadata for next workflow
    if project_id:
        summary += f"\n\n---\nMetadata for next workflow:\nPROJECT_ID: {project_id}"
        if doc2_url.startswith("https://"):
            summary += f"\nARCHITECTURE_URL: {doc2_url}"

    return StepOutput(content=summary, success=True)


# ============================================================================
# EXECUTOR FUNCTIONS - EXISTING PROJECT PATH
# ============================================================================

def get_project_context_executor(step_input: StepInput) -> StepOutput:
    """Step 1 (Existing): Get project from DB."""
    import re
    from tools.project_tools import get_project

    # Extract project_id from input
    project_id_match = re.search(r'PROJECT_ID:\s*(.+)', str(step_input.input), re.IGNORECASE)
    if not project_id_match:
        return StepOutput(
            content="ERROR: PROJECT_ID not found in input. For existing projects, please provide PROJECT_ID.",
            success=False
        )

    project_id = project_id_match.group(1).strip()
    set_current_project_id(project_id)

    # Get project from DB
    project = get_project(project_id)
    if not project:
        return StepOutput(
            content=f"ERROR: Project {project_id} not found in database",
            success=False
        )

    _log("📂", "GET-PROJECT", f"Found project: {project['project_name']}")

    # Build context from project DB record
    context_parts = []
    if project.get('prd_doc_url'):
        context_parts.append(f"PRD URL: {project['prd_doc_url']}")
    if project.get('architecture_doc_url'):
        context_parts.append(f"Architecture URL: {project['architecture_doc_url']}")

    # Build context output
    output = f"""
PROJECT CONTEXT RETRIEVED:
Project ID: {project_id}
Project Name: {project['project_name']}
Description: {project.get('project_description', 'N/A')}
Status: {project.get('status', 'unknown')}
GitHub Repo: {project.get('github_repo_url', 'Not set')}
{chr(10).join(context_parts)}
"""

    return StepOutput(content=output, success=True)


def validate_github_repo_executor(step_input: StepInput) -> StepOutput:
    """Step 2 (Existing): Validate GitHub repo exists and is accessible."""
    import re
    import asyncio
    from tools.project_tools import get_project

    project_id = get_current_project_id()
    project = get_project(project_id)

    github_repo_url = project.get('github_repo_url')
    if not github_repo_url:
        return StepOutput(
            content="⚠️ No GitHub repo URL found for this project. Skipping validation.",
            success=True  # Don't fail, just warn
        )

    # Extract owner/repo from URL
    match = re.search(r'github\.com/([^/]+)/([^/]+)', github_repo_url)
    if not match:
        return StepOutput(
            content=f"⚠️ Invalid GitHub URL format: {github_repo_url}. Skipping validation.",
            success=True  # Don't fail, just warn
        )

    owner, repo = match.groups()
    repo = repo.replace('.git', '')  # Remove .git suffix if present

    _log("🔍", "GITHUB-VALIDATE", f"Validating repo: {owner}/{repo}")

    # Get user_id for API call
    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    # Call Lead Engineer agent to validate repo using GitHub tools
    description = f"""
You have access to GitHub tools. Please validate that the repository exists and is accessible.

Repository: {owner}/{repo}
GitHub URL: {github_repo_url}

Use get_repository("{owner}", "{repo}") to check if it exists.

If it exists, return:
✅ GitHub Repo Valid: {owner}/{repo}
Repo URL: {github_repo_url}

If it doesn't exist or is inaccessible, return:
⚠️ GitHub Repo Not Found: {owner}/{repo}
Note: Repository may need to be created or permissions may need to be updated.
"""

    result = asyncio.run(get_lead_engineer_agent().arun(description, user_id=user_id))

    _log("✅", "GITHUB-VALIDATE", f"Validation complete")
    return StepOutput(content=result.content, success=True)  # Always succeed, validation is informational


def create_feature_spec_executor(step_input: StepInput) -> StepOutput:
    """Step 3 (Existing): Product Lead creates Feature Specification."""
    import re
    import asyncio

    # Get user_id from workflow session
    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    # Get project_id from context
    project_id = get_current_project_id()

    # Extract project details
    project_name_match = re.search(r'PROJECT_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    feature_name_match = re.search(r'FEATURE_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    feature_desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?:PROJECT_TYPE:|$)', str(step_input.input), re.IGNORECASE | re.DOTALL)

    project_name = project_name_match.group(1).strip() if project_name_match else "Unknown Project"
    feature_name = feature_name_match.group(1).strip() if feature_name_match else "Unknown Feature"
    feature_description = feature_desc_match.group(1).strip() if feature_desc_match else "No description provided"

    # Get project context from previous step
    prev_context = step_input.previous_step_content or ""

    # Format project_id for filename (first 8 chars)
    project_id_short = project_id[:8] if project_id else "00000000"

    _log("📝", "FEATURE-SPEC-CREATE", f"Starting Feature Spec creation for user_id={user_id}, project_id={project_id}")

    description = f"""Create a Feature Specification for this existing product.

**CRITICAL: USE THE CONTEXT AND INFORMATION PROVIDED BELOW.**

**PROJECT CONTEXT:**
{prev_context}

**STEP 1: Write the Feature Spec starting with the DOCUMENT HEADER:**

DOCUMENT TYPE: Feature Specification
PROJECT TYPE: Existing Project
PROJECT ID: {project_id}
PROJECT NAME: {project_name}
FEATURE NAME: {feature_name}
FEATURE DESCRIPTION: {feature_description}

====================================================================================================

Then continue with all Feature Spec sections as per your instructions.

**Save to Google Docs:**
CRITICAL - Document title format: FeatureSpec_{feature_name.replace(' ', '')}_{project_id_short}

Use create_feature_spec_document tool:
- title: "FeatureSpec_{feature_name.replace(' ', '')}_{project_id_short}"
- content: [your spec with header]
- feature_name: "{feature_name}"
- project_name: "{project_name}"

**Return the Google Docs URL AND the full content**

Return in this format:
Feature Spec URL: [URL]

FEATURE SPEC CONTENT:
[Full content]"""

    # Call agent with user_id
    _log("🤖", "FEATURE-SPEC-CREATE", "Calling Product Lead agent...")
    result = asyncio.run(get_product_lead_agent().arun(description, user_id=user_id))
    _log("✅", "FEATURE-SPEC-CREATE", f"Product Lead completed. Result length: {len(result.content) if result and result.content else 0}")

    return StepOutput(content=result.content, success=True)


def create_technical_doc_executor(step_input: StepInput) -> StepOutput:
    """Step 4 (Existing): Lead Engineer creates Feature Technical Document."""
    import re
    import asyncio

    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    project_id = get_current_project_id()

    # Get feature spec content from previous step
    feature_spec_content = step_input.previous_step_content or ""

    # Extract feature name and project name
    feature_name_match = re.search(r'FEATURE[_ ]NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    project_name_match = re.search(r'PROJECT[_ ]NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)

    feature_name = feature_name_match.group(1).strip() if feature_name_match else "Unknown Feature"
    project_name = project_name_match.group(1).strip() if project_name_match else "Unknown Project"

    project_id_short = project_id[:8] if project_id else "00000000"

    _log("🏗️", "TECH-DOC-CREATE", f"Creating technical doc for feature: {feature_name}")

    description = f"""
Create a Feature Technical Document based on the Feature Specification below.

**DOCUMENT HEADER:**

DOCUMENT TYPE: Feature Technical Document
PROJECT TYPE: Existing Project
PROJECT ID: {project_id}
PROJECT NAME: {project_name}
FEATURE NAME: {feature_name}

====================================================================================================

Then continue with technical architecture for this feature.

**CRITICAL:** Read the Feature Spec below and design the technical implementation.

**Save to Google Docs:**
Document title format: TechDoc_{feature_name.replace(' ', '')}_{project_id_short}

Use create_document tool:
- title: "TechDoc_{feature_name.replace(' ', '')}_{project_id_short}"
- content: [your technical document with header]

**Return format:**
Technical Document URL: [URL]

TECHNICAL DOC CONTENT:
[Full content]

FEATURE SPEC CONTENT:
{feature_spec_content}
"""

    _log("🤖", "TECH-DOC-CREATE", "Calling Lead Engineer agent...")
    result = asyncio.run(get_lead_engineer_agent().arun(description, user_id=user_id))
    _log("✅", "TECH-DOC-CREATE", f"Lead Engineer completed. Result length: {len(result.content) if result and result.content else 0}")

    return StepOutput(content=result.content, success=True)


def supervisor_validation_existing_executor(step_input: StepInput) -> StepOutput:
    """Step 5 (Existing): Supervisor validates Feature Spec + Technical Doc and stores in DB."""
    import re
    import asyncio

    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    project_id = get_current_project_id()

    # Get feature spec and tech doc content from previous steps
    feature_spec_content = step_input.get_step_content("create_feature_spec") or ""
    tech_doc_content = step_input.get_step_content("create_technical_doc") or ""

    # Extract URLs
    fs_url_match = re.search(r'Feature Spec URL:\s*(https://docs\.google\.com/document/d/[^\s]+)', feature_spec_content, re.IGNORECASE)
    tech_url_match = re.search(r'Technical Document URL:\s*(https://docs\.google\.com/document/d/[^\s]+)', tech_doc_content, re.IGNORECASE)

    fs_url = fs_url_match.group(1).strip() if fs_url_match else None
    tech_url = tech_url_match.group(1).strip() if tech_url_match else None

    if not fs_url or not tech_url:
        return StepOutput(
            content=f"ERROR: Could not extract URLs. FS: {fs_url}, Tech: {tech_url}",
            success=False
        )

    # Extract feature name and project name from input
    feature_name_match = re.search(r'FEATURE_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    project_name_match = re.search(r'PROJECT_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)

    feature_name = feature_name_match.group(1).strip() if feature_name_match else "Unknown Feature"
    project_name = project_name_match.group(1).strip() if project_name_match else "Unknown Project"

    description = f"""
You are the Supervisor. Validate Feature Spec and Technical Doc, then store them in the database.

**DOCUMENT URLs:**
- Feature Spec URL: {fs_url}
- Technical Doc URL: {tech_url}

**Your tasks:**

1. Call validate_feature_spec_document("{fs_url}", "{project_name}", "{feature_name}")
2. Call validate_technical_doc_document("{tech_url}", "{project_name}", "{feature_name}")
3. Call add_feature_spec(project_id="{project_id}", doc_url="{fs_url}", title="Feature Spec: {feature_name}")
4. Call add_technical_doc(project_id="{project_id}", doc_url="{tech_url}", title="Technical Doc: {feature_name}")
5. Report validation results

**CRITICAL:**
- USE THE URLs PROVIDED ABOVE
- READ the documents to validate
- Store them in the project's feature_specs and technical_docs arrays
- The project_id is: {project_id}
"""

    _log("🤖", "SUPERVISOR", "Calling Supervisor agent...")
    result = asyncio.run(get_supervisor_agent().arun(description, user_id=user_id))
    _log("✅", "SUPERVISOR", f"Supervisor completed")

    return StepOutput(content=result.content, success=True)


# ============================================================================
# GROUPED STEPS (NEW PROJECT PATH)
# ============================================================================

new_project_steps = Steps(
    name="new_project_path",
    description="Complete workflow for new projects: PRD + Architecture",
    steps=[
        Step(
            name="create_project_entry",
            executor=create_project_entry_executor,
            description="Create project entry in database"
        ),
        Step(
            name="create_prd",
            executor=create_prd_executor,
            description="Create PRD document"
        ),
        Step(
            name="create_architecture",
            executor=create_architecture_executor,
            description="Create architecture document"
        ),
        Step(
            name="supervisor_validation",
            executor=supervisor_validation_executor,
            description="Validate PRD and Architecture, create knowledge base"
        ),
        Step(
            name="summary",
            executor=create_summary_executor,
            description="Present document URLs"
        ),
    ]
)


# ============================================================================
# GROUPED STEPS (EXISTING PROJECT PATH)
# ============================================================================

existing_project_steps = Steps(
    name="existing_project_path",
    description="Complete workflow for existing projects: Feature Spec + Technical Doc",
    steps=[
        Step(
            name="get_project_context",
            executor=get_project_context_executor,
            description="Get project from DB and search knowledge base"
        ),
        Step(
            name="validate_github_repo",
            executor=validate_github_repo_executor,
            description="Validate GitHub repository exists (informational)"
        ),
        Step(
            name="create_feature_spec",
            executor=create_feature_spec_executor,
            description="Create Feature Specification document"
        ),
        Step(
            name="create_technical_doc",
            executor=create_technical_doc_executor,
            description="Create Feature Technical Document"
        ),
        Step(
            name="supervisor_validation_existing",
            executor=supervisor_validation_existing_executor,
            description="Validate and store Feature Spec + Technical Doc"
        ),
        Step(
            name="summary",
            executor=create_summary_executor,
            description="Present document URLs"
        ),
    ]
)


# ============================================================================
# ROUTER SELECTOR FUNCTION
# ============================================================================

def route_by_project_type(step_input: StepInput) -> List[Step]:
    """
    Route to new project or existing project path.

    Returns a list of Step objects (Router expects List[Step], not Steps object).

    Checks for:
    - PROJECT_TYPE: new|existing
    - PROJECT_ID: <uuid> (existing projects have this)
    - Keywords: "new project", "existing project", "add feature"
    """
    content = str(step_input.input).lower()

    # Check for explicit PROJECT_TYPE
    if "project_type: existing" in content or "project_type:existing" in content:
        _log("🔀", "ROUTER", "Route: EXISTING PROJECT PATH")
        return existing_project_steps.steps  # Return the list of steps, not the Steps wrapper

    if "project_type: new" in content or "project_type:new" in content:
        _log("🔀", "ROUTER", "Route: NEW PROJECT PATH")
        return new_project_steps.steps  # Return the list of steps, not the Steps wrapper

    # Check for PROJECT_ID (indicates existing project)
    if "project_id:" in content:
        _log("🔀", "ROUTER", "Route: EXISTING PROJECT PATH (project_id found)")
        return existing_project_steps.steps

    # Check for keywords
    if any(kw in content for kw in ["add feature", "existing product", "enhance", "update", "modify"]):
        _log("🔀", "ROUTER", "Route: EXISTING PROJECT PATH (keywords)")
        return existing_project_steps.steps

    # Default to new project
    _log("🔀", "ROUTER", "Route: NEW PROJECT PATH (default)")
    return new_project_steps.steps  # Return the list of steps, not the Steps wrapper


# ============================================================================
# WORKFLOW DEFINITION (ROUTER-BASED)
# ============================================================================

product_requirements_workflow = Workflow(
    name="Product Requirements Workflow",
    stream=False,
    description="Create PRD/Feature Spec + Architecture/Technical documents using Router + Steps",
    steps=[
        Router(
            name="project_type_router",
            selector=route_by_project_type,
            choices=[new_project_steps, existing_project_steps]
        )
    ]
)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def run_product_requirements(
    request: str,
    project_type: str = None,
    project_name: str = None,
    feature_name: str = None,
    project_id: str = None,
    github_repo_url: str = None,
) -> dict:
    """Run the product requirements workflow."""
    _log("🚀", "WORKFLOW", "Starting Product Requirements Workflow (Router + Steps)")

    parts = [f"DESCRIPTION: {request}"]
    if project_type:
        parts.append(f"PROJECT_TYPE: {project_type}")
    if project_name:
        parts.append(f"PROJECT_NAME: {project_name}")
    if feature_name:
        parts.append(f"FEATURE_NAME: {feature_name}")
    if project_id:
        parts.append(f"PROJECT_ID: {project_id}")
    if github_repo_url:
        parts.append(f"GITHUB_REPO_URL: {github_repo_url}")

    full_input = "\n".join(parts)
    result = product_requirements_workflow.run(input=full_input)

    _log("✅", "WORKFLOW", "Complete")
    return {"success": True, "content": result.content or ""}

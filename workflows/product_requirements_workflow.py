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


def get_supervisor_agent():
    from agents.supervisor import supervisor_agent
    return supervisor_agent


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

def create_project_entry_executor(step_input: StepInput) -> StepOutput:
    """Create project entry in database at workflow start."""
    from agno.workflow.types import StepOutput
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
    from agno.workflow.types import StepOutput
    from services.project_context import get_current_project_id
    import re

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
    _log("📝", "PRD-CREATE", f"Input:\n{step_input.input}")

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
    import asyncio
    _log("🤖", "PRD-CREATE", "Calling Product Lead agent...")
    result = asyncio.run(get_product_lead_agent().arun(description + f"\n\nInput: {step_input.input}", user_id=user_id))
    _log("✅", "PRD-CREATE", f"Product Lead completed. Result length: {len(result.content) if result and result.content else 0}")

    # Log first paragraph of PRD content
    if result.content:
        lines = result.content.split('\n')
        first_paragraph = '\n'.join(lines[:10])  # First 10 lines
        _log("📄", "PRD-CONTENT", f"PRD Preview:\n{first_paragraph}")

    return StepOutput(content=result.content, success=True)


def create_feature_spec_executor(step_input: StepInput) -> StepOutput:
    """Simple wrapper to call product_lead with user_id from workflow."""
    from agno.workflow.types import StepOutput
    from services.project_context import get_current_project_id
    import re

    # Get user_id from workflow session
    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    # Get project_id from context
    project_id = get_current_project_id()

    # Extract project details
    project_name_match = re.search(r'PROJECT_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    feature_name_match = re.search(r'FEATURE_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)

    project_name = project_name_match.group(1).strip() if project_name_match else "Unknown Project"
    feature_name = feature_name_match.group(1).strip() if feature_name_match else "Unknown Feature"

    # Format project_id for filename (first 8 chars)
    project_id_short = project_id[:8] if project_id else "00000000"

    _log("📝", "FEATURE-SPEC-CREATE", f"Starting Feature Spec creation for user_id={user_id}, project_id={project_id}")

    description = f"""Create a Feature Specification for this existing product.

**CRITICAL: USE ONLY THE INFORMATION PROVIDED IN THE INPUT BELOW.**

**STEP 1: Write the Feature Spec starting with the DOCUMENT HEADER:**

DOCUMENT TYPE: Feature Specification
PROJECT TYPE: Existing Project
PROJECT ID: {project_id}
PROJECT NAME: {project_name}
FEATURE NAME: {feature_name}

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
    import asyncio
    _log("🤖", "FEATURE-SPEC-CREATE", "Calling Product Lead agent...")
    result = asyncio.run(get_product_lead_agent().arun(description + f"\n\nInput: {step_input.input}", user_id=user_id))
    _log("✅", "FEATURE-SPEC-CREATE", f"Product Lead completed. Result length: {len(result.content) if result and result.content else 0}")

    # Log first paragraph
    if result.content:
        lines = result.content.split('\n')
        first_paragraph = '\n'.join(lines[:10])
        _log("📄", "FEATURE-SPEC-CONTENT", f"Feature Spec Preview:\n{first_paragraph}")

    return StepOutput(content=result.content, success=True)


def create_architecture_executor(step_input: StepInput) -> StepOutput:
    """Simple wrapper to call lead_engineer with user_id from workflow."""
    from agno.workflow.types import StepOutput
    from services.project_context import get_current_project_id
    import re

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
    import asyncio
    _log("🤖", "ARCH-CREATE", "Calling Lead Engineer agent...")
    _log("🤖", "ARCH-CREATE", f"Passing PRD content to Lead Engineer:\n{prev_content[:500]}...")
    result = asyncio.run(get_lead_engineer_agent().arun(description + f"\n\nPRD CONTENT:\n{prev_content}", user_id=user_id))
    _log("✅", "ARCH-CREATE", f"Lead Engineer completed. Result length: {len(result.content) if result and result.content else 0}")

    # Log first paragraph of Architecture content
    if result.content:
        lines = result.content.split('\n')
        first_paragraph = '\n'.join(lines[:10])  # First 10 lines
        _log("🏗️", "ARCH-CONTENT", f"Architecture Preview:\n{first_paragraph}")

    return StepOutput(content=result.content, success=True)


def supervisor_validation_executor(step_input: StepInput) -> StepOutput:
    """Supervisor validates documents and creates project in database."""
    from agno.workflow.types import StepOutput
    import re
    import asyncio

    # Get user_id from workflow session
    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    # Get all previous content (PRD + Architecture)
    all_content = step_input.get_all_previous_content() or ""

    _log("🔍", "SUPERVISOR", f"Starting supervisor validation for user_id={user_id}")
    _log("🔍", "SUPERVISOR", f"Previous content length: {len(all_content)}")

    # Extract URLs from previous content to prevent hallucination
    prd_url_match = re.search(r'PRD Document URL:\s*(https://docs\.google\.com/document/d/[^\s]+)', all_content, re.IGNORECASE)
    arch_url_match = re.search(r'Architecture Document URL:\s*(https://docs\.google\.com/document/d/[^\s]+)', all_content, re.IGNORECASE)

    prd_url = prd_url_match.group(1).strip() if prd_url_match else None
    arch_url = arch_url_match.group(1).strip() if arch_url_match else None

    _log("🔗", "SUPERVISOR", f"Extracted PRD URL: {prd_url}")
    _log("🔗", "SUPERVISOR", f"Extracted Architecture URL: {arch_url}")

    # Extract project name and description from input
    project_name_match = re.search(r'PROJECT_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    project_desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?:PROJECT_TYPE:|$)', str(step_input.input), re.IGNORECASE | re.DOTALL)
    project_type_match = re.search(r'PROJECT_TYPE:\s*(.+)', str(step_input.input), re.IGNORECASE)

    project_name = project_name_match.group(1).strip() if project_name_match else "Unknown Project"
    project_description = project_desc_match.group(1).strip() if project_desc_match else "No description provided"
    project_type = project_type_match.group(1).strip() if project_type_match else "new"

    _log("📋", "SUPERVISOR", f"Project: {project_name}")
    _log("📋", "SUPERVISOR", f"Type: {project_type}")

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
   - This will READ the document and check:
     * Does it have the proper header (DOCUMENT TYPE, PROJECT ID, etc.)?
     * Does it contain valid PRD sections?
     * Is the content complete and not placeholder text?
   - The project_id from context is used automatically

2. **READ and Validate Architecture**:
   - Call validate_architecture_document("{arch_url}", "{project_name}")
   - This will READ the document and check:
     * Does it have the proper header with TECH STACK?
     * Does it contain architecture sections (file structure, components)?
     * Is the tech stack appropriate for the requirements?
   - The project_id from context is used automatically

3. **Update Project**: Get the project_id from context, then call:
   update_project(project_id, prd_doc_url="{prd_url}", architecture_doc_url="{arch_url}", status="in_development")

4. **Create Knowledge Base**: Call create_project_knowledge_base()
   - This will automatically use the project_id from context

5. **Report**: Summarize validation results including:
   - Are both documents valid and readable?
   - Do they have proper headers?
   - What tech stack was chosen?

**CRITICAL:**
- USE THE URLs PROVIDED ABOVE - DO NOT extract or hallucinate URLs
- READ the documents to validate content (don't just check if URLs exist)
- Check for proper document headers
- Verify architecture contains tech stack
- The project_id is already in context (from workflow start)
- Do NOT call create_project - project already exists
- Use status='in_development' when updating project"""

    _log("🤖", "SUPERVISOR", "Calling Supervisor agent...")
    result = asyncio.run(get_supervisor_agent().arun(description, user_id=user_id))
    _log("✅", "SUPERVISOR", f"Supervisor completed. Result length: {len(result.content) if result and result.content else 0}")

    return StepOutput(content=result.content, success=True)


def create_summary_executor(step_input: StepInput) -> StepOutput:
    """Simple wrapper to call product_lead with user_id from workflow."""
    from agno.workflow.types import StepOutput
    from services.project_context import get_current_project_id
    import re

    # Get user_id from workflow session
    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    # Get project_id from context
    project_id = get_current_project_id()

    _log("📊", "SUMMARY", f"Creating summary - project_id={project_id}")

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

    # Extract architecture URL for next workflow
    architecture_url = None
    if result.content:
        arch_match = re.search(r'https://docs\.google\.com/document/d/[^/\s]+', result.content)
        if arch_match:
            architecture_url = arch_match.group(0)

    _log("📊", "SUMMARY", f"Extracted architecture_url={architecture_url}")

    # Append metadata for next workflow
    final_content = result.content
    if project_id:
        final_content += f"\n\n---\n**Metadata for next workflow:**\nPROJECT_ID: {project_id}"
        if architecture_url:
            final_content += f"\nARCHITECTURE_URL: {architecture_url}"

    return StepOutput(content=final_content, success=True)


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

product_requirements_workflow = Workflow(
    name="Product Requirements Workflow",
    stream=False,
    description="Create PRD/Feature Spec + Architecture documents",
    steps=[
        # Step 1: Create project entry and set project_id in context
        Step(
            name="create_project_entry",
            executor=create_project_entry_executor,
            description="""Create project entry in database and set project_id in context."""
        ),
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
        # Supervisor validation (validate docs and create project in DB)
        Step(
            name="supervisor_validation",
            executor=supervisor_validation_executor,
            description="""Supervisor validates documents, creates project in database, and stores doc URLs."""
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

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
import asyncio
import re
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Step, Workflow
from agno.workflow.condition import Condition
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info
from utils.cloud_logger import CloudLogger


# ============================================================================
# STATE TO TRACK URLS
# ============================================================================

class WorkflowState:
    """Track document URLs across workflow steps."""
    def __init__(self):
        self.prd_url = ""
        self.architecture_url = ""
        self.project_name = ""
        self.project_type = "new"
        self.log_doc_url = ""  # Google Doc URL for logs


_state = WorkflowState()


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
    return loop.run_until_complete(coro)


def _log(emoji: str, step: str, msg: str, data: dict = None):
    """Concise logging - writes to both console and Google Docs."""
    print(f"{emoji} [{step}] {msg}")
    log_info(f"[{step}] {msg}")
    # Also log to cloud logger for Railway visibility
    CloudLogger.get_instance().log("INFO", step, msg, data, emoji)


def _extract_url(text: str) -> Optional[str]:
    """Extract Google Docs URL from text."""
    match = re.search(r'https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+/edit', text)
    return match.group(0) if match else None


def _extract_param(text: str, param: str) -> str:
    """Extract parameter from text."""
    match = re.search(rf'{param}:\s*([^\n]+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


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
# WORKFLOW STEPS
# ============================================================================

def create_prd(step_input: StepInput) -> StepOutput:
    """Create PRD for new project."""
    global _state
    _state = WorkflowState()

    # Start cloud logging session for Railway visibility
    logger = CloudLogger.get_instance()
    _state.log_doc_url = logger.start_session("Product Requirements Workflow")
    if _state.log_doc_url:
        print(f"\n📋 LIVE LOGS: {_state.log_doc_url}\n")

    input_str = str(step_input.input)
    _state.project_name = _extract_param(input_str, "PROJECT_NAME") or "New Project"
    _state.project_type = "new"
    description = _extract_param(input_str, "DESCRIPTION") or input_str

    _log("📝", "PRD", f"Creating PRD for: {_state.project_name}")

    prompt = f"""You MUST create a PRD and save it to Google Docs.

**Project:** {_state.project_name}
**Description:** {description}

**STEP 1: Write the PRD content with these exact sections:**

1. OVERVIEW
What is this product?

2. GOALS
What problem does it solve?

3. TARGET USERS
Who will use it?

4. FEATURES
List of features (keep it focused)

5. SUCCESS METRICS
How do we measure success?

**STEP 2: YOU MUST call the create_prd_document tool**

Call it NOW with these parameters:
- title: "PRD: {_state.project_name}"
- content: (the PRD content you wrote above as plain text)
- project_name: "{_state.project_name}"

**STEP 3: Return the Google Docs URL**

The tool will return a URL like https://docs.google.com/document/d/XXXXX/edit
You MUST include this complete URL in your response.

CRITICAL: You MUST call create_prd_document tool. Do NOT skip this step.
"""

    result = _run_async(get_product_lead_agent().arun(prompt))
    output = result.content or ""

    # Extract URL
    _state.prd_url = _extract_url(output) or ""
    if _state.prd_url:
        _log("✅", "PRD", f"Created: {_state.prd_url}")
    else:
        _log("⚠️", "PRD", "No URL found in response")

    return StepOutput(content=output, success=True)


def create_feature_spec(step_input: StepInput) -> StepOutput:
    """Create Feature Spec for existing project."""
    global _state
    _state = WorkflowState()

    # Start cloud logging session for Railway visibility
    logger = CloudLogger.get_instance()
    _state.log_doc_url = logger.start_session("Product Requirements Workflow (Feature)")
    if _state.log_doc_url:
        print(f"\n📋 LIVE LOGS: {_state.log_doc_url}\n")

    input_str = str(step_input.input)
    _state.project_name = _extract_param(input_str, "PROJECT_NAME") or "Existing Project"
    _state.project_type = "existing"
    feature_name = _extract_param(input_str, "FEATURE_NAME") or "New Feature"
    description = _extract_param(input_str, "DESCRIPTION") or input_str

    _log("📝", "FEATURE_SPEC", f"Creating Feature Spec: {feature_name} for {_state.project_name}")

    prompt = f"""Create a Feature Specification for this existing product.

**Project:** {_state.project_name}
**Feature:** {feature_name}
**Description:** {description}

Create a concise Feature Spec with:
1. Feature Overview - What does this feature do?
2. User Stories - Who needs it and why?
3. Requirements - What it must do
4. Acceptance Criteria - How we know it's done

**IMPORTANT:** Keep it simple and actionable.

**Save to Google Docs:**
Use create_feature_spec_document tool with:
- title: "Feature: {feature_name}"
- content: [your spec]
- feature_name: "{feature_name}"
- project_name: "{_state.project_name}"

Return the Google Docs URL.
"""

    result = _run_async(get_product_lead_agent().arun(prompt))
    output = result.content or ""

    # Extract URL
    _state.prd_url = _extract_url(output) or ""
    if _state.prd_url:
        _log("✅", "FEATURE_SPEC", f"Created: {_state.prd_url}")
    else:
        _log("⚠️", "FEATURE_SPEC", "No URL found in response")

    return StepOutput(content=output, success=True)


def create_architecture(step_input: StepInput) -> StepOutput:
    """Create SIMPLE architecture document proportional to requirements."""
    global _state

    prd_content = step_input.previous_step_content or ""

    # Try to get PRD URL if we don't have it
    if not _state.prd_url:
        _state.prd_url = _extract_url(prd_content) or ""

    _log("🏗️", "ARCH", f"Creating architecture for: {_state.project_name}")

    # READ FULL PRD from Google Docs to understand complete scope and tech requirements
    full_prd_content = prd_content[:2000]  # Fallback to truncated content
    if _state.prd_url:
        _log("📖", "ARCH", f"Reading full PRD from Google Docs: {_state.prd_url}")
        try:
            from tools.google_docs_tools import GoogleDocsTools
            doc_id = re.search(r'/document/d/([a-zA-Z0-9-_]+)', _state.prd_url).group(1)
            full_prd_content = GoogleDocsTools().read_document(doc_id)
            _log("✅", "ARCH", f"PRD loaded: {len(full_prd_content)} characters")

            # Log key requirements
            prd_lower = full_prd_content.lower()
            _log("🔍", "ARCH", "Analyzing PRD requirements...")

            # Detect tech stack mentions
            tech_hints = []
            if "static" in prd_lower or "html" in prd_lower:
                tech_hints.append("static HTML/CSS/JS")
            if "react" in prd_lower:
                tech_hints.append("React")
            if "next" in prd_lower:
                tech_hints.append("Next.js")
            if "database" in prd_lower or "supabase" in prd_lower:
                tech_hints.append("database")
            if "api" in prd_lower:
                tech_hints.append("API")

            if tech_hints:
                _log("💡", "ARCH", f"Tech stack hints found: {', '.join(tech_hints)}")
            else:
                _log("💡", "ARCH", "No specific tech stack mentioned - will choose appropriate stack")

        except Exception as e:
            _log("⚠️", "ARCH", f"Could not read full PRD: {e} - using truncated content")
    else:
        _log("⚠️", "ARCH", "No PRD URL available - using content from previous step")

    if _state.project_type == "existing":
        prompt = f"""Create a SIMPLE architecture document for this feature.

**CRITICAL:** Read the FULL PRD below and respect its scope. Do NOT go beyond what's requested.

**Project:** {_state.project_name}
**PRD/Feature Spec URL:** {_state.prd_url or 'Not available'}

**FULL PRD CONTENT:**
{full_prd_content}

**Your task:**
1. Read the ENTIRE PRD above carefully
2. Identify the ACTUAL requirements and scope
3. If a tech stack is mentioned → USE IT (don't change it)
4. If no tech stack mentioned → choose the SIMPLEST appropriate stack
5. Create architecture that matches the PRD scope (no more, no less)

**Create a SHORT architecture document with:**

1. **What We're Building** (2-3 sentences - based on PRD)
2. **Tech Stack** (use what's mentioned in PRD, or choose minimal stack)
3. **Components** (bullet list - only what's needed for PRD requirements)
4. **Database Changes** (only if PRD requires it)
5. **Implementation Steps** (3-5 steps - direct from PRD requirements)

**CRITICAL RULES:**
- RESPECT THE PRD SCOPE - don't add features not mentioned
- If PRD says "static webpage" → use HTML/CSS/JS (NOT Next.js + Supabase!)
- If PRD says specific tech → USE THAT TECH
- Simple requirements = Simple architecture
- 1 page is often enough

**Save to Google Docs:**
Use create_document tool:
- title: "Architecture: {_state.project_name}"
- content: [your architecture]

Return the Google Docs URL.
"""
    else:
        prompt = f"""Create a SIMPLE architecture document for this project.

**CRITICAL:** Read the FULL PRD below and respect its scope. Do NOT over-engineer or add unnecessary complexity.

**Project:** {_state.project_name}
**PRD URL:** {_state.prd_url or 'Not available'}

**FULL PRD CONTENT:**
{full_prd_content}

**Your task:**
1. Read the ENTIRE PRD above carefully
2. Understand the ACTUAL requirements (not what could be built, what SHOULD be built)
3. Check if PRD mentions any tech stack → USE IT
4. If no tech stack mentioned → choose SIMPLEST appropriate stack
5. Match architecture complexity to PRD complexity

**Create a SHORT architecture document with:**

1. **What We're Building** (2-3 sentences - summarize PRD)
2. **Tech Stack** (MATCH TO REQUIREMENTS):
   - Static content only? → HTML/CSS/JS
   - Interactive but no backend? → React or Vanilla JS
   - Needs backend/database? → Next.js + Supabase
   - Always deploy to: Vercel
3. **Main Components** (bullet list - only what PRD requires)
4. **Data Model** (ONLY if PRD explicitly needs a database)
5. **Implementation Steps** (3-5 steps - map directly from PRD features)

**CRITICAL RULES:**
- RESPECT THE PRD - don't add features, complexity, or tech not needed
- If PRD is 5 bullet points → architecture should be 1 page
- If PRD says "landing page" → don't build a full application
- If PRD mentions specific tech → USE IT (don't substitute)
- When in doubt, GO SIMPLER

**Save to Google Docs:**
Use create_document tool:
- title: "Architecture: {_state.project_name}"
- content: [your architecture]

Return the Google Docs URL.
"""

    result = _run_async(get_lead_engineer_agent().arun(prompt))
    output = result.content or ""

    # Extract Architecture URL
    _state.architecture_url = _extract_url(output) or ""
    if _state.architecture_url:
        _log("✅", "ARCH", f"Created: {_state.architecture_url}")
    else:
        _log("⚠️", "ARCH", "No URL found in response")

    return StepOutput(content=output, success=True)


def create_summary(step_input: StepInput) -> StepOutput:
    """Final step: Return both document URLs clearly."""
    global _state

    # Try to extract URLs from previous content if we don't have them
    prev_content = step_input.previous_step_content or ""
    if not _state.architecture_url:
        _state.architecture_url = _extract_url(prev_content) or ""

    doc_type = "Feature Spec" if _state.project_type == "existing" else "PRD"

    # End cloud logging session and get final log URL
    log_url = CloudLogger.get_instance().end_session()

    summary = f"""
## ✅ Documents Created!

**Project:** {_state.project_name}

### 📄 Document 1: {doc_type}
{_state.prd_url or 'Not available'}

### 🏗️ Document 2: Architecture
{_state.architecture_url or 'Not available'}

### 📋 Logs
{log_url if log_url else 'N/A'}

---
**Next step:** Would you like me to implement this? Just say "yes" or "implement this".
"""

    _log("🎉", "DONE", f"Workflow complete - 2 documents created")
    _log("📄", "DONE", f"{doc_type}: {_state.prd_url}")
    _log("🏗️", "DONE", f"Architecture: {_state.architecture_url}")

    return StepOutput(content=summary, success=True)


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
            steps=[Step(name="create_prd", executor=create_prd)],
        ),
        # Conditional: Existing Project → Feature Spec
        Condition(
            name="existing_project_path",
            description="Create Feature Spec for existing projects",
            evaluator=is_existing_project,
            steps=[Step(name="create_feature_spec", executor=create_feature_spec)],
        ),
        # Architecture (always runs)
        Step(name="create_architecture", executor=create_architecture),
        # Summary with both URLs
        Step(name="summary", executor=create_summary),
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
    """Run the product requirements workflow."""
    _log("🚀", "WORKFLOW", "Starting Product Requirements Workflow")

    parts = [f"DESCRIPTION: {request}"]
    if project_type:
        parts.append(f"PROJECT_TYPE: {project_type}")
    if project_name:
        parts.append(f"PROJECT_NAME: {project_name}")
    if feature_name:
        parts.append(f"FEATURE_NAME: {feature_name}")

    full_input = "\n".join(parts)
    result = product_requirements_workflow.run(input=full_input)

    _log("✅", "WORKFLOW", "Complete")
    return {"success": True, "content": result.content or ""}

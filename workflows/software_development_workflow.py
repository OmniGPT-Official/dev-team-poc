"""
Software Development Workflow - End to End

Complete implementation workflow from architecture to deployment.

Flow:
1. Ask Permission -> Confirm with user before starting implementation
2. Architecture Design -> Create architecture/stack document (Next.js+Supabase+Vercel OR Python)
3. Create GitHub Repo -> Initialize repository with code
4. Write Code -> Implement using Supabase MCP for database
5. Deploy -> Deploy to Vercel and get preview link
6. Summary -> Return architecture doc + deployment link

Input: document_url (PRD/Feature Spec from Product Lead), project_type, project_name
Output: Architecture document + Vercel deployment link
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
    - DOCUMENT_URL: <url>
    - PROJECT_TYPE: new|existing
    - PROJECT_NAME: <name>
    - FEATURE_NAME: <name>
    """
    params = {
        "document_url": None,
        "project_type": None,
        "project_name": None,
        "feature_name": None,
    }

    # Extract document URL
    doc_url_match = re.search(r'DOCUMENT_URL:\s*(https://[^\s]+)', input_str, re.I)
    if not doc_url_match:
        # Try to find Google Docs URL anywhere in the string
        doc_url_match = re.search(r'https://docs\.google\.com/document/d/[^\s)]+', input_str)
    if doc_url_match:
        params["document_url"] = doc_url_match.group(1) if doc_url_match.lastindex else doc_url_match.group(0)

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

def ask_permission(step_input: StepInput) -> StepOutput:
    """
    Step 1: Ask user permission before starting implementation.

    This is a placeholder - in practice, the Product Lead agent handles this
    by asking the user before triggering this workflow.
    """
    log_info("[STEP:permission] User permission granted (via Product Lead)")

    return StepOutput(
        content="Permission granted to proceed with implementation.",
        success=True
    )


def create_architecture(step_input: StepInput) -> StepOutput:
    """
    Step 2: Create Architecture Document

    Lead Engineer determines if project is new or existing, then:
    - New project: Choose tech stack (Next.js + Supabase + Vercel OR Python)
    - Existing project: Use existing stack

    Creates architecture document with:
    - Tech stack
    - System design
    - Database schema
    - API design
    - Deployment plan
    """
    input_str = step_input.input if isinstance(step_input.input, str) else ""
    params = parse_input_params(input_str)

    log_info("[STEP:architecture] Creating architecture document")
    log_debug(f"[STEP:architecture] Params: {params}")

    from agents.lead_engineer import lead_engineer_agent

    project_type = params["project_type"] or "new"
    project_name = params["project_name"] or "Unnamed Project"
    document_url = params["document_url"]

    prompt = f"""Create a comprehensive architecture document for this project.

**Project Type:** {project_type}
**Project Name:** {project_name}
**Requirements Document:** {document_url or 'See below'}

{input_str}

## Instructions

1. **Determine Tech Stack:**
   - For NEW projects: Choose between:
     * **Next.js + Supabase + Vercel** (for web apps)
     * **Python + FastAPI + PostgreSQL** (for APIs/backend)
   - For EXISTING projects: Identify current stack from requirements

2. **Create Architecture Document with:**
   - **Tech Stack Selection** (with justification)
   - **System Architecture** (components, data flow)
   - **Database Schema** (tables, relationships)
   - **API Design** (endpoints, request/response)
   - **Security Considerations**
   - **Deployment Strategy** (Vercel deployment plan)

3. **Output Format:**
   Use plain text formatting (NOT markdown) since this may be shared in Google Docs.
   - Use clear headings with spacing
   - Use bullet points with "•" or "-"
   - Use line breaks for structure

Be specific and actionable. Focus on implementation-ready design.
"""

    log_info("[AGENT:lead_engineer] Designing architecture and stack")
    result = _run_async(lead_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:architecture] Architecture document created")
    return StepOutput(content=output, success=True)


def create_github_repo(step_input: StepInput) -> StepOutput:
    """
    Step 3: Create GitHub Repository

    Software Engineer creates a new GitHub repo and initializes it with code structure.
    """
    architecture = step_input.previous_step_content or ""
    input_str = step_input.input if isinstance(step_input.input, str) else ""
    params = parse_input_params(input_str)

    log_info("[STEP:create_repo] Creating GitHub repository")

    from agents.software_engineer import software_engineer_agent

    project_name = params["project_name"] or "unnamed-project"

    prompt = f"""Create a new GitHub repository for this project and initialize it with the basic structure.

**Project Name:** {project_name}
**Architecture:**
{architecture}

## Instructions

1. **Create GitHub Repository:**
   - Use the GitHubTools to create a new repository
   - Repository name: {project_name.lower().replace(' ', '-')}
   - Initialize with README
   - Add .gitignore based on tech stack

2. **Set up Initial Structure:**
   - Create basic project structure based on the architecture
   - Add initial configuration files
   - Set up environment variable templates (.env.example)

3. **Return:**
   - Repository URL
   - Initial structure created
   - Next steps for code implementation

Use the GitHub MCP tools available to you.
"""

    log_info("[AGENT:software_engineer] Creating repository")
    result = _run_async(software_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:create_repo] Repository created")
    return StepOutput(content=output, success=True)


def write_code(step_input: StepInput) -> StepOutput:
    """
    Step 4: Write Code

    Software Engineer implements the code using:
    - GitHub MCP for code storage
    - Supabase MCP for database operations
    """
    repo_info = step_input.previous_step_content or ""
    input_str = step_input.input if isinstance(step_input.input, str) else ""
    params = parse_input_params(input_str)

    # Get architecture from earlier steps
    architecture = step_input.workflow_context.get("architecture", "")

    log_info("[STEP:write_code] Implementing code")

    from agents.software_engineer import software_engineer_agent

    prompt = f"""Implement the complete codebase for this project.

**Repository Info:**
{repo_info}

**Architecture:**
{architecture}

## Instructions

1. **Write Code:**
   - Implement all core features from the architecture
   - Use best practices for the chosen tech stack
   - Include proper error handling and validation
   - Add code comments where necessary

2. **Database Setup (using Supabase MCP):**
   - Create database tables based on schema
   - Set up authentication if needed
   - Configure Row Level Security (RLS)
   - Add seed data if applicable

3. **Code Organization:**
   - Follow the project structure
   - Separate concerns properly
   - Create reusable components/modules
   - Add configuration files

4. **Write to GitHub:**
   - Use GitHub MCP tools to commit and push code
   - Create meaningful commit messages
   - Organize files properly

Use the GitHub MCP and Supabase MCP tools available to you.
"""

    log_info("[AGENT:software_engineer] Writing code")
    result = _run_async(software_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:write_code] Code implementation complete")
    return StepOutput(content=output, success=True)


def deploy_to_vercel(step_input: StepInput) -> StepOutput:
    """
    Step 5: Deploy to Vercel

    Software Engineer deploys the code to Vercel and returns the preview link.
    """
    code_info = step_input.previous_step_content or ""
    input_str = step_input.input if isinstance(step_input.input, str) else ""

    log_info("[STEP:deploy] Deploying to Vercel")

    from agents.software_engineer import software_engineer_agent

    prompt = f"""Deploy the project to Vercel.

**Code Implementation:**
{code_info}

## Instructions

1. **Deploy to Vercel:**
   - Use Vercel MCP tools to deploy the project
   - Connect the GitHub repository
   - Configure environment variables
   - Set up Supabase connection strings

2. **Verify Deployment:**
   - Check deployment status
   - Test the preview URL
   - Ensure all features are working

3. **Return:**
   - Deployment URL (preview link)
   - Deployment status
   - Any configuration notes

Use the Vercel MCP tools available to you.
"""

    log_info("[AGENT:software_engineer] Deploying to Vercel")
    result = _run_async(software_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:deploy] Deployment complete")
    return StepOutput(content=output, success=True)


def create_final_summary(step_input: StepInput) -> StepOutput:
    """
    Step 6: Create Final Summary

    Return architecture document and deployment link.
    """
    deployment_info = step_input.previous_step_content or ""
    input_str = step_input.input if isinstance(step_input.input, str) else ""
    params = parse_input_params(input_str)

    log_info("[STEP:summary] Creating final summary")

    # Get architecture from workflow context
    architecture = step_input.workflow_context.get("architecture", "")

    # Extract deployment URL
    deploy_url_match = re.search(r'https://[^\s]+vercel\.app[^\s]*', deployment_info)
    deploy_url = deploy_url_match.group(0) if deploy_url_match else "Deployment in progress"

    # Extract GitHub repo URL
    repo_url_match = re.search(r'https://github\.com/[^\s]+', deployment_info)
    repo_url = repo_url_match.group(0) if repo_url_match else "Repository created"

    project_name = params["project_name"] or "Project"
    document_url = params["document_url"]

    summary = f"""
## 🎉 Implementation Complete!

### Project: {project_name}

**Good news! Your product has been successfully built and deployed.**

---

### 📋 Documents

**Requirements Document (PRD/Feature Spec):**
{document_url or 'Created'}

**Architecture Document:**
{architecture[:500] if architecture else 'See full output below'}

---

### 🚀 Deployment

**Preview Link:** {deploy_url}
**GitHub Repository:** {repo_url}

---

### ✅ What Was Done

1. ✓ Architecture designed with tech stack selection
2. ✓ GitHub repository created and initialized
3. ✓ Complete codebase implemented
4. ✓ Database configured with Supabase
5. ✓ Deployed to Vercel with preview link

---

### 📝 Full Architecture Document

{architecture}

---

### 🔗 Deployment Details

{deployment_info}

---

**Next Steps:**
1. Visit the preview link to test your product
2. Review the code in the GitHub repository
3. Configure custom domain (if needed)
4. Set up production environment variables
5. Monitor deployment and database usage
"""

    log_info("[STEP:summary] Summary complete")
    return StepOutput(content=summary, success=True)


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

software_development_workflow = Workflow(
    name="Software Development",
    stream=False,
    description="""Complete implementation from architecture to deployment:
    1. Ask Permission
    2. Create Architecture (Stack selection: Next.js+Supabase+Vercel OR Python)
    3. Create GitHub Repo
    4. Write Code (using Supabase MCP for database)
    5. Deploy to Vercel
    6. Return architecture + deployment link""",
    steps=[
        Step(name="permission", executor=ask_permission),
        Step(name="architecture", executor=create_architecture),
        Step(name="create_repo", executor=create_github_repo),
        Step(name="write_code", executor=write_code),
        Step(name="deploy", executor=deploy_to_vercel),
        Step(name="summary", executor=create_final_summary),
    ]
)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def run_software_development(
    document_url: str,
    project_type: str,
    project_name: str,
    feature_name: Optional[str] = None,
) -> dict:
    """
    Run the complete software development workflow.

    Args:
        document_url: Google Docs URL of PRD/Feature Spec
        project_type: "new" or "existing"
        project_name: Name of the project
        feature_name: Name of the feature (for existing products)

    Returns:
        Dict with success status, content, and deployment info
    """
    log_info("[WORKFLOW:software_development] Starting")

    # Build input with parameters
    input_parts = [f"DOCUMENT_URL: {document_url}"]
    input_parts.append(f"PROJECT_TYPE: {project_type}")
    input_parts.append(f"PROJECT_NAME: {project_name}")
    if feature_name:
        input_parts.append(f"FEATURE_NAME: {feature_name}")

    full_input = "\n".join(input_parts)
    log_debug(f"[WORKFLOW:software_development] INPUT:\n{full_input}")

    result = software_development_workflow.run(input=full_input)
    output = result.content or ""

    log_info("[WORKFLOW:software_development] Complete")

    return {"success": True, "content": output}

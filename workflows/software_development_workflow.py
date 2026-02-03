"""
Software Development Workflow - Implementation Only

This workflow handles ONLY implementation. It does NOT create PRDs.
The PRD should already exist and the document_url is provided as input.

Flow:
1. Read PRD -> Fetch PRD content from the provided Google Docs URL
2. Create Architecture -> Design tech stack and architecture
3. Create GitHub Repo -> Initialize repository
4. Write Code -> Implement using Supabase MCP
5. Deploy to Vercel -> Deploy and get preview link
6. Summary -> Return architecture + deployment link

Input: document_url (PRD/Feature Spec already created by Product Lead)
Output: Architecture document + Vercel deployment link
"""

import os
import sys
import re
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Step, Workflow
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _run_async(coro):
    """
    Run async coroutine from sync context.
    Uses the existing event loop if available, creates one if not.
    Does NOT close the loop to allow Agno to use it for cleanup.
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            # Loop exists but closed - create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        # No event loop exists - create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run the coroutine and return result
    # DO NOT close the loop - Agno needs it for cleanup
    return loop.run_until_complete(coro)


def parse_document_url(input_str: str) -> str:
    """
    Parse input string to extract ONLY the document URL.

    Required:
    - DOCUMENT_URL: <url> (Google Docs URL of the PRD/Feature Spec)
    OR
    - Just the raw URL anywhere in the input
    """
    print(f"\n[DEBUG:parse_document_url] Parsing input (length {len(input_str)})")
    print(f"[DEBUG:parse_document_url] Input preview: {input_str[:300]}\n")

    # Extract document URL
    doc_url_match = re.search(r'DOCUMENT_URL:\s*(https://[^\s]+)', input_str, re.I)
    if not doc_url_match:
        # Try to find Google Docs URL anywhere in the string
        doc_url_match = re.search(r'https://docs\.google\.com/document/d/[^\s)]+', input_str)

    if doc_url_match:
        url = doc_url_match.group(1) if doc_url_match.lastindex else doc_url_match.group(0)
        print(f"[DEBUG:parse_document_url] ✓ Found document_url: {url}\n")
        return url
    else:
        print(f"[DEBUG:parse_document_url] ❌ No document_url found in input!\n")
        return None


# ============================================================================
# WORKFLOW STEP FUNCTIONS
# ============================================================================

def read_prd(step_input: StepInput) -> StepOutput:
    """
    Step 1: Read PRD from Google Docs URL

    Fetches the PRD/Feature Spec content from the provided document URL.
    This is the ONLY input to the workflow - we do NOT create a new PRD.

    Input: Just the document URL (nothing else needed)
    Output: Full PRD content from Google Docs
    """
    input_str = step_input.input if isinstance(step_input.input, str) else ""

    # EXTENSIVE LOGGING
    print("\n" + "="*80)
    print("[DEBUG:read_prd] === STEP 1: READ PRD ===")
    print(f"[DEBUG:read_prd] step_input.input TYPE: {type(step_input.input)}")
    print(f"[DEBUG:read_prd] step_input.input VALUE:\n{repr(input_str)[:500]}")
    print("="*80 + "\n")

    document_url = parse_document_url(input_str)

    if not document_url:
        error_msg = "ERROR: No document_url provided. The software development workflow requires a PRD/Feature Spec URL."
        print(f"\n❌ [ERROR:read_prd] {error_msg}\n")
        log_info(f"[STEP:read_prd] {error_msg}")
        return StepOutput(content=error_msg, success=False)

    print(f"\n✓ [DEBUG:read_prd] Found document_url: {document_url}\n")
    log_info(f"[STEP:read_prd] Reading PRD from: {document_url}")

    from tools.google_docs_tools import GoogleDocsTools

    # Try to read the document
    try:
        google_docs = GoogleDocsTools()
        # Extract document ID from URL
        doc_id_match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', document_url)
        if not doc_id_match:
            error_msg = f"ERROR: Invalid Google Docs URL: {document_url}"
            log_info(f"[STEP:read_prd] {error_msg}")
            return StepOutput(content=error_msg, success=False)

        doc_id = doc_id_match.group(1)

        # Read the actual document content using Google Docs API
        try:
            print(f"\n[DEBUG:read_prd] Calling google_docs.read_document({doc_id})\n")
            prd_content = google_docs.read_document(doc_id)
            print(f"\n✓ [DEBUG:read_prd] Document read successfully!")
            print(f"[DEBUG:read_prd] Content length: {len(prd_content)} chars")
            print(f"[DEBUG:read_prd] Content preview: {prd_content[:200]}...\n")

            log_info("[STEP:read_prd] PRD content retrieved successfully")

            # Include URL and content
            full_content = f"""PRD Document URL: {document_url}
Document ID: {doc_id}

=== PRD CONTENT ===
{prd_content}
===================
"""
            print(f"\n✓ [DEBUG:read_prd] Returning StepOutput with {len(full_content)} chars\n")
            return StepOutput(content=full_content, success=True)

        except Exception as read_error:
            log_info(f"[STEP:read_prd] Could not read document content: {read_error}")
            # If reading fails, at least pass the URL
            prd_content = f"PRD Document URL: {document_url}\nDocument ID: {doc_id}\n\nWARNING: Could not read document content. Error: {str(read_error)}"
            return StepOutput(content=prd_content, success=True)

    except Exception as e:
        error_msg = f"ERROR: Failed to process document URL: {str(e)}"
        log_info(f"[STEP:read_prd] {error_msg}")
        return StepOutput(content=error_msg, success=False)


def create_architecture(step_input: StepInput) -> StepOutput:
    """
    Step 2: Create Architecture Document

    Lead Engineer reads the PRD (from previous step) and creates architecture with tech stack selection.
    - New project: Choose between Next.js+Supabase+Vercel OR Python+FastAPI
    - Existing project: Use existing stack

    Input: Original document URL (from workflow input)
    Previous Step Output: Full PRD content
    Output: Architecture document
    """
    prd_content = step_input.previous_step_content or ""
    input_str = step_input.input if isinstance(step_input.input, str) else ""

    # EXTENSIVE LOGGING
    print("\n" + "="*80)
    print("[DEBUG:create_architecture] === STEP 2: CREATE ARCHITECTURE ===")
    print(f"[DEBUG:create_architecture] PRD content length: {len(prd_content)} chars")
    print(f"[DEBUG:create_architecture] PRD content PREVIEW:\n{prd_content[:500]}")
    print("="*80 + "\n")

    # Extract document URL from original input (for reference)
    document_url = parse_document_url(input_str)

    log_info("[STEP:architecture] Creating architecture document")

    from agents.lead_engineer import lead_engineer_agent

    prompt = f"""You are creating the technical architecture for this project.

**CRITICAL INSTRUCTION:** DO NOT use any workflow tools. DO NOT run the Software Development Workflow. You are INSIDE the workflow already. Just design the architecture directly.

**IMPORTANT:** The PRD has already been read from Google Docs. Your job is to design the architecture, NOT create or fetch the PRD.

=== PRD CONTENT (ALREADY FETCHED FROM GOOGLE DOCS) ===
{prd_content}
============================================================

## Your Task

1. **Read the PRD content above** (it's already provided - do NOT try to fetch it again)
2. **Determine project type** from the PRD (new project or existing product feature)
3. **Select Tech Stack:**
   - For NEW web projects: **Next.js + Supabase + Vercel**
   - For NEW API/backend projects: **Python + FastAPI + PostgreSQL + Vercel**
   - For EXISTING projects: Identify and use the current stack from the PRD

4. **Create Complete Architecture Document:**
   - Tech Stack Selection (with justification based on PRD requirements)
   - System Architecture (components, data flow)
   - Database Schema (tables, columns, relationships)
   - API Design (endpoints, methods, request/response)
   - Security Considerations
   - Deployment Strategy (Vercel deployment plan)

5. **Output Format:**
   Plain text formatting (NOT markdown):
   - Clear headings with spacing
   - Bullet points with "•" or "-"
   - Line breaks for structure
   - No markdown symbols

Be specific and implementation-ready. Focus on actionable technical details.

REMEMBER: DO NOT use workflow tools or try to fetch documents. Just write the architecture based on the PRD content provided above.
"""

    print(f"\n[DEBUG:create_architecture] Calling lead_engineer_agent.arun()\n")

    log_info("[AGENT:lead_engineer] Designing architecture")
    result = _run_async(lead_engineer_agent.arun(prompt))
    output = result.content or ""

    print(f"\n✓ [DEBUG:create_architecture] Agent returned {len(output)} chars\n")

    log_info("[STEP:architecture] Architecture created")
    return StepOutput(content=output, success=True)


def create_github_repo(step_input: StepInput) -> StepOutput:
    """
    Step 3: Create GitHub Repository

    Input: Original document URL
    Previous Step Output: Architecture document
    Output: GitHub repository info
    """
    architecture = step_input.previous_step_content or ""
    input_str = step_input.input if isinstance(step_input.input, str) else ""

    log_info("[STEP:create_repo] Creating GitHub repository")

    from agents.software_engineer import software_engineer_agent

    prompt = f"""Create a new GitHub repository for this project.

**Architecture Document:**
{architecture}

## Instructions

1. **Extract project name** from the architecture document above
2. **Create repository name** by converting project name to lowercase kebab-case
3. **Use GitHubTools** to create a new repository
4. Initialize with README
5. Add .gitignore based on tech stack from architecture
6. Set up initial project structure
7. Add .env.example with required environment variables

Return the repository URL and initial structure.
"""

    log_info("[AGENT:software_engineer] Creating repository")
    result = _run_async(software_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:create_repo] Repository created")
    return StepOutput(content=output, success=True)


def write_code(step_input: StepInput) -> StepOutput:
    """
    Step 4: Write Code with Supabase MCP
    """
    repo_info = step_input.previous_step_content or ""
    input_str = step_input.input if isinstance(step_input.input, str) else ""

    log_info("[STEP:write_code] Implementing code")

    from agents.software_engineer import software_engineer_agent

    prompt = f"""Implement the complete codebase for this project.

**Repository Info:**
{repo_info}

## Instructions

1. **Write Complete Code:**
   - Implement all features from the architecture
   - Follow best practices for the tech stack
   - Include error handling and validation
   - Add necessary comments

2. **Database Setup with Supabase MCP:**
   - Create database tables
   - Set up Row Level Security (RLS)
   - Configure authentication if needed
   - Add initial seed data

3. **Commit to GitHub:**
   - Use GitHub MCP tools to commit and push
   - Organize files properly
   - Write clear commit messages

Use GitHub MCP and Supabase MCP tools.
"""

    log_info("[AGENT:software_engineer] Writing code")
    result = _run_async(software_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:write_code] Code complete")
    return StepOutput(content=output, success=True)


def deploy_to_vercel(step_input: StepInput) -> StepOutput:
    """
    Step 5: Deploy to Vercel
    """
    code_info = step_input.previous_step_content or ""

    log_info("[STEP:deploy] Deploying to Vercel")

    from agents.software_engineer import software_engineer_agent

    prompt = f"""Deploy the project to Vercel.

**Code Implementation:**
{code_info}

## Instructions

1. Use Vercel MCP tools to deploy
2. Connect the GitHub repository
3. Configure environment variables
4. Set up Supabase connection strings
5. Verify deployment
6. Return the preview URL

Use Vercel MCP tools.
"""

    log_info("[AGENT:software_engineer] Deploying")
    result = _run_async(software_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:deploy] Deployment complete")
    return StepOutput(content=output, success=True)


def create_summary(step_input: StepInput) -> StepOutput:
    """
    Step 6: Create Final Summary

    Input: Original document URL
    Previous Step Output: Deployment info
    Output: Final summary with all links
    """
    deployment_info = step_input.previous_step_content or ""
    input_str = step_input.input if isinstance(step_input.input, str) else ""

    log_info("[STEP:summary] Creating summary")

    # Extract document URL
    document_url = parse_document_url(input_str)

    # Extract URLs from deployment info
    deploy_url_match = re.search(r'https://[^\s]+vercel\.app[^\s]*', deployment_info)
    deploy_url = deploy_url_match.group(0) if deploy_url_match else "Deployment in progress"

    repo_url_match = re.search(r'https://github\.com/[^\s]+', deployment_info)
    repo_url = repo_url_match.group(0) if repo_url_match else "Repository created"

    # Extract project name from repo URL or use generic name
    project_name = "Your Project"
    if repo_url and repo_url != "Repository created":
        # Extract from github.com/owner/repo-name
        repo_name_match = re.search(r'github\.com/[^/]+/([^/\s]+)', repo_url)
        if repo_name_match:
            project_name = repo_name_match.group(1).replace('-', ' ').title()

    summary = f"""
## 🎉 Implementation Complete!

### Project: {project_name}

**Good news! Your product has been successfully built and deployed.**

---

### 📋 Documents

**Requirements (PRD/Feature Spec):**
{document_url}

---

### 🚀 Deployment

**Live Preview:** {deploy_url}
**GitHub Repository:** {repo_url}

---

### ✅ What Was Done

1. ✓ Read PRD from Google Docs
2. ✓ Designed architecture with tech stack
3. ✓ Created GitHub repository
4. ✓ Implemented complete codebase
5. ✓ Configured database with Supabase
6. ✓ Deployed to Vercel

---

### 🔗 Full Details

{deployment_info}

---

**Next Steps:**
1. Visit the preview link to test your product
2. Review the code in GitHub
3. Configure custom domain (optional)
4. Set up production environment variables
"""

    log_info("[STEP:summary] Summary complete")
    return StepOutput(content=summary, success=True)


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

software_development_workflow = Workflow(
    name="Software Development",
    stream=False,
    description="""Implementation workflow (does NOT create PRD).

    Input: Google Docs URL of PRD/Feature Spec (ONLY)

    Sequential Steps:
    1. Read PRD from Google Docs URL
    2. Create Architecture (based on PRD content)
    3. Create GitHub Repo
    4. Write Code (using Supabase MCP)
    5. Deploy to Vercel
    6. Return summary + deployment link

    Each step receives the original document URL and output from previous step.
    """,
    steps=[
        Step(name="read_prd", executor=read_prd),
        Step(name="architecture", executor=create_architecture),
        Step(name="create_repo", executor=create_github_repo),
        Step(name="write_code", executor=write_code),
        Step(name="deploy", executor=deploy_to_vercel),
        Step(name="summary", executor=create_summary),
    ]
)

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
import threading
import contextvars

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


def _run_async(coro):
    """Run an async coroutine in an isolated thread with its own event loop.

    Using asyncio.run() directly in sync step executors (which are called from
    within FastAPI's async event loop) closes the current event loop after each
    call, causing 'Event loop is closed' errors when Agno tries to stream the
    final Team response back to the SSE client.

    This helper runs the coroutine in a brand-new thread with its own loop so
    the parent event loop is never touched. contextvars are copied so that
    context-var-based values (e.g. user_id, project_id) are visible inside.
    """
    import asyncio

    result_holder = [None]
    error_holder = [None]
    ctx = contextvars.copy_context()

    def _execute():
        def _run_in_context():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result_holder[0] = loop.run_until_complete(coro)
            except Exception as e:
                error_holder[0] = e
            finally:
                loop.close()
        ctx.run(_run_in_context)

    thread = threading.Thread(target=_execute, daemon=True)
    thread.start()
    thread.join()

    if error_holder[0]:
        raise error_holder[0]
    return result_holder[0]


def get_product_lead_agent():
    from agents.product_lead import product_lead_agent
    return product_lead_agent


def get_lead_engineer_agent():
    from agents.lead_engineer import lead_engineer_agent
    return lead_engineer_agent


def get_supervisor_agent():
    from agents.supervisor import supervisor_agent
    return supervisor_agent


def _save_to_google_docs(user_id: str, method: str, step_label: str, **kwargs) -> str | None:
    """Save content to Google Docs programmatically (no agent hallucination possible).

    Args:
        user_id: User ID for credential lookup.
        method: GoogleDocsTools method name ('create_document', 'create_prd_document',
                'create_feature_spec_document').
        step_label: Label for log messages (e.g. 'PRD-SAVE').
        **kwargs: Arguments to pass to the GoogleDocsTools method.

    Returns:
        Google Docs URL on success, None on failure.
    """
    import json
    from services.tool_providers import resolve_tools

    try:
        google_docs_tools = resolve_tools(user_id, "google_docs")
        if not google_docs_tools:
            _log("⚠️", step_label, "No Google Docs tools available for this user")
            return None

        toolkit = google_docs_tools[0]
        fn = getattr(toolkit, method, None)
        if not fn:
            _log("❌", step_label, f"Method {method} not found on GoogleDocsTools")
            return None

        _log("📄", step_label, f"Saving to Google Docs via {method}...")
        save_result = fn(**kwargs)
        save_data = json.loads(save_result)

        if save_data.get("success"):
            doc_url = save_data["document_url"]
            _log("✅", step_label, f"Saved: {doc_url}")
            return doc_url
        else:
            _log("❌", step_label, f"Save failed: {save_data.get('error', 'Unknown error')}")
            return None
    except Exception as e:
        _log("❌", step_label, f"Error saving to Google Docs: {e}")
        return None


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
    """Create PRD: Phase 1 agent writes content, Phase 2 saves to Google Docs programmatically."""
    import re
    import asyncio

    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    project_id = get_current_project_id()

    project_name_match = re.search(r'PROJECT_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    project_desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?:PROJECT_TYPE:|$)', str(step_input.input), re.IGNORECASE | re.DOTALL)

    project_name = project_name_match.group(1).strip() if project_name_match else "Unknown Project"
    project_description = project_desc_match.group(1).strip() if project_desc_match else "No description provided"
    project_id_short = project_id[:8] if project_id else "00000000"

    _log("📝", "PRD-CREATE", f"Starting PRD creation for user_id={user_id}, project_id={project_id}")

    # ---- PHASE 1: Generate PRD content via Product Lead ----
    description = f"""Create a Product Requirements Document (PRD).

**CRITICAL: USE ONLY THE INFORMATION PROVIDED IN THE INPUT BELOW. DO NOT ADD EXAMPLES, DO NOT HALLUCINATE.**

**CRITICAL — LINK PRESERVATION: The input below may contain image URLs, font links, icon CDN links, documentation URLs, reference website links, social media links, video URLs, or any other URLs. You MUST include EVERY SINGLE link/URL from the input in the PRD document EXACTLY as provided. Do NOT skip, summarize, or omit any link. Place them in CONTENT & ASSETS section AND in the relevant feature sections.**

Write the PRD content starting with the DOCUMENT HEADER:

DOCUMENT TYPE: Product Requirements Document (PRD)
PROJECT TYPE: New Project
PROJECT ID: {project_id}
PROJECT NAME: {project_name}
PROJECT DESCRIPTION: {project_description}

====================================================================================================

Then continue with all the PRD sections as per your instructions.

**IMPORTANT: Do NOT call any tools. Just write the complete PRD content. The document will be saved to Google Docs automatically by the system.**

Return ONLY the full PRD content starting with the DOCUMENT HEADER above. Do not include any URLs."""

    _log("🤖", "PRD-CREATE", "Phase 1: Generating content via Product Lead...")
    result = _run_async(get_product_lead_agent().arun(description + f"\n\nInput: {step_input.input}", user_id=user_id))
    prd_content = result.content if result and result.content else ""
    _log("✅", "PRD-CREATE", f"Phase 1 complete. Content length: {len(prd_content)}")
    _log("📄", "PRD-OUTPUT", f"First 200 chars: {prd_content[:200]}")

    # ---- PHASE 2: Save to Google Docs programmatically ----
    doc_title = f"PRD_{project_name.replace(' ', '')}_{project_id_short}"
    doc_url = _save_to_google_docs(
        user_id, "create_prd_document", "PRD-SAVE",
        title=doc_title, content=prd_content, project_name=project_name
    )

    # Build output
    url_line = f"PRD Document URL: {doc_url}" if doc_url else "PRD Document URL: SAVE_FAILED"
    output = f"{url_line}\n\nPRD CONTENT:\n{prd_content}"

    return StepOutput(content=output, success=True)


def create_architecture_executor(step_input: StepInput) -> StepOutput:
    """Create Architecture: Phase 1 agent writes content, Phase 2 saves to Google Docs programmatically."""
    import re
    import asyncio

    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    project_id = get_current_project_id()
    prev_content = step_input.previous_step_content or ""

    project_name_match = re.search(r'PROJECT[_ ]NAME:\s*(.+)', prev_content, re.IGNORECASE)
    if not project_name_match:
        input_match = re.search(r'PROJECT_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
        project_name = input_match.group(1).strip() if input_match else "Unknown Project"
    else:
        project_name = project_name_match.group(1).strip()

    project_id_short = project_id[:8] if project_id else "00000000"

    _log("🏗️", "ARCH-CREATE", f"Starting architecture creation for user_id={user_id}, project_id={project_id}")
    _log("🏗️", "ARCH-CREATE", f"Previous PRD content length: {len(prev_content)}")

    # ---- PHASE 1: Generate architecture content via Lead Engineer ----
    description = f"""Create a SIMPLE architecture document based on the PRD content below.

**CRITICAL: READ THE PRD CONTENT BELOW. USE ONLY WHAT'S MENTIONED THERE.**

**CRITICAL — LINK PRESERVATION: The PRD content below contains image URLs, font links, icon links, documentation links, social media links, and other URLs provided by the user. You MUST carry forward EVERY SINGLE link/URL from the PRD into this architecture document. Place them in the Assets section AND reference them in the relevant component/page sections. No link from the PRD may be dropped.**

Write the Architecture starting with the DOCUMENT HEADER:

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
- INCLUDE ALL LINKS from the PRD in Assets and relevant sections

**IMPORTANT: Do NOT call any tools. Just write the complete architecture document content. The document will be saved to Google Docs automatically by the system.**

Return ONLY the full architecture content starting with the DOCUMENT HEADER above. Do not include any URLs."""

    _log("🤖", "ARCH-CREATE", "Phase 1: Generating content via Lead Engineer...")
    result = _run_async(get_lead_engineer_agent().arun(description + f"\n\nPRD CONTENT:\n{prev_content}", user_id=user_id))
    arch_content = result.content if result and result.content else ""
    _log("✅", "ARCH-CREATE", f"Phase 1 complete. Content length: {len(arch_content)}")
    _log("📄", "ARCH-OUTPUT", f"First 200 chars: {arch_content[:200]}")

    # ---- PHASE 2: Save to Google Docs programmatically ----
    doc_title = f"Architecture_{project_name.replace(' ', '')}_{project_id_short}"
    doc_url = _save_to_google_docs(
        user_id, "create_document", "ARCH-SAVE",
        title=doc_title, content=arch_content
    )

    # Build output
    url_line = f"Architecture Document URL: {doc_url}" if doc_url else "Architecture Document URL: SAVE_FAILED"
    output = f"{url_line}\n\nARCHITECTURE CONTENT:\n{arch_content}"

    return StepOutput(content=output, success=True)


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

4. **Report**: Summarize validation results

**CRITICAL:**
- USE THE URLs PROVIDED ABOVE - DO NOT extract or hallucinate URLs
- READ the documents to validate content
- The project_id is already in context (from workflow start)
- Do NOT call create_project - project already exists
- Use status='in_development' when updating project"""

    _log("🤖", "SUPERVISOR", "Calling Supervisor agent...")
    result = _run_async(get_supervisor_agent().arun(description, user_id=user_id))
    output = result.content if result and result.content else ""
    _log("✅", "SUPERVISOR", f"Supervisor completed. Length: {len(output)}")
    _log("📄", "SUPERVISOR-OUTPUT", f"First 200 chars: {output[:200]}")

    return StepOutput(content=output, success=True)


def create_summary_executor(step_input: StepInput) -> StepOutput:
    """Build summary using the raw content strings from previous steps directly."""
    import re

    project_id = get_current_project_id()

    _log("📊", "SUMMARY", f"Creating summary - project_id={project_id}")

    # Get content from specific previous steps by name
    # New project path: create_prd, create_architecture
    # Existing project path: create_feature_spec, create_technical_doc
    doc1_step_content = step_input.get_step_content("create_prd") or step_input.get_step_content("create_feature_spec") or ""
    doc2_step_content = step_input.get_step_content("create_architecture") or step_input.get_step_content("create_technical_doc") or ""

    # Extract project name
    all_content = doc1_step_content + "\n" + doc2_step_content
    project_name_match = re.search(r'PROJECT[_ ]NAME:\s*(.+)', all_content, re.IGNORECASE)
    project_name = project_name_match.group(1).strip() if project_name_match else "Project"

    # Extract feature name (for existing projects)
    feature_name_match = re.search(r'FEATURE[_ ]NAME:\s*(.+)', all_content, re.IGNORECASE)
    feature_name = feature_name_match.group(1).strip() if feature_name_match else None

    # Detect project type
    is_existing = feature_name is not None or bool(step_input.get_step_content("create_feature_spec"))

    # Extract Google Docs URLs from each step
    doc1_urls = re.findall(r'https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+(?:/edit)?', doc1_step_content)
    doc2_urls = re.findall(r'https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+(?:/edit)?', doc2_step_content)

    doc1_url = doc1_urls[0] if doc1_urls else "Not found"
    doc2_url = doc2_urls[0] if doc2_urls else "Not found"

    if is_existing:
        doc1_label = "Feature Specification"
        doc2_label = "Technical Document"
    else:
        doc1_label = "Product Requirements Document (PRD)"
        doc2_label = "Architecture Document"

    # Build summary — include the raw step output content directly
    summary_parts = [
        "Documents Created Successfully!",
        f"Project: {project_name}",
    ]
    if feature_name:
        summary_parts.append(f"Feature: {feature_name}")

    summary_parts.extend([
        "",
        f"--- {doc1_label} ---",
        f"URL: {doc1_url}",
        "",
        doc1_step_content,
        "",
        f"--- {doc2_label} ---",
        f"URL: {doc2_url}",
        "",
        doc2_step_content,
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
    """Step 2 (Existing): Validate GitHub repo and read repo structure programmatically.

    Reads the repo file tree, README, and key config files (package.json, etc.)
    so subsequent steps (Feature Spec, Tech Doc) have real codebase context.
    """
    import re
    import json
    from tools.project_tools import get_project
    from services.tool_providers import resolve_tools

    project_id = get_current_project_id()
    project = get_project(project_id)

    github_repo_url = project.get('github_repo_url')
    if not github_repo_url:
        return StepOutput(
            content="⚠️ No GitHub repo URL found for this project. Skipping repo analysis.",
            success=True
        )

    match = re.search(r'github\.com/([^/]+)/([^/]+)', github_repo_url)
    if not match:
        return StepOutput(
            content=f"⚠️ Invalid GitHub URL format: {github_repo_url}. Skipping repo analysis.",
            success=True
        )

    owner, repo = match.groups()
    repo = repo.replace('.git', '')

    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    _log("🔍", "GITHUB-READ", f"Reading repo structure: {owner}/{repo}")

    # Resolve GitHub tools for this user
    github_tools_list = resolve_tools(user_id, "github")
    if not github_tools_list:
        _log("⚠️", "GITHUB-READ", "No GitHub tools available for this user")
        return StepOutput(
            content=f"⚠️ No GitHub credentials found. Repo: {github_repo_url}",
            success=True
        )

    gh = github_tools_list[0]
    context_parts = [f"GITHUB REPOSITORY: {github_repo_url}", f"Owner: {owner}, Repo: {repo}", ""]

    # 1. Validate repo exists
    try:
        repo_info = json.loads(gh.get_repository(owner, repo))
        if repo_info.get("error"):
            _log("⚠️", "GITHUB-READ", f"Repo not accessible: {repo_info.get('message', '')}")
            return StepOutput(
                content=f"⚠️ GitHub repo not accessible: {github_repo_url}\nError: {repo_info.get('message', 'Unknown')}",
                success=True
            )
        context_parts.append(f"Description: {repo_info.get('description', 'N/A')}")
        context_parts.append(f"Default Branch: {repo_info.get('default_branch', 'main')}")
        context_parts.append(f"Language: {repo_info.get('language', 'N/A')}")
        _log("✅", "GITHUB-READ", f"Repo exists. Language: {repo_info.get('language', 'N/A')}")
    except Exception as e:
        _log("⚠️", "GITHUB-READ", f"Error getting repo info: {e}")

    default_branch = repo_info.get('default_branch', 'main') if 'repo_info' in dir() else 'main'

    # 2. List root directory files
    try:
        files_json = gh.list_repository_files(owner, repo, path="", ref=default_branch)
        files = json.loads(files_json)
        if isinstance(files, list):
            context_parts.append("")
            context_parts.append("FILE STRUCTURE (root):")
            for f in files:
                icon = "📁" if f.get("type") == "dir" else "📄"
                context_parts.append(f"  {icon} {f['path']}")
            _log("📁", "GITHUB-READ", f"Found {len(files)} items in root")

            # List contents of common subdirectories (src/, app/, pages/, components/)
            subdirs = [f['path'] for f in files if f.get("type") == "dir" and f['path'] in
                       ("src", "app", "pages", "components", "lib", "public", "api", "styles")]
            for subdir in subdirs[:3]:  # Limit to 3 subdirs to avoid too many API calls
                try:
                    sub_json = gh.list_repository_files(owner, repo, path=subdir, ref=default_branch)
                    sub_files = json.loads(sub_json)
                    if isinstance(sub_files, list):
                        context_parts.append(f"\n  {subdir}/:")
                        for sf in sub_files[:20]:  # Limit to 20 files per subdir
                            icon = "📁" if sf.get("type") == "dir" else "📄"
                            context_parts.append(f"    {icon} {sf['path']}")
                except Exception:
                    pass
    except Exception as e:
        _log("⚠️", "GITHUB-READ", f"Error listing files: {e}")

    # 3. Read key files for tech stack context
    key_files = ["README.md", "package.json", "requirements.txt", "pyproject.toml",
                 "Cargo.toml", "go.mod", "tsconfig.json", "next.config.js", "next.config.ts",
                 "vite.config.ts", "vite.config.js", ".env.example"]

    for key_file in key_files:
        try:
            content = gh.get_file_contents(owner, repo, key_file, ref=default_branch)
            # Skip if it returned an error JSON
            if content.startswith("{") and "error" in content:
                continue
            # Truncate large files
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated)"
            context_parts.append(f"\n--- {key_file} ---")
            context_parts.append(content)
            _log("📄", "GITHUB-READ", f"Read {key_file} ({len(content)} chars)")
        except Exception:
            pass  # File doesn't exist, skip silently

    output = "\n".join(context_parts)
    _log("✅", "GITHUB-READ", f"Repo analysis complete. Context length: {len(output)}")

    return StepOutput(content=output, success=True)


def create_feature_spec_executor(step_input: StepInput) -> StepOutput:
    """Create Feature Spec: Phase 1 agent writes content, Phase 2 saves to Google Docs programmatically."""
    import re
    import asyncio

    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    project_id = get_current_project_id()

    project_name_match = re.search(r'PROJECT_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    feature_name_match = re.search(r'FEATURE_NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    feature_desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?:PROJECT_TYPE:|$)', str(step_input.input), re.IGNORECASE | re.DOTALL)

    project_name = project_name_match.group(1).strip() if project_name_match else "Unknown Project"
    feature_name = feature_name_match.group(1).strip() if feature_name_match else "Unknown Feature"
    feature_description = feature_desc_match.group(1).strip() if feature_desc_match else "No description provided"

    prev_context = step_input.previous_step_content or ""
    project_id_short = project_id[:8] if project_id else "00000000"

    _log("📝", "FEATURE-SPEC-CREATE", f"Starting Feature Spec creation for user_id={user_id}, project_id={project_id}")

    # ---- PHASE 1: Generate Feature Spec content via Product Lead ----
    description = f"""Create a Feature Specification for this existing product.

**CRITICAL: USE THE CONTEXT AND INFORMATION PROVIDED BELOW.**

**CRITICAL — LINK PRESERVATION: The input and context below may contain image URLs, font links, icon CDN links, documentation URLs, API reference links, reference website links, social media links, video URLs, or any other URLs the user provided. You MUST include EVERY SINGLE link/URL in the Feature Spec document EXACTLY as provided. Place them in the USER-PROVIDED LINKS AND ASSETS section AND in the relevant FUNCTIONAL REQUIREMENTS sections. No link may be dropped.**

**PROJECT CONTEXT:**
{prev_context}

Write the Feature Spec starting with the DOCUMENT HEADER:

DOCUMENT TYPE: Feature Specification
PROJECT TYPE: Existing Project
PROJECT ID: {project_id}
PROJECT NAME: {project_name}
FEATURE NAME: {feature_name}
FEATURE DESCRIPTION: {feature_description}

====================================================================================================

Then continue with all Feature Spec sections as per your instructions.

**IMPORTANT: Do NOT call any tools. Just write the complete Feature Specification content. The document will be saved to Google Docs automatically by the system.**

Return ONLY the full Feature Spec content starting with the DOCUMENT HEADER above. Do not include any URLs."""

    _log("🤖", "FEATURE-SPEC-CREATE", "Phase 1: Generating content via Product Lead...")
    result = _run_async(get_product_lead_agent().arun(description, user_id=user_id))
    fs_content = result.content if result and result.content else ""
    _log("✅", "FEATURE-SPEC-CREATE", f"Phase 1 complete. Content length: {len(fs_content)}")
    _log("📄", "FEATURE-SPEC-OUTPUT", f"First 200 chars: {fs_content[:200]}")

    # ---- PHASE 2: Save to Google Docs programmatically ----
    doc_title = f"FeatureSpec_{feature_name.replace(' ', '')}_{project_id_short}"
    doc_url = _save_to_google_docs(
        user_id, "create_feature_spec_document", "FEATURE-SPEC-SAVE",
        title=doc_title, content=fs_content,
        feature_name=feature_name, project_name=project_name
    )

    # Build output
    url_line = f"Feature Spec URL: {doc_url}" if doc_url else "Feature Spec URL: SAVE_FAILED"
    output = f"{url_line}\n\nFEATURE SPEC CONTENT:\n{fs_content}"

    return StepOutput(content=output, success=True)


def create_technical_doc_executor(step_input: StepInput) -> StepOutput:
    """Create Technical Doc: Phase 1 agent writes content, Phase 2 saves to Google Docs programmatically."""
    import re
    import asyncio

    user_id = None
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        user_id = step_input.workflow_session.user_id

    project_id = get_current_project_id()

    # Get feature spec content from previous step
    feature_spec_content = step_input.previous_step_content or ""

    # Get GitHub repo context from validate_github_repo step
    repo_context = step_input.get_step_content("validate_github_repo") or ""

    # Extract feature name and project name
    feature_name_match = re.search(r'FEATURE[_ ]NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)
    project_name_match = re.search(r'PROJECT[_ ]NAME:\s*(.+)', str(step_input.input), re.IGNORECASE)

    feature_name = feature_name_match.group(1).strip() if feature_name_match else "Unknown Feature"
    project_name = project_name_match.group(1).strip() if project_name_match else "Unknown Project"

    project_id_short = project_id[:8] if project_id else "00000000"

    _log("🏗️", "TECH-DOC-CREATE", f"Creating technical doc for feature: {feature_name}")
    _log("🏗️", "TECH-DOC-CREATE", f"Feature Spec input length: {len(feature_spec_content)}")
    _log("🏗️", "TECH-DOC-CREATE", f"Repo context length: {len(repo_context)}")
    _log("🏗️", "TECH-DOC-CREATE", f"Feature Spec first 200 chars: {feature_spec_content[:200]}")

    # ---- PHASE 1: Generate technical document CONTENT via Lead Engineer ----
    description = f"""Create a comprehensive Feature Technical Document based on the Feature Specification AND the existing GitHub repository structure below.

**CRITICAL: READ THE ENTIRE FEATURE SPEC CONTENT AND REPO STRUCTURE BELOW. Your technical document MUST cover the technical implementation for EVERY single requirement, feature, user story, edge case, and detail mentioned in the Feature Spec. Do NOT skip or omit ANY item. Every functional requirement, non-functional requirement, affected component, dependency, and edge case in the Feature Spec must have a corresponding technical implementation detail in your document.**

**CRITICAL — LINK PRESERVATION: The Feature Spec below contains image URLs, font links, icon CDN links, documentation URLs, API reference links, reference website links, social media links, video URLs, and other user-provided URLs. You MUST carry forward EVERY SINGLE link/URL from the Feature Spec into this technical document. Place them in the relevant component/implementation sections where they will be used by the Software Engineer. No link from the Feature Spec may be dropped, summarized, or omitted. The Software Engineer must have every link needed to implement the feature without going back to the Feature Spec.**

**IMPORTANT: Use the EXISTING REPO STRUCTURE to inform your technical decisions. Reference actual files, folders, and tech stack from the repo. Your architecture changes should fit into the existing codebase structure.**

Write the Technical Document starting with the DOCUMENT HEADER:

DOCUMENT TYPE: Feature Technical Document
PROJECT TYPE: Existing Project
PROJECT ID: {project_id}
PROJECT NAME: {project_name}
FEATURE NAME: {feature_name}

====================================================================================================

Then continue with these technical architecture sections:
- TECHNICAL OVERVIEW (how this feature will be implemented)
- ARCHITECTURE CHANGES (what components/modules are affected)
- DATA MODEL CHANGES (database schema changes, new tables/columns)
- API DESIGN (new or modified endpoints, request/response formats)
- COMPONENT DESIGN (frontend components, UI changes, state management)
- IMPLEMENTATION DETAILS (for EACH functional requirement from the Feature Spec, describe the technical approach)
- THIRD-PARTY INTEGRATIONS (any external services, APIs, SDKs needed)
- ERROR HANDLING (for EACH edge case from the Feature Spec, describe technical handling)
- SECURITY CONSIDERATIONS (auth, data protection, input validation)
- TESTING STRATEGY (unit tests, integration tests, test cases for each requirement)
- DEPLOYMENT & MIGRATION (deployment steps, database migrations, rollback plan)

**IMPORTANT: Do NOT call any tools. Just write the complete technical document content. The document will be saved to Google Docs automatically by the system.**

Return ONLY the full technical document content starting with the DOCUMENT HEADER above. Do not include any URLs."""

    # Build the full input with repo context + feature spec
    full_input = description
    if repo_context:
        full_input += f"\n\nEXISTING REPOSITORY STRUCTURE (use this to inform your technical decisions):\n{repo_context}"
    full_input += f"\n\nFEATURE SPECIFICATION CONTENT (you MUST address EVERY item below):\n{feature_spec_content}"

    _log("🤖", "TECH-DOC-CREATE", "Phase 1: Generating content via Lead Engineer...")
    result = _run_async(get_lead_engineer_agent().arun(full_input, user_id=user_id))
    tech_doc_content = result.content if result and result.content else ""
    _log("✅", "TECH-DOC-CREATE", f"Phase 1 complete. Content length: {len(tech_doc_content)}")
    _log("📄", "TECH-DOC-OUTPUT", f"First 200 chars: {tech_doc_content[:200]}")

    # ---- PHASE 2: Save to Google Docs programmatically ----
    doc_title = f"TechDoc_{feature_name.replace(' ', '')}_{project_id_short}"
    doc_url = _save_to_google_docs(
        user_id, "create_document", "TECH-DOC-SAVE",
        title=doc_title, content=tech_doc_content
    )

    # Build output
    url_line = f"Technical Document URL: {doc_url}" if doc_url else "Technical Document URL: SAVE_FAILED"
    output = f"{url_line}\n\nTECHNICAL DOC CONTENT:\n{tech_doc_content}"

    return StepOutput(content=output, success=True)


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

    _log("🤖", "SUPERVISOR", "Calling Supervisor agent (existing)...")
    result = _run_async(get_supervisor_agent().arun(description, user_id=user_id))
    output = result.content if result and result.content else ""
    _log("✅", "SUPERVISOR", f"Supervisor completed. Length: {len(output)}")
    _log("📄", "SUPERVISOR-EXISTING-OUTPUT", f"First 200 chars: {output[:200]}")

    return StepOutput(content=output, success=True)


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
            description="Validate PRD and Architecture"
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
            description="Get project from DB"
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

def route_by_project_type(step_input: StepInput):
    """
    Route to new project or existing project path.

    Returns the actual Steps object (not a string) because Agno's Router
    only accepts Step, list, or Steps — returning a string triggers
    'Router function returned unexpected type: <class 'str'>'.

    Checks for:
    - PROJECT_TYPE: new|existing
    - PROJECT_ID: <uuid> (existing projects have this)
    - Keywords: "new project", "existing project", "add feature"
    """
    content = str(step_input.input).lower()

    # Check for explicit PROJECT_TYPE
    if "project_type: existing" in content or "project_type:existing" in content:
        _log("🔀", "ROUTER", "Route: EXISTING PROJECT PATH")
        return [existing_project_steps]

    if "project_type: new" in content or "project_type:new" in content:
        _log("🔀", "ROUTER", "Route: NEW PROJECT PATH")
        return [new_project_steps]

    # Check for PROJECT_ID (indicates existing project)
    if "project_id:" in content:
        _log("🔀", "ROUTER", "Route: EXISTING PROJECT PATH (project_id found)")
        return [existing_project_steps]

    # Check for keywords
    if any(kw in content for kw in ["add feature", "existing product", "enhance", "update", "modify"]):
        _log("🔀", "ROUTER", "Route: EXISTING PROJECT PATH (keywords)")
        return [existing_project_steps]

    # Default to new project
    _log("🔀", "ROUTER", "Route: NEW PROJECT PATH (default)")
    return [new_project_steps]


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

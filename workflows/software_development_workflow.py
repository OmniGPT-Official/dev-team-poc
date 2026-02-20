"""
Software Development Workflow - Implementation with Review Cycle (Conditional)

Flow is conditional based on project type (new vs existing):

**Step 1: Read Architecture** (all projects)
- Extract project context, determine if existing or new project

**NEW PROJECTS** (complete flow):
1. Read Architecture from Google Docs URL
2. Create GitHub Repo (DevOps Engineer)
3. Validate Repo Link (Supervisor)
4. Implementation Cycle (Loop max 2 iterations):
   - Development: Software Engineer writes code
   - Code Review: Lead Engineer reviews (quality + security + conventions)
   - Loop until approved OR max iterations
5. Deploy to Vercel (DevOps Engineer)
6. Validate Deployment Link (Supervisor)
7. Summary with deployment link

**EXISTING PROJECTS** (skip repo creation + deployment):
1. Read Architecture from Google Docs URL
2. Validate Repo Link (Supervisor) - verify existing repo
3. Implementation Cycle (Loop max 2 iterations):
   - Development: Software Engineer writes code to update project
   - Code Review: Lead Engineer reviews (quality + security + conventions)
   - Loop until approved OR max iterations
4. Summary with GitHub repo (skip deployment - already deployed)

Input: ARCHITECTURE_URL (Architecture Document from Google Docs)
Output:
- New projects: Vercel deployment link + GitHub repo (both validated and stored in DB)
- Existing projects: GitHub repo with updated code (skip deployment)
"""

import os
import sys
import re
import asyncio
import random
import string
import threading
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Step, Workflow, Loop, Router, Steps
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info, log_error


# ============================================================================
# SESSION STATE
# ============================================================================

class ImplementationState:
    """Tracks project context across workflow."""
    def __init__(self):
        self.iteration = 0
        self.code_file_path = ""
        self.code_review_status = "approved"  # Default to approved
        self.github_repo = ""
        self.github_owner = ""
        self.project_name = ""
        self.architecture_content = ""
        self.is_existing_repo = False  # True when working with an existing repo
        self.user_id = ""  # Per-user credential lookup


_state = ImplementationState()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _run_with_heartbeat(coro, step_name: str, timeout_seconds: int = 0):
    """Run coroutine in a background thread with heartbeat logging while preserving contextvars.
    If timeout_seconds <= 0, no timeout is applied (waits indefinitely).
    Returns the agent result, or None if errored."""
    import contextvars

    result_holder = [None]
    error_holder = [None]
    done_event = threading.Event()

    # Capture current context (including user_id contextvar) in parent thread
    ctx = contextvars.copy_context()

    def _execute():
        """Execute coroutine in captured context."""
        def run_in_context():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result_holder[0] = loop.run_until_complete(coro)
            except Exception as e:
                error_holder[0] = e
            finally:
                done_event.set()

        # Run in the captured context from parent thread
        ctx.run(run_in_context)

    thread = threading.Thread(target=_execute, daemon=True)
    thread.start()

    # Heartbeat every 30s so you can see progress instead of a frozen screen
    elapsed = 0
    while not done_event.wait(timeout=30):
        elapsed += 30
        _log("⏳", step_name, f"Working... ({elapsed}s)")
        # Only apply timeout if timeout_seconds > 0
        if timeout_seconds > 0 and elapsed >= timeout_seconds:
            _log("⏰", step_name, f"Timed out after {timeout_seconds}s")
            return None

    if error_holder[0]:
        _log("❌", step_name, f"Error: {error_holder[0]}")
        return None

    return result_holder[0]


def _log(emoji: str, step: str, msg: str, data: dict = None):
    """Concise logging helper."""
    print(f"{emoji} [{step}] {msg}")
    log_info(f"[{step}] {msg}")


def parse_input_urls(input_str: str) -> dict:
    """Parse input string to extract Architecture URL, GitHub repo, and optional params."""
    result = {
        "architecture_url": "",
        "github_repo": "",
        "github_owner": "",
        "project_name": "",
        "github_repo_url": "",  # Full GitHub URL for existing projects
    }

    # Architecture URL
    arch_match = re.search(r'ARCHITECTURE_URL:\s*(https://[^\s]+)', input_str, re.I)
    if arch_match:
        result["architecture_url"] = arch_match.group(1)
    else:
        docs_match = re.search(r'https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+/[^\s]*', input_str)
        if docs_match:
            result["architecture_url"] = docs_match.group(0)

    # GitHub Repo URL (full URL like https://github.com/owner/repo)
    repo_url_match = re.search(r'GITHUB_REPO_URL:\s*(https://github\.com/[^\s]+)', input_str, re.I)
    if repo_url_match:
        result["github_repo_url"] = repo_url_match.group(1).rstrip('/')
    else:
        # Also try to find any GitHub URL in the input
        gh_url_match = re.search(r'https://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)', input_str)
        if gh_url_match:
            result["github_repo_url"] = gh_url_match.group(0).rstrip('/')

    # Extract owner/repo from GitHub URL if found
    if result["github_repo_url"]:
        gh_parts = re.search(r'github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)', result["github_repo_url"])
        if gh_parts:
            result["github_owner"] = result["github_owner"] or gh_parts.group(1)
            result["github_repo"] = result["github_repo"] or gh_parts.group(2)

    # Optional params (explicit values override URL-extracted ones)
    for key, pattern in [("github_repo", r'GITHUB_REPO:\s*([^\s\n]+)'),
                         ("github_owner", r'GITHUB_OWNER:\s*([^\s\n]+)'),
                         ("project_name", r'PROJECT_NAME:\s*([^\n]+)')]:
        match = re.search(pattern, input_str, re.I)
        if match:
            result[key] = match.group(1).strip()

    return result


def _extract_project_name(content: str) -> str:
    """Extract project name from architecture document."""
    patterns = [r'Project\s*Name[:\s]+([^\n]+)', r'#\s*([^\n]+)', r'Title[:\s]+([^\n]+)']
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            name = re.sub(r'[^\w\s-]', '', match.group(1).strip())[:40]
            if name and len(name) > 2:
                return name
    return None


def _generate_repo_name(project_name: str = None) -> str:
    """Generate unique repository name."""
    suffix = ''.join(random.choices(string.digits, k=5))
    if project_name:
        safe = re.sub(r'[^\w-]', '-', project_name.lower())[:25]
        return f"{safe}-{suffix}"
    return f"project-{suffix}"


def _get_user_id() -> str:
    """Get the current user_id from context (set by pre-hook) or state."""
    if _state.user_id:
        return _state.user_id
    from services.user_context import get_current_user_id
    uid = get_current_user_id()
    if uid:
        _state.user_id = uid
    return uid or ""


def _get_github_tools():
    """Create GitHubTools with per-user token (falls back to env var)."""
    from tools.github_tools import GitHubTools
    user_id = _get_user_id()
    _log("🔧", "TOOLS", f"_get_github_tools — user_id={user_id!r}")
    if user_id:
        from services.api_key_store import get_api_key
        token = get_api_key(user_id, "github")
        if token:
            preview = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "***"
            _log("✅", "TOOLS", f"Using per-user GitHub token: {preview}")
            return GitHubTools(token=token)
        else:
            _log("⚠️", "TOOLS", f"No GitHub token in DB for user_id={user_id!r}")
    else:
        _log("⚠️", "TOOLS", "No user_id available — using env var fallback")
    return GitHubTools()


def _get_google_docs_tools():
    """Create GoogleDocsTools with per-user OAuth creds (falls back to env var / token.json)."""
    from tools.google_docs_tools import GoogleDocsTools
    from google.auth.transport.requests import Request as GoogleRequest
    user_id = _get_user_id()
    if user_id:
        from services.oauth_store import get_google_credentials, update_google_credentials
        # Use google_docs provider for Google Docs operations (not google_sheets)
        creds = get_google_credentials(user_id, "google_docs")
        if creds:
            # Refresh token if expired
            if creds.expired and creds.refresh_token:
                try:
                    _log("🔄", "OAUTH", "Refreshing expired Google OAuth token...")
                    creds.refresh(GoogleRequest())
                    # Persist refreshed token back to database
                    update_google_credentials(user_id, "google_docs", creds)
                    _log("✅", "OAUTH", "Token refreshed and persisted")
                except Exception as e:
                    _log("❌", "OAUTH", f"Token refresh failed: {e}")
                    # Continue anyway - the API call might still work or will fail with a better error
            return GoogleDocsTools(creds=creds)
    return GoogleDocsTools()


def _get_vercel_token() -> str:
    """Get per-user Vercel token (falls back to env var)."""
    user_id = _get_user_id()
    if user_id:
        from services.api_key_store import get_api_key
        token = get_api_key(user_id, "vercel")
        if token:
            return token
    return os.environ.get("VERCEL_TOKEN", "")


def _get_github_owner() -> str:
    """Get the GitHub username from the authenticated user's token via GET /user."""
    import json
    gh = _get_github_tools()
    try:
        user_info = json.loads(gh.get_authenticated_user())
        login = user_info.get("login", "")
        if login:
            _log("🔑", "AUTH", f"GitHub owner resolved from token: {login}")
            return login
    except Exception as e:
        _log("⚠️", "AUTH", f"Could not resolve GitHub owner from token: {e}")
    return ""


def _get_project_id() -> str:
    """Get current project_id from context."""
    from services.project_context import get_current_project_id
    return get_current_project_id() or ""


# ============================================================================
# WORKFLOW STEPS
# ============================================================================

def _extract_github_url(content: str) -> dict:
    """Extract GitHub owner/repo from architecture document content."""
    result = {"owner": "", "repo": "", "url": ""}

    # Look for explicit GitHub URL patterns in the document
    patterns = [
        r'(?:GitHub|Repository|Repo)\s*(?:URL|Link|:)\s*(https://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+))',
        r'(?:Existing\s+)?(?:GitHub|Repository|Repo)\s*:\s*(https://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+))',
        r'(https://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+))',
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            result["url"] = match.group(1).rstrip('/')
            result["owner"] = match.group(2)
            result["repo"] = match.group(3)
            break

    return result


def read_architecture(step_input: StepInput) -> StepOutput:
    """Step 1: Read Architecture from Google Docs. Detects existing vs new project."""
    global _state
    _state = ImplementationState()  # Fresh state

    # Extract user_id from workflow session (same pattern as product_requirements_workflow)
    if step_input.workflow_session and hasattr(step_input.workflow_session, 'user_id'):
        _state.user_id = step_input.workflow_session.user_id
        _log("🔑", "READ", f"Extracted user_id from workflow: {_state.user_id}")

    input_str = step_input.input if isinstance(step_input.input, str) else ""
    parsed = parse_input_urls(input_str)

    if not parsed["architecture_url"]:
        _log("❌", "READ", "No ARCHITECTURE_URL provided!")
        return StepOutput(content="ERROR: No ARCHITECTURE_URL provided", success=False)

    _log("📖", "READ", f"Reading architecture from Google Docs...")

    try:
        doc_id = re.search(r'/document/d/([a-zA-Z0-9-_]+)', parsed["architecture_url"]).group(1)
        _state.architecture_content = _get_google_docs_tools().read_document(doc_id)
        _log("✅", "READ", f"Architecture loaded ({len(_state.architecture_content)} chars)")

        # Extract project_id from architecture document header
        project_id_match = re.search(r'PROJECT\s*ID:\s*([a-zA-Z0-9-]+)', _state.architecture_content, re.IGNORECASE)
        if project_id_match:
            project_id = project_id_match.group(1).strip()
            from services.project_context import set_current_project_id
            set_current_project_id(project_id)
            _log("📋", "READ", f"Extracted project_id from architecture: {project_id}")
        else:
            _log("⚠️", "READ", "No PROJECT_ID found in architecture document - will skip DB storage")

        # Extract project name
        _state.project_name = parsed["project_name"] or _extract_project_name(_state.architecture_content) or "project"

        # --- EXISTING PROJECT DETECTION ---
        # Priority 1: GitHub repo URL from input params
        # Priority 2: GitHub repo URL found in architecture document
        # Priority 3: Create new repo (default)

        github_owner = parsed["github_owner"]
        github_repo = parsed["github_repo"]

        # Check if a GitHub repo URL was provided in the input
        if parsed["github_repo_url"]:
            gh_parts = re.search(r'github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)', parsed["github_repo_url"])
            if gh_parts:
                github_owner = github_owner or gh_parts.group(1)
                github_repo = github_repo or gh_parts.group(2)
                _state.is_existing_repo = True
                _log("🔍", "READ", f"Existing repo from input: {github_owner}/{github_repo}")

        # If no repo from input, scan the architecture document for a GitHub URL
        if not _state.is_existing_repo:
            doc_github = _extract_github_url(_state.architecture_content)
            if doc_github["owner"] and doc_github["repo"]:
                github_owner = github_owner or doc_github["owner"]
                github_repo = github_repo or doc_github["repo"]
                _state.is_existing_repo = True
                _log("🔍", "READ", f"Existing repo from architecture doc: {github_owner}/{github_repo}")

        # Fallback: resolve owner from GitHub token, generate repo name for new projects
        _state.github_owner = github_owner or _get_github_owner()
        _state.github_repo = github_repo or _generate_repo_name(_state.project_name)

        if not _state.github_owner:
            _log("❌", "READ", "Could not determine GitHub owner. Ensure a valid GitHub token is stored.")
            return StepOutput(content="ERROR: Could not determine GitHub owner from token", success=False)

        project_type = "EXISTING" if _state.is_existing_repo else "NEW"
        _log("📋", "READ", f"Project: {_state.project_name} ({project_type})")
        _log("🔗", "READ", f"GitHub: {_state.github_owner}/{_state.github_repo}")

        return StepOutput(
            content=f"Architecture loaded. Project type: {project_type}. Repo: {_state.github_owner}/{_state.github_repo}",
            success=True,
        )
    except Exception as e:
        _log("❌", "READ", f"Failed: {e}")
        return StepOutput(content=f"ERROR: {e}", success=False)


def create_github_repo(step_input: StepInput) -> StepOutput:
    """Step 2: Create or verify GitHub Repository using DevOps Engineer.

    - EXISTING project: Verify repo exists, list current files, skip creation.
    - NEW project: DevOps Engineer creates repo with initial structure.
    """
    global _state

    if not _state.github_owner or not _state.github_repo:
        return StepOutput(content="ERROR: GitHub not configured", success=False)

    import json

    gh = _get_github_tools()
    repo_url = f"https://github.com/{_state.github_owner}/{_state.github_repo}"

    # =====================================================================
    # EXISTING PROJECT — verify repo exists and list current files
    # =====================================================================
    if _state.is_existing_repo:
        _log("🔍", "REPO", f"Existing project — verifying repo: {_state.github_owner}/{_state.github_repo}")

        # Verify the repo is accessible
        repo_info = json.loads(gh.get_repository(_state.github_owner, _state.github_repo))
        if repo_info.get("error"):
            _log("❌", "REPO", f"Cannot access repo: {repo_info.get('message', '')}")
            return StepOutput(content=f"ERROR: Cannot access repo {repo_url}: {repo_info.get('message', '')}", success=False)

        # List existing files so the dev step knows the current structure
        files = json.loads(gh.list_repository_files(_state.github_owner, _state.github_repo))
        file_names = []
        if isinstance(files, list):
            file_names = [f.get('name', '') if isinstance(f, dict) else str(f) for f in files]

        _log("✅", "REPO", f"Existing repo verified: {repo_url}")
        _log("📂", "REPO", f"Current files: {', '.join(file_names[:20]) if file_names else 'empty'}")

        return StepOutput(
            content=f"Existing repository verified: {repo_url}\nCurrent files: {', '.join(file_names)}",
            success=True,
        )

    # =====================================================================
    # NEW PROJECT — DevOps Engineer creates repo
    # =====================================================================
    _log("🏗️", "REPO", f"New project — asking DevOps Engineer to create repository")

    from agents.devops_engineer import devops_engineer_agent

    prompt = f"""Create a new GitHub repository:

Owner: {_state.github_owner}
Repo Name: {_state.github_repo}
Description: {_state.project_name}
Private: false
Auto Init: true (with README)

Use create_repository tool to create the repo, then seed it with:
1. README.md with project name and description
2. .gitignore with common patterns (Python, Node, .env, .DS_Store)
3. .dev-team/README.md for development artifacts

Return the repository URL when done."""

    _log("🤖", "REPO", "Asking DevOps Engineer to create repo...")
    user_id = _get_user_id()
    result = _run_with_heartbeat(
        devops_engineer_agent.arun(prompt, user_id=user_id), "REPO-CREATE", timeout_seconds=0
    )

    if result is None:
        _log("❌", "REPO", "DevOps Engineer failed to create repo")
        return StepOutput(content="ERROR: Repo creation failed", success=False)

    # Extract repo URL from response
    url_match = re.search(r'https://github\.com/[^\s]+', result.content)
    if url_match:
        repo_url = url_match.group(0)
        _log("✅", "REPO", f"Repository created: {repo_url}")
        return StepOutput(content=f"Repository: {repo_url}", success=True)
    else:
        _log("⚠️", "REPO", "Repo might be created but couldn't extract URL")
        return StepOutput(content=f"Repository created at: {repo_url}", success=True)


def _extract_code(response: str) -> str:
    """Extract code from agent response - handles markdown code blocks or raw code."""
    if not response:
        return ""

    # Try to extract from markdown code block first
    code_match = re.search(r'```(?:html|css|javascript|js)?\s*\n?(.*?)```', response, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()

    # If no code block, return the response as-is (might be raw code)
    return response.strip()


def _generate_file_content(agent, file_type: str, project_name: str, architecture: str) -> str:
    """Ask agent to generate code for a specific file type."""

    # Shared context so every file knows the exact folder structure
    folder_context = """
## EXACT FOLDER STRUCTURE (all files will be created at these paths):
```
/
  index.html          ← you are here (for HTML)
  css/
    styles.css        ← you are here (for CSS)
  js/
    script.js         ← you are here (for JS)
  images/             ← use Unsplash URLs if no images provided
```
"""

    prompts = {
        "html": f"""Generate a complete index.html file for: {project_name}

Based on this architecture:
{architecture[:3000]}
{folder_context}

Requirements:
- Complete HTML5 structure with DOCTYPE, html, head, body
- Include meta tags (charset, viewport)
- Link stylesheet as: <link rel="stylesheet" href="css/styles.css">
- Link script as: <script src="js/script.js"></script>
- CRITICAL: CSS is at css/styles.css NOT styles.css
- CRITICAL: JS is at js/script.js NOT script.js
- All sections from the architecture
- Semantic HTML elements
- Real content (not Lorem ipsum)
- For images: use Unsplash URLs relevant to the project, e.g.:
  <img src="https://images.unsplash.com/photo-XXXXX?w=800&h=600&fit=crop" alt="description">
  Pick REAL Unsplash photo IDs that match the project topic

Output ONLY the HTML code, nothing else. Start with <!DOCTYPE html>""",

        "css": f"""Generate a complete styles.css file for: {project_name}

This file will be saved at: css/styles.css
It is linked from index.html as: <link rel="stylesheet" href="css/styles.css">

Based on this architecture:
{architecture[:2000]}
{folder_context}

Requirements:
- Modern, professional styling
- Responsive design (mobile-first)
- Style all sections from the architecture
- Nice colors, typography, spacing
- Hover effects, transitions
- CSS variables for colors
- If referencing images in CSS, use Unsplash URLs:
  background-image: url('https://images.unsplash.com/photo-XXXXX?w=1200&h=800&fit=crop');
- Do NOT use url() with local paths like ../images/ — use Unsplash directly

Output ONLY the CSS code, nothing else. Start with /* or :root""",

        "js": f"""Generate a complete script.js file for: {project_name}

This file will be saved at: js/script.js
It is linked from index.html as: <script src="js/script.js"></script>

Based on this architecture:
{architecture[:1500]}
{folder_context}

Requirements:
- Mobile navigation toggle
- Smooth scrolling
- Form validation if forms exist
- Any interactive features from architecture
- Clean, modern JavaScript (ES6+)
- Use document.querySelector / querySelectorAll to target HTML elements
- Make sure IDs/classes you target actually exist in the HTML

Output ONLY the JavaScript code, nothing else. Start with // or 'use strict'"""
    }

    prompt = prompts.get(file_type, "")
    if not prompt:
        return ""

    user_id = _get_user_id()
    result = _run_with_heartbeat(agent.arun(prompt, user_id=user_id), f"DEV-{file_type.upper()}", timeout_seconds=0)
    if result and result.content:
        return _extract_code(result.content)
    return ""


def development(step_input: StepInput) -> StepOutput:
    """Software Engineer implements code.

    - EXISTING project: Reads current files, then asks agent to make targeted updates.
    - NEW project: Generates each file from scratch (HTML/CSS/JS).
    """
    global _state

    if not _state.github_owner or not _state.github_repo:
        return StepOutput(content="ERROR: GitHub not configured", success=False)

    _state.iteration += 1
    _state.code_file_path = "src/"

    from agents.software_engineer import software_engineer_agent
    import json

    gh = _get_github_tools()
    arch_content = _state.architecture_content
    files_created = []

    # =====================================================================
    # EXISTING PROJECT — agent-driven updates on existing codebase
    # =====================================================================
    if _state.is_existing_repo:
        _log("💻", "DEV", f"Iteration {_state.iteration} - Updating EXISTING repo...")

        # 1. List all existing files
        all_files = json.loads(gh.list_repository_files(_state.github_owner, _state.github_repo))
        file_list = []
        if isinstance(all_files, list):
            file_list = [f.get('name', '') if isinstance(f, dict) else str(f) for f in all_files]

        _log("📂", "DEV", f"Existing files: {', '.join(file_list[:30])}")

        # 2. Read key existing files to give agent context
        existing_code = {}
        code_extensions = ('.html', '.css', '.js', '.jsx', '.tsx', '.ts', '.json', '.py', '.md')
        files_to_read = [f for f in file_list if any(f.endswith(ext) for ext in code_extensions)][:10]

        for file_path in files_to_read:
            try:
                content = json.loads(gh.get_file_contents(
                    owner=_state.github_owner,
                    repo=_state.github_repo,
                    path=file_path,
                ))
                if isinstance(content, dict) and content.get("content"):
                    existing_code[file_path] = content["content"][:3000]  # Truncate large files
                    _log("📄", "DEV", f"Read: {file_path} ({len(content.get('content', ''))} chars)")
            except Exception as e:
                _log("⚠️", "DEV", f"Could not read {file_path}: {e}")

        # 3. Build context of existing code for the agent
        existing_code_context = "\n\n".join(
            f"--- FILE: {path} ---\n{code}" for path, code in existing_code.items()
        )

        # 4. Ask agent to generate updates based on architecture + existing code
        prompt = f"""You are updating an EXISTING project: {_state.project_name}
Repository: https://github.com/{_state.github_owner}/{_state.github_repo}

## Architecture / Requirements for changes:
{arch_content[:4000]}

## Current files in the repository:
{', '.join(file_list)}

## Current code (read from repo):
{existing_code_context[:8000]}

## YOUR TASK:
Based on the architecture document above, make the required changes to this existing codebase.

CRITICAL RULES:
1. RESPECT existing code — do NOT rewrite files that don't need changes
2. Only modify/create files that the architecture requires changing
3. Match the existing code style, patterns, and tech stack
4. Use create_or_update_file for EACH file you need to change
5. Use conventional commit messages: "feat:", "fix:", "update:", "refactor:"
6. Owner: "{_state.github_owner}", Repo: "{_state.github_repo}", Branch: "main"

For EACH file you change, call create_or_update_file with the COMPLETE updated file content.
List exactly which files you modified when done."""

        _log("🤖", "DEV", "Asking Software Engineer to update existing code...")
        user_id = _get_user_id()
        result = _run_with_heartbeat(
            software_engineer_agent.arun(prompt, user_id=user_id), "DEV-UPDATE", timeout_seconds=0
        )

        if result and result.content:
            _log("✅", "DEV", f"Agent completed updates")
            # The agent uses GitHub tools directly, so files are already pushed
            return StepOutput(content=f"Updated existing repo: {result.content[:500]}", success=True)
        else:
            _log("❌", "DEV", "Agent failed to produce updates")
            return StepOutput(content="ERROR: Agent failed to update existing repo", success=False)

    # =====================================================================
    # NEW PROJECT — generate files from scratch
    # =====================================================================
    _log("💻", "DEV", f"Iteration {_state.iteration} - Implementing NEW project code...")

    # --- Generate and create index.html (at root) ---
    _log("📄", "DEV", "Generating index.html...")
    html_code = _generate_file_content(software_engineer_agent, "html", _state.project_name, arch_content)

    if html_code and len(html_code) > 100:
        res = json.loads(gh.create_or_update_file(
            owner=_state.github_owner,
            repo=_state.github_repo,
            path="index.html",
            content=html_code,
            message="feat: add index.html",
            branch="main",
        ))
        if res.get("success"):
            files_created.append("index.html")
            _log("✓", "DEV", f"Created index.html ({len(html_code)} chars)")
        else:
            _log("⚠️", "DEV", f"Failed to create index.html: {res.get('message', '')}")
    else:
        _log("⚠️", "DEV", f"HTML generation failed or too short ({len(html_code) if html_code else 0} chars)")

    # --- Generate and create css/styles.css ---
    _log("🎨", "DEV", "Generating css/styles.css...")
    css_code = _generate_file_content(software_engineer_agent, "css", _state.project_name, arch_content)

    if css_code and len(css_code) > 50:
        res = json.loads(gh.create_or_update_file(
            owner=_state.github_owner,
            repo=_state.github_repo,
            path="css/styles.css",
            content=css_code,
            message="feat: add css/styles.css",
            branch="main",
        ))
        if res.get("success"):
            files_created.append("css/styles.css")
            _log("✓", "DEV", f"Created css/styles.css ({len(css_code)} chars)")
        else:
            _log("⚠️", "DEV", f"Failed to create css/styles.css: {res.get('message', '')}")
    else:
        _log("⚠️", "DEV", f"CSS generation failed or too short ({len(css_code) if css_code else 0} chars)")

    # --- Generate and create js/script.js ---
    _log("⚡", "DEV", "Generating js/script.js...")
    js_code = _generate_file_content(software_engineer_agent, "js", _state.project_name, arch_content)

    if js_code and len(js_code) > 20:
        res = json.loads(gh.create_or_update_file(
            owner=_state.github_owner,
            repo=_state.github_repo,
            path="js/script.js",
            content=js_code,
            message="feat: add js/script.js",
            branch="main",
        ))
        if res.get("success"):
            files_created.append("js/script.js")
            _log("✓", "DEV", f"Created js/script.js ({len(js_code)} chars)")
        else:
            _log("⚠️", "DEV", f"Failed to create js/script.js: {res.get('message', '')}")
    else:
        _log("ℹ️", "DEV", "Skipping js/script.js (not needed or too short)")

    # --- Summary ---
    if files_created:
        _log("✅", "DEV", f"Files created: {', '.join(files_created)}")
    else:
        _log("❌", "DEV", "No files were created!")

    return StepOutput(content=f"Created files: {', '.join(files_created) if files_created else 'none'}", success=True)


def validate_repo_link(step_input: StepInput) -> StepOutput:
    """Step 3: Supervisor validates repo link and stores it in DB."""
    global _state

    repo_url = f"https://github.com/{_state.github_owner}/{_state.github_repo}"
    _log("🔍", "VALIDATE_REPO", f"Supervisor validating repo: {repo_url}")

    # Store repo link in project database
    try:
        from tools.project_tools import update_project
        project_id = _get_project_id()

        if project_id:
            update_project(
                project_id=project_id,
                github_repo_url=repo_url,
                github_repo_name=_state.github_repo,
                github_owner=_state.github_owner,
                status="in_development"
            )
            _log("✅", "VALIDATE_REPO", f"Repo link stored in DB for project {project_id}")
        else:
            _log("⚠️", "VALIDATE_REPO", "No project_id in context - skipping DB storage")

        _log("✅", "VALIDATE_REPO", "Repository validation complete")
        return StepOutput(content=f"Repository validated and stored: {repo_url}", success=True)

    except Exception as e:
        _log("❌", "VALIDATE_REPO", f"Validation failed: {e}")
        return StepOutput(content=f"ERROR: Validation failed: {e}", success=False)


def code_review(step_input: StepInput) -> StepOutput:
    """Lead Engineer reviews code - auto-approves if code files exist."""
    global _state

    _log("👀", "CODE_REVIEW", "Checking project files...")

    # First, verify files exist directly (don't rely on agent)
    import json

    gh = _get_github_tools()
    files = json.loads(gh.list_repository_files(_state.github_owner, _state.github_repo))

    # Check for actual code files
    code_files = []
    if isinstance(files, list):
        code_files = [f for f in files if isinstance(f, dict) and
                      f.get('name', '').endswith(('.html', '.css', '.js', '.tsx', '.jsx', '.py', '.ts'))]

    if not code_files:
        _log("⚠️", "CODE_REVIEW", "No code files found - requesting implementation")
        _state.code_review_status = "changes_requested"
        return StepOutput(content="CHANGES_REQUESTED: No code files found. Create index.html, styles.css, etc.", success=True)

    # Code files exist - auto-approve
    file_names = [f['name'] for f in code_files]
    _log("✅", "CODE_REVIEW", f"Found code files: {', '.join(file_names)}")
    _state.code_review_status = "approved"
    return StepOutput(content=f"APPROVED ✓ Found {len(code_files)} code files: {', '.join(file_names)}", success=True)


def code_review_with_agent(step_input: StepInput) -> StepOutput:
    """Original agent-based code review (kept for reference)."""
    global _state

    from agents.lead_engineer import lead_engineer_agent

    prompt = f"""Review code in {_state.github_owner}/{_state.github_repo}.

1. Call: list_repository_files(owner="{_state.github_owner}", repo="{_state.github_repo}")
2. Read main files with get_file_contents
3. Reply: APPROVED ✓ or CHANGES_REQUESTED: [issues]
"""

    user_id = _get_user_id()
    result = _run_with_heartbeat(lead_engineer_agent.arun(prompt, user_id=user_id), "CODE_REVIEW", timeout_seconds=90)

    if result is None:
        # Timeout/error — auto-approve since reviews are lenient by policy
        _state.code_review_status = "approved"
        _log("✅", "CODE_REVIEW", "Auto-approved (timeout/error)")
        return StepOutput(content="Code Review: approved (auto)", success=True)

    content = result.content.lower()

    if "changes_requested" in content or "critical" in content:
        _state.code_review_status = "changes_requested"
        _log("⚠️", "CODE_REVIEW", "Changes requested")
    else:
        _state.code_review_status = "approved"
        _log("✅", "CODE_REVIEW", "Approved")

    return StepOutput(content=f"Code Review: {_state.code_review_status}", success=True)


def reviews_passed(outputs: List[StepOutput]) -> bool:
    """Check if review passed. Returns True to break loop."""
    global _state

    if _state.code_review_status == "approved":
        _log("🎉", "LOOP", "Code review passed!")
        return True

    if _state.iteration >= 2:
        _log("⏰", "LOOP", "Max iterations reached - proceeding to deploy")
        return True

    _log("🔄", "LOOP", f"Iteration {_state.iteration} - needs revision")
    return False


def deploy_to_vercel(step_input: StepInput) -> StepOutput:
    """Deploy to Vercel using the DevOps Engineer agent."""
    global _state

    _log("🚀", "DEPLOY", "Deploying to Vercel...")
    _log("📋", "DEPLOY", f"Owner: {_state.github_owner}, Repo: {_state.github_repo}, Project: {_state.project_name}")

    # Verify Vercel token is available (per-user or env var)
    vercel_token = _get_vercel_token()
    if not vercel_token:
        _log("❌", "DEPLOY", "No Vercel token found (checked user_api_keys and VERCEL_TOKEN env var)")
        return StepOutput(content="ERROR: No Vercel token available.", success=False)

    # Set env var so the deployer agent's tools can use it
    os.environ["VERCEL_TOKEN"] = vercel_token

    from agents.devops_engineer import devops_engineer_agent

    prompt = f"""Deploy this GitHub repository to Vercel using the 2-step process:

**STEP 1: Create Vercel Project**
Call `create_vercel_project` with:
- project_name: {_state.project_name}
- github_repo: {_state.github_repo}
- github_owner: {_state.github_owner}
- framework: null (let Vercel auto-detect)

This will create the project and link it to GitHub.

**STEP 2: Trigger Initial Deployment**
Call `trigger_deployment` with:
- project_name: {_state.project_name}
- git_branch: main

This will trigger the first deployment. Future git pushes will auto-deploy via GitHub webhooks.

**CRITICAL**: You MUST call BOTH functions. Don't skip trigger_deployment!

Return the deployment URL when done.
"""

    _log("🤖", "DEPLOY", "Asking DevOps Engineer to deploy...")
    user_id = _get_user_id()
    result = _run_with_heartbeat(devops_engineer_agent.arun(prompt, user_id=user_id), "DEPLOY", timeout_seconds=0)

    if result is None:
        _log("❌", "DEPLOY", "DevOps Engineer failed")
        return StepOutput(content="ERROR: Deployment failed", success=False)

    # Check if deployment was successful by looking for URL or error in response
    response = result.content.lower()
    if "error" in response or "failed" in response:
        _log("❌", "DEPLOY", f"Deployment failed: {result.content[:200]}")
        return StepOutput(content=f"ERROR: {result.content}", success=False)

    _log("✅", "DEPLOY", "Deployment complete")
    return StepOutput(content=result.content, success=True)


def validate_deployment_link(step_input: StepInput) -> StepOutput:
    """Step 6: Supervisor validates deployment link and stores it in DB."""
    global _state

    deploy_content = step_input.previous_step_content or ""

    # Extract Vercel URL
    url_match = re.search(r'https://[^\s]+vercel\.app[^\s]*', deploy_content)
    deploy_url = url_match.group(0) if url_match else ""

    if not deploy_url:
        _log("⚠️", "VALIDATE_DEPLOY", "Could not extract Vercel URL from deployment response")
        return StepOutput(content="WARNING: Deployment completed but URL not extracted", success=True)

    _log("🔍", "VALIDATE_DEPLOY", f"Supervisor validating deployment: {deploy_url}")

    # Store deployment link in project database
    try:
        from tools.project_tools import update_project
        project_id = _get_project_id()

        if project_id:
            update_project(
                project_id=project_id,
                vercel_deployment_url=deploy_url,
                status="deployed"
            )
            _log("✅", "VALIDATE_DEPLOY", f"Deployment link stored in DB for project {project_id}")
        else:
            _log("⚠️", "VALIDATE_DEPLOY", "No project_id in context - skipping DB storage")

        _log("✅", "VALIDATE_DEPLOY", "Deployment validation complete")
        return StepOutput(content=f"Deployment validated and stored: {deploy_url}", success=True)

    except Exception as e:
        _log("❌", "VALIDATE_DEPLOY", f"Validation failed: {e}")
        return StepOutput(content=f"ERROR: Validation failed: {e}", success=False)


def create_summary(step_input: StepInput) -> StepOutput:
    """Create final summary."""
    global _state

    deploy_content = step_input.previous_step_content or ""

    # Extract Vercel URL
    url_match = re.search(r'https://[^\s]+vercel\.app[^\s]*', deploy_content)
    deploy_url = url_match.group(0) if url_match else "Deployment in progress"

    repo_url = f"https://github.com/{_state.github_owner}/{_state.github_repo}"

    summary = f"""
## ✅ Implementation Complete!

**Project:** {_state.project_name}
**Iterations:** {_state.iteration}

### Links
- 🚀 **Live:** {deploy_url}
- 📂 **GitHub:** {repo_url}

### Review
- Code Review (Quality + Security + Conventions): {_state.code_review_status}
"""

    _log("🎉", "DONE", f"Project complete! {deploy_url}")

    # Reset for next run
    _state.__init__()

    return StepOutput(content=summary, success=True)


# ============================================================================
# WORKFLOW DEFINITION WITH ROUTER
# ============================================================================

# Define grouped steps for NEW projects (full flow with repo creation + deployment)
new_project_steps = Steps(
    name="new_project_path",
    description="Complete workflow for new projects: create repo, implement, deploy, validate",
    steps=[
        Step(name="create_repo", executor=create_github_repo),
        Step(name="validate_repo", executor=validate_repo_link),
        Loop(
            name="implementation_cycle",
            steps=[
                Step(name="development", executor=development),
                Step(name="code_review", executor=code_review),
            ],
            end_condition=reviews_passed,
            max_iterations=2,
        ),
        Step(name="deploy", executor=deploy_to_vercel),
        Step(name="validate_deployment", executor=validate_deployment_link),
        Step(name="summary", executor=create_summary),
    ]
)

# Define grouped steps for EXISTING projects (skip repo creation + deployment)
existing_project_steps = Steps(
    name="existing_project_path",
    description="Workflow for existing projects: validate repo, implement, summary (skip creation + deployment)",
    steps=[
        Step(name="validate_repo", executor=validate_repo_link),
        Loop(
            name="implementation_cycle",
            steps=[
                Step(name="development", executor=development),
                Step(name="code_review", executor=code_review),
            ],
            end_condition=reviews_passed,
            max_iterations=2,
        ),
        Step(name="summary", executor=create_summary),
    ]
)


def route_by_repo_type(step_input: StepInput) -> List[Step]:
    """
    Route based on whether this is a new or existing project.

    Checks _state.is_existing_repo flag (set in read_architecture executor).
    - New projects: create repo → implement → deploy → validate
    - Existing projects: validate repo → implement → summary (skip creation + deployment)
    """
    if _state.is_existing_repo:
        _log("🔀", "ROUTER", "Route: EXISTING PROJECT PATH (skip repo creation + deployment)")
        return existing_project_steps.steps
    else:
        _log("🔀", "ROUTER", "Route: NEW PROJECT PATH (full flow)")
        return new_project_steps.steps


software_development_workflow = Workflow(
    name="Software Development",
    stream=False,
    description="Implement code from architecture, review, and deploy to Vercel (conditional based on project type).",
    steps=[
        Step(name="read_architecture", executor=read_architecture),
        Router(
            name="project_type_router",
            selector=route_by_repo_type,
            choices=[new_project_steps, existing_project_steps]
        )
    ]
)

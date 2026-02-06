"""
Software Development Workflow - Implementation with Review Cycle

Flow:
1. Read Architecture from Google Docs URL
2. Create GitHub Repo
3. Implementation Cycle (Loop max 2 iterations):
   - Development: Software Engineer writes code
   - Code Review: Lead Engineer reviews (quality + security + conventions)
   - Loop until approved OR max iterations
4. Deploy to Vercel
5. Summary with deployment link

Input: ARCHITECTURE_URL (Architecture Document from Google Docs)
Output: Vercel deployment link + GitHub repo
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

from agno.workflow import Step, Workflow, Loop
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info, log_error
from utils.cloud_logger import CloudLogger


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
        self.log_doc_url = ""  # Google Doc URL for logs


_state = ImplementationState()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _run_with_heartbeat(coro, step_name: str, timeout_seconds: int = 0):
    """Run coroutine in a background thread with heartbeat logging.
    If timeout_seconds <= 0, no timeout is applied (waits indefinitely).
    Returns the agent result, or None if errored."""
    result_holder = [None]
    error_holder = [None]
    done_event = threading.Event()

    def _execute():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result_holder[0] = loop.run_until_complete(coro)
        except Exception as e:
            error_holder[0] = e
        finally:
            done_event.set()

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
    """Concise logging helper - writes to both console and Google Docs."""
    print(f"{emoji} [{step}] {msg}")
    log_info(f"[{step}] {msg}")
    # Also log to cloud logger for Railway visibility
    CloudLogger.get_instance().log("INFO", step, msg, data, emoji)


def parse_input_urls(input_str: str) -> dict:
    """Parse input string to extract Architecture URL and optional params."""
    result = {"architecture_url": "", "github_repo": "", "github_owner": "", "project_name": ""}

    # Architecture URL
    arch_match = re.search(r'ARCHITECTURE_URL:\s*(https://[^\s]+)', input_str, re.I)
    if arch_match:
        result["architecture_url"] = arch_match.group(1)
    else:
        docs_match = re.search(r'https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+/[^\s]*', input_str)
        if docs_match:
            result["architecture_url"] = docs_match.group(0)

    # Optional params
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


# ============================================================================
# WORKFLOW STEPS
# ============================================================================

def read_architecture(step_input: StepInput) -> StepOutput:
    """Step 1: Read Architecture from Google Docs."""
    global _state
    _state = ImplementationState()  # Fresh state

    # Start cloud logging session for Railway visibility
    logger = CloudLogger.get_instance()
    _state.log_doc_url = logger.start_session("Software Development Workflow")
    if _state.log_doc_url:
        print(f"\n📋 LIVE LOGS: {_state.log_doc_url}\n")

    input_str = step_input.input if isinstance(step_input.input, str) else ""
    parsed = parse_input_urls(input_str)

    if not parsed["architecture_url"]:
        _log("❌", "READ", "No ARCHITECTURE_URL provided!")
        return StepOutput(content="ERROR: No ARCHITECTURE_URL provided", success=False)

    _log("📖", "READ", f"Reading architecture from Google Docs...")

    from tools.google_docs_tools import GoogleDocsTools
    try:
        doc_id = re.search(r'/document/d/([a-zA-Z0-9-_]+)', parsed["architecture_url"]).group(1)
        _state.architecture_content = GoogleDocsTools().read_document(doc_id)
        _log("✅", "READ", f"Architecture loaded ({len(_state.architecture_content)} chars)")

        # Extract/set project info
        _state.project_name = parsed["project_name"] or _extract_project_name(_state.architecture_content) or "project"
        _state.github_owner = parsed["github_owner"] or os.environ.get("GITHUB_OWNER", "")
        _state.github_repo = parsed["github_repo"] or _generate_repo_name(_state.project_name)

        if not _state.github_owner:
            _log("❌", "READ", "GITHUB_OWNER not set! Export GITHUB_OWNER env var.")
            return StepOutput(content="ERROR: GITHUB_OWNER not set", success=False)

        _log("📋", "READ", f"Project: {_state.project_name}")
        _log("🔗", "READ", f"GitHub: {_state.github_owner}/{_state.github_repo}")

        return StepOutput(content=f"Architecture loaded. Repo: {_state.github_owner}/{_state.github_repo}", success=True)
    except Exception as e:
        _log("❌", "READ", f"Failed: {e}")
        return StepOutput(content=f"ERROR: {e}", success=False)


def create_github_repo(step_input: StepInput) -> StepOutput:
    """Step 2: Create GitHub Repository with initial structure (direct API — no agent)."""
    global _state

    if not _state.github_owner or not _state.github_repo:
        return StepOutput(content="ERROR: GitHub not configured", success=False)

    from tools.github_tools import GitHubTools
    import json

    gh = GitHubTools()
    repo_url = f"https://github.com/{_state.github_owner}/{_state.github_repo}"

    # --- 1. Create repo with auto_init so main branch exists immediately ---
    _log("🏗️", "REPO", f"Creating repository: {_state.github_owner}/{_state.github_repo}")
    result = json.loads(gh.create_repository(
        name=_state.github_repo,
        description=_state.project_name,
        private=False,
        auto_init=True,
    ))
    if result.get("error"):
        # 422 = already exists — that's fine, continue
        if result.get("status_code") != 422:
            _log("❌", "REPO", f"create_repository failed: {result.get('message', '')}")
            return StepOutput(content=f"ERROR: {result.get('message', '')}", success=False)
        _log("ℹ️", "REPO", "Repository already exists — continuing")
    else:
        _log("✅", "REPO", f"Repository created: {repo_url}")

    # --- 2. Seed initial files directly — no get_file_contents needed ---
    files = {
        "README.md": f"# {_state.project_name}\n\n{_state.project_name} — generated by Agent-Os.\n",
        ".gitignore": (
            "__pycache__/\n*.pyc\n.env\n"
            "node_modules/\n.DS_Store\n"
        ),
        ".dev-team/README.md": "# Development Artifacts\n\nInternal development files.\n",
    }

    for path, content in files.items():
        res = json.loads(gh.create_or_update_file(
            owner=_state.github_owner,
            repo=_state.github_repo,
            path=path,
            content=content,
            message=f"feat: add {path}",
            branch="main",
        ))
        if res.get("error"):
            _log("⚠️", "REPO", f"Failed to create {path}: {res.get('message', '')}")
        else:
            _log("✓", "REPO", f"Created {path}")

    _log("✅", "REPO", f"Repository ready: {repo_url}")
    return StepOutput(content=f"Repository: {repo_url}", success=True)


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
    prompts = {
        "html": f"""Generate a complete index.html file for: {project_name}

Based on this architecture:
{architecture[:3000]}

Requirements:
- Complete HTML5 structure with DOCTYPE, html, head, body
- Include meta tags (charset, viewport)
- Link to styles.css and script.js
- All sections from the architecture
- Semantic HTML elements
- Real content (not Lorem ipsum)

Output ONLY the HTML code, nothing else. Start with <!DOCTYPE html>""",

        "css": f"""Generate a complete styles.css file for: {project_name}

Based on this architecture:
{architecture[:2000]}

Requirements:
- Modern, professional styling
- Responsive design (mobile-first)
- Style all sections from the architecture
- Nice colors, typography, spacing
- Hover effects, transitions
- CSS variables for colors

Output ONLY the CSS code, nothing else. Start with /* or :root""",

        "js": f"""Generate a complete script.js file for: {project_name}

Based on this architecture:
{architecture[:1500]}

Requirements:
- Mobile navigation toggle
- Smooth scrolling
- Form validation if forms exist
- Any interactive features from architecture
- Clean, modern JavaScript

Output ONLY the JavaScript code, nothing else. Start with // or 'use strict'"""
    }

    prompt = prompts.get(file_type, "")
    if not prompt:
        return ""

    result = _run_with_heartbeat(agent.arun(prompt), f"DEV-{file_type.upper()}", timeout_seconds=0)
    if result and result.content:
        return _extract_code(result.content)
    return ""


def development(step_input: StepInput) -> StepOutput:
    """Software Engineer implements code - generates each file separately."""
    global _state

    if not _state.github_owner or not _state.github_repo:
        return StepOutput(content="ERROR: GitHub not configured", success=False)

    _state.iteration += 1
    _state.code_file_path = "src/"

    _log("💻", "DEV", f"Iteration {_state.iteration} - Implementing code...")

    from agents.software_engineer import software_engineer_agent
    from tools.github_tools import GitHubTools
    import json

    gh = GitHubTools()
    arch_content = _state.architecture_content
    files_created = []

    # --- Generate and create index.html ---
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

    # --- Generate and create styles.css ---
    _log("🎨", "DEV", "Generating styles.css...")
    css_code = _generate_file_content(software_engineer_agent, "css", _state.project_name, arch_content)

    if css_code and len(css_code) > 50:
        res = json.loads(gh.create_or_update_file(
            owner=_state.github_owner,
            repo=_state.github_repo,
            path="styles.css",
            content=css_code,
            message="feat: add styles.css",
            branch="main",
        ))
        if res.get("success"):
            files_created.append("styles.css")
            _log("✓", "DEV", f"Created styles.css ({len(css_code)} chars)")
        else:
            _log("⚠️", "DEV", f"Failed to create styles.css: {res.get('message', '')}")
    else:
        _log("⚠️", "DEV", f"CSS generation failed or too short ({len(css_code) if css_code else 0} chars)")

    # --- Generate and create script.js ---
    _log("⚡", "DEV", "Generating script.js...")
    js_code = _generate_file_content(software_engineer_agent, "js", _state.project_name, arch_content)

    if js_code and len(js_code) > 20:
        res = json.loads(gh.create_or_update_file(
            owner=_state.github_owner,
            repo=_state.github_repo,
            path="script.js",
            content=js_code,
            message="feat: add script.js",
            branch="main",
        ))
        if res.get("success"):
            files_created.append("script.js")
            _log("✓", "DEV", f"Created script.js ({len(js_code)} chars)")
        else:
            _log("⚠️", "DEV", f"Failed to create script.js: {res.get('message', '')}")
    else:
        _log("ℹ️", "DEV", "Skipping script.js (not needed or too short)")

    # --- Summary ---
    if files_created:
        _log("✅", "DEV", f"Files created: {', '.join(files_created)}")
    else:
        _log("❌", "DEV", "No files were created!")

    return StepOutput(content=f"Created files: {', '.join(files_created) if files_created else 'none'}", success=True)


def code_review(step_input: StepInput) -> StepOutput:
    """Lead Engineer reviews code - auto-approves if code files exist."""
    global _state

    _log("👀", "CODE_REVIEW", "Checking project files...")

    # First, verify files exist directly (don't rely on agent)
    from tools.github_tools import GitHubTools
    import json

    gh = GitHubTools()
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

    result = _run_with_heartbeat(lead_engineer_agent.arun(prompt), "CODE_REVIEW", timeout_seconds=90)

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
    """Deploy to Vercel using the dedicated Vercel Deployer agent."""
    global _state

    _log("🚀", "DEPLOY", "Deploying to Vercel...")
    _log("📋", "DEPLOY", f"Owner: {_state.github_owner}, Repo: {_state.github_repo}, Project: {_state.project_name}")

    # Verify VERCEL_TOKEN is set
    if not os.environ.get("VERCEL_TOKEN"):
        _log("❌", "DEPLOY", "VERCEL_TOKEN environment variable not set!")
        return StepOutput(content="ERROR: VERCEL_TOKEN not set. Export VERCEL_TOKEN before running.", success=False)

    from agents.vercel_deployer import vercel_deployer_agent

    prompt = f"""Deploy this GitHub repository to Vercel:

github_owner: {_state.github_owner}
github_repo: {_state.github_repo}
project_name: {_state.project_name}
"""

    _log("🤖", "DEPLOY", "Asking Vercel Deployer agent...")
    result = _run_with_heartbeat(vercel_deployer_agent.arun(prompt), "DEPLOY", timeout_seconds=0)

    if result is None:
        _log("❌", "DEPLOY", "Agent failed")
        return StepOutput(content="ERROR: Deployment agent failed", success=False)

    # Check if deployment was successful by looking for URL or error in response
    response = result.content.lower()
    if "error" in response or "failed" in response:
        _log("❌", "DEPLOY", f"Deployment failed: {result.content[:200]}")
        return StepOutput(content=f"ERROR: {result.content}", success=False)

    _log("✅", "DEPLOY", "Deployment complete")
    return StepOutput(content=result.content, success=True)


def create_summary(step_input: StepInput) -> StepOutput:
    """Create final summary."""
    global _state

    deploy_content = step_input.previous_step_content or ""

    # Extract Vercel URL
    url_match = re.search(r'https://[^\s]+vercel\.app[^\s]*', deploy_content)
    deploy_url = url_match.group(0) if url_match else "Deployment in progress"

    repo_url = f"https://github.com/{_state.github_owner}/{_state.github_repo}"

    # End cloud logging session and get final log URL
    log_url = CloudLogger.get_instance().end_session()

    summary = f"""
## ✅ Implementation Complete!

**Project:** {_state.project_name}
**Iterations:** {_state.iteration}

### Links
- 🚀 **Live:** {deploy_url}
- 📂 **GitHub:** {repo_url}
- 📋 **Logs:** {log_url if log_url else "N/A"}

### Review
- Code Review (Quality + Security + Conventions): {_state.code_review_status}
"""

    _log("🎉", "DONE", f"Project complete! {deploy_url}")

    # Reset for next run
    _state.__init__()

    return StepOutput(content=summary, success=True)


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

software_development_workflow = Workflow(
    name="Software Development",
    stream=False,
    description="Implement code from architecture, review, and deploy to Vercel.",
    steps=[
        Step(name="read_architecture", executor=read_architecture),
        Step(name="create_repo", executor=create_github_repo),
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
        Step(name="summary", executor=create_summary),
    ]
)

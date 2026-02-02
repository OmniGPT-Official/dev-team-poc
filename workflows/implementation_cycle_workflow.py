"""
Implementation Cycle Workflow

Input: PRD + Technical Documentation (string)
Flow: Setup -> [Development -> Code Review + Security Review] loops until both approve

Setup creates a new GitHub repo with README.md containing PRD, tech doc, and GitHub info.
All subsequent steps read README.md from GitHub for context.

Uses async executors - run workflow with arun() instead of run().

IMPORTANT: Repository info (owner, repo, branch) is stored in session_state and passed
explicitly to all steps to ensure reviewers know where to look for code.
"""

import os
import re
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.run import RunContext
from agno.workflow import Loop, Parallel, Step, Workflow
from agno.workflow.step import StepInput, StepOutput

from agents.software_engineer import software_engineer_agent
from agents.lead_engineer import lead_engineer_agent
from agents.security_engineer import security_engineer_agent


MAX_ITERATIONS = 5


def extract_repo_info(text: str) -> Optional[Dict[str, str]]:
    """Extract owner/repo/branch from step output text."""
    # Try pattern: Repository: owner/repo
    match = re.search(r'Repository:\s*([^/\s]+)/([^\s\n]+)', text)
    if match:
        return {
            "owner": match.group(1).strip(),
            "repo": match.group(2).strip(),
            "branch": "main"
        }

    # Try pattern: owner: X, repo: Y
    owner_match = re.search(r'[Oo]wner:\s*([^\s\n,]+)', text)
    repo_match = re.search(r'[Rr]epo(?:sitory)?:\s*([^\s\n,]+)', text)
    if owner_match and repo_match:
        return {
            "owner": owner_match.group(1).strip(),
            "repo": repo_match.group(1).strip(),
            "branch": "main"
        }

    return None


def format_repo_context(repo_info: Dict[str, str]) -> str:
    """Format repo info as context string for prompts."""
    return f"""## Repository Information (REQUIRED - use these exact values)
- Owner: {repo_info['owner']}
- Repository: {repo_info['repo']}
- Branch: {repo_info['branch']}
- Full path: {repo_info['owner']}/{repo_info['repo']}"""


# =============================================================================
# SETUP STEP
# =============================================================================

def log_run_context(step_name: str, run_context: RunContext) -> None:
    """Log run_context details for debugging."""
    print(f"\n[DEBUG {step_name}] === RUN CONTEXT ===")
    print(f"  run_context is None: {run_context is None}")
    if run_context:
        print(f"  user_id: {getattr(run_context, 'user_id', 'N/A')}")
        print(f"  session_id: {getattr(run_context, 'session_id', 'N/A')}")
        print(f"  run_id: {getattr(run_context, 'run_id', 'N/A')}")
        print(f"  session_state is None: {run_context.session_state is None}")
        if run_context.session_state is not None:
            print(f"  session_state keys: {list(run_context.session_state.keys())}")
            print(f"  session_state contents: {run_context.session_state}")


def log_step_input(step_name: str, step_input: StepInput) -> None:
    """Log step_input details for debugging."""
    print(f"\n[DEBUG {step_name}] === STEP INPUT ===")
    print(f"  input type: {type(step_input.input).__name__}")
    print(f"  input length: {len(step_input.input) if isinstance(step_input.input, str) else 'N/A'}")
    print(f"  previous_step_content is None: {step_input.previous_step_content is None}")
    if step_input.previous_step_content:
        print(f"  previous_step_content length: {len(step_input.previous_step_content)}")
    print(f"  previous_step_outputs: {list(step_input.previous_step_outputs.keys()) if step_input.previous_step_outputs else 'None'}")


async def setup_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Setup: create repo and README with all project info."""
    specs = step_input.input if isinstance(step_input.input, str) else ""

    print(f"\n{'='*60}")
    print(f"[STEP: Setup]")
    print(f"{'='*60}")

    # Debug logging for context verification
    log_run_context("Setup", run_context)
    log_step_input("Setup", step_input)

    # Initialize session_state if needed
    if run_context.session_state is None:
        run_context.session_state = {}
        print(f"[DEBUG Setup] Initialized empty session_state")

    print(f"\n[DEBUG Setup] === STEP EXECUTION ===")
    print(f"[INPUT] step_input.input: {len(specs)} chars")
    print(f"[INPUT] step_input.previous_step_content: {step_input.previous_step_content}")
    print(f"[INPUT STRING]\n{specs[:1000]}{'...' if len(specs) > 1000 else ''}")

    prompt = f"""You are setting up a new project repository.

## Specifications
{specs}

## Instructions
1. Create a NEW GitHub repository for this project using GitHub MCP tools
2. Create README.md with this structure:

```markdown
# <Project Name>

## GitHub Info
- owner: <your github username or org>
- repo: <repository name>
- branch: main

## PRD (Product Requirements)
<paste PRD from specifications>

## Technical Documentation
<paste technical docs from specifications>

## Implementation Status
- [ ] Setup complete
- [ ] Implementation in progress
- [ ] Code review passed
- [ ] Security review passed
```

3. Commit README.md with message "Initial project setup"

## Output Format (MUST follow exactly)
SETUP_COMPLETE
Repository: <owner>/<repo>
Branch: main

README.md contains:
- GitHub Info (owner, repo, branch)
- PRD (Product Requirements)
- Technical Documentation
- Implementation Status

CRITICAL: Your output MUST include "Repository: owner/repo" on its own line.
"""

    result = await software_engineer_agent.arun(prompt)
    output = result.content or ""

    # Extract and store repo info in session_state for subsequent steps
    repo_info = extract_repo_info(output)
    if repo_info:
        run_context.session_state["repo_info"] = repo_info
        print(f"\n[DEBUG Setup] === SESSION STATE UPDATED ===")
        print(f"  repo_info STORED: {repo_info}")
        print(f"  session_state after update: {run_context.session_state}")
    else:
        print(f"\n[DEBUG Setup] [WARNING] Could not extract repo info from output")
        print(f"  Output searched: {output[:500]}...")

    print(f"\n[DEBUG Setup] === STEP OUTPUT ===")
    print(f"[OUTPUT] {len(output)} chars")
    print(f"[RAW OUTPUT]\n{output}")
    print(f"{'='*60}")

    return StepOutput(content=output, success=True)


# =============================================================================
# DEVELOPMENT STEP
# =============================================================================

async def development_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Development: implement or revise code based on README specs and review feedback from repo."""
    original_input = step_input.input if isinstance(step_input.input, str) else ""
    previous_output = step_input.previous_step_content or ""

    print(f"\n{'='*60}")
    print(f"[STEP: Development]")
    print(f"{'='*60}")

    # Debug logging for context verification
    log_run_context("Development", run_context)
    log_step_input("Development", step_input)

    # Initialize session_state if needed
    if run_context.session_state is None:
        run_context.session_state = {}
        print(f"[DEBUG Development] Initialized empty session_state")

    # Get repo info from session_state (set by Setup step)
    repo_info = run_context.session_state.get("repo_info", {})
    repo_context = format_repo_context(repo_info) if repo_info else "## Repository Information\nNOT AVAILABLE - extract from previous output"

    print(f"\n[DEBUG Development] === REPO INFO CHECK ===")
    print(f"  repo_info from session_state: {repo_info}")
    print(f"  repo_info is empty: {not repo_info}")
    if repo_info:
        print(f"  repo_context generated:\n{repo_context}")

    print(f"\n[DEBUG Development] === STEP EXECUTION ===")
    print(f"[INPUT] step_input.input: {len(original_input)} chars")
    print(f"[INPUT] step_input.previous_step_content: {len(previous_output)} chars")
    print(f"[INPUT STRING - previous_step_content]\n{previous_output[:1500]}{'...' if len(previous_output) > 1500 else ''}")

    prompt = f"""Implement or revise the project based on specs and review feedback.

{repo_context}

## Previous Step Output
{previous_output}

## Instructions
1. Use the repository information above (owner/repo) with GitHub MCP tools
2. Read README.md - contains PRD and Technical Documentation
3. Check for review feedback files:
   - Read CODE_REVIEW.md if it exists (code quality feedback from lead engineer)
   - Read SECURITY_REVIEW.md if it exists (security feedback from security engineer)
   - If either has CHANGES_REQUESTED or CHANGES_REQUIRED: address ALL feedback points
   - If neither exists or both are APPROVED: implement according to README.md specs
4. Create/update all necessary code files
5. Update README.md Implementation Status
6. Commit all changes with descriptive messages

IMPORTANT: You MUST actually create/modify code files, not just describe what you will do.

## Output Format (REQUIRED - follow exactly)
IMPLEMENTATION_COMPLETE or REVISION_COMPLETE
Repository: {repo_info.get('owner', '<owner>')}/{repo_info.get('repo', '<repo>')}
Branch: {repo_info.get('branch', 'main')}

Files created/modified:
- <list all files>

Summary: <what was done>

CRITICAL: Your output MUST include the Repository line with owner/repo.
"""

    result = await software_engineer_agent.arun(prompt)
    output = result.content or ""

    # Try to extract repo info from output if not in session_state
    if not repo_info:
        extracted = extract_repo_info(output)
        if extracted:
            run_context.session_state["repo_info"] = extracted
            print(f"\n[DEBUG Development] === SESSION STATE UPDATED ===")
            print(f"  repo_info EXTRACTED and stored: {extracted}")

    # Ensure repo info is in output for downstream steps
    if repo_info and "Repository:" not in output:
        output += f"\n\nRepository: {repo_info['owner']}/{repo_info['repo']}\nBranch: {repo_info['branch']}"
        print(f"\n[DEBUG Development] repo_info APPENDED to output")

    print(f"\n[DEBUG Development] === STEP OUTPUT ===")
    print(f"  session_state at end: {run_context.session_state}")
    print(f"[OUTPUT] {len(output)} chars")
    print(f"[RAW OUTPUT]\n{output}")
    print(f"{'='*60}")

    return StepOutput(content=output, success=True)


# =============================================================================
# CODE REVIEW STEP
# =============================================================================

async def code_review_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Code review: check implementation and write feedback to CODE_REVIEW.md."""

    print(f"\n{'='*60}")
    print(f"[STEP: Code Review]")
    print(f"{'='*60}")

    # Debug logging for context verification
    log_run_context("Code Review", run_context)
    log_step_input("Code Review", step_input)

    # Initialize session_state if needed
    if run_context.session_state is None:
        run_context.session_state = {}
        print(f"[DEBUG Code Review] Initialized empty session_state")

    # Get repo info from session_state (set by Setup step)
    repo_info = run_context.session_state.get("repo_info", {})
    if not repo_info:
        return StepOutput(content="ERROR: No repo_info in session_state", success=False)

    repo_context = format_repo_context(repo_info)

    print(f"\n[DEBUG Code Review] === REPO INFO CHECK ===")
    print(f"  repo_info from session_state: {repo_info}")
    print(f"  Will use owner={repo_info.get('owner')}, repo={repo_info.get('repo')}")

    prompt = f"""Review implementation for code quality and requirements.

{repo_context}

## Instructions
1. Use the repository information above with GitHub MCP tools
2. Read README.md - contains PRD and Technical Documentation
3. Read and review ALL implementation files in the repository
4. Verify implementation matches PRD and technical documentation
5. Check code quality, structure, best practices

## IMPORTANT: Write Your Review to GitHub
After completing your review, you MUST:
1. Create/update CODE_REVIEW.md in the repo with your review
2. Commit the file with message "Code review feedback"

The CODE_REVIEW.md format:
```markdown
# Code Review

Decision: APPROVED or CHANGES_REQUESTED

## Findings
<your detailed findings>

## Required Changes (if CHANGES_REQUESTED)
- <specific change 1>
- <specific change 2>

## Code Quality Notes
<any additional observations>
```

## Output Format (REQUIRED - follow exactly)
Repository: {repo_info.get('owner', '<owner>')}/{repo_info.get('repo', '<repo>')}
Branch: {repo_info.get('branch', 'main')}
Decision: APPROVED or CHANGES_REQUESTED
Feedback written to: CODE_REVIEW.md
"""

    result = await lead_engineer_agent.arun(prompt)
    output = result.content or ""

    # Ensure repo info is in output
    if repo_info and "Repository:" not in output:
        output = f"Repository: {repo_info['owner']}/{repo_info['repo']}\nBranch: {repo_info['branch']}\n\n{output}"
        print(f"\n[DEBUG Code Review] repo_info PREPENDED to output")

    print(f"\n[DEBUG Code Review] === STEP OUTPUT ===")
    print(f"  session_state at end: {run_context.session_state}")
    print(f"[OUTPUT] {len(output)} chars")
    print(f"  APPROVED: {'APPROVED' in output and 'CHANGES_REQUESTED' not in output}")
    print(f"  CHANGES_REQUESTED: {'CHANGES_REQUESTED' in output}")
    print(f"[RAW OUTPUT]\n{output}")
    print(f"{'='*60}")

    return StepOutput(content=output, success=True)


# =============================================================================
# SECURITY REVIEW STEP
# =============================================================================

async def security_review_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Security review: check for vulnerabilities and write feedback to SECURITY_REVIEW.md."""

    print(f"\n{'='*60}")
    print(f"[STEP: Security Review]")
    print(f"{'='*60}")

    # Debug logging for context verification
    log_run_context("Security Review", run_context)
    log_step_input("Security Review", step_input)

    # Initialize session_state if needed
    if run_context.session_state is None:
        run_context.session_state = {}
        print(f"[DEBUG Security Review] Initialized empty session_state")

    # Get repo info from session_state (set by Setup step)
    repo_info = run_context.session_state.get("repo_info", {})
    if not repo_info:
        return StepOutput(content="ERROR: No repo_info in session_state", success=False)

    repo_context = format_repo_context(repo_info)

    print(f"\n[DEBUG Security Review] === REPO INFO CHECK ===")
    print(f"  repo_info from session_state: {repo_info}")
    print(f"  Will use owner={repo_info.get('owner')}, repo={repo_info.get('repo')}")

    prompt = f"""Review implementation for security vulnerabilities.

{repo_context}

## Instructions
1. Use the repository information above with GitHub MCP tools
2. Read README.md - contains PRD and Technical Documentation
3. Read and review ALL implementation files for security issues
4. Check for OWASP top 10 vulnerabilities
5. Verify no sensitive data or credentials exposed
6. Check input validation and error handling

## IMPORTANT: Write Your Review to GitHub
After completing your review, you MUST:
1. Create/update SECURITY_REVIEW.md in the repo with your review
2. Commit the file with message "Security review feedback"

The SECURITY_REVIEW.md format:
```markdown
# Security Review

Decision: APPROVED or CHANGES_REQUIRED

## Findings
<your detailed security findings>

## Required Changes (if CHANGES_REQUIRED)
- <specific security fix 1>
- <specific security fix 2>

## OWASP Checklist
- [ ] Injection vulnerabilities
- [ ] Authentication issues
- [ ] Sensitive data exposure
- [ ] etc.
```

## Output Format (REQUIRED - follow exactly)
Repository: {repo_info.get('owner', '<owner>')}/{repo_info.get('repo', '<repo>')}
Branch: {repo_info.get('branch', 'main')}
Decision: APPROVED or CHANGES_REQUIRED
Feedback written to: SECURITY_REVIEW.md
"""

    result = await security_engineer_agent.arun(prompt)
    output = result.content or ""

    # Ensure repo info is in output
    if repo_info and "Repository:" not in output:
        output = f"Repository: {repo_info['owner']}/{repo_info['repo']}\nBranch: {repo_info['branch']}\n\n{output}"
        print(f"\n[DEBUG Security Review] repo_info PREPENDED to output")

    print(f"\n[DEBUG Security Review] === STEP OUTPUT ===")
    print(f"  session_state at end: {run_context.session_state}")
    print(f"[OUTPUT] {len(output)} chars")
    print(f"  APPROVED: {'APPROVED' in output and 'CHANGES_REQUIRED' not in output}")
    print(f"  CHANGES_REQUIRED: {'CHANGES_REQUIRED' in output}")
    print(f"[RAW OUTPUT]\n{output}")
    print(f"{'='*60}")

    return StepOutput(content=output, success=True)


# =============================================================================
# WORKFLOW DEFINITION
# =============================================================================

def check_approval(outputs: List[StepOutput]) -> bool:
    """Check if both reviews approved. Returns True to EXIT loop."""
    print(f"\n{'='*60}")
    print(f"[CHECK_APPROVAL]")
    print(f"{'='*60}")

    print(f"\n[DEBUG check_approval] === OUTPUTS RECEIVED ===")
    print(f"  outputs count: {len(outputs)}")

    for i, out in enumerate(outputs):
        print(f"\n  output[{i}]:")
        print(f"    step_name: {out.step_name}")
        print(f"    step_type: {out.step_type}")
        print(f"    content length: {len(out.content or '')}")
        print(f"    success: {out.success}")
        # Check if this output has nested steps (e.g., from Parallel)
        if out.steps:
            print(f"    nested steps: {[s.step_name for s in out.steps]}")

    if len(outputs) < 2:
        print(f"\n[DEBUG check_approval] === RESULT ===")
        print(f"  CONTINUE (not enough outputs, need at least 2)")
        print(f"{'='*60}")
        return False

    code_review = outputs[-2].content or ""
    security_review = outputs[-1].content or ""

    print(f"\n[DEBUG check_approval] === REVIEW ANALYSIS ===")
    print(f"  Code Review (output[-2]):")
    print(f"    step_name: {outputs[-2].step_name}")
    print(f"    content preview: {code_review[:300]}{'...' if len(code_review) > 300 else ''}")
    print(f"    contains 'APPROVED': {'APPROVED' in code_review}")
    print(f"    contains 'CHANGES_REQUESTED': {'CHANGES_REQUESTED' in code_review}")

    print(f"\n  Security Review (output[-1]):")
    print(f"    step_name: {outputs[-1].step_name}")
    print(f"    content preview: {security_review[:300]}{'...' if len(security_review) > 300 else ''}")
    print(f"    contains 'APPROVED': {'APPROVED' in security_review}")
    print(f"    contains 'CHANGES_REQUIRED': {'CHANGES_REQUIRED' in security_review}")

    code_ok = "APPROVED" in code_review and "CHANGES_REQUESTED" not in code_review
    security_ok = "APPROVED" in security_review and "CHANGES_REQUIRED" not in security_review

    print(f"\n[DEBUG check_approval] === RESULT ===")
    print(f"  code_approved: {code_ok}")
    print(f"  security_approved: {security_ok}")
    print(f"  both_approved: {code_ok and security_ok}")
    print(f"  action: {'EXIT LOOP' if code_ok and security_ok else 'CONTINUE LOOP'}")
    print(f"{'='*60}")

    return code_ok and security_ok


# Steps
setup_step = Step(name="Setup", executor=setup_executor)
development_step = Step(name="Development", executor=development_executor)
code_review_step = Step(name="Code Review", executor=code_review_executor)
security_review_step = Step(name="Security Review", executor=security_review_executor)

# Workflow - use arun() to execute
implementation_cycle_workflow = Workflow(
    name="Implementation Cycle",
    description="Setup repo, then development loop until reviews approve",
    steps=[
        setup_step,
        Loop(
            name="Development Loop",
            steps=[
                development_step,
                Parallel(code_review_step, security_review_step, name="Reviews"),
            ],
            end_condition=check_approval,
            max_iterations=MAX_ITERATIONS,
        ),
    ],
)

#!/usr/bin/env python3
"""
Vercel Deploy Test — @vercel/sdk

Calls the local deploy.js tool (which uses the official @vercel/sdk) to
create a git-sourced deployment and poll it to READY.  The Node script
writes the live URL to stdout; this script captures it and prints the
test summary.

Target repo: Muhammad-Anique/--crumble-bakery--softwar-33438

Run:
    cd <project-root>
    export VERCEL_TOKEN="YOUR_VERCEL_TOKEN"
    python tests/vercel_mcp/test_deploy_vercel.py

Test Flow:
    1. Run deploy.js via Node  — creates + polls the deployment
    2. Capture the preview URL from stdout
    3. Print test summary
"""

import os
import sys
import subprocess
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VERCEL_TOKEN   = os.environ.get("VERCEL_TOKEN", "")
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
DEPLOY_TIMEOUT = 360   # seconds — slightly more than the 5 min JS-side timeout


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def log_section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def log_step(step_num: int, description: str):
    print(f"\n[STEP {step_num}] {description}")
    print("-" * 50)

def log_success(message: str):
    print(f"  SUCCESS: {message}")

def log_error(message: str, detail=None):
    print(f"  ERROR: {message}")
    if detail:
        print(f"     Details: {detail}")

def log_info(message: str):
    print(f"  INFO: {message}")


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def step_deploy() -> str:
    """Run deploy.js and capture the preview URL from its stdout."""
    log_step(1, "Deploy via @vercel/sdk (deploy.js)")
    log_info("Running: node deploy.js")

    try:
        result = subprocess.run(
            ["node", "deploy.js"],
            capture_output=True,
            text=True,
            timeout=DEPLOY_TIMEOUT,
            cwd=SCRIPT_DIR,
            env={**os.environ, "VERCEL_TOKEN": VERCEL_TOKEN},
        )
    except subprocess.TimeoutExpired:
        log_error(f"deploy.js timed out after {DEPLOY_TIMEOUT}s")
        sys.exit(1)

    # stderr has all the SDK logs — print them for visibility
    if result.stderr:
        for line in result.stderr.splitlines():
            print(f"    {line}")

    if result.returncode != 0:
        log_error(f"deploy.js exited with code {result.returncode}")
        sys.exit(1)

    url = result.stdout.strip()
    if url:
        log_success(f"LIVE → {url}")
        return url

    log_info("Deploy finished but no URL returned — check Vercel dashboard.")
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    GITHUB_OWNER = "Muhammad-Anique"
    GITHUB_REPO  = "--crumble-bakery--softwar-33438"
    PROJECT_NAME = "crumble-bakery-deploy-test"

    log_section("VERCEL DEPLOY TEST (@vercel/sdk)")
    log_info(f"Timestamp: {datetime.now().isoformat()}")
    log_info(f"Repo:      https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}")
    log_info(f"Project:   {PROJECT_NAME}")

    # Guard
    if not VERCEL_TOKEN:
        log_section("MISSING TOKEN")
        print('  export VERCEL_TOKEN="YOUR_VALUE"')
        print()
        print("  Then re-run: python tests/vercel_mcp/test_deploy_vercel.py")
        sys.exit(1)

    log_info(f"VERCEL_TOKEN: {VERCEL_TOKEN[:8]}...{VERCEL_TOKEN[-4:]}")

    # Run
    url = step_deploy()

    # Summary
    log_section("TEST SUMMARY")
    print(f"""
  Repo:      https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}
  Project:   {PROJECT_NAME}
  Live URL:  {url or 'check Vercel dashboard'}
  Timestamp: {datetime.now().isoformat()}
""")
    log_section("TEST COMPLETE")

#!/usr/bin/env python3
"""
Vercel Deployment Test - Complete End-to-End Test

Tests the full deployment flow with all parameters.
Can be used to verify deployment works before running the workflow.

Usage:
    # Using environment variables
    export VERCEL_TOKEN="your_token"
    export GITHUB_TOKEN="your_token"
    export GITHUB_OWNER="Muhammad-Anique"
    export GITHUB_REPO="your-repo-name"
    export PROJECT_NAME="your-project-name"
    python tests/test_vercel_deploy.py

    # Or pass as arguments
    python tests/test_vercel_deploy.py \
        --github-owner "Muhammad-Anique" \
        --github-repo "your-repo-name" \
        --project-name "your-project" \
        --vercel-token "your_vercel_token" \
        --github-token "your_github_token"
"""

import os
import sys
import argparse
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vercel_deploy_tools import VercelDeployTools


def log_section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def log_info(key: str, value: str):
    print(f"  {key:20} {value}")


def log_success(message: str):
    print(f"\n✅ {message}")


def log_error(message: str):
    print(f"\n❌ {message}")


def main():
    parser = argparse.ArgumentParser(description="Test Vercel deployment")
    parser.add_argument("--github-owner", help="GitHub owner/org")
    parser.add_argument("--github-repo", help="GitHub repository name")
    parser.add_argument("--project-name", help="Vercel project name")
    parser.add_argument("--vercel-token", help="Vercel API token")
    parser.add_argument("--github-token", help="GitHub API token")
    args = parser.parse_args()

    log_section("VERCEL DEPLOYMENT TEST")
    log_info("Timestamp:", datetime.now().isoformat())

    # Get parameters from args or env
    github_owner = args.github_owner or os.environ.get("GITHUB_OWNER", "")
    github_repo = args.github_repo or os.environ.get("GITHUB_REPO", "")
    project_name = args.project_name or os.environ.get("PROJECT_NAME", "")
    vercel_token = args.vercel_token or os.environ.get("VERCEL_TOKEN", "")
    github_token = args.github_token or os.environ.get("GITHUB_TOKEN", "")

    # Validate required parameters
    missing = []
    if not github_owner:
        missing.append("GITHUB_OWNER")
    if not github_repo:
        missing.append("GITHUB_REPO")
    if not project_name:
        missing.append("PROJECT_NAME")
    if not vercel_token:
        missing.append("VERCEL_TOKEN")

    if missing:
        log_section("MISSING PARAMETERS")
        log_error(f"Missing required parameters: {', '.join(missing)}")
        print("\nSet them as environment variables or pass as arguments:")
        print("  export GITHUB_OWNER='Muhammad-Anique'")
        print("  export GITHUB_REPO='your-repo-name'")
        print("  export PROJECT_NAME='your-project'")
        print("  export VERCEL_TOKEN='your_token'")
        print("\nOr:")
        print("  python tests/test_vercel_deploy.py \\")
        print("    --github-owner 'Muhammad-Anique' \\")
        print("    --github-repo 'your-repo' \\")
        print("    --project-name 'your-project' \\")
        print("    --vercel-token 'your_token'")
        sys.exit(1)

    # Set environment variables for deploy.js
    os.environ["VERCEL_TOKEN"] = vercel_token
    if github_token:
        os.environ["GITHUB_TOKEN"] = github_token

    log_section("CONFIGURATION")
    log_info("GitHub Owner:", github_owner)
    log_info("GitHub Repo:", github_repo)
    log_info("Project Name:", project_name)
    log_info("Vercel Token:", f"{vercel_token[:8]}...{vercel_token[-4:]}" if len(vercel_token) > 12 else "***")
    log_info("GitHub Token:", "✓ Set" if github_token else "✗ Not set")
    log_info("Repo URL:", f"https://github.com/{github_owner}/{github_repo}")

    # Test deployment
    log_section("DEPLOYING TO VERCEL")
    print("\n  Calling deploy_to_vercel()...")
    print(f"  This will deploy: {github_owner}/{github_repo}")
    print(f"  As project: {project_name}")
    print("\n  Please wait (this may take 2-5 minutes)...\n")

    try:
        tools = VercelDeployTools()
        result_json = tools.deploy_to_vercel(
            github_owner=github_owner,
            github_repo=github_repo,
            project_name=project_name
        )

        # Parse result
        result = json.loads(result_json)

        log_section("DEPLOYMENT RESULT")
        print("\n" + result_json)

        if result.get("success"):
            log_success("DEPLOYMENT SUCCESSFUL!")
            log_info("Live URL:", result.get("url", "N/A"))
            log_section("TEST PASSED ✓")
            return 0
        else:
            log_error("DEPLOYMENT FAILED!")
            log_info("Error:", result.get("message", "Unknown error"))
            if "stderr" in result:
                print(f"\n  Stderr:\n{result['stderr']}")
            log_section("TEST FAILED ✗")
            return 1

    except Exception as e:
        log_error(f"EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        log_section("TEST FAILED ✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Direct test of VercelDeployTools to diagnose deployment issues.

This bypasses the agent and calls the tool directly to see if it works.

Usage:
    export VERCEL_TOKEN="your_token"
    export GITHUB_OWNER="Muhammad-Anique"
    python tests/test_deploy_direct.py
"""

import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vercel_deploy_tools import VercelDeployTools


def main():
    print("=" * 70)
    print("  DIRECT VERCEL DEPLOY TEST")
    print("=" * 70)

    # Check env vars
    vercel_token = os.environ.get("VERCEL_TOKEN", "")
    github_owner = os.environ.get("GITHUB_OWNER", "Muhammad-Anique")
    github_repo = os.environ.get("GITHUB_REPO", "test-repo-12345")
    project_name = os.environ.get("PROJECT_NAME", "test-deployment")

    if not vercel_token:
        print("\n❌ ERROR: VERCEL_TOKEN not set!")
        print("\nRun:")
        print('  export VERCEL_TOKEN="your_token"')
        print("  python tests/test_deploy_direct.py")
        sys.exit(1)

    print(f"\n📋 Configuration:")
    print(f"  VERCEL_TOKEN: {vercel_token[:8]}...{vercel_token[-4:]}")
    print(f"  GITHUB_OWNER: {github_owner}")
    print(f"  GITHUB_REPO: {github_repo}")
    print(f"  PROJECT_NAME: {project_name}")

    # Test the tool
    print(f"\n🚀 Testing VercelDeployTools directly...")
    print(f"  Calling: deploy_to_vercel(...)")

    tools = VercelDeployTools()
    result = tools.deploy_to_vercel(
        github_owner=github_owner,
        github_repo=github_repo,
        project_name=project_name
    )

    print(f"\n📤 Tool Response:")
    print("-" * 70)
    print(result)
    print("-" * 70)

    # Parse result
    try:
        data = json.loads(result)
        if data.get("success"):
            print(f"\n✅ SUCCESS!")
            print(f"  Live URL: {data.get('url')}")
        else:
            print(f"\n❌ FAILED!")
            print(f"  Error: {data.get('message', 'Unknown error')}")
            if "stderr" in data:
                print(f"  Stderr: {data['stderr']}")
    except json.JSONDecodeError:
        print(f"\n⚠️  Could not parse JSON response")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

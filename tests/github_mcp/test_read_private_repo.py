#!/usr/bin/env python3
"""
Read Private Repository Content Test

Tests reading files from a private GitHub repository via MCP.

Run:
    cd <project-root>
    source venv/bin/activate
    pip install -r requirements.txt

    # Set your token (replace with your real GitHub PAT):
    export GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"

    python tests/github_mcp/test_read_private_repo.py
"""

import os
import sys
import asyncio
import json
import base64
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration  (set GITHUB_TOKEN env var or replace the default below)
# ---------------------------------------------------------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN_HERE")

if GITHUB_TOKEN == "YOUR_GITHUB_TOKEN_HERE":
    print("=" * 70)
    print("  ERROR: No GitHub token configured")
    print("=" * 70)
    print()
    print("  Set your token before running:")
    print()
    print('    export GITHUB_TOKEN="ghp_YourRealTokenHere"')
    print("    python tests/github_mcp/test_read_private_repo.py")
    print()
    print("  Get a token at: https://github.com/settings/tokens")
    print("=" * 70)
    sys.exit(1)

os.environ["GITHUB_TOKEN"] = GITHUB_TOKEN
os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = GITHUB_TOKEN

OWNER = os.environ.get("GITHUB_TEST_OWNER", "Muhammad-Anique")
REPO = "agno-test-private"

FILES_TO_READ = [
    "README.md",
    "secret.txt",
    "config/settings.json",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def decode_base64_content(content: str) -> str:
    try:
        cleaned = content.replace("\n", "").replace("\r", "")
        decoded_bytes = base64.b64decode(cleaned)
        try:
            return decoded_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return decoded_bytes.decode("latin-1")
    except Exception as e:
        return f"[Failed to decode: {e}]"


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

async def test_read_private_repo():
    from agno.tools.mcp import MCPTools

    print("=" * 70)
    print("  READ PRIVATE REPOSITORY TEST")
    print("=" * 70)
    print(f"  Repository: {OWNER}/{REPO}")
    print(f"  Type: PRIVATE")
    print(f"  Token: {GITHUB_TOKEN[:10]}...{GITHUB_TOKEN[-4:]}")
    print("=" * 70)

    # Initialize MCP
    print("\n[1] Initializing GitHub MCP...")
    github_mcp = MCPTools(
        command="npx -y @modelcontextprotocol/server-github",
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_TOKEN},
        timeout_seconds=60,
    )
    print("    MCP created")

    # Connect
    print("\n[2] Connecting to GitHub MCP server...")
    await github_mcp.connect()
    print("    Connected")

    # Get session
    print("\n[3] Getting session...")
    session = await github_mcp.get_session_for_run()
    print(f"    Session ready: {type(session).__name__}")

    # List root directory
    print(f"\n[4] Listing repository contents (root)...")
    try:
        result = await session.call_tool("get_file_contents", {
            "owner": OWNER,
            "repo": REPO,
            "path": "",
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    data = json.loads(content.text)
                    if isinstance(data, list):
                        print(f"    Found {len(data)} items:")
                        for item in data:
                            icon = "dir" if item.get("type") == "dir" else "file"
                            print(f"       [{icon}] {item.get('name')}")
    except Exception as e:
        print(f"    Failed to list contents: {e}")

    # Read each file
    print(f"\n[5] Reading files from {OWNER}/{REPO}...")
    print("-" * 70)

    for file_path in FILES_TO_READ:
        print(f"\n  Reading: {file_path}")
        try:
            result = await session.call_tool("get_file_contents", {
                "owner": OWNER,
                "repo": REPO,
                "path": file_path,
            })
            if result.content:
                for content in result.content:
                    if hasattr(content, "text"):
                        data = json.loads(content.text)
                        print(f"    Name: {data.get('name')}")
                        print(f"    Size: {data.get('size')} bytes")
                        if data.get("content"):
                            decoded = decode_base64_content(data["content"])
                            lines = decoded.split("\n")
                            print(f"    Content:")
                            for line in lines[:20]:
                                print(f"      {line}")
                            if len(lines) > 20:
                                print(f"      ... ({len(lines) - 20} more lines)")
                            print(f"    OK: {file_path}")
                        else:
                            print(f"    WARN: No content in response")
        except Exception as e:
            print(f"    FAIL: {file_path}: {e}")

    # Close
    print(f"\n[6] Closing connection...")
    await github_mcp.close()
    print("    Closed")

    # Summary
    print("\n" + "=" * 70)
    print("  TEST COMPLETE")
    print("=" * 70)
    print(f"  Repository: https://github.com/{OWNER}/{REPO}")
    print(f"  Files tested: {len(FILES_TO_READ)}")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  PRIVATE REPOSITORY READ TEST")
    print("=" * 70)
    try:
        asyncio.run(test_read_private_repo())
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    print()

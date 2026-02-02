#!/usr/bin/env python3
"""
GitHub MCP Comprehensive Test

Tests all GitHub MCP operations against public and private repositories.

Run:
    cd <project-root>
    source venv/bin/activate
    pip install -r requirements.txt

    # Set your token (replace with your real GitHub PAT):
    export GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"

    python tests/github_mcp/test_github_mcp.py

Test Flow:
    1.  Initialize MCP
    2.  Connect to server
    3.  List tools
    4.  Create public repo
    5.  Add file to public repo
    6.  Read file
    7.  Update file
    8.  Add nested file
    9.  Create private repo
    10. Add file to private repo
    11. Read from private repo
    12. Update in private repo
    13. Add nested file in private repo
    14. Search repositories
    15. List commits (public)
    16. List commits (private)
    17. Verify updates
    18. Close connection
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
    print("    python tests/github_mcp/test_github_mcp.py")
    print()
    print("  Get a token at: https://github.com/settings/tokens")
    print("=" * 70)
    sys.exit(1)

os.environ["GITHUB_TOKEN"] = GITHUB_TOKEN
os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = GITHUB_TOKEN

TEST_OWNER = os.environ.get("GITHUB_TEST_OWNER", "Muhammad-Anique")
TEST_REPO_PUBLIC = "agno-test-repo"
TEST_REPO_PRIVATE = "agno-test-private"


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

def log_error(message: str, error: Exception = None):
    print(f"  ERROR: {message}")
    if error:
        print(f"     Details: {str(error)}")

def log_info(message: str):
    print(f"  INFO: {message}")

def log_data(label: str, data):
    if isinstance(data, (dict, list)):
        print(f"  {label}:")
        for line in json.dumps(data, indent=4).split("\n"):
            print(f"     {line}")
    else:
        print(f"  {label}: {data}")

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
# MCP Test
# ---------------------------------------------------------------------------

async def run_mcp_tests():
    from agno.tools.mcp import MCPTools

    log_section("GITHUB MCP COMPREHENSIVE TEST")
    log_info(f"Timestamp: {datetime.now().isoformat()}")
    log_info(f"Token: {GITHUB_TOKEN[:10]}...{GITHUB_TOKEN[-4:]}")
    log_info(f"Test Owner: {TEST_OWNER}")
    log_info(f"Public Repo: {TEST_REPO_PUBLIC}")
    log_info(f"Private Repo: {TEST_REPO_PRIVATE}")

    # Step 1: Initialize MCP
    log_step(1, "Initialize GitHub MCP")
    try:
        github_mcp = MCPTools(
            command="npx -y @modelcontextprotocol/server-github",
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_TOKEN},
            timeout_seconds=60,
        )
        log_success("MCPTools instance created")
    except Exception as e:
        log_error("Failed to create MCPTools", e)
        return

    # Step 2: Connect
    log_step(2, "Connect to MCP Server")
    try:
        await github_mcp.connect()
        log_success("Connected to MCP server")
    except Exception as e:
        log_error("Failed to connect to MCP server", e)
        import traceback
        traceback.print_exc()
        return

    # Step 3: List tools
    log_step(3, "Get Session and List Available Tools")
    try:
        session = await github_mcp.get_session_for_run()
        log_success(f"Got session: {type(session).__name__}")
        tools_list = await session.list_tools()
        log_success(f"Found {len(tools_list.tools)} tools")
        log_info("Available tools:")
        for tool in tools_list.tools:
            print(f"     - {tool.name}")
    except Exception as e:
        log_error("Failed to get session or list tools", e)
        import traceback
        traceback.print_exc()
        return

    # ======================================================================
    # PUBLIC REPOSITORY TESTS
    # ======================================================================
    log_section("PUBLIC REPOSITORY TESTS")

    # Step 4: Create public repo
    log_step(4, f"Create Public Repository: {TEST_REPO_PUBLIC}")
    try:
        result = await session.call_tool("create_repository", {
            "name": TEST_REPO_PUBLIC,
            "description": "Test repository for Agno MCP testing (PUBLIC)",
            "private": False,
            "autoInit": True,
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    data = json.loads(content.text)
                    log_success(f"Repository created: {data.get('full_name')}")
                    log_data("Repository Info", {
                        "name": data.get("name"),
                        "html_url": data.get("html_url"),
                        "private": data.get("private"),
                    })
    except Exception as e:
        if "already exists" in str(e).lower() or "422" in str(e):
            log_info(f"Repository {TEST_REPO_PUBLIC} already exists, continuing...")
        else:
            log_error("Failed to create repository", e)

    await asyncio.sleep(2)

    # Step 5: Add file
    log_step(5, f"Add Initial File (hello.txt) to {TEST_REPO_PUBLIC}")
    try:
        file_content = (
            f"Hello from Agno MCP Test!\n\n"
            f"Created: {datetime.now().isoformat()}\n"
            f"Repository: {TEST_REPO_PUBLIC} (PUBLIC)\n"
        )
        result = await session.call_tool("create_or_update_file", {
            "owner": TEST_OWNER,
            "repo": TEST_REPO_PUBLIC,
            "path": "hello.txt",
            "content": file_content,
            "message": "Add hello.txt - Initial file creation test",
            "branch": "main",
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    data = json.loads(content.text)
                    log_success("File created successfully")
                    log_data("Commit", {"sha": data.get("commit", {}).get("sha", "")[:7]})
    except Exception as e:
        log_error("Failed to create initial file", e)

    await asyncio.sleep(1)

    # Step 6: Read file
    log_step(6, f"Read File Content (hello.txt) from {TEST_REPO_PUBLIC}")
    try:
        result = await session.call_tool("get_file_contents", {
            "owner": TEST_OWNER,
            "repo": TEST_REPO_PUBLIC,
            "path": "hello.txt",
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    data = json.loads(content.text)
                    log_success("File read successfully")
                    if data.get("content"):
                        decoded = decode_base64_content(data["content"])
                        log_info(f"Content:\n{decoded[:200]}")
    except Exception as e:
        log_error("Failed to read file", e)

    # Step 7: Update file
    log_step(7, f"Update Existing File (hello.txt) in {TEST_REPO_PUBLIC}")
    try:
        updated = (
            f"Hello from Agno MCP Test - UPDATED!\n\n"
            f"Updated: {datetime.now().isoformat()}\n"
            f"Repository: {TEST_REPO_PUBLIC} (PUBLIC)\n"
        )
        result = await session.call_tool("create_or_update_file", {
            "owner": TEST_OWNER,
            "repo": TEST_REPO_PUBLIC,
            "path": "hello.txt",
            "content": updated,
            "message": "Update hello.txt - Testing update operation",
            "branch": "main",
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    data = json.loads(content.text)
                    log_success("File updated successfully")
    except Exception as e:
        log_error("Failed to update file", e)

    await asyncio.sleep(1)

    # Step 8: Nested file
    log_step(8, f"Add Nested File (src/config.json) to {TEST_REPO_PUBLIC}")
    try:
        config = json.dumps({
            "name": "agno-test",
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
        }, indent=2)
        result = await session.call_tool("create_or_update_file", {
            "owner": TEST_OWNER,
            "repo": TEST_REPO_PUBLIC,
            "path": "src/config.json",
            "content": config,
            "message": "Add src/config.json - Nested file creation",
            "branch": "main",
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    log_success("Nested file created")
    except Exception as e:
        log_error("Failed to create nested file", e)

    # ======================================================================
    # PRIVATE REPOSITORY TESTS
    # ======================================================================
    log_section("PRIVATE REPOSITORY TESTS")

    # Step 9: Create private repo
    log_step(9, f"Create PRIVATE Repository: {TEST_REPO_PRIVATE}")
    try:
        result = await session.call_tool("create_repository", {
            "name": TEST_REPO_PRIVATE,
            "description": "Test repository for Agno MCP testing (PRIVATE)",
            "private": True,
            "autoInit": True,
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    data = json.loads(content.text)
                    log_success(f"PRIVATE repository created: {data.get('full_name')}")
    except Exception as e:
        if "already exists" in str(e).lower() or "422" in str(e):
            log_info(f"Repository {TEST_REPO_PRIVATE} already exists, continuing...")
        else:
            log_error("Failed to create private repository", e)

    await asyncio.sleep(2)

    # Step 10: Add file to private repo
    log_step(10, f"Add File (secret.txt) to PRIVATE repo {TEST_REPO_PRIVATE}")
    try:
        secret = (
            f"Private repo test file.\n"
            f"Created: {datetime.now().isoformat()}\n"
        )
        result = await session.call_tool("create_or_update_file", {
            "owner": TEST_OWNER,
            "repo": TEST_REPO_PRIVATE,
            "path": "secret.txt",
            "content": secret,
            "message": "Add secret.txt - Private repo test",
            "branch": "main",
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    log_success("File created in PRIVATE repo")
    except Exception as e:
        log_error("Failed to create file in private repo", e)

    await asyncio.sleep(1)

    # Step 11: Read from private repo
    log_step(11, f"Read File (secret.txt) from PRIVATE repo {TEST_REPO_PRIVATE}")
    try:
        result = await session.call_tool("get_file_contents", {
            "owner": TEST_OWNER,
            "repo": TEST_REPO_PRIVATE,
            "path": "secret.txt",
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    data = json.loads(content.text)
                    log_success("File read from PRIVATE repo")
                    if data.get("content"):
                        decoded = decode_base64_content(data["content"])
                        log_info(f"Content:\n{decoded[:200]}")
    except Exception as e:
        log_error("Failed to read file from private repo", e)

    # Step 12: Update in private repo
    log_step(12, f"Update File (secret.txt) in PRIVATE repo {TEST_REPO_PRIVATE}")
    try:
        updated_secret = (
            f"Private repo test file - UPDATED!\n"
            f"Updated: {datetime.now().isoformat()}\n"
        )
        result = await session.call_tool("create_or_update_file", {
            "owner": TEST_OWNER,
            "repo": TEST_REPO_PRIVATE,
            "path": "secret.txt",
            "content": updated_secret,
            "message": "Update secret.txt - Private repo update test",
            "branch": "main",
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    log_success("File UPDATED in PRIVATE repo")
    except Exception as e:
        log_error("Failed to update file in private repo", e)

    # Step 13: Nested file in private repo
    log_step(13, "Add Nested File (config/settings.json) to PRIVATE repo")
    try:
        settings = json.dumps({
            "app_name": "agno-private-test",
            "private": True,
            "created_at": datetime.now().isoformat(),
        }, indent=2)
        result = await session.call_tool("create_or_update_file", {
            "owner": TEST_OWNER,
            "repo": TEST_REPO_PRIVATE,
            "path": "config/settings.json",
            "content": settings,
            "message": "Add config/settings.json - Nested file in private repo",
            "branch": "main",
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    log_success("Nested file created in PRIVATE repo")
    except Exception as e:
        log_error("Failed to create nested file in private repo", e)

    # ======================================================================
    # GENERAL TESTS
    # ======================================================================
    log_section("GENERAL TESTS")

    # Step 14: Search repos
    log_step(14, "Search Repositories (query: 'agno python')")
    try:
        result = await session.call_tool("search_repositories", {
            "query": "agno python",
            "page": 1,
            "perPage": 5,
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    data = json.loads(content.text)
                    log_success(f"Search found {data.get('total_count', 0)} repos")
                    for item in data.get("items", [])[:5]:
                        print(f"     - {item.get('full_name')}")
    except Exception as e:
        log_error("Failed to search repositories", e)

    # Step 15: List commits (public)
    log_step(15, f"List Commits in PUBLIC repo {TEST_REPO_PUBLIC}")
    try:
        result = await session.call_tool("list_commits", {
            "owner": TEST_OWNER,
            "repo": TEST_REPO_PUBLIC,
            "page": 1,
            "perPage": 5,
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    data = json.loads(content.text)
                    if isinstance(data, list):
                        log_success(f"Found {len(data)} commits")
                        for c in data[:5]:
                            sha = c.get("sha", "")[:7]
                            msg = c.get("commit", {}).get("message", "").split("\n")[0][:50]
                            print(f"     - {sha}: {msg}")
    except Exception as e:
        log_error("Failed to list commits", e)

    # Step 16: List commits (private)
    log_step(16, f"List Commits in PRIVATE repo {TEST_REPO_PRIVATE}")
    try:
        result = await session.call_tool("list_commits", {
            "owner": TEST_OWNER,
            "repo": TEST_REPO_PRIVATE,
            "page": 1,
            "perPage": 5,
        })
        if result.content:
            for content in result.content:
                if hasattr(content, "text"):
                    data = json.loads(content.text)
                    if isinstance(data, list):
                        log_success(f"Found {len(data)} commits in PRIVATE repo")
                        for c in data[:5]:
                            sha = c.get("sha", "")[:7]
                            msg = c.get("commit", {}).get("message", "").split("\n")[0][:50]
                            print(f"     - {sha}: {msg}")
    except Exception as e:
        log_error("Failed to list commits in private repo", e)

    # Step 17: Verify updates
    log_step(17, "Verify File Updates")
    for repo, path in [(TEST_REPO_PUBLIC, "hello.txt"), (TEST_REPO_PRIVATE, "secret.txt")]:
        try:
            result = await session.call_tool("get_file_contents", {
                "owner": TEST_OWNER,
                "repo": repo,
                "path": path,
            })
            if result.content:
                for content in result.content:
                    if hasattr(content, "text"):
                        data = json.loads(content.text)
                        if data.get("content"):
                            decoded = decode_base64_content(data["content"])
                            if "UPDATED" in decoded:
                                log_success(f"{repo}/{path} update verified")
                            else:
                                log_error(f"{repo}/{path} update NOT verified")
        except Exception as e:
            log_error(f"Failed to verify {repo}/{path}", e)

    # Step 18: Close
    log_step(18, "Close MCP Connection")
    try:
        await github_mcp.close()
        log_success("MCP connection closed")
    except Exception as e:
        log_error("Failed to close MCP connection", e)

    # Summary
    log_section("TEST SUMMARY")
    print(f"""
  PUBLIC Repository:  https://github.com/{TEST_OWNER}/{TEST_REPO_PUBLIC}
  PRIVATE Repository: https://github.com/{TEST_OWNER}/{TEST_REPO_PRIVATE}

  18 tests completed.
  Timestamp: {datetime.now().isoformat()}
""")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  AGNO GITHUB MCP TEST SUITE")
    print("=" * 70)
    try:
        asyncio.run(run_mcp_tests())
    except Exception as e:
        log_section("FATAL ERROR")
        log_error("Test suite failed", e)
        import traceback
        traceback.print_exc()
    print("=" * 70)
    print("  TEST COMPLETE")
    print("=" * 70 + "\n")

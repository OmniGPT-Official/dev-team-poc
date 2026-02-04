# GitHub MCP Tests

Tests for GitHub operations via the Model Context Protocol (MCP).

## Quick Start

```bash
# Set your GitHub Personal Access Token
export GITHUB_TOKEN="ghp_YourRealTokenHere"

# Run the comprehensive test
python tests/github_mcp/test_github_mcp.py

# Run the private repo read test
python tests/github_mcp/test_read_private_repo.py
```

## Get a Token

1. Go to https://github.com/settings/tokens
2. Generate a new token (classic)
3. Select scopes: `repo`, `read:org`
4. Copy the token

## Files

| File | Purpose |
|------|---------|
| `test_github_mcp.py` | Full test: create repos, add/read/update files, search, list commits |
| `test_read_private_repo.py` | Read files from a private repository |

## What Gets Tested

### test_github_mcp.py (18 steps)
- MCP initialization and connection
- Public repo: create, add file, read, update, nested file
- Private repo: create, add file, read, update, nested file
- Search repositories
- List commits (public + private)
- Verify updates

### test_read_private_repo.py
- Connect to GitHub MCP
- List private repo contents
- Read multiple files (README.md, secret.txt, config/settings.json)
- Decode base64 content

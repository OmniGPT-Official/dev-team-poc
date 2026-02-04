# MCP (Model Context Protocol) Setup Guide

This guide explains how MCP servers work in Agent OS and how to set them up properly for both local development and production deployment.

## What is MCP?

**Model Context Protocol (MCP)** is a standard protocol that allows AI agents to interact with external services and tools. In Agent OS, MCP servers provide agents with capabilities to:

- **GitHub MCP**: Create repositories, read/write files, manage pull requests
- **Supabase MCP**: Interact with Supabase databases (optional)
- **Vercel MCP**: Deploy and manage Vercel projects (optional)

## How MCP Works in Agent OS

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│ FastAPI App (agno_agent.py)                            │
│ Accessible in browser at /docs                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Agents (Software Engineer, Lead Engineer, etc.)        │
│ When workflows run, agents spawn MCP servers           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ MCP Servers (spawned via npx as subprocesses)          │
│ - @modelcontextprotocol/server-github                  │
│ - @supabase/mcp-server-supabase                        │
│ - mcp-remote (for Vercel)                              │
└─────────────────────────────────────────────────────────┘
```

### Key Points

1. **MCP servers are NOT web services** - they run as subprocesses, not browser-accessible endpoints
2. **Same behavior locally and in production** - MCP servers work identically whether you're running locally or on Railway
3. **Downloaded on first use** - `npx -y` downloads MCP packages on first run (30-60 seconds)
4. **Require authentication tokens** - Without tokens, tools will fail with "Unauthorized" errors

## GitHub MCP Setup (Required)

GitHub MCP is **REQUIRED** for workflows to function. Without it, agents cannot:
- Create repositories for new projects
- Store workflow outputs (PRDs, code reviews, security reviews)
- Read/write files to the `.dev-team/` folder structure

### Step 1: Create GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Give it a descriptive name: `Agent OS Development`
4. Set expiration (recommend: 90 days for development, no expiration for production)
5. Select scopes:
   - ✅ **repo** (Full control of private repositories)
     - This includes: repo:status, repo_deployment, public_repo, repo:invite, security_events
6. Click **"Generate token"**
7. **IMPORTANT**: Copy the token immediately - you won't see it again!

### Step 2: Add Token to Environment

#### For Local Development:

Edit your `.env` file:
```bash
GITHUB_TOKEN=ghp_your_token_here_1234567890abcdefghijklmnopqrstuvwxyz
```

#### For Railway Deployment:

1. Go to your Railway project dashboard
2. Click on **"Variables"** tab
3. Add new variable:
   - Name: `GITHUB_TOKEN`
   - Value: `ghp_your_token_here...`
4. Save and redeploy

### Step 3: Verify Setup

Start your application and check logs for:
```
✅ GitHub MCP server initialized successfully
```

If you see errors like:
```
❌ Unauthorized: Bad credentials
```
Your token is missing or invalid.

## Supabase MCP Setup (Optional)

Only needed if you're using Supabase database features.

### Step 1: Get Supabase Access Token

1. Go to https://supabase.com/dashboard
2. Select your project
3. Go to **Settings** → **API**
4. Copy the **"service_role"** key (NOT the "anon" key)

### Step 2: Add to Environment

```bash
# Local (.env file)
SUPABASE_ACCESS_TOKEN=your_supabase_service_role_key_here

# Railway (Variables tab)
SUPABASE_ACCESS_TOKEN=your_supabase_service_role_key_here
```

## Vercel MCP Setup (Optional)

Only needed if you're using Vercel deployment features.

### Step 1: Create Vercel Token

1. Go to https://vercel.com/account/tokens
2. Click **"Create Token"**
3. Give it a name: `Agent OS`
4. Set scope: Full Account access (or specific team)
5. Click **"Create"**
6. Copy the token

### Step 2: Add to Environment

```bash
# Local (.env file)
VERCEL_TOKEN=your_vercel_token_here

# Railway (Variables tab)
VERCEL_TOKEN=your_vercel_token_here
```

## Complete .env File Example

Here's what your `.env` file should look like:

```bash
# Required for AI agents
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Required for Agent OS security
OS_SECURITY_KEY=omnigpt

# Required for GitHub MCP (workflows need this!)
GITHUB_TOKEN=ghp_your_github_token_here

# Optional: Only if using Supabase
SUPABASE_ACCESS_TOKEN=your_supabase_token_here

# Optional: Only if using Vercel
VERCEL_TOKEN=your_vercel_token_here

# Server port (Railway overrides this automatically)
PORT=8000
```

## Testing Your Setup

### Local Testing

1. Start the server:
```bash
cp .env.example .env
# Edit .env with your tokens
uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

2. Open browser to http://localhost:8000/docs

3. Test a workflow by sending a request to `/workflows/software_development` endpoint

4. Check logs for MCP initialization:
```
INFO: MCP servers initialized
INFO: - GitHub MCP: ✅
INFO: - Supabase MCP: ✅ (if configured)
INFO: - Vercel MCP: ✅ (if configured)
```

### Railway Testing

1. Push your code to GitHub
2. Deploy on Railway
3. Set environment variables in Railway dashboard
4. Check deployment logs for MCP initialization
5. First deployment may take longer (npx downloads packages)

## Troubleshooting

### Error: "Unauthorized" when workflows run

**Cause**: `GITHUB_TOKEN` is missing or invalid

**Solution**:
- Check that `GITHUB_TOKEN` is set in environment variables
- Verify token has `repo` scope
- Regenerate token if it expired
- Restart application after setting token

### Error: "Repository name already exists"

**Cause**: Trying to create a repo that already exists (this was fixed in commit 0109bc5)

**Solution**:
- Update to latest code - workflow now checks if repo exists first
- Or manually delete the existing repo and try again

### Error: "MCP server timeout"

**Cause**: First-time `npx` download taking too long (>60 seconds)

**Solution**:
- Wait for first initialization to complete (can take 1-2 minutes)
- On Railway: Check logs and wait for "Downloaded @modelcontextprotocol/server-github"
- Subsequent runs will be fast (packages are cached)

### Error: "Cannot find module '@modelcontextprotocol/server-github'"

**Cause**: NPX failed to download the package

**Solution**:
- Check internet connectivity
- Verify Railway has network access
- Check for npm registry issues
- Try redeploying to trigger fresh download

### Workflows fail silently with no error

**Cause**: Missing environment variables causing agents to skip GitHub operations

**Solution**:
- Check ALL required environment variables are set:
  - `ANTHROPIC_API_KEY`
  - `OS_SECURITY_KEY`
  - `GITHUB_TOKEN` (most commonly forgotten!)
- Restart the application

## How Workflows Use GitHub MCP

When you run a workflow (e.g., Software Development workflow):

1. **Product Discovery Phase**
   - Creates PRD and stores it in `.dev-team/implementations/` folder in GitHub repo

2. **Architecture Design Phase**
   - Creates technical design and stores in `.dev-team/implementations/` folder

3. **Implementation Cycle** (3 iterations max)
   - Software Engineer writes code → stored in GitHub repo
   - Lead Engineer reviews → stored in `.dev-team/code_reviews/`
   - Security Engineer reviews → stored in `.dev-team/security_reviews/`

### GitHub Repository Structure

Workflows create this structure in your GitHub repos:

```
your-project-repo/
├── .dev-team/
│   ├── implementations/
│   │   └── software_engineer_[product_name].py
│   ├── code_reviews/
│   │   └── lead_engineer_review_[product_name].md
│   └── security_reviews/
│       └── security_engineer_review_[product_name].md
└── [your actual project files]
```

## Security Best Practices

1. **Never commit tokens to git**
   - `.env` file is in `.gitignore`
   - Use `.env.example` for templates only

2. **Use tokens with minimal required scopes**
   - GitHub: Only `repo` scope
   - Supabase: Use service_role key only in secure environments
   - Vercel: Limit to specific team if possible

3. **Rotate tokens regularly**
   - Especially for production deployments
   - Set expiration dates for development tokens

4. **Use different tokens for different environments**
   - Development: Personal Access Token with expiration
   - Production: Dedicated token for the deployment
   - Never share tokens between team members

## FAQ

### Q: Do I need MCP tokens for local testing?
**A:** Yes! MCP servers work the same locally and in production. You need at least `GITHUB_TOKEN` for workflows to function.

### Q: Can I use the app without MCP tokens?
**A:** The app will start, but workflows that require GitHub MCP (most of them) will fail with authorization errors.

### Q: Do MCP servers need to be deployed separately?
**A:** No! MCP servers are spawned automatically by agents when workflows run. You don't deploy them separately.

### Q: Why does first deployment take so long?
**A:** First run downloads MCP server packages via `npx`. This can take 30-60 seconds. Subsequent runs use cached packages.

### Q: Can I use GitHub MCP with public repos only?
**A:** Yes, but you still need the `repo` scope token for creating repos and writing files.

### Q: What if I don't want to use GitHub for storage?
**A:** Currently, workflows are designed to use GitHub MCP for file storage. You'd need to modify the workflow code to use local files or another storage system.

## Support

If you continue having issues:

1. Check this guide thoroughly
2. Review the [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for deployment-specific issues
3. Check the [SETUP_GUIDE.md](SETUP_GUIDE.md) for general setup
4. Enable debug logging to see MCP server initialization details
5. Verify all environment variables are set correctly with `printenv | grep TOKEN`

## Summary Checklist

Before running workflows, ensure:

- ✅ Created GitHub Personal Access Token with `repo` scope
- ✅ Added `GITHUB_TOKEN` to `.env` file (local) or Railway variables (production)
- ✅ Added `ANTHROPIC_API_KEY` and `OS_SECURITY_KEY`
- ✅ Restarted application after setting tokens
- ✅ Verified MCP servers initialized successfully in logs
- ✅ Tested a workflow to confirm GitHub integration works

With proper MCP setup, your workflows will seamlessly create repos, store files, and manage the entire development lifecycle through GitHub!

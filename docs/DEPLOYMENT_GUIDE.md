# Vercel Deployment Guide

This guide explains how to deploy projects to Vercel using Agent-OS, both for testing and in production workflows.

## Prerequisites

You need:
1. ✅ **Vercel Account** - [Sign up](https://vercel.com/signup)
2. ✅ **Vercel Token** - [Create token](https://vercel.com/account/tokens)
3. ✅ **GitHub Repository** - With code to deploy
4. ✅ **GitHub Token** - [Create token](https://github.com/settings/tokens) (optional but recommended)

---

## Method 1: Test Deployment (Manual)

Use this to **test deployment** before running the full workflow.

### Quick Test

```bash
# Set required environment variables
export VERCEL_TOKEN="your_vercel_token"
export GITHUB_OWNER="Muhammad-Anique"
export GITHUB_REPO="your-repo-name"
export PROJECT_NAME="your-project-name"

# Run test
python tests/test_vercel_deploy.py
```

### With Command-Line Arguments

```bash
python tests/test_vercel_deploy.py \
  --github-owner "Muhammad-Anique" \
  --github-repo "your-repo-name" \
  --project-name "your-project" \
  --vercel-token "your_vercel_token"
```

### Expected Output

```
======================================================================
  VERCEL DEPLOYMENT TEST
======================================================================
  Timestamp:           2024-02-04T10:30:00

======================================================================
  CONFIGURATION
======================================================================
  GitHub Owner:        Muhammad-Anique
  GitHub Repo:         your-repo-name
  Project Name:        your-project
  Vercel Token:        sQM0sYnK...CuVi
  GitHub Token:        ✓ Set
  Repo URL:            https://github.com/Muhammad-Anique/your-repo-name

======================================================================
  DEPLOYING TO VERCEL
======================================================================

  Calling deploy_to_vercel()...
  This will deploy: Muhammad-Anique/your-repo-name
  As project: your-project

  Please wait (this may take 2-5 minutes)...

[deploy.js] Creating deployment: Muhammad-Anique/your-repo-name
[deploy.js] Project name: your-project
[deploy.js] Created — id=dpl_xxx status=BUILDING
  [poll 1] state=BUILDING
  [poll 2] state=BUILDING
  [poll 3] state=READY

======================================================================
  DEPLOYMENT RESULT
======================================================================

{"success": true, "url": "https://your-project-xxx.vercel.app"}

✅ DEPLOYMENT SUCCESSFUL!
  Live URL:            https://your-project-xxx.vercel.app

======================================================================
  TEST PASSED ✓
======================================================================
```

---

## Method 2: Workflow Deployment (Automatic)

The **Software Development Workflow** automatically deploys after implementation.

### Setup

```bash
# Set ALL required environment variables
export ANTHROPIC_API_KEY="your_anthropic_key"
export GITHUB_TOKEN="your_github_token"
export GITHUB_OWNER="Muhammad-Anique"
export VERCEL_TOKEN="your_vercel_token"
export GOOGLE_CLIENT_ID="your_google_client_id"
export GOOGLE_CLIENT_SECRET="your_google_client_secret"

# Start the server
source venv/bin/activate
uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

### Workflow Flow

1. **Read Architecture** from Google Docs
2. **Create GitHub Repo** (if needed)
3. **Implementation Cycle** (max 2 iterations):
   - Software Engineer writes code
   - Lead Engineer reviews code
   - Loop until approved
4. **Deploy to Vercel** ← Automatic deployment happens here
5. **Summary** with deployment link

### What Happens During Deployment

```
🚀 [DEPLOY] Deploying to Vercel...
📋 [DEPLOY] Owner: Muhammad-Anique, Repo: your-repo, Project: your-project
🤖 [DEPLOY] Asking agent to deploy...

[deploy.js] Creating deployment: Muhammad-Anique/your-repo
[deploy.js] Project name: your-project
[deploy.js] Created — id=dpl_xxx status=BUILDING
  [poll 1] state=BUILDING
  [poll 2] state=READY

✅ [DEPLOY] Deployment complete
```

### Workflow Output

```markdown
## ✅ Implementation Complete!

**Project:** Your Project Name
**Iterations:** 1

### Links
- 🚀 **Live:** https://your-project-xxx.vercel.app
- 📂 **GitHub:** https://github.com/Muhammad-Anique/your-repo
- 💻 **Code:** https://github.com/Muhammad-Anique/your-repo/blob/main/.dev-team/implementations/your-project.py

### Review
- Code Review (Quality + Security + Conventions): approved
```

---

## Troubleshooting

### Error: "VERCEL_TOKEN not set"

**Fix:**
```bash
export VERCEL_TOKEN="your_vercel_token"
```

### Error: "invalid_project_name"

**Cause:** Project name has uppercase or invalid characters

**Fix:** Already handled! The deployment script now automatically sanitizes:
- Converts to lowercase
- Replaces invalid chars with `-`
- Limits to 100 characters

### Error: "missing_project_settings"

**Cause:** Vercel requires framework settings for new projects

**Fix:** Already handled! Now uses `skipAutoDetectionConfirmation=1`

### Error: "Repository not found" (404)

**Causes:**
1. Repository doesn't exist
2. GitHub token doesn't have access
3. Repository name is wrong

**Fix:**
```bash
# Verify repo exists
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/Muhammad-Anique/your-repo

# Check GITHUB_OWNER matches your GitHub username
echo $GITHUB_OWNER
```

### Deployment Hangs

**Cause:** Large repository or slow build

**Fix:** Increase timeout (already set to 10 minutes):
```python
# In workflow: timeout_seconds=600 (10 min)
```

### Agent Not Calling Tool

**Symptoms:** No deployment attempts in logs

**Fix:** Verify agent has the tool:
```python
# In agents/software_engineer.py
tools=[
    github_tools,
    supabase_mcp,
    vercel_deploy_tools,  # ← Must be present
],
```

---

## Environment Variables Reference

### Required for Testing

```bash
VERCEL_TOKEN="your_vercel_token"      # From vercel.com/account/tokens
GITHUB_OWNER="Muhammad-Anique"         # Your GitHub username/org
GITHUB_REPO="your-repo-name"           # Repository name
PROJECT_NAME="your-project-name"       # Vercel project name
```

### Required for Workflow

```bash
# AI & APIs
ANTHROPIC_API_KEY="sk-ant-..."
OPENAI_API_KEY="sk-..."               # Optional

# GitHub
GITHUB_TOKEN="ghp_..."                # Personal access token
GITHUB_OWNER="Muhammad-Anique"

# Vercel
VERCEL_TOKEN="..."                    # API token

# Google (for Docs)
GOOGLE_CLIENT_ID="...apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="GOCSPX-..."

# Supabase (optional)
SUPABASE_ACCESS_TOKEN="sbp_..."
DATABASE_URL="postgresql://..."
```

---

## Tips

1. **Test First**: Always run the test script before using the workflow
2. **Use .env**: Store tokens in `.env` file (add to `.gitignore`!)
3. **Check Logs**: Watch for the deployment logs to debug issues
4. **Verify Repo**: Make sure the GitHub repo exists and has code on `main` branch
5. **Wait Time**: Deployments can take 2-5 minutes, be patient

---

## Quick Reference

| Action | Command |
|--------|---------|
| Test deployment | `python tests/test_vercel_deploy.py` |
| Run workflow | Start server, then trigger via API |
| Check deployment | Visit Vercel dashboard |
| View logs | Check terminal output during deployment |
| Debug issues | Run test script with verbose output |

---

## Support

If deployment fails:
1. Run the test script first to isolate the issue
2. Check the error logs carefully
3. Verify all environment variables are set
4. Ensure GitHub repo exists and is accessible
5. Check Vercel dashboard for deployment status

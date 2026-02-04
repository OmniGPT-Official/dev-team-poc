# Setup Gmail & Sheets Integration on Your Mac

## Quick Setup (Run these commands on your Mac)

### Step 1: Switch to the Gmail Integration Branch

```bash
# Make sure you're in the project directory
cd /tmp/dev-team-poc-clean  # or wherever your clone is

# Fetch all branches from GitHub
git fetch origin

# Switch to the Gmail integration branch
git checkout claude/add-gmail-sheets-integration-fIuCb

# Pull the latest changes
git pull origin claude/add-gmail-sheets-integration-fIuCb
```

### Step 2: Create Your .env File

```bash
# Copy the template
cp .env.local.template .env

# Open .env in your editor
nano .env  # or: code .env  # or: vim .env
```

### Step 3: Add Your API Keys to .env

**IMPORTANT:** Replace the placeholder values below with your actual API keys.
You should have received these keys separately (not committed to GitHub for security).

If you don't have the keys, refer to the comments in `.env.local.template` for where to get them.

Replace the placeholder values with your actual keys:

```bash
# ============================================
# ENVIRONMENT CONFIGURATION
# ============================================

OS_SECURITY_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyT10RGyzdscB2dx+cTNR
3vMlQrtJ+rB3Qhq/b7CM7EWYqfZ/zYx0CxJi4hVmWFRWv+VZ63s6rBf1g653qB8D
MuuDrGP2MJkbcT6d5l7Qg+qAWq+ITdEPAVRQ3BZUEke0hA3jZVfCPHoN7DvK6nVb
BXTnA/EjYknULrIr4owsLAZ7J2J80X4FC/ZpppSlumkqP36y45QLu1TSs+ob5t1P
9lTzcLYY8e3NPMeRtXzDmQd+XfM2CxhiM95Pu1R16ldgVCAZ7OhQB5g/9cSwNTxP
H1a0XO87Ek3+5uLh2L+4OzKweCA4Zz+4rJe/+xU9pnk8FGLRe7dqYHxUuLoYqXe6
0QIDAQAB
-----END PUBLIC KEY-----"

# Google API Key (for Gemini model)
GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"

# OpenAI API Key (for image generation)
OPENAI_API_KEY="YOUR_OPENAI_API_KEY_HERE"

# ============================================
# MCP SERVER CREDENTIALS
# ============================================

# GitHub Token
GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"

# Vercel Token
VERCEL_TOKEN="YOUR_VERCEL_TOKEN_HERE"

# Supabase Access Token
SUPABASE_ACCESS_TOKEN="YOUR_SUPABASE_TOKEN_HERE"

# ============================================
# GOOGLE OAUTH CREDENTIALS (For Follow-Up Manager)
# ============================================

GOOGLE_OAUTH_CLIENT_ID="YOUR_GOOGLE_OAUTH_CLIENT_ID_HERE"
GOOGLE_OAUTH_CLIENT_SECRET="YOUR_GOOGLE_OAUTH_CLIENT_SECRET_HERE"
GOOGLE_OAUTH_REFRESH_TOKEN="YOUR_GOOGLE_OAUTH_REFRESH_TOKEN_HERE"
```

### Step 4: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install google-auth-oauthlib for OAuth
pip install google-auth-oauthlib
```

### Step 5: Start the Server

```bash
uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

### Step 6: Verify Everything Works

The server should start without errors. You should see:
- ✅ No "OpenAI API key not set" error
- ✅ No "Google OAuth credentials not configured" warning
- ✅ "Sales Follow-Up Manager" workflow available

---

## What's on This Branch?

The `claude/add-gmail-sheets-integration-fIuCb` branch includes:

### 1. Enhanced Agent Instructions
File: `instructions/sales_followup_instructions.py`

Added detailed MCP tool usage examples for:
- **Sheet Analyzer** - How to use `read_spreadsheet` with Google Sheets
- **Context Researcher** - How to use `search_gmail` and `get_gmail_message`
- **Follow-Up Coordinator** - How to use `send_gmail_message` and `update_spreadsheet`

### 2. Complete Integration Guide
File: `GMAIL_SHEETS_INTEGRATION_GUIDE.md`

Comprehensive documentation including:
- Quick setup walkthrough
- All available MCP tools
- Usage examples for common scenarios
- Troubleshooting guide
- Best practices

### 3. All Previous Features

This branch is based on the latest code and includes everything that was already there.

---

## Common Issues

### "Branch not found"

If you get an error about the branch not existing:

```bash
# List all remote branches
git branch -r

# If you see the branch, fetch it
git fetch origin claude/add-gmail-sheets-integration-fIuCb

# Then checkout
git checkout claude/add-gmail-sheets-integration-fIuCb
```

### "Already on main"

If you're still on main after following steps:

```bash
# Force checkout the branch
git checkout -B claude/add-gmail-sheets-integration-fIuCb origin/claude/add-gmail-sheets-integration-fIuCb
```

### "Modified files" warning

If git warns about modified files:

```bash
# Stash your changes
git stash

# Then checkout the branch
git checkout claude/add-gmail-sheets-integration-fIuCb

# Optionally restore your changes
git stash pop
```

---

## Next Steps

Once everything is running:

1. ✅ Review `GMAIL_SHEETS_INTEGRATION_GUIDE.md` for detailed usage instructions
2. ✅ Create a Google Sheet with your contacts (see guide for format)
3. ✅ Run the Sales Follow-Up Manager workflow
4. ✅ Test with a small number of contacts first

---

## Files Changed on This Branch

```
Modified:
  instructions/sales_followup_instructions.py

Created:
  GMAIL_SHEETS_INTEGRATION_GUIDE.md
  SETUP_ON_MAC.md (this file)
```

All changes have been committed and pushed to GitHub.

---

## Need Help?

Check the documentation:
- `GMAIL_SHEETS_INTEGRATION_GUIDE.md` - Complete integration guide
- `GOOGLE_MCP_SETUP.md` - OAuth setup details
- `MCP_SETUP_GUIDE.md` - General MCP configuration
- `workflows/FOLLOWUP_MANAGER_README.md` - Workflow details

The integration is complete and ready to use! 🚀

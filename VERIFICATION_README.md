# 🔍 Pre-Deployment Verification System

## Quick Start

**Before creating any PR, run this command:**

```bash
python3 scripts/verify_deployment.py
```

**That's it!** The agent will check your changes and tell you if they're safe to deploy.

---

## What It Does

Catches deployment-blocking errors before you push:

✅ **Syntax errors** - Python won't compile
✅ **Import errors** - Wrong module names (like the `agno.tools.google` error we just fixed!)
✅ **Database changes** - Unauthorized `db.py` modifications
✅ **Missing registrations** - New agents not added to `agno_agent.py`
✅ **Environment variables** - New required env vars
✅ **Workflow issues** - Broken Agno workflow structure

---

## Example Output

### ✅ Success (safe to deploy):

```
🔍 Running Pre-Deployment Verification...

════════════════════════════════════════════════════════════
PRE-DEPLOYMENT VERIFICATION REPORT
════════════════════════════════════════════════════════════

✅ SYNTAX VALIDATION: PASS
✅ IMPORT VALIDATION: PASS
✅ DATABASE SAFETY: PASS
ℹ️  AGENT REGISTRATION: INFO
ℹ️  ENVIRONMENT VARIABLES: INFO
✅ WORKFLOW VALIDATION: PASS

════════════════════════════════════════════════════════════
RESULT: ✅ SAFE TO DEPLOY
════════════════════════════════════════════════════════════

✅ Verification passed - Safe to create PR and deploy!
```

### ❌ Failure (fix before deploying):

```
════════════════════════════════════════════════════════════
PRE-DEPLOYMENT VERIFICATION REPORT
════════════════════════════════════════════════════════════

❌ IMPORT VALIDATION: FAIL
   - Found: from agno.tools.google import GoogleSheetsTools
   - Should be: from agno.tools.googlesheets import GoogleSheetsTools

════════════════════════════════════════════════════════════
RESULT: ❌ DO NOT DEPLOY - FIX ERRORS FIRST
════════════════════════════════════════════════════════════

⚠️  VERIFICATION FAILED - Please fix issues before deploying
```

---

## Your New Workflow

**OLD (without verification):**
1. Write code
2. Push
3. Deploy crashes ❌
4. Debug for 30 minutes
5. Fix and redeploy

**NEW (with verification):**
1. Write code
2. Run `python3 scripts/verify_deployment.py` ✅
3. Fix any issues (10 seconds)
4. Push
5. Deploy succeeds ✅

---

## Setup (One-Time)

### 1. Install Dependencies

```bash
pip install agno openai
```

### 2. Set API Key

Add to your `.env` file or export:

```bash
export OPENAI_API_KEY="sk-..."
```

The verification agent uses `gpt-4o-mini` which is:
- **Fast** (~2 seconds)
- **Cheap** (~$0.001 per verification)
- **Smart** (catches all common errors)

---

## Usage

### Method 1: Command Line (Easiest)

```bash
python3 scripts/verify_deployment.py
```

### Method 2: Git Alias (Convenient)

Add to your `~/.gitconfig` or run:

```bash
git config --global alias.verify '!python3 scripts/verify_deployment.py'
```

Now you can just run:

```bash
git verify
```

### Method 3: Automatic on Push (Safest)

Create `.git/hooks/pre-push`:

```bash
#!/bin/bash
python3 scripts/verify_deployment.py || exit 1
```

Make it executable:

```bash
chmod +x .git/hooks/pre-push
```

Now **every `git push` automatically verifies your code!**

---

## Real Example

**The error you just had:**

```python
# ❌ This caused Railway to crash:
from agno.tools.google import GoogleSheetsTools
```

**Verification would have caught it:**

```
❌ IMPORT VALIDATION: FAIL
   - Invalid import: agno.tools.google does not exist
   - Use: agno.tools.googlesheets
```

**Saved you 20 minutes of debugging!** 🎉

---

## Full Documentation

See `docs/VERIFICATION_GUIDE.md` for:
- Detailed check descriptions
- Troubleshooting guide
- Advanced configuration
- GitHub Actions integration

---

## Quick Reference

| Command | What It Does |
|---------|--------------|
| `python3 scripts/verify_deployment.py` | Run verification check |
| `chmod +x scripts/verify_deployment.py` | Make script executable |
| `./scripts/verify_deployment.py` | Run with `./` (if executable) |

---

## Tips

💡 **Run before every commit** - Catch issues early
💡 **Never skip for "quick fixes"** - Quick fixes = production crashes
💡 **Takes 2 seconds** - Faster than debugging crashes
💡 **Bookmark this command** - You'll use it a lot

---

**Remember:** 2 minutes of verification > 30 minutes of production debugging! ✅

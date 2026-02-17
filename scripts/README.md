# Deployment Verification Script

Automated testing for Railway preview deployments.

## Quick Start

```bash
./verify-deployment.sh <PR_NUMBER>
```

## What It Does

This script automates the manual testing workflow:

**Before (Manual):**
1. ✋ Push branch → Wait for Railway
2. ✋ Check Railway dashboard for crashes
3. ✋ Copy preview URL
4. ✋ Paste into AgentOS to test
5. ✋ Manually approve PR if works

**After (Automated):**
1. ✅ `./verify-deployment.sh 47`
2. ✅ Script does everything above
3. ✅ Auto-approves PR if all checks pass

## Prerequisites

### One-Time Setup (5 minutes)

**1. Install Homebrew (if not installed):**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**2. Install tools:**
```bash
brew install gh jq
```

**3. Authenticate GitHub CLI:**
```bash
gh auth login
# Choose: GitHub.com → HTTPS → Yes → Browser
```

**4. Link Railway project:**
```bash
railway link
# Select: OmniGPT-Official → dev-team-poc
```

**5. Verify setup:**
```bash
gh --version && jq --version && railway --version
# All should show version numbers
```

## Usage

### Basic Usage

```bash
# Test PR #47
./verify-deployment.sh 47
```

### What Happens

**Phase 1: Wait for deployment**
- Polls Railway every 10 seconds (max 5 minutes)
- Shows deployment status (BUILDING → DEPLOYING → SUCCESS)

**Phase 2: Check logs**
- Scans last 200 lines for errors
- Catches: ImportError, SyntaxError, crashes
- Reports any startup failures

**Phase 3: Extract URL**
- Gets preview deployment URL
- Format: `https://dev-team-poc-pr-N.up.railway.app`

**Phase 4: Health check**
- Tests `/health` endpoint
- Verifies deployment is responding

**Phase 5: AgentOS test (optional)**
- Tests in live AgentOS if `AGENTOS_URL` set
- Takes screenshots for review

**Phase 6: Verdict**
- ✅ Auto-approves PR if all phases pass
- ❌ Comments on PR with failure details if any phase fails

### Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Deployment Verification: PR #47
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━ [Phase 1] Waiting for Railway deployment ━━━
  ℹ Attempt 3/30: Status = SUCCESS
  ✓ Deployment is live

━━━ [Phase 2] Checking deployment logs ━━━
  ✓ Logs look clean (0 errors, 1 success indicators)

━━━ [Phase 3] Extracting preview URL ━━━
  ✓ Preview URL: https://dev-team-poc-pr-47.up.railway.app

━━━ [Phase 4] Health endpoint check ━━━
  ✓ Health endpoint: 200 OK

━━━ [Phase 6] Verdict ━━━
  ✓ VERDICT: ALL CHECKS PASSED
  ✓ PR #47 auto-approved. Ready to merge!
```

## Configuration

### Optional: AgentOS Testing

To enable Phase 5 (AgentOS smoke tests):

```bash
# Add to ~/.zshrc or ~/.bashrc
export AGENTOS_URL="https://your-agentos-instance.com"
```

Without this, Phase 5 is skipped (other phases still work).

## Troubleshooting

### "command not found: brew"

Install Homebrew:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### "command not found: gh"

```bash
brew install gh
gh auth login
```

### "Environment not ready yet..." (timeout after 5 min)

Railway PR environments might not be enabled:
1. Go to Railway Dashboard
2. Project Settings → Environments
3. Enable "PR Environments"

### "Health endpoint returned: 404"

Your app might not have a `/health` endpoint. This is optional - the script still validates deployment and logs.

## CI/CD Integration

To run automatically on every PR, add `.github/workflows/verify-deployment.yml`:

```yaml
name: Verify Deployment
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  verify:
    runs-on: ubuntu-latest
    env:
      RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
    steps:
      - uses: actions/checkout@v4
      - name: Install Railway CLI
        run: curl -fsSL https://railway.app/install.sh | sh
      - name: Install tools
        run: |
          sudo apt-get update
          sudo apt-get install -y jq
      - name: Run verification
        run: ./scripts/verify-deployment.sh ${{ github.event.pull_request.number }}
```

## Support

Questions? Check `CLAUDE.md` for coding guidelines or ask in team chat.

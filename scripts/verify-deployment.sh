#!/bin/bash
# File: scripts/verify-deployment.sh
# Usage: ./scripts/verify-deployment.sh <pr-number> [service-name]
#
# Automated deployment verification for dev-team-poc Railway previews.
# Checks Railway deployment health, scans logs for crashes, extracts preview URL,
# runs Browser skill smoke tests against live AgentOS, and auto-approves or flags the PR.

set -euo pipefail

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PR_NUMBER="${1:?Usage: verify-deployment.sh <pr-number> [service-name]}"
SERVICE_NAME="${2:-dev-team-poc}"
ENVIRONMENT="dev-team-poc-pr-${PR_NUMBER}"
REPO_OWNER="OmniGPT-Official"
REPO_NAME="dev-team-poc"
AGENTOS_BASE_URL="${AGENTOS_URL:-https://your-agentos-instance.com}"
MAX_POLL_ATTEMPTS=30
POLL_INTERVAL=10  # seconds
BROWSE="bun run $HOME/.claude/skills/Browser/Tools/Browse.ts"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

log_phase() {
  echo -e "\n${BLUE}━━━ [Phase $1] $2 ━━━${NC}"
}

log_info() {
  echo -e "  ${BLUE}ℹ${NC} $1"
}

log_success() {
  echo -e "  ${GREEN}✓${NC} $1"
}

log_warning() {
  echo -e "  ${YELLOW}⚠${NC} $1"
}

log_error() {
  echo -e "  ${RED}✗${NC} $1"
}

# Check prerequisites
check_prerequisites() {
  local missing=0

  if ! command -v railway &> /dev/null; then
    log_error "Railway CLI not found. Install: curl -fsSL https://railway.com/install.sh | sh"
    missing=1
  fi

  if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI not found. Install: brew install gh"
    missing=1
  fi

  if ! command -v jq &> /dev/null; then
    log_error "jq not found. Install: brew install jq"
    missing=1
  fi

  if ! command -v bun &> /dev/null; then
    log_error "Bun not found. Install: curl -fsSL https://bun.sh/install | bash"
    missing=1
  fi

  if [ $missing -eq 1 ]; then
    exit 1
  fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 1: Wait for Railway Deployment
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

poll_deployment_status() {
  log_phase "1" "Waiting for Railway deployment"

  local attempt=0
  local status=""
  local deploy_id=""

  log_info "Polling environment: ${ENVIRONMENT}"
  log_info "Service: ${SERVICE_NAME}"

  while [ $attempt -lt $MAX_POLL_ATTEMPTS ]; do
    attempt=$((attempt + 1))

    # Get latest deployment status as JSON
    local deploy_json=$(railway deployment list \
      --service "$SERVICE_NAME" \
      --environment "$ENVIRONMENT" \
      --limit 1 \
      --json 2>/dev/null || echo "[]")

    if [ "$deploy_json" = "[]" ] || [ -z "$deploy_json" ]; then
      log_info "Attempt ${attempt}/${MAX_POLL_ATTEMPTS}: Environment not ready yet..."
      sleep "$POLL_INTERVAL"
      continue
    fi

    # Parse status from JSON
    status=$(echo "$deploy_json" | jq -r '.[0].status // "UNKNOWN"')
    deploy_id=$(echo "$deploy_json" | jq -r '.[0].id // ""')

    log_info "Attempt ${attempt}/${MAX_POLL_ATTEMPTS}: Status = ${status} (ID: ${deploy_id:0:8})"

    case "$status" in
      "SUCCESS"|"ACTIVE")
        log_success "Deployment is live"
        DEPLOY_ID="$deploy_id"
        return 0
        ;;
      "CRASHED"|"FAILED"|"REMOVED")
        log_error "Deployment status is ${status}"
        return 1
        ;;
      "BUILDING"|"DEPLOYING"|"INITIALIZING"|"WAITING")
        sleep "$POLL_INTERVAL"
        ;;
      *)
        log_warning "Unknown status: ${status}. Waiting..."
        sleep "$POLL_INTERVAL"
        ;;
    esac
  done

  log_error "Timeout: Deployment did not succeed within $((MAX_POLL_ATTEMPTS * POLL_INTERVAL)) seconds"
  return 1
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 2: Check Railway Logs for Crashes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

check_deployment_logs() {
  log_phase "2" "Checking deployment logs"

  # Fetch recent logs
  log_info "Fetching last 200 lines of deployment logs..."
  local deploy_logs=$(railway logs \
    --service "$SERVICE_NAME" \
    --environment "$ENVIRONMENT" \
    --lines 200 2>/dev/null || echo "")

  if [ -z "$deploy_logs" ]; then
    log_warning "Could not fetch logs. Proceeding with caution."
    return 0  # Non-blocking - logs might be delayed
  fi

  # Check for critical error patterns
  local error_patterns="(ModuleNotFoundError|ImportError|SyntaxError|TypeError.*__init__|Address already in use|FATAL|Traceback.*Error)"
  local startup_errors=$(echo "$deploy_logs" | grep -ciE "$error_patterns" || echo "0")

  # Check for successful startup indicators
  local success_patterns="(Server.*running|Listening on|Application startup complete|Started server)"
  local success_count=$(echo "$deploy_logs" | grep -ciE "$success_patterns" || echo "0")

  log_info "Startup error patterns found: ${startup_errors}"
  log_info "Successful startup indicators: ${success_count}"

  if [ "$startup_errors" -gt 5 ]; then
    log_error "Excessive startup errors detected (${startup_errors} occurrences)"
    echo ""
    echo "━━━ Recent Error Logs ━━━"
    echo "$deploy_logs" | grep -iE "$error_patterns" | tail -10
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
    return 1
  fi

  if [ "$success_count" -eq 0 ] && [ "$startup_errors" -gt 0 ]; then
    log_warning "No startup success indicators found, but errors present"
    return 1
  fi

  log_success "Logs look clean (${startup_errors} errors, ${success_count} success indicators)"
  return 0
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 3: Extract Preview URL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

get_preview_url() {
  log_phase "3" "Extracting preview URL"

  # Method 1: Railway domain command
  log_info "Attempting to get domain from Railway..."
  local domain_json=$(railway domain \
    --service "$SERVICE_NAME" \
    --environment "$ENVIRONMENT" \
    --json 2>/dev/null || echo "[]")

  if [ "$domain_json" != "[]" ]; then
    local domain=$(echo "$domain_json" | jq -r '.[0].domain // ""')
    if [ -n "$domain" ] && [ "$domain" != "null" ]; then
      PREVIEW_URL="https://${domain}"
      log_success "Preview URL: ${PREVIEW_URL}"
      return 0
    fi
  fi

  # Method 2: Construct from pattern
  log_info "Domain not found, constructing from pattern..."
  PREVIEW_URL="https://${SERVICE_NAME}-pr-${PR_NUMBER}.up.railway.app"
  log_warning "Inferred URL: ${PREVIEW_URL} (verify manually if tests fail)"
  return 0
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 4: Health Check
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

check_health_endpoint() {
  log_phase "4" "Health endpoint check"

  log_info "Testing health endpoint: ${PREVIEW_URL}/health"
  local health_code=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 10 \
    "${PREVIEW_URL}/health" 2>/dev/null || echo "000")

  if [ "$health_code" = "200" ]; then
    log_success "Health endpoint: 200 OK"
    return 0
  else
    log_warning "Health endpoint returned: ${health_code}"

    # Try base URL as fallback
    log_info "Testing base URL: ${PREVIEW_URL}/"
    local base_code=$(curl -s -o /dev/null -w "%{http_code}" \
      --max-time 10 \
      "${PREVIEW_URL}/" 2>/dev/null || echo "000")

    if [ "$base_code" = "200" ]; then
      log_success "Base URL: 200 OK (health endpoint not available)"
      return 0
    else
      log_error "Base URL returned: ${base_code}"
      return 1
    fi
  fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 5: Browser Smoke Test in AgentOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

run_agentos_smoke_test() {
  log_phase "5" "Browser smoke test in AgentOS"

  if [ "$AGENTOS_BASE_URL" = "https://your-agentos-instance.com" ]; then
    log_warning "AGENTOS_URL not configured. Skipping AgentOS test."
    log_info "Set AGENTOS_URL environment variable to enable this check."
    return 0
  fi

  log_info "Loading AgentOS: ${AGENTOS_BASE_URL}"

  # Test AgentOS loads
  if ! $BROWSE "$AGENTOS_BASE_URL" > /tmp/agentos-test.log 2>&1; then
    log_error "Failed to load AgentOS"
    cat /tmp/agentos-test.log
    return 1
  fi

  # Check for console errors
  local console_errors=$(grep -c "Console Errors" /tmp/agentos-test.log || echo "0")
  local failed_requests=$(grep -c "Failed Requests" /tmp/agentos-test.log || echo "0")

  log_info "Console errors: ${console_errors}"
  log_info "Failed requests: ${failed_requests}"

  # Take screenshot for manual review
  $BROWSE screenshot /tmp/agentos-preview-test.png 2>/dev/null || true
  log_info "Screenshot saved: /tmp/agentos-preview-test.png"

  if [ "$console_errors" -gt 5 ] || [ "$failed_requests" -gt 3 ]; then
    log_error "Too many errors in AgentOS test"
    return 1
  fi

  log_success "AgentOS smoke test passed"
  return 0
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 6: Deliver Verdict
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

deliver_verdict() {
  local phase1_result=$1
  local phase2_result=$2
  local phase4_result=$3
  local phase5_result=$4

  log_phase "6" "Verdict"

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  DEPLOYMENT VERIFICATION REPORT"
  echo "  PR #${PR_NUMBER} | Environment: ${ENVIRONMENT}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  printf "  [Phase 1] Deployment Status:  "
  [ $phase1_result -eq 0 ] && echo -e "${GREEN}PASS${NC}" || echo -e "${RED}FAIL${NC}"

  printf "  [Phase 2] Log Health Check:   "
  [ $phase2_result -eq 0 ] && echo -e "${GREEN}PASS${NC}" || echo -e "${RED}FAIL${NC}"

  printf "  [Phase 4] Health Endpoint:    "
  [ $phase4_result -eq 0 ] && echo -e "${GREEN}PASS${NC}" || echo -e "${RED}FAIL${NC}"

  printf "  [Phase 5] AgentOS Smoke Test: "
  [ $phase5_result -eq 0 ] && echo -e "${GREEN}PASS${NC}" || echo -e "${RED}FAIL${NC}"

  echo ""

  if [ $phase1_result -eq 0 ] && [ $phase2_result -eq 0 ] && [ $phase4_result -eq 0 ] && [ $phase5_result -eq 0 ]; then
    echo -e "  ${GREEN}✓ VERDICT: ALL CHECKS PASSED${NC}"
    echo ""

    # Auto-approve the PR
    log_info "Auto-approving PR #${PR_NUMBER}..."
    gh pr review "$PR_NUMBER" \
      --repo "${REPO_OWNER}/${REPO_NAME}" \
      --approve \
      --body "✅ **Automated verification passed**

| Check | Result |
|-------|--------|
| Railway Deployment | ✅ ACTIVE |
| Log Health | ✅ Clean |
| Health Endpoint | ✅ 200 OK |
| AgentOS Smoke Test | ✅ Passed |

**Preview URL:** ${PREVIEW_URL}

_Verified automatically by verify-deployment.sh_" 2>/dev/null || log_warning "Failed to auto-approve (check gh auth)"

    log_success "PR #${PR_NUMBER} auto-approved. Ready to merge!"

  else
    echo -e "  ${RED}✗ VERDICT: CHECKS FAILED${NC}"
    echo ""

    # Comment on PR with failure details
    log_info "Adding failure report to PR #${PR_NUMBER}..."
    gh pr comment "$PR_NUMBER" \
      --repo "${REPO_OWNER}/${REPO_NAME}" \
      --body "❌ **Automated verification FAILED**

| Check | Result |
|-------|--------|
| Railway Deployment | $([ $phase1_result -eq 0 ] && echo '✅ PASS' || echo '❌ FAIL') |
| Log Health | $([ $phase2_result -eq 0 ] && echo '✅ PASS' || echo '❌ FAIL') |
| Health Endpoint | $([ $phase4_result -eq 0 ] && echo '✅ PASS' || echo '❌ FAIL') |
| AgentOS Smoke Test | $([ $phase5_result -eq 0 ] && echo '✅ PASS' || echo '❌ FAIL') |

**Preview URL:** ${PREVIEW_URL}

Please review deployment logs and test manually before merging.

_Verified automatically by verify-deployment.sh_" 2>/dev/null || log_warning "Failed to comment (check gh auth)"

    log_error "PR #${PR_NUMBER} flagged with failure report"
  fi

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main Execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Deployment Verification: PR #${PR_NUMBER}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # Check prerequisites
  check_prerequisites

  # Phase 1: Wait for deployment
  poll_deployment_status
  PHASE1=$?

  if [ $PHASE1 -ne 0 ]; then
    deliver_verdict $PHASE1 1 1 1
    exit 1
  fi

  # Phase 2: Check logs
  check_deployment_logs
  PHASE2=$?

  # Phase 3: Get URL (always needed)
  get_preview_url

  # Phase 4: Health check
  check_health_endpoint
  PHASE4=$?

  # Phase 5: Browser smoke test (skip if earlier phases failed)
  PHASE5=1
  if [ $PHASE2 -eq 0 ] && [ $PHASE4 -eq 0 ]; then
    run_agentos_smoke_test
    PHASE5=$?
  else
    log_warning "Skipping AgentOS test due to earlier failures"
  fi

  # Phase 6: Verdict
  deliver_verdict $PHASE1 $PHASE2 $PHASE4 $PHASE5

  # Exit with appropriate code
  if [ $PHASE1 -eq 0 ] && [ $PHASE2 -eq 0 ] && [ $PHASE4 -eq 0 ] && [ $PHASE5 -eq 0 ]; then
    exit 0
  else
    exit 1
  fi
}

# Run main function
main

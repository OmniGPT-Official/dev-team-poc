# Agent & Workflow Audit Report
**Date:** 2026-02-10
**Branch:** claude/fix-broken-agents-egubR

---

## Executive Summary

Audited all agents and workflows registered in `agno_agent.py` to identify broken implementations. Found several agents/workflows using **deprecated mock data tools** that violate CLAUDE.md guidelines.

---

## ✅ WORKING (Keep These)

### Agents

1. **email_followup_agent** (`email_followup.py`)
   - Status: ✅ Working
   - Uses: OAuth pre-hooks with proper Google Sheets/Gmail integration
   - Pattern: Follows CLAUDE.md OAuth pattern correctly

2. **gmail_sheets_agent** (`gmail_sheets_agent.py`)
   - Status: ✅ Working
   - Uses: OAuth pre-hooks with Google Sheets/Gmail
   - Pattern: Clean, general-purpose OAuth agent

3. **content_strategist, content_writer** (`content_creation.py`)
   - Status: ✅ Working
   - Uses: Gemini Flash, no external dependencies
   - Pattern: Simple content creation agents

4. **content_creation_team** (`content_creation.py`)
   - Status: ✅ Working
   - Uses: Team pattern with workflow tools
   - Pattern: Supervisor pattern with OpenAI image generation

5. **Product Team Agents** (`agents/` directory)
   - product_lead_agent
   - lead_engineer_agent
   - software_engineer_agent
   - security_engineer_agent
   - vercel_deployer_agent
   - Status: ✅ Working
   - Pattern: Development team agents

### Workflows

1. **product_requirements_workflow** (`workflows/product_requirements_workflow.py`)
   - Status: ✅ Working
   - Registered in: `workflows/__init__.py`

2. **software_development_workflow** (`workflows/software_development_workflow.py`)
   - Status: ✅ Working
   - Registered in: `workflows/__init__.py`

3. **email_followup_workflow** (`workflows/email_followup_workflow_working.py`)
   - Status: ✅ Working
   - Uses: email_followup_agent (OAuth-enabled)
   - Pattern: 3-step workflow with explicit boundaries

4. **requirement_gathering_workflow_definition** (`content_creation.py`)
   - Status: ✅ Working
   - Uses: Content strategist for requirements gathering
   - Pattern: Single-step workflow for clarifying questions

---

## ⚠️ POTENTIALLY BROKEN (Need Environment Variables)

### Calling Agents & Workflows

**Files:**
- `agents/calling_agents.py`
  - lead_reader_agent
  - calling_coordinator_agent
  - results_logger_agent
  - campaign_coordinator_agent
- `workflows/outbound_calling_workflow.py`
  - outbound_calling_workflow
  - simple_calling_workflow

**Status:** ⚠️ May work if ElevenLabs credentials are configured

**Issues:**
- Requires `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`, `ELEVENLABS_PHONE_NUMBER_ID`
- Uses `tools/elevenlabs_tools.py` (properly implemented, not mock data)
- Uses OAuth pre-hooks for Google Sheets access (good pattern)

**Recommendation:**
- **KEEP** if ElevenLabs integration is needed
- **REMOVE** if ElevenLabs is not being used
- **Action needed:** Verify if ElevenLabs env vars are set in Railway

---

## ❌ BROKEN (Remove These)

### 1. OLD Email Follow-Up Workflow

**File:** `workflows/email_followup_workflow.py`

**Why broken:**
- Uses `agents/email_followup_agents.py` which uses **mock data tools**
- CLAUDE.md explicitly forbids: "Mock Data: tools/google_sheets_tools.py (deprecated, don't use)"
- Returns hardcoded contacts (John Smith, Sarah Lee) instead of real data

**Evidence:**
```python
# From tools/google_sheets_tools.py
return [
    {
        "Name": "John Smith",  # ❌ Mock data
        "Company": "Acme Co",
        "Email": "john@acme.com",
        ...
    }
]
```

**Replacement:** `workflows/email_followup_workflow_working.py` (already registered)

**Action:** ❌ **REMOVE** from `agno_agent.py`

---

### 2. Email Follow-Up Agents (Mock Version)

**File:** `agents/email_followup_agents.py`

**Why broken:**
- Uses custom tools from `tools/google_sheets_tools.py` (returns mock data)
- Uses custom tools from `tools/gmail_tools.py` (likely also mock)
- Not following OAuth pre-hook pattern

**Used by:**
- `workflows/email_followup_workflow.py` (also broken)

**Replacement:** `email_followup.py` (single-agent OAuth pattern)

**Action:** ❌ **DELETE** file

---

### 3. Sales Follow-Up Workflow

**File:** `workflows/sales_followup_workflow.py`

**Why broken:**
- **NOT registered** in `agno_agent.py` (not exposed in UI)
- Uses `agents/sales_followup_agents.py`
- Uses Google MCP (requires complex env var setup)
- Not following standard OAuth pre-hook pattern

**Action:** ❌ **DELETE** file

---

### 4. Sales Follow-Up Agents

**File:** `agents/sales_followup_agents.py`

**Why broken:**
- Uses Google MCP instead of standard OAuth pre-hooks
- Requires `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN`
- Not the pattern used by other working agents
- Not following CLAUDE.md guidelines

**Used by:**
- `workflows/sales_followup_workflow.py` (not registered)

**Action:** ❌ **DELETE** file

---

## 📋 Action Plan

### Step 1: Remove from `agno_agent.py`

**Remove from workflows list:**
```python
# ❌ REMOVE THIS:
from workflows.email_followup_workflow import email_followup_workflow

# In workflows list:
email_followup_workflow,  # ❌ REMOVE (old broken version)
```

**Keep this (already there):**
```python
# ✅ KEEP THIS:
from workflows.email_followup_workflow_working import email_followup_workflow

# In workflows list:
email_followup_workflow,  # ✅ Email Follow-Up Manager (working version)
```

### Step 2: Delete Deprecated Files

```bash
# Delete broken agents
rm agents/email_followup_agents.py
rm agents/sales_followup_agents.py

# Delete broken workflows
rm workflows/email_followup_workflow.py
rm workflows/sales_followup_workflow.py

# Delete mock tools (deprecated per CLAUDE.md)
rm tools/google_sheets_tools.py
rm tools/gmail_tools.py  # If this is also mock data
```

### Step 3: Verify Calling Agents

**Check if ElevenLabs is configured:**
```bash
# In Railway dashboard, check for:
ELEVENLABS_API_KEY
ELEVENLABS_AGENT_ID
ELEVENLABS_PHONE_NUMBER_ID
```

**If NOT configured:**
- Remove calling agents from `agno_agent.py`
- Delete `agents/calling_agents.py`
- Delete `workflows/outbound_calling_workflow.py`

**If configured:**
- Keep calling agents (they follow good patterns)
- Test in AgentOS UI

### Step 4: Clean Up Instructions Files

**Check if these are referenced:**
```bash
instructions/sales_followup_instructions.py
```

**If only used by deleted agents:** Delete them

---

## 🎯 Summary

**Working agents/workflows:** 13 (keep)
**Broken agents/workflows:** 4 (delete)
**Conditional agents/workflows:** 6 (keep if ElevenLabs configured, else delete)

**Files to DELETE:**
1. `agents/email_followup_agents.py` ❌
2. `agents/sales_followup_agents.py` ❌
3. `workflows/email_followup_workflow.py` ❌
4. `workflows/sales_followup_workflow.py` ❌
5. `tools/google_sheets_tools.py` ❌ (explicit in CLAUDE.md)
6. `tools/gmail_tools.py` ❌ (if mock data)
7. `instructions/sales_followup_instructions.py` ❌ (if orphaned)

**Changes to `agno_agent.py`:**
- Remove import of old `email_followup_workflow` from `workflows.email_followup_workflow`
- Keep import of working `email_followup_workflow` from `workflows.email_followup_workflow_working`
- Remove `email_followup_workflow` duplicate entry in workflows list

---

## ✅ After Cleanup

Your AgentOS will have:

**Agents (13):**
1. product_lead_agent ✅
2. lead_engineer_agent ✅
3. software_engineer_agent ✅
4. security_engineer_agent ✅
5. vercel_deployer_agent ✅
6. content_strategist ✅
7. content_writer ✅
8. email_followup_agent ✅
9. gmail_sheets_agent ✅
10. lead_reader_agent ⚠️ (if ElevenLabs configured)
11. calling_coordinator_agent ⚠️
12. results_logger_agent ⚠️
13. campaign_coordinator_agent ⚠️

**Teams (2):**
1. product_team ✅
2. content_creation_team ✅

**Workflows (6):**
1. product_requirements_workflow ✅
2. software_development_workflow ✅
3. requirement_gathering_workflow_definition ✅
4. email_followup_workflow ✅ (working version)
5. outbound_calling_workflow ⚠️ (if ElevenLabs configured)
6. simple_calling_workflow ⚠️

---

## 🔍 How to Verify

After cleanup:
1. Restart Railway deployment
2. Check AgentOS UI - only working agents/workflows should appear
3. Test each agent/workflow with actual data
4. No mock data (John Smith, Sarah Lee) should appear

---

*Report generated by Claude Code*

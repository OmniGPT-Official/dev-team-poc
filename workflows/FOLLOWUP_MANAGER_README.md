# Sales Follow-Up Manager Workflow

## Overview

The Follow-Up Manager automates your email follow-up campaigns with a **review-then-send** approach. It reads your Google Sheet of leads, drafts personalized follow-ups, and lets you approve before sending.

**Key Feature:** You maintain control - all emails are shown to you for approval before sending.

## How It Works

```
1. You provide Google Sheet →
2. AI identifies who needs follow-up →
3. AI drafts personalized emails →
4. YOU REVIEW AND APPROVE →
5. AI sends approved emails →
6. AI updates your sheet →
7. AI provides campaign insights
```

## Quick Start

### Option 1: With AgentOS UI

1. Start the server:
```bash
cd "/Users/albagarridomartin/Downloads/omnigpt github/dev-team-poc-main"
source venv/bin/activate
ANTHROPIC_API_KEY='your-key' OS_SECURITY_KEY='omnigpt' uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

2. Open AgentOS UI

3. Select **"Sales Follow-Up Manager (Simple)"** workflow for testing OR **"Sales Follow-Up Manager"** for full version

4. Provide your:
   - Google Sheet URL (or paste contact data for simple version)
   - Follow-up criteria (days since last contact)
   - Any special notes

5. Review the drafts AI creates

6. Approve emails you want to send

7. Done! Sheet is updated automatically.

### Option 2: Local Testing (No UI)

```python
from workflows.sales_followup_workflow import simple_followup_workflow

# Test with manual data
result = simple_followup_workflow.run(
    message="I have 3 contacts needing follow-up:
    1. John Smith, Acme Co, john@acme.com - last contact 7 days ago
    2. Sarah Lee, TechCorp, sarah@techcorp.com - last contact 10 days ago
    3. Mike Johnson, StartupX, mike@startupx.com - last contact 14 days ago"
)

print(result.content)
```

## Google Sheet Format

Your sheet should have these columns:

| Name | Company | Email | Last Contact | Status | Notes |
|------|---------|-------|--------------|--------|-------|
| John Smith | Acme Co | john@acme.com | 2026-01-28 | Pending | Met at conference |
| Sarah Lee | TechCorp | sarah@techcorp.com | 2026-01-25 | Interested | Wants demo |

**Required columns:**
- Name
- Email
- Last Contact (date)
- Status

**Optional columns:**
- Company
- Notes
- Any other context

## Features

### 1. Smart Follow-Up Detection

Identifies contacts needing follow-up based on:
- Days since last contact (default: 7+ days)
- Status (Pending, Interested, etc.)
- No recent follow-up

### 2. Context-Aware Drafting

Each email is personalized using:
- Previous conversation history
- Notes from your sheet
- Company information
- Timing (recent news, events)

### 3. Review-Then-Send Safety

- ALL emails shown before sending
- You can: Approve, Edit, or Skip
- No accidental sends
- Full control maintained

### 4. Automatic Sheet Updates

After sending, the sheet is automatically updated with:
- New "Last Contact" date
- Status change (e.g., "Followed up")
- Notes about the follow-up

### 5. Campaign Insights

Get plain-language insights like:
```
## What's Working
- Emails with specific company news get 2.5x more replies
- Tuesday morning sends have 61% open rate
- Subject lines under 50 characters perform best

## What's Not Working
- Generic "checking in" messages have 0% reply rate
- Friday sends only get 15% opens
- Long emails (150+ words) get ignored

## Recommendations
1. Use "Quick question about [X]" subject lines
2. Keep emails under 100 words
3. Send Tuesday/Wednesday mornings
```

## Two Workflow Versions

### Simple Version (For Testing)
**Use when:** You want to test without Google Sheets integration

```
Input: Paste contact data directly
↓
Draft emails
↓
Show drafts
```

### Full Version (Production)
**Use when:** You have Google Sheets + Gmail MCP configured

```
Input: Google Sheet URL
↓
Analyze sheet
↓
Gather context from Gmail history
↓
Draft emails
↓
Review interface
↓
Send via Gmail MCP
↓
Update sheet
↓
Campaign insights
```

## Example Usage

### Test with Simple Version

```
User: "I need to follow up with:
- John at Acme Co (john@acme.com) - 7 days since last contact about Headquarters demo
- Sarah at TechCorp (sarah@techcorp.com) - 10 days since conference where we discussed pricing"

AI: [Analyzes] → [Drafts 2 personalized emails] → [Shows you for approval]

Draft 1:
Subject: Quick question about Headquarters demo

Hi John,

Saw Acme just closed Series A - congrats! Wanted to follow up on the Headquarters demo we discussed last week.

Would 15 minutes this Thursday work?

Best,
Albs

---

User: "Approve both"

AI: [Would send via Gmail if MCP configured] → [Shows confirmation]
```

### Weekly Report Example

```
## Your Follow-Up Week

**This Week:**
- Sent: 12 follow-ups
- Opened: 8 (67%) ↑ +15% vs last week
- Replied: 3 (25%)
- Meetings: 1 booked

**Best Performer:**
Subject: "Saw your Series A announcement"
- 100% open rate (3/3)
- 66% reply rate (2/3)
→ KEEP using company news

**Stop Using:**
Subject: "Checking in"
- 0% open rate (0/4)
→ Too generic, not working
```

## Technical Details

### Agents Used
1. **Sheet Analyzer** - Identifies follow-up candidates
2. **Context Researcher** - Gathers email/note context
3. **Message Writer** - Drafts personalized emails
4. **Campaign Analyst** - Provides insights
5. **Follow-Up Coordinator** - Orchestrates everything

### Database
- Uses `agno.db` (SQLite) for conversation history
- Tracks campaign performance over time
- Enables week-over-week analysis

### MCP Tools Needed (For Full Version)
- **Google Sheets MCP** - Read/write sheet data
- **Gmail MCP** - Send emails, read history

## Configuration

### Environment Variables

```bash
ANTHROPIC_API_KEY='your-anthropic-key'
OS_SECURITY_KEY='your-security-key'
```

### Customization

Edit `instructions/sales_followup_instructions.py` to customize:
- Follow-up criteria (days threshold)
- Email tone and style
- Analysis format
- Report structure

## Troubleshooting

### "Can't access Google Sheet"
→ Ensure Google Sheets MCP is configured
→ Sheet must be shared with service account

### "Emails not sending"
→ Gmail MCP must be configured
→ Check authentication

### "Drafts are too generic"
→ Add more notes to your Google Sheet
→ Provide more context in initial brief

## Roadmap

**Iteration 1 (Current):**
- ✅ Manual data input (simple version)
- ✅ Draft generation
- ✅ Review interface

**Iteration 2:**
- [ ] Google Sheets integration
- [ ] Gmail MCP sending
- [ ] Automatic sheet updates
- [ ] Campaign analytics

**Iteration 3:**
- [ ] Weekly automatic reports
- [ ] A/B testing different messages
- [ ] Multi-channel (LinkedIn + Email)
- [ ] Lead scoring

## Support

Questions? Issues?
1. Check this README
2. Review `sales_followup_workflow.py` code
3. Test with simple version first
4. Check AgentOS logs for errors

---

**Built for:** Headquarters POC
**Created:** 2026-02-04
**Version:** 1.0 (Iteration 1)

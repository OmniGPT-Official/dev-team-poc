# Gmail & Google Sheets Integration Guide

Complete guide for using Gmail and Google Sheets MCP integration with the Sales Follow-Up Manager.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Setup](#quick-setup)
3. [How It Works](#how-it-works)
4. [MCP Tools Available](#mcp-tools-available)
5. [Usage Examples](#usage-examples)
6. [Troubleshooting](#troubleshooting)

---

## Overview

The Sales Follow-Up Manager integrates with Gmail and Google Sheets through MCP (Model Context Protocol) to automate your follow-up email campaigns.

**What it does:**
- ✅ Reads your Google Sheets to identify contacts needing follow-up
- ✅ Searches Gmail history for context about each contact
- ✅ Drafts personalized follow-up emails based on context
- ✅ Sends approved emails via your Gmail account
- ✅ Updates Google Sheets with new contact dates automatically

**Key Feature: REVIEW-THEN-SEND**
- All emails are drafted and shown to you BEFORE sending
- You approve each email (or edit/skip)
- System only sends emails you approve
- Sheet automatically updates after sending

---

## Quick Setup

### Step 1: Install Required Package

```bash
pip install google-auth-oauthlib
```

### Step 2: Generate OAuth Credentials

```bash
# Run the token generator
python3 get_google_token.py
```

The script will:
1. Ask for your Google OAuth Client ID and Client Secret
2. Open a browser for authentication
3. Generate a refresh token
4. Output the credentials to add to `.env`

**Getting Client ID and Secret:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select a project
3. Enable Gmail API and Google Sheets API
4. Create OAuth 2.0 credentials (Desktop app)
5. Copy the Client ID and Secret

See [GOOGLE_MCP_SETUP.md](./GOOGLE_MCP_SETUP.md) for detailed instructions.

### Step 3: Configure Environment Variables

Add to your `.env` file:

```bash
GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET="GOCSPX-your-client-secret"
GOOGLE_OAUTH_REFRESH_TOKEN="1//your-refresh-token"
```

### Step 4: Restart the Server

```bash
uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
- ✅ No Google OAuth warning on startup
- ✅ "Sales Follow-Up Manager" workflow available

---

## How It Works

### Workflow Overview

```
1. Intake & Analysis
   ├── User provides Google Sheet URL
   └── System identifies contacts needing follow-up (7+ days)

2. Context & Drafting
   ├── System searches Gmail for email history
   └── AI drafts personalized follow-ups based on context

3. Review & Send (USER APPROVAL REQUIRED)
   ├── System shows all drafts for review
   ├── User approves/edits/skips each email
   └── System sends only approved emails

4. Reporting
   ├── System updates Google Sheet with new dates
   └── Provides campaign performance insights
```

### Agents Involved

| Agent | Role | MCP Tools Used |
|-------|------|----------------|
| **Sheet Analyzer** | Reads Google Sheets, identifies contacts | `read_spreadsheet` |
| **Context Researcher** | Searches Gmail for email history | `search_gmail`, `get_gmail_message` |
| **Message Writer** | Drafts personalized emails | None (uses context) |
| **Follow-Up Coordinator** | Sends emails, updates sheets | `send_gmail_message`, `update_spreadsheet` |
| **Campaign Analyst** | Provides insights | None (analyzes results) |

---

## MCP Tools Available

### Gmail Tools

#### 1. Search Gmail

Search for emails matching a query:

```python
Tool: search_gmail
Parameters:
  query: "from:contact@example.com OR to:contact@example.com"
  maxResults: 10
```

**Common Search Queries:**
- `from:email@example.com OR to:email@example.com` - All emails with this contact
- `from:email@example.com after:2024/01/01` - Recent emails only
- `from:*@company.com` - All emails from a company domain
- `subject:"Product Demo"` - Find emails by subject

#### 2. Get Email Details

Retrieve full email content:

```python
Tool: get_gmail_message
Parameters:
  messageId: "abc123..."
  format: "full"
```

#### 3. Send Email

Send an email via Gmail:

```python
Tool: send_gmail_message
Parameters:
  to: "contact@example.com"
  subject: "Quick question about your Series A"
  body: "Hi John,\n\nSaw your recent announcement...\n\nBest,\nAlbs"
  from: "your-email@domain.com"  # Optional
```

### Google Sheets Tools

#### 1. Read Spreadsheet

Read data from a Google Sheet:

```python
Tool: read_spreadsheet
Parameters:
  spreadsheetId: "1ABC...XYZ"  # From sheet URL
  range: "Sheet1!A1:Z100"      # Or just "Sheet1"
```

**Getting the Spreadsheet ID:**
- URL format: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`
- Copy the ID between `/d/` and `/edit`

#### 2. Update Spreadsheet

Update a single cell or range:

```python
Tool: update_spreadsheet
Parameters:
  spreadsheetId: "1ABC...XYZ"
  range: "Sheet1!D2"
  values: [["2024-01-15"]]
```

#### 3. Batch Update

Update multiple cells at once:

```python
Tool: batch_update_spreadsheet
Parameters:
  spreadsheetId: "1ABC...XYZ"
  data: [
    {
      range: "Sheet1!D2",
      values: [["2024-01-15"]]
    },
    {
      range: "Sheet1!F2",
      values: [["Follow-up sent on 2024-01-15"]]
    }
  ]
```

---

## Usage Examples

### Example 1: Basic Follow-Up Campaign

**Your Google Sheet Structure:**

| Name | Company | Email | Last Contact | Status | Notes |
|------|---------|-------|--------------|--------|-------|
| John Smith | Acme Inc | john@acme.com | 2024-01-01 | Interested | Product demo done |
| Jane Doe | TechCorp | jane@techcorp.com | 2024-01-05 | Pending | Needs pricing |

**Workflow:**

1. **Start the workflow**
   ```
   Select: "Sales Follow-Up Manager"
   Provide: Google Sheet URL
   ```

2. **System analyzes contacts**
   ```
   Output: "Found 2 contacts needing follow-up:
   - John Smith (15 days since last contact)
   - Jane Doe (11 days since last contact)"
   ```

3. **System gathers context**
   - Searches Gmail for previous emails with John and Jane
   - Reviews email threads and engagement
   - Extracts relevant context

4. **System drafts emails**
   ```
   DRAFT FOR JOHN SMITH:
   Subject: Quick question about Acme's Q1 roadmap

   Hi John,

   Following up on the product demo we did 2 weeks ago.
   I saw Acme just raised Series A - congrats!

   Would you have 15 minutes this week to discuss next steps?

   Best,
   Albs

   ---
   WORD COUNT: 38
   ```

5. **You review and approve**
   - Review each draft
   - Approve, edit, or skip
   - System sends only approved emails

6. **System updates sheet**
   - Last Contact Date updated to today
   - Notes updated with "Follow-up sent on [date]"

### Example 2: Targeted Campaign

**Scenario:** You want to follow up only with "Interested" contacts from the last 14 days.

1. **Intake Phase**
   ```
   You: "I want to follow up with contacts marked 'Interested'
        who haven't been contacted in 14+ days"
   ```

2. **System filters accordingly**
   - Reads your sheet
   - Filters by status = "Interested"
   - Filters by last contact >= 14 days ago
   - Identifies qualifying contacts

3. **Rest of workflow proceeds as normal**

### Example 3: Manual Mode (No Google Integration)

**Scenario:** You want to test the workflow without setting up MCP.

1. **Select: "Sales Follow-Up Manager (Simple)"**

2. **Paste contact data**
   ```
   Name: John Smith
   Company: Acme Inc
   Email: john@acme.com
   Last Contact: 15 days ago
   Notes: Product demo completed, interested in enterprise plan
   ```

3. **System drafts follow-up**
   - Based on the notes you provided
   - No Gmail/Sheets access needed
   - Perfect for testing

---

## Troubleshooting

### Issue: "Google OAuth credentials not configured" warning

**Cause:** Missing or incorrect credentials in `.env`

**Fix:**
1. Run `python3 get_google_token.py` again
2. Verify all three variables are in `.env`:
   - `GOOGLE_OAUTH_CLIENT_ID`
   - `GOOGLE_OAUTH_CLIENT_SECRET`
   - `GOOGLE_OAUTH_REFRESH_TOKEN`
3. Check for typos or extra spaces
4. Restart the server

### Issue: "invalid_client" error

**Cause:** Incorrect Client ID or Secret

**Fix:**
1. Go to Google Cloud Console → APIs & Services → Credentials
2. Find your OAuth 2.0 Client ID
3. Verify the Client ID and Secret match your `.env`
4. Regenerate credentials if needed

### Issue: "invalid_grant" or "Token expired"

**Cause:** Refresh token is invalid or revoked

**Fix:**
1. Re-run `python3 get_google_token.py`
2. Authenticate again
3. Get a new refresh token
4. Update `.env` with the new token

### Issue: Emails not sending

**Check:**
1. Are credentials configured correctly?
2. Did you approve the drafts in the Review phase?
3. Check terminal for error messages
4. Verify Gmail API is enabled in Google Cloud Console
5. Check Gmail sent folder to confirm

### Issue: Can't read Google Sheet

**Check:**
1. Is the spreadsheet ID correct? (from URL)
2. Is the sheet shared with your Google account?
3. Is Google Sheets API enabled in Google Cloud Console?
4. Try accessing the sheet manually in browser first

### Issue: MCP server not starting

**Fix:**
```bash
# Install the Google MCP server
npx -y @pegasusheavy/google-mcp --version
```

---

## Best Practices

### Email Best Practices

1. **Keep it short** - Under 100 words (better response rate)
2. **Be specific** - Reference actual context from previous conversations
3. **One CTA** - One clear call-to-action per email
4. **Natural tone** - Write like a human, not a corporate robot
5. **Good subject lines** - Specific, not generic ("Following up")

### Sheet Structure

**Recommended columns:**

| Column | Purpose | Example |
|--------|---------|---------|
| A: Name | Contact name | "John Smith" |
| B: Company | Company name | "Acme Inc" |
| C: Email | Email address | "john@acme.com" |
| D: Last Contact | Date of last contact | "2024-01-15" |
| E: Status | Contact status | "Interested", "Pending", "Closed" |
| F: Notes | Additional context | "Product demo completed" |

**Tips:**
- Use consistent date format (YYYY-MM-DD)
- Keep notes concise but informative
- Update status after each interaction
- Use consistent status values

### Workflow Tips

1. **Test first** - Use "Sales Follow-Up Manager (Simple)" to test without MCP
2. **Review carefully** - Always review drafts before approving
3. **Batch smart** - Don't send too many follow-ups at once (pace yourself)
4. **Track results** - Check reply rates and adjust messaging
5. **Update sheet** - Keep your sheet current for better context

---

## Security & Privacy

### Current Setup (Testing/Personal Use)

- **OAuth tokens in .env**: Your personal credentials
- **Access**: Only you can access your Gmail/Sheets
- **Storage**: Tokens stored in plaintext in .env (not committed to git)

### For Production (Future)

When deploying for real users:
- **Frontend OAuth flow**: Each user authenticates themselves
- **Token storage**: Encrypted tokens in database
- **Token refresh**: Automatic refresh token handling
- **Scope consent**: Users approve what data the app can access
- **Audit logs**: Track all email sends and sheet updates

---

## Resources

- [Google MCP Setup Guide](./GOOGLE_MCP_SETUP.md) - Detailed setup instructions
- [MCP Setup Guide](./MCP_SETUP_GUIDE.md) - General MCP configuration
- [Follow-Up Manager README](./workflows/FOLLOWUP_MANAGER_README.md) - Workflow details
- [Google OAuth 2.0 Docs](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Reference](https://developers.google.com/gmail/api)
- [Google Sheets API Reference](https://developers.google.com/sheets/api)
- [@pegasusheavy/google-mcp](https://www.npmjs.com/package/@pegasusheavy/google-mcp)

---

## Support

**Still having issues?**

1. Check the troubleshooting section above
2. Verify all APIs are enabled in Google Cloud Console
3. Make sure you're using the correct Google account
4. Try regenerating the refresh token
5. Check terminal logs for specific error messages

**Have questions?** Open an issue on GitHub or reach out for help!

---

## Next Steps

1. ✅ Complete the Quick Setup steps above
2. ✅ Test with "Sales Follow-Up Manager (Simple)" first
3. ✅ Set up your Google Sheet with contact data
4. ✅ Run your first automated follow-up campaign
5. ✅ Review results and iterate on your messaging

Happy following up! 🚀

# Google MCP Setup Guide

This guide walks you through setting up Gmail and Google Sheets MCP integration for the Follow-Up Manager workflow.

---

## Overview

The Follow-Up Manager uses MCP (Model Context Protocol) to:
- **Read Google Sheets** to identify contacts needing follow-up
- **Search Gmail** for email history and context
- **Send emails** via Gmail programmatically
- **Update Google Sheets** after sending follow-ups

This requires OAuth credentials from Google Cloud Console.

---

## Quick Start (Automated)

The easiest way to get set up:

```bash
# 1. Run the token generator script
python3 get_google_token.py

# 2. Follow prompts to enter Client ID and Secret
# 3. Authenticate in browser when prompted
# 4. Copy the output to your .env file
# 5. Restart the server
```

---

## Manual Setup (Step-by-Step)

### Step 1: Google Cloud Console Setup

#### A. Create or Select Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your **OmniGPT organization** from the dropdown
3. Create a new project:
   - Click "Select a project" → "New Project"
   - Name: "Follow-Up Manager" (or similar)
   - Organization: OmniGPT
   - Click "Create"

#### B. Enable Required APIs

1. In your project, go to **APIs & Services** → **Library**
2. Search for and enable each of these APIs:
   - **Gmail API**
   - **Google Sheets API**

#### C. Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **Internal** (only for OmniGPT organization users)
3. Fill in the form:
   - **App name**: Follow-Up Manager
   - **User support email**: Your email
   - **Developer contact**: Your email
4. Click **Save and Continue**
5. **Scopes**: Add these scopes:
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/spreadsheets`
6. Click **Save and Continue**
7. Review and click **Back to Dashboard**

#### D. Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: "Follow-Up Manager Local Testing"
5. Click **Create**
6. **IMPORTANT**: Copy and save:
   - **Client ID** (looks like: `xxx.apps.googleusercontent.com`)
   - **Client Secret** (looks like: `GOCSPX-xxx`)

### Step 2: Generate Refresh Token

#### Option A: Use Our Script (Recommended)

```bash
# Install required package
pip install google-auth-oauthlib

# Run the token generator
python3 get_google_token.py
```

The script will:
1. Ask for your Client ID and Client Secret
2. Open a browser for authentication
3. Output the complete credentials to add to `.env`

#### Option B: Manual OAuth Flow

If you prefer to do it manually, you'll need to:
1. Build an OAuth2 authorization URL
2. Handle the redirect callback
3. Exchange the authorization code for tokens
4. Extract the refresh token

(This is complex - we recommend using the script)

### Step 3: Add Credentials to .env

Edit your `.env` file and add:

```bash
GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET="GOCSPX-your-client-secret"
GOOGLE_OAUTH_REFRESH_TOKEN="1//your-refresh-token"
```

### Step 4: Restart the Server

```bash
uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

If configured correctly, you should see:
- ✅ No Google OAuth warning on startup
- ✅ Follow-Up Manager workflow available with MCP tools

---

## Troubleshooting

### Warning: "Google OAuth credentials not configured"

**Cause**: Missing or incorrect credentials in `.env`

**Fix**:
1. Verify all three variables are set in `.env`:
   - `GOOGLE_OAUTH_CLIENT_ID`
   - `GOOGLE_OAUTH_CLIENT_SECRET`
   - `GOOGLE_OAUTH_REFRESH_TOKEN`
2. Check for typos or extra spaces
3. Ensure the `.env` file is in the project root
4. Restart the server

### Error: "invalid_client"

**Cause**: Incorrect Client ID or Client Secret

**Fix**:
1. Go back to Google Cloud Console
2. APIs & Services → Credentials
3. Find your OAuth 2.0 Client ID
4. Click to view details
5. Verify the Client ID and Secret match your `.env`

### Error: "invalid_grant" or "Token expired"

**Cause**: Refresh token is invalid or revoked

**Fix**:
1. Re-run `python3 get_google_token.py`
2. Authenticate again
3. Get a new refresh token
4. Update `.env`

### Error: "Access blocked: Authorization Error"

**Cause**: OAuth consent screen not configured for your organization

**Fix**:
1. Make sure OAuth consent screen is set to **Internal**
2. Verify you're signed in with an OmniGPT organization account
3. Check that required scopes are added

### MCP Server Not Starting

**Cause**: Missing npm package

**Fix**:
```bash
# Install the Google MCP server
npx -y @pegasusheavy/google-mcp --version
```

---

## Testing the Integration

Once configured, test the integration:

1. Start the server
2. Open http://localhost:8000
3. Select "Sales Follow-Up Manager (Simple)" workflow
4. When prompted, provide a Google Sheet URL
5. The agent should be able to:
   - Read the sheet contents
   - Search your Gmail for context
   - Draft emails
   - (In full version) Send emails and update the sheet

---

## Security Notes

### For Testing (Current Setup)

- **OAuth tokens in .env**: Your personal credentials
- **Access**: Only you can access your Gmail/Sheets
- **Storage**: Tokens stored in plaintext in .env (not committed to git)

### For Production (Future)

When you deploy this for real users, you'll need:
- **Frontend OAuth flow**: Each user authenticates themselves
- **Token storage**: Encrypted in database
- **Token refresh**: Automatic refresh token handling
- **Scope consent**: Users approve what data the app can access

---

## Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Reference](https://developers.google.com/gmail/api)
- [Google Sheets API Reference](https://developers.google.com/sheets/api)
- [@pegasusheavy/google-mcp Package](https://www.npmjs.com/package/@pegasusheavy/google-mcp)
- [Model Context Protocol](https://www.pulsemcp.com/)

---

## Need Help?

If you're stuck:
1. Check the troubleshooting section above
2. Verify all APIs are enabled in Google Cloud Console
3. Make sure you're using an OmniGPT organization account
4. Try regenerating the refresh token

**Still having issues?** Share the error message and we can debug together.

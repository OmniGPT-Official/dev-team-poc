# Simple Local Setup (For Non-Technical Users)

## Step 1: Get Your Google API Key

1. Go to: https://makersuite.google.com/app/apikey
2. Sign in with Google
3. Click "Create API Key"
4. Copy the key (looks like: `AIzaSyD...`)

## Step 2: Create Your .env File

**Option A: Using Finder (Easiest)**
1. Open the project folder in Finder
2. Find the file `.env.local.template`
3. Right-click → Duplicate
4. Rename the copy to `.env` (just `.env`, no template)
5. Open `.env` with TextEdit
6. Find this line: `GOOGLE_API_KEY="REPLACE_WITH_YOUR_GOOGLE_API_KEY"`
7. Replace `REPLACE_WITH_YOUR_GOOGLE_API_KEY` with your actual key
8. Save the file

**Option B: Tell Claude Code to do it**
Just say: "Create my .env file with my Google API key: [paste your key]"

## Step 3: Test It

Ask your developer to run:
```bash
uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

Then open: http://localhost:8000

You should see AgentOS with your Follow-Up Manager workflow!

---

## What Each Key Does

- **OS_SECURITY_KEY**: AgentOS authentication (already set up ✅)
- **GOOGLE_API_KEY**: Powers Gemini 3 (you need to add this ✏️)

---

## Troubleshooting

**"Invalid API key"**
→ Check your Google API key is copied correctly (no extra spaces)

**"OS_SECURITY_KEY error"**
→ Make sure you copied the ENTIRE public key including BEGIN and END lines

**Can't find .env file**
→ It's hidden by default. In Finder: Cmd+Shift+. to show hidden files

---

**Need help?** Ask in your team chat or tell Claude Code to help you set this up.

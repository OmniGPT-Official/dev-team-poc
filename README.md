# Agent-OS

AI-powered product development system with end-to-end workflow automation.

<!-- trigger ci/cd -->

## Features

### Agents (14 total)

**Product Development Team:**
- **Product Lead Agent**: Conducts product discovery, creates PRDs and Feature Specs
- **Lead Engineer Agent**: Designs technical architecture
- **Software Engineer Agent**: Implements code
- **Security Engineer Agent**: Reviews code for security
- **Vercel Deployer Agent**: Handles Vercel deployment automation

**Content Creation Team:**
- **Content Strategist**: Plans content strategy
- **Content Writer**: Writes content

**OAuth-Enabled Agents:**
- **Email Follow-Up Agent**: Manages email follow-ups with Google Sheets and Gmail integration
- **Gmail & Sheets Agent**: Direct Gmail and Google Sheets access (Claude-powered)

**Outbound Calling Agents:**
- **Lead Reader Agent**: Reads leads from Google Sheets
- **Calling Coordinator Agent**: Coordinates calling campaigns
- **Results Logger Agent**: Logs call results to Google Sheets
- **Campaign Coordinator Agent**: Orchestrates entire campaigns

**System Agents:**
- **Supabase Manager Agent**: Manages Supabase operations (MCP-enabled)

### Core Features
- **Google Docs Integration**: Automatically creates PRDs and Feature Specs in Google Docs
- **OAuth Pre-Hook Pattern**: Per-user Google API authentication for multi-tenant workflows
- **Knowledge Base**: PostgreSQL-backed knowledge storage via DATABASE_URL
- **ElevenLabs Integration**: Voice synthesis for outbound calling workflows
- **OpenTelemetry Tracing**: Built-in observability for all agent interactions

## Quick Start

### 1. Create .env file

Copy the example file and add your credentials:

```bash
ANTHROPIC_API_KEY=your-anthropic-api-key-here
OS_SECURITY_KEY=omnigpt
GITHUB_TOKEN=your-github-token-here
SUPABASE_ACCESS_TOKEN=your-supabase-token-here
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
```

### 2. Run the Server

```bash
source .env
uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

Or use environment variables directly:

```bash
export ANTHROPIC_API_KEY='your-key'
export OS_SECURITY_KEY='omnigpt'
export GITHUB_TOKEN='your-token'
export SUPABASE_ACCESS_TOKEN='your-token'
uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Enable Google Docs (Optional)

To enable Google Docs creation, run the OAuth server once:

```bash
python tests/google_docs/oauth_server.py
```

Visit `http://localhost:8000/authorize` and authorize the app. The token will be saved to `tests/google_docs/token.json`.

## Environment Variables

**Required:**
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `OS_SECURITY_KEY`: Security key for the system (default: `omnigpt`)
- `DATABASE_URL`: PostgreSQL connection string for Knowledge Base

**Optional:**
- `GITHUB_TOKEN`: GitHub Personal Access Token (for GitHub operations)
- `SUPABASE_ACCESS_TOKEN`: Supabase access token (for Supabase MCP)
- `GOOGLE_CLIENT_ID`: Google OAuth Client ID (for Google Docs integration)
- `GOOGLE_CLIENT_SECRET`: Google OAuth Client Secret (for Google Docs integration)

## Architecture

```
Agent-OS/
├── agents/              # 14 agents across 4 domains:
│   ├── product_lead.py           # Product discovery & PRDs
│   ├── lead_engineer.py          # Technical architecture
│   ├── software_engineer.py      # Implementation
│   ├── security_engineer.py      # Security review
│   ├── vercel_deployer.py        # Vercel deployment
│   └── calling_agents.py         # 4 outbound calling agents (OAuth-enabled)
├── teams/               # 2 teams:
│   └── product_team.py           # Product development team
├── workflows/           # 7 workflows:
│   ├── product_requirements_workflow.py
│   ├── software_development_workflow.py
│   ├── email_followup_workflow_working.py    # 3-step OAuth workflow
│   ├── outbound_calling_workflow.py          # Full ElevenLabs integration
│   ├── outbound_calling_test_workflow.py     # OAuth test version
│   └── simple_calling_workflow (in outbound_calling_workflow.py)
├── tools/               # Custom tools:
│   ├── google_docs_tools.py      # Google Docs integration
│   ├── knowledge_base_tools.py   # PostgreSQL knowledge base
│   ├── github_tools.py           # GitHub operations
│   ├── vercel_deploy_tools.py    # Vercel deployment
│   └── elevenlabs_tools.py       # Voice synthesis
├── services/            # Shared services:
│   └── oauth_store.py            # Per-user OAuth credential storage
├── utils/               # Utilities:
│   └── credentials.py            # OAuth credential retrieval
├── instructions/        # Agent instruction files
├── tests/               # Integration tests
└── agno_agent.py        # Main FastAPI application
```

## Workflows

### 1. Product Requirements Workflow
- Asks business questions (new vs existing project)
- Creates PRD (new) or Feature Spec (existing)
- Saves to knowledge base
- Creates Google Doc with shareable link

### 2. Software Development Workflow
1. Product Requirements (PRD/Feature Spec)
2. Architecture Design (Lead Engineer)
3. Implementation (Software Engineer)
4. Summary with links

### 3. Content Creation Workflow (Requirement Gathering)
- Content strategist defines strategy
- Content writer creates content
- Integrated content planning and execution

### 4. Email Follow-Up Workflow (OAuth-Enabled)
**3-step workflow with Google API integration:**
1. **Read Leads**: Fetches leads from Google Sheets using OAuth
2. **Draft Emails**: Creates personalized follow-up emails
3. **Log Results**: Saves sent emails to Google Sheets

### 5. Outbound Calling Workflow (Full Version)
**Complete calling campaign with ElevenLabs voice synthesis:**
1. Lead Reader: Fetches leads from Google Sheets
2. Calling Coordinator: Makes calls with voice synthesis
3. Results Logger: Logs call outcomes to Google Sheets
4. Campaign Coordinator: Orchestrates entire campaign

### 6. Simple Calling Workflow
Simplified test version of outbound calling without voice synthesis

### 7. Outbound Calling Test Workflow
OAuth integration test for calling workflows (first iteration)

## API

The server runs on `http://localhost:8000` with FastAPI endpoints for agents, teams, and workflows.

## Testing

- Google Docs: `tests/google_docs/`
- GitHub MCP: `tests/github_mcp/`
- Supabase MCP: `tests/supabase_mcp/`
- Vercel MCP: `tests/vercel_mcp/`

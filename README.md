# Agent-OS

AI-powered product development system with end-to-end workflow automation.


## Features

- **Product Lead Agent**: Conducts product discovery, creates PRDs and Feature Specs
- **Lead Engineer Agent**: Designs technical architecture
- **Software Engineer Agent**: Implements code
- **Security Engineer Agent**: Reviews code for security
- **Content Creation Team**: Content strategist, writer, and image generator
- **Google Docs Integration**: Automatically creates PRDs and Feature Specs in Google Docs
- **Knowledge Base**: Stores project context and requirements
- **Multiple Workflows**: Product Requirements, Software Development, Content Creation

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
Agent-Os/
├── agents/              # 4 agents: product_lead, lead_engineer, software_engineer, security_engineer
├── teams/               # product_team (all 4 agents)
├── workflows/           # 2 workflows: product_requirements, software_development
├── tools/               # Custom tools: GoogleDocsTools, KnowledgeBaseTools, GitHubTools
├── instructions/        # Agent instructions
├── utils/               # Knowledge base utilities
└── tests/               # Test files for Google Docs, GitHub MCP, etc.
```

## Workflows

### Product Requirements Workflow
- Asks business questions (new vs existing project)
- Creates PRD (new) or Feature Spec (existing)
- Saves to knowledge base
- Creates Google Doc with shareable link

### Software Development Workflow
1. Product Requirements (PRD/Feature Spec)
2. Architecture Design (Lead Engineer)
3. Implementation (Software Engineer)
4. Summary with links

## API

The server runs on `http://localhost:8000` with FastAPI endpoints for agents, teams, and workflows.

## Testing

- Google Docs: `tests/google_docs/`
- GitHub MCP: `tests/github_mcp/`
- Supabase MCP: `tests/supabase_mcp/`
- Vercel MCP: `tests/vercel_mcp/`

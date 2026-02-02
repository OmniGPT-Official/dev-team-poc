# Agent-OS

AI-powered product development system with end-to-end workflow automation.

## Features

- **Product Lead Agent**: Conducts product discovery, creates PRDs and Feature Specs
- **Lead Engineer Agent**: Designs technical architecture
- **Software Engineer Agent**: Implements code
- **Security Engineer Agent**: Reviews code for security
- **Google Docs Integration**: Automatically creates PRDs and Feature Specs in Google Docs
- **Knowledge Base**: Stores project context and requirements
- **2 Workflows**: Product Requirements + Software Development

## Quick Start

### 1. Run the Server

```bash
./run.sh
```

Or with environment variables:

```bash
ANTHROPIC_API_KEY='your-anthropic-api-key' \
OS_SECURITY_KEY='omnigpt' \
GITHUB_TOKEN='your-github-token' \
SUPABASE_ACCESS_TOKEN='your-supabase-token' \
uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Enable Google Docs (Optional)

To enable Google Docs creation, run the OAuth server once:

```bash
python tests/google_docs/oauth_server.py
```

Visit `http://localhost:8000/authorize` and authorize the app. The token will be saved to `tests/google_docs/token.json`.

## Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key (required)
- `OS_SECURITY_KEY`: Security key for the system (default: `omnigpt`)
- `GITHUB_TOKEN`: GitHub Personal Access Token (optional, for GitHub operations)
- `SUPABASE_ACCESS_TOKEN`: Supabase access token (optional, for Supabase MCP)

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

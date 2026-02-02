# Agent OS - Product Development AI System

A modular AI agent system powered by Claude Sonnet 4.5, featuring end-to-end product development workflows from requirements to technical architecture.

## 📚 Documentation

- **[MCP_SETUP_GUIDE.md](MCP_SETUP_GUIDE.md)** - 🔥 **REQUIRED**: MCP servers & GitHub token setup
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Quick start guide for the Product Team Lead agent
- **[RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)** - Deploy to Railway with environment variables
- **[Software Development Workflow](workflow_readme/software_development_workflow.md)** - Complete workflow documentation
- **[Product Discovery Workflow](workflow_readme/product_discovery_worklow.md)** - PRD creation workflow
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Project organization guide
- **[STRUCTURE.md](STRUCTURE.md)** - Detailed architecture documentation

## Setup Instructions

### 1. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 2. Set Up Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Then edit `.env` and add your tokens:

#### Required Variables:
- **ANTHROPIC_API_KEY** - Get from https://console.anthropic.com/
- **OS_SECURITY_KEY** - Use `omnigpt` (or your custom security key)
- **GITHUB_TOKEN** - 🔥 **CRITICAL**: Required for workflows to work!
  - Create at: https://github.com/settings/tokens
  - Required scope: `repo` (full control of private repositories)
  - See [MCP_SETUP_GUIDE.md](MCP_SETUP_GUIDE.md) for detailed instructions

#### Optional Variables:
- **SUPABASE_ACCESS_TOKEN** - Only if using Supabase features
- **VERCEL_TOKEN** - Only if using Vercel deployment features

**⚠️ Without GITHUB_TOKEN, workflows will fail!** See the [MCP Setup Guide](MCP_SETUP_GUIDE.md) for complete instructions.

### 3. Run the Agent

Using environment variables:

```bash
ANTHROPIC_API_KEY='your-key' OS_SECURITY_KEY='omnigpt' ./venv/bin/uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

Or export them first:

```bash
export ANTHROPIC_API_KEY='your-key'
export OS_SECURITY_KEY='omnigpt'
./venv/bin/uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

The agent will start running on http://localhost:8000 with hot-reload enabled.

## Project Structure

```
Agent-Os/
├── agno_agent.py           # Main application entry point
│
├── agents/                 # Agent definitions (each agent = 1 file)
│   ├── product_lead.py          # 🆕 Product Lead (orchestrator with WorkflowTools)
│   ├── lead_engineer.py         # Lead Engineer agent
│   ├── software_engineer.py     # Software Engineer agent
│   └── research_agent.py        # Research agent with DuckDuckGo
│
├── instructions/           # Agent instructions (each agent = 1 file)
│   ├── product_lead_instructions.py
│   ├── lead_engineer_instructions.py
│   └── research_agent_instructions.py
│
├── tools/                  # Custom tools (each tool = 1 file)
│   └── product_discovery_tool.py
│
├── teams/                  # Team configurations (each team = 1 file)
│   └── product_team.py
│
├── workflows/              # Workflows (each workflow = 1 file)
│   ├── software_development_workflow.py    # 🆕 Main orchestrator
│   ├── product_discovery_workflow.py       # PRD creation
│   ├── architecture_design_workflow.py     # 🆕 Architecture design
│   └── code_review_workflow.py             # Code review
│
├── workflow_readme/        # Workflow documentation
│   ├── software_development_workflow.md    # 🆕 Complete guide
│   └── product_discovery_worklow.md
│
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (API keys)
├── SETUP_GUIDE.md         # 🆕 Quick start guide
└── venv/                   # Virtual environment
```

**📖 See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for complete guide on where to add new agents, tools, teams, and workflows.**

## 🚀 Product Lead Agent (Enhanced)

**The ultimate orchestrator** - Talk to one agent that manages the entire software development process.

### Features:
- **Automated Workflow Orchestration** - Triggers complete software development workflow
- **End-to-End Process** - From idea to implementation plan
- **Nested Workflows** - Product Discovery + Architecture Design
- **File Outputs** - Generates PRD and ticket.md files
- **Conversational Interface** - Just describe what you want to build

### Quick Start:

```python
from agents.product_lead import product_lead_agent

product_lead_agent.print_response(
    "Create a blog post scheduling system",
    stream=True
)
```

**Output:**
- `prd_blog_post_scheduling_[timestamp].md` - Product Requirements
- `ticket_blog_post_scheduling_[timestamp].md` - Technical Architecture

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for complete usage examples.

---

## 🔄 Software Development Workflow (NEW)

**Nested workflow** that combines Product Discovery + Architecture Design:

```
Product Lead Agent
    ↓
Software Development Workflow
    ├── Product Discovery Workflow
    │   └── Creates PRD (prd_[name]_[timestamp].md)
    │
    └── Architecture Design Workflow
        └── Creates Ticket (ticket_[name]_[timestamp].md)
```

### Features:
- ✅ Automatic PRD creation
- ✅ Technical architecture design
- ✅ Implementation task breakdown
- ✅ Conditional market research
- ✅ Pass data between workflows
- ✅ Persistent documentation files

See [Software Development Workflow Documentation](workflow_readme/software_development_workflow.md) for details.

---

## 👥 Agents

### Product Lead Agent (Orchestrator)
- Manages complete software development process
- Uses WorkflowTools to trigger nested workflows
- Creates PRD + Architecture tickets
- Creates PRDs and requirements documents
- Defines goals and acceptance criteria
- RICE prioritization framework

### Lead Engineer Agent
- Designs technical architecture
- Creates technical specifications
- Defines implementation approach

### Software Engineer Agent
- Implements features
- Code reviews
- Technical execution

## Research Agent Features

The Research Agent provides:
- DuckDuckGo web search capabilities
- Market trends and competitor analysis
- User insights and industry research
- Data synthesis and recommendations

## System Features

- Claude Sonnet 4.5 model
- SQLite database for conversation history
- Modular architecture (separate agents, teams, instructions)
- DuckDuckGo web search integration
- Markdown support
- Auto-reload on code changes
- Extensible design for adding new agents

## Adding New Components

**See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for complete step-by-step guides on:**
- Creating new agents (each in separate file)
- Adding custom tools (each in separate file)
- Building teams (each team in separate file)
- Creating workflows (each workflow in separate file)
- Adding instructions (each agent's instructions in separate file)

**Quick Summary:**
- **New Agent** → `agents/agent_name.py` + `instructions/agent_name_instructions.py`
- **New Tool** → `tools/tool_name.py`
- **New Team** → `teams/team_name.py`
- **New Workflow** → `workflows/workflow_name.py`

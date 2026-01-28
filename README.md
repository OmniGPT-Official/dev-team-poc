# Agent OS - Product Lead AI System

A modular AI agent system powered by Claude Sonnet 4.5, featuring a Product Lead agent specialized in creating PRDs, managing tickets, and leading product development.

## Setup Instructions

### 1. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 2. Set Up API Key

Create a `.env` file and add your Anthropic API key:

```bash
cp .env.example .env
```

Then edit `.env` and replace `your_api_key_here` with your actual Anthropic API key.

Get your API key from: https://console.anthropic.com/

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
├── agents/                 # Agent definitions
│   ├── product_lead.py     # Product Lead agent
│   └── research_agent.py   # Research agent with DuckDuckGo
├── instructions/           # Agent instructions/prompts
│   ├── product_lead_instructions.py
│   └── research_agent_instructions.py
├── teams/                  # Team configurations
│   └── product_team.py
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (API keys)
└── venv/                   # Python virtual environment
```

See [STRUCTURE.md](STRUCTURE.md) for detailed documentation on the project architecture.

## Product Lead Agent Features

The Product Lead agent is an expert in:

### 1. Creating Comprehensive PRDs
- Product overview & vision
- Business objectives & KPIs
- User personas & target audience
- Problem statements & solutions
- Technical requirements
- Success metrics & analytics plans

### 2. Generating Structured Tickets
- User stories with clear acceptance criteria
- Priority levels (P0-P3)
- Story point estimation
- Dependency mapping
- Technical implementation notes

### 3. Setting Goals & Roadmaps
- Quarterly OKRs (Objectives & Key Results)
- Prioritized feature roadmaps
- Business goal alignment

### 4. RICE Prioritization Framework
- Reach × Impact × Confidence / Effort scoring
- Data-driven feature prioritization

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

## Adding New Agents

See [STRUCTURE.md](STRUCTURE.md) for instructions on:
- Creating new agents
- Adding new instructions
- Building teams

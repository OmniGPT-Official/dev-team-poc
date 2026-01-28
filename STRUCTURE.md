# Agent OS Project Structure

This document describes the organization of the Agent OS project.

## Directory Structure

```
Agent-Os/
├── agno_agent.py           # Main application entry point
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (API keys)
├── .env.example            # Template for environment variables
├── agno.db                 # SQLite database (auto-generated)
├── venv/                   # Python virtual environment
│
├── agents/                 # Agent definitions
│   ├── __init__.py
│   ├── product_lead.py     # Product Lead agent
│   └── research_agent.py   # Research agent with DuckDuckGo
│
├── instructions/           # Agent instructions/prompts
│   ├── __init__.py
│   ├── product_lead_instructions.py
│   └── research_agent_instructions.py
│
└── teams/                  # Team configurations
    ├── __init__.py
    └── product_team.py     # Product team setup
```

## Module Descriptions

### `agno_agent.py` - Main Entry Point
The main application file that:
- Imports agents and teams
- Creates the Agent OS instance
- Exposes the FastAPI app
- Starts the server when run directly

### `agents/` - Agent Definitions
Contains individual agent configurations. Each file defines a specific agent with:
- Agent name and model
- Database configuration
- Instructions reference
- Tools (e.g., DuckDuckGo search)
- Direct export as variable

**Example**: `product_lead.py` exports `product_lead_agent`
**Example**: `research_agent.py` exports `research_agent`

### `instructions/` - Agent Instructions
Contains the instruction prompts for each agent. Separating instructions allows:
- Easy modification without touching agent code
- Reusability across multiple agents
- Version control of prompts
- Clear documentation of agent capabilities

**Example**: `product_lead_instructions.py` contains the Product Lead's system prompt
**Example**: `research_agent_instructions.py` contains the Research Agent's system prompt

### `teams/` - Team Configurations
Defines teams of agents that work together. Teams can include:
- Multiple agents with different specializations
- Team-level configurations
- Collaboration patterns

**Example**: `product_team.py` assembles a team with Product Lead and Research Agent

## Adding New Agents

To add a new agent:

1. **Create instructions** in `instructions/`:
```python
# instructions/designer_instructions.py
DESIGNER_INSTRUCTIONS = """Your instructions here..."""
```

2. **Create agent** in `agents/`:
```python
# agents/designer.py
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.db.sqlite import SqliteDb
from instructions.designer_instructions import DESIGNER_INSTRUCTIONS

designer_agent = Agent(
    name="Designer Agent",
    model=Claude(id="claude-sonnet-4-5"),
    db=SqliteDb(db_file="agno.db"),
    instructions=DESIGNER_INSTRUCTIONS,
    markdown=True
)
```

3. **Add to team** in `teams/product_team.py`:
```python
from agents.designer import designer_agent

product_team = [
    product_lead_agent,
    research_agent,
    designer_agent,  # Add here
]
```

4. **Update main file** if using teams:
```python
# In agno_agent.py
from agents.designer import designer_agent

agent_os = AgentOS(
    name="Product Lead OS",
    agents=[product_lead_agent, research_agent, designer_agent],
    tracing=True
)
```

## Running the Application

```bash
# Start the server
ANTHROPIC_API_KEY='your-key' ./venv/bin/uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

Or:

```bash
# Set environment variables first
export ANTHROPIC_API_KEY='your-key'
export OS_SECURITY_KEY='your-security-key'

# Then run
./venv/bin/uvicorn agno_agent:app --host 0.0.0.0 --port 8000 --reload
```

## Benefits of This Structure

1. **Separation of Concerns**: Each module has a clear, single responsibility
2. **Scalability**: Easy to add new agents and teams
3. **Maintainability**: Instructions and configurations are separate from code
4. **Reusability**: Agents can be shared across teams
5. **Testing**: Each component can be tested independently
6. **Version Control**: Track changes to instructions and configurations separately
7. **Direct Exports**: Simple imports without wrapper functions

## Agent Features

### Product Lead Agent
- Creates PRDs and product descriptions
- Generates structured tickets with user stories
- Sets goals and roadmaps (OKRs)
- Uses RICE prioritization framework
- Provides product strategy guidance

### Research Agent
- DuckDuckGo web search integration
- Market trends and competitor analysis
- User insights gathering
- Industry research and best practices
- Data synthesis and recommendations

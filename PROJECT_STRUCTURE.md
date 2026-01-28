# Project Structure Guide

This document defines the organizational structure for the Agent OS project and where each component should be placed.

## Directory Structure

```
Agent-Os/
├── agno_agent.py                    # Main application entry point
├── requirements.txt                  # Python dependencies
├── .env                             # Environment variables (gitignored)
├── .env.example                     # Template for environment variables
├── .gitignore                       # Git ignore rules
├── README.md                        # Project overview and setup
├── PROJECT_STRUCTURE.md             # This file - structure guide
├── STRUCTURE.md                     # Detailed architecture documentation
│
├── agents/                          # Agent Definitions
│   ├── __init__.py
│   ├── product_lead.py              # Product Lead agent
│   ├── research_agent.py            # Research agent
│   └── <new_agent>.py               # Add new agents here
│
├── instructions/                    # Agent Instructions/Prompts
│   ├── __init__.py
│   ├── product_lead_instructions.py
│   ├── research_agent_instructions.py
│   └── <new_agent>_instructions.py  # Add new instructions here
│
├── tools/                           # Custom Tools (create when needed)
│   ├── __init__.py
│   ├── <tool_name>.py               # Each tool in separate file
│   └── <tool_name>_instructions.py  # Tool-specific instructions (optional)
│
├── teams/                           # Team Configurations
│   ├── __init__.py
│   ├── product_team.py              # Product team
│   └── <new_team>.py                # Each team in separate file
│
├── workflows/                       # Workflow Definitions (create when needed)
│   ├── __init__.py
│   └── <workflow_name>.py           # Each workflow in separate file
│
└── venv/                            # Virtual environment (gitignored)
```

## Component Guidelines

### 1. Agents (`agents/`)

**Purpose**: Define individual AI agents with their configurations.

**Structure**: Each agent should be in its own file.

**Example**: `agents/designer_agent.py`

```python
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from instructions.designer_instructions import DESIGNER_INSTRUCTIONS

designer_agent = Agent(
    name="Designer Agent",
    model=Claude(id="claude-sonnet-4-5"),
    db=SqliteDb(db_file="agno.db"),
    instructions=DESIGNER_INSTRUCTIONS,
    markdown=True
)
```

**Naming Convention**: `<role>_agent.py`

**Export**: Always export as `<role>_agent` variable (not a function)

---

### 2. Instructions (`instructions/`)

**Purpose**: Store agent system prompts and instructions separately from agent code.

**Structure**: Each agent should have its own instruction file.

**Example**: `instructions/designer_instructions.py`

```python
"""
Designer Agent Instructions
"""

DESIGNER_INSTRUCTIONS = """You are an expert UI/UX Designer...

Your responsibilities:
1. Create user interface designs
2. Design user experience flows
3. Provide design feedback
...
"""
```

**Naming Convention**: `<role>_instructions.py`

**Export**: Always export as `<ROLE>_INSTRUCTIONS` constant

**Benefits**:
- Easy to modify prompts without touching code
- Version control of instructions
- Reusable across multiple agents
- Clear documentation of agent capabilities

---

### 3. Tools (`tools/`)

**Purpose**: Custom tools that agents can use (e.g., API integrations, calculators, data processors).

**Structure**: Each tool should be in its own file.

**When to Create**: Only when you need custom tools beyond what agno provides (agno already has DuckDuckGo, Wikipedia, etc.)

**Example**: `tools/jira_tool.py`

```python
from agno.tools import Tool

class JiraTool(Tool):
    name = "jira_tool"
    description = "Create and manage Jira tickets"

    def run(self, action: str, **kwargs):
        if action == "create_ticket":
            # Implementation
            pass
        elif action == "update_ticket":
            # Implementation
            pass
```

**Example with Instructions**: `tools/jira_tool_instructions.py`

```python
JIRA_TOOL_INSTRUCTIONS = """
How to use the Jira tool:
1. Create tickets: jira_tool(action="create_ticket", ...)
2. Update tickets: jira_tool(action="update_ticket", ...)
...
"""
```

**Naming Convention**:
- Tool: `<tool_name>_tool.py`
- Instructions (optional): `<tool_name>_tool_instructions.py`

---

### 4. Teams (`teams/`)

**Purpose**: Group agents that work together as a team.

**Structure**: Each team should be in its own file.

**Example**: `teams/marketing_team.py`

```python
"""
Marketing Team Configuration
"""

from agents.copywriter_agent import copywriter_agent
from agents.social_media_agent import social_media_agent
from agents.seo_agent import seo_agent

marketing_team = [
    copywriter_agent,
    social_media_agent,
    seo_agent,
]
```

**Example**: `teams/engineering_team.py`

```python
"""
Engineering Team Configuration
"""

from agents.backend_agent import backend_agent
from agents.frontend_agent import frontend_agent
from agents.devops_agent import devops_agent

engineering_team = [
    backend_agent,
    frontend_agent,
    devops_agent,
]
```

**Naming Convention**: `<team_name>_team.py`

**Export**: Always export as `<team_name>_team` list

---

### 5. Workflows (`workflows/`)

**Purpose**: Define multi-step processes that orchestrate multiple agents or tasks.

**Structure**: Each workflow should be in its own file.

**When to Create**: When you need to coordinate multiple agents in a specific sequence.

**Example**: `workflows/content_creation_workflow.py`

```python
"""
Content Creation Workflow

This workflow creates blog content with research, writing, and SEO optimization.
"""

from agents.research_agent import research_agent
from agents.copywriter_agent import copywriter_agent
from agents.seo_agent import seo_agent


def content_creation_workflow(
    topic: str,
    target_audience: str,
    needs_research: bool = True
) -> dict:
    """
    Creates optimized blog content.

    Steps:
    1. Research (optional)
    2. Write content
    3. SEO optimization

    Args:
        topic: Content topic
        target_audience: Target audience description
        needs_research: Whether to conduct research

    Returns:
        dict: Final content with metadata
    """
    research_data = ""

    # Step 1: Research (conditional)
    if needs_research:
        research_response = research_agent.run(f"Research: {topic}")
        research_data = research_response.content

    # Step 2: Write content
    write_prompt = f"Write blog post about {topic} for {target_audience}"
    if research_data:
        write_prompt += f"\n\nResearch: {research_data}"

    content_response = copywriter_agent.run(write_prompt)

    # Step 3: SEO optimization
    seo_response = seo_agent.run(
        f"Optimize for SEO:\n{content_response.content}"
    )

    return {
        "topic": topic,
        "content": seo_response.content,
        "research_conducted": needs_research,
        "status": "completed"
    }
```

**Naming Convention**: `<workflow_name>_workflow.py`

**Function Name**: `<workflow_name>_workflow()`

**Key Features**:
- Function-based (simple and flexible)
- Conditional logic support
- Clear step documentation
- Return structured data

---

## File Naming Conventions Summary

| Component | File Name | Export Name | Example |
|-----------|-----------|-------------|---------|
| Agent | `<role>_agent.py` | `<role>_agent` | `product_lead_agent.py` → `product_lead_agent` |
| Instructions | `<role>_instructions.py` | `<ROLE>_INSTRUCTIONS` | `product_lead_instructions.py` → `PRODUCT_LEAD_INSTRUCTIONS` |
| Tool | `<tool_name>_tool.py` | `<ToolName>Tool` | `jira_tool.py` → `JiraTool` |
| Team | `<team_name>_team.py` | `<team_name>_team` | `product_team.py` → `product_team` |
| Workflow | `<workflow_name>_workflow.py` | `<workflow_name>_workflow()` | `content_creation_workflow.py` → `content_creation_workflow()` |

---

## Adding New Components - Step by Step

### Adding a New Agent

1. **Create instructions** in `instructions/`:
```bash
touch instructions/analyst_instructions.py
```

2. **Write instructions**:
```python
ANALYST_INSTRUCTIONS = """You are a Data Analyst..."""
```

3. **Create agent** in `agents/`:
```bash
touch agents/analyst_agent.py
```

4. **Define agent**:
```python
from agno.agent import Agent
from instructions.analyst_instructions import ANALYST_INSTRUCTIONS

analyst_agent = Agent(
    name="Analyst Agent",
    instructions=ANALYST_INSTRUCTIONS,
    # ... other config
)
```

5. **Add to team** (optional) in `teams/`:
```python
from agents.analyst_agent import analyst_agent

product_team = [
    product_lead_agent,
    analyst_agent,  # Add here
]
```

6. **Register in main** (`agno_agent.py`):
```python
from agents.analyst_agent import analyst_agent

agent_os = AgentOS(
    agents=[product_lead_agent, research_agent, analyst_agent],
)
```

---

### Adding a New Tool

1. **Create tool file** in `tools/`:
```bash
mkdir -p tools
touch tools/__init__.py
touch tools/slack_tool.py
```

2. **Implement tool**:
```python
from agno.tools import Tool

class SlackTool(Tool):
    # Implementation
    pass
```

3. **Add to agent** in `agents/`:
```python
from tools.slack_tool import SlackTool

agent = Agent(
    name="Support Agent",
    tools=[SlackTool()],
)
```

---

### Adding a New Team

1. **Create team file** in `teams/`:
```bash
touch teams/support_team.py
```

2. **Define team**:
```python
from agents.support_agent import support_agent
from agents.escalation_agent import escalation_agent

support_team = [
    support_agent,
    escalation_agent,
]
```

---

### Adding a New Workflow

1. **Create workflow file** in `workflows/`:
```bash
mkdir -p workflows
touch workflows/__init__.py
touch workflows/onboarding_workflow.py
```

2. **Implement workflow**:
```python
def onboarding_workflow(user_info: dict) -> dict:
    # Step 1: Verify info
    # Step 2: Create account
    # Step 3: Send welcome email
    return {"status": "completed"}
```

3. **Use in application**:
```python
from workflows.onboarding_workflow import onboarding_workflow

result = onboarding_workflow(user_data)
```

---

## Separation of Concerns - Why?

### Benefits:

1. **Modularity**: Each component is independent and reusable
2. **Maintainability**: Easy to find and update specific parts
3. **Scalability**: Add new agents/tools/teams without affecting others
4. **Testing**: Test each component in isolation
5. **Version Control**: Track changes to specific components
6. **Collaboration**: Multiple developers can work on different components
7. **Clarity**: Clear structure makes onboarding easier

### Example - Updating Instructions:

**Bad** (everything in one file):
```python
agent = Agent(
    name="Agent",
    instructions="Long instructions here..."  # Hard to maintain
)
```

**Good** (separated):
```python
# instructions/agent_instructions.py
AGENT_INSTRUCTIONS = """
Clear, well-documented instructions here...
"""

# agents/agent.py
from instructions.agent_instructions import AGENT_INSTRUCTIONS

agent = Agent(
    name="Agent",
    instructions=AGENT_INSTRUCTIONS
)
```

Now you can update instructions without touching agent code!

---

## Best Practices

1. **One Component Per File**: Each agent, tool, team, workflow in its own file
2. **Clear Naming**: Follow naming conventions consistently
3. **Documentation**: Add docstrings to all components
4. **Imports**: Keep imports organized and clear
5. **Constants**: Use UPPERCASE for instruction constants
6. **Comments**: Add comments for complex logic
7. **Git**: Commit related changes together

---

## Quick Reference

**Creating a new agent:**
```bash
# 1. Create instruction file
touch instructions/new_agent_instructions.py

# 2. Create agent file
touch agents/new_agent.py

# 3. Define both files
# 4. Import in agno_agent.py
```

**Creating a new tool:**
```bash
# 1. Create tools directory (if not exists)
mkdir -p tools && touch tools/__init__.py

# 2. Create tool file
touch tools/new_tool.py

# 3. Implement tool
# 4. Add to agent's tools list
```

**Creating a new team:**
```bash
# 1. Create team file
touch teams/new_team.py

# 2. Import agents and create list
# 3. Use in agno_agent.py
```

**Creating a new workflow:**
```bash
# 1. Create workflows directory (if not exists)
mkdir -p workflows && touch workflows/__init__.py

# 2. Create workflow file
touch workflows/new_workflow.py

# 3. Implement workflow function
# 4. Import and use where needed
```

---

## Questions?

See [STRUCTURE.md](STRUCTURE.md) for detailed architecture documentation and examples.

"""
Research Agent Configuration
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from agno.tools.duckduckgo import DuckDuckGoTools
from instructions.research_agent_instructions import RESEARCH_AGENT_INSTRUCTIONS


research_agent = Agent(
    name="Research Agent",
    model=Claude(id="claude-sonnet-4-5"),
    tools=[DuckDuckGoTools()],
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=RESEARCH_AGENT_INSTRUCTIONS
)

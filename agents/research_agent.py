"""
Research Agent Configuration
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
# from agno.tools.duckduckgo import DuckDuckGoTools  # Disabled due to SSL issues
from instructions.research_agent_instructions import RESEARCH_AGENT_INSTRUCTIONS


research_agent = Agent(
    name="Research Agent",
    role="Performs web research, market analysis, competitor research, and industry trend analysis. Synthesizes information from multiple sources.",
    model=Claude(id="claude-sonnet-4-5"),
    tools=[],  # Web search disabled temporarily due to SSL compatibility issues
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=RESEARCH_AGENT_INSTRUCTIONS
)

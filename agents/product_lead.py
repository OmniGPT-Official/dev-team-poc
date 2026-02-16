"""
Product Lead Agent

Asks business questions, triggers Product Requirements Workflow.
Workflow creates PRD or Feature Spec and saves to Google Docs.
After PRD creation, delegates to Lead Engineer for implementation.
"""

from pathlib import Path
from agno.agent import Agent
from agno.skills import Skills, LocalSkills
from db import db
from agno.models.openrouter import OpenRouter
from agno.tools.duckduckgo import DuckDuckGoTools

from instructions.product_lead_instructions import PRODUCT_LEAD_INSTRUCTIONS
from services.tool_injector import make_tool_hook

# Get skills directory relative to this file
skills_dir = Path(__file__).parent.parent / "skills"

product_lead_agent = Agent(
    name="Product Lead",
    role="Conducts product discovery with progressive discovery workflow, performs market research, creates PRDs/Feature Specs in Google Docs, then delegates to Lead Engineer for implementation.",
    model=OpenRouter(id="google/gemini-3-flash-preview", max_tokens=16384),
    db=db,
    add_history_to_context=True,
    num_history_messages=20,  # Keep last 20 messages in context
    markdown=True,
    instructions=PRODUCT_LEAD_INSTRUCTIONS,
    skills=Skills(loaders=[LocalSkills(str(skills_dir))]),  # Load all skills (prd-creation, etc.)
    tools=[DuckDuckGoTools()],  # DuckDuckGo for web search (market research)
    pre_hooks=[make_tool_hook("google_docs")],  # Inject per-user Google Docs tools
    tool_call_limit=50,  # Prevent infinite tool call loops
    debug_mode=False,
    reasoning=False,  # Explicitly disable reasoning to avoid Gemini API errors
)

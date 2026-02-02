"""
Architecture Design Steps

Flow: PRD -> Technical Architecture
Input: PRD (string)
Output: Architecture (string)

Uses grouped steps pattern for composition into larger workflows.
"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Step, Steps, Workflow
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info, log_debug

from agents.lead_engineer import lead_engineer_agent


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def run_architecture_design(step_input: StepInput) -> StepOutput:
    """Lead Engineer creates technical architecture from PRD."""
    prd = step_input.input if isinstance(step_input.input, str) else ""

    log_info("[STEP:architecture_design] Starting")
    log_debug(f"[STEP:architecture_design] INPUT:\n{prd[:500]}{'...' if len(prd) > 500 else ''}")

    prompt = f"""<task>Create a technical architecture design.</task>

<prd>
{prd}
</prd>

<instructions>
Create a technical architecture document with:
1. System Overview - High-level approach (2-3 sentences)
2. Components - Main components with responsibilities
3. Data Flow - How data moves through the system
4. Technology Stack - Languages, frameworks, infrastructure
5. Implementation Tasks - Ordered list of specific tasks

Format as clear markdown.
</instructions>"""

    log_info("[AGENT:lead_engineer] Calling for architecture design")
    result = _run_async(lead_engineer_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:architecture_design] Complete")
    log_debug(f"[STEP:architecture_design] OUTPUT:\n{output[:500]}{'...' if len(output) > 500 else ''}")

    return StepOutput(content=output, success=True)


# Grouped steps for architecture design (reusable in larger workflows)
architecture_design_steps = Steps(
    name="Architecture Design",
    description="Technical architecture creation sequence",
    steps=[
        Step(name="architecture_design", executor=run_architecture_design),
    ]
)

# Standalone workflow for direct use (registered with AgentOS)
architecture_design_workflow = Workflow(
    name="Architecture Design",
    stream=False,
    description="PRD -> Architecture",
    steps=[architecture_design_steps]
)

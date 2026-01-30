"""
Product Discovery Workflow

Flow: Analysis → PRD Creation
Input: User request (string)
Output: PRD (string)
"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Step, Workflow
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info, log_debug

from agents.product_lead import product_lead_agent


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def run_analysis(step_input: StepInput) -> StepOutput:
    """Product Lead analyzes the request."""
    request = step_input.input if isinstance(step_input.input, str) else ""

    log_info("[STEP:analysis] Starting")
    log_debug(f"[STEP:analysis] INPUT:\n{request[:500]}{'...' if len(request) > 500 else ''}")

    prompt = f"""<task>Analyze this product/feature request.</task>

<request>
{request}
</request>

<instructions>
1. Assess scope: product, feature, enhancement, or refactor
2. Identify key information from the request
3. List information gaps as open questions
Be concise. Only analyze what's provided.
</instructions>"""

    log_info("[AGENT:product_lead] Calling for analysis")
    result = _run_async(product_lead_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:analysis] Complete")
    log_debug(f"[STEP:analysis] OUTPUT:\n{output[:500]}{'...' if len(output) > 500 else ''}")

    return StepOutput(content=output, success=True)


def run_prd_creation(step_input: StepInput) -> StepOutput:
    """Product Lead creates the PRD."""
    request = step_input.input if isinstance(step_input.input, str) else ""
    analysis = step_input.previous_step_content or ""

    log_info("[STEP:prd_creation] Starting")
    log_debug(f"[STEP:prd_creation] INPUT (request):\n{request[:300]}{'...' if len(request) > 300 else ''}")
    log_debug(f"[STEP:prd_creation] INPUT (previous):\n{analysis[:300]}{'...' if len(analysis) > 300 else ''}")

    prompt = f"""<task>Create a requirements document.</task>

<request>
{request}
</request>

<analysis>
{analysis}
</analysis>

<instructions>
Create a simple requirements document with:
1. What - What we're building (2 sentences)
2. Why - Why this matters (1 sentence)
3. Goal - One specific, measurable objective
4. Requirements - Key features with acceptance criteria
5. Out of Scope - What this won't do
6. Open Questions - If any

NO HALLUCINATION. Keep it concise.
</instructions>"""

    log_info("[AGENT:product_lead] Calling for PRD creation")
    result = _run_async(product_lead_agent.arun(prompt))
    output = result.content or ""

    log_info("[STEP:prd_creation] Complete")
    log_debug(f"[STEP:prd_creation] OUTPUT:\n{output[:500]}{'...' if len(output) > 500 else ''}")

    return StepOutput(content=output, success=True)


product_discovery_workflow = Workflow(
    name="Product Discovery",
    stream=False,
    description="Analysis → PRD",
    steps=[
        Step(name="analysis", executor=run_analysis),
        Step(name="prd_creation", executor=run_prd_creation),
    ]
)

# Alias
discovery_and_requirements_workflow = product_discovery_workflow


def run_discovery_and_requirements(request: str) -> dict:
    """Run the workflow with a request string."""
    log_info("[WORKFLOW:product_discovery] ========== STARTING ==========")
    log_debug(f"[WORKFLOW:product_discovery] INPUT:\n{request}")

    result = product_discovery_workflow.run(input=request)
    output = result.content or ""

    log_info("[WORKFLOW:product_discovery] ========== COMPLETE ==========")
    log_debug(f"[WORKFLOW:product_discovery] OUTPUT:\n{output[:500]}{'...' if len(output) > 500 else ''}")

    return {"success": True, "content": output}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    result = run_discovery_and_requirements(args.request)
    print(result["content"])

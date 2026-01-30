"""
Software Development Workflow

Flow: Product Discovery → Architecture Design → Implementation Cycle
Input: User request (string)
Output: Implementation summary (string)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Step, Workflow
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info, log_debug

from workflows.product_discovery_workflow import run_discovery_and_requirements
from workflows.architecture_design_workflow import run_architecture_design_workflow
from workflows.implementation_cycle_workflow import run_implementation_cycle


def run_product_discovery(step_input: StepInput) -> StepOutput:
    """Product Lead creates PRD."""
    request = step_input.input if isinstance(step_input.input, str) else ""

    log_info("[STEP:product_discovery] Starting")
    log_debug(f"[STEP:product_discovery] INPUT:\n{request}")

    result = run_discovery_and_requirements(request)
    output = result.get("content", "")

    log_info("[STEP:product_discovery] Complete")
    log_debug(f"[STEP:product_discovery] OUTPUT:\n{output[:500]}{'...' if len(output) > 500 else ''}")

    return StepOutput(content=output, success=True)


def run_architecture(step_input: StepInput) -> StepOutput:
    """Lead Engineer creates architecture."""
    prd = step_input.previous_step_content or ""

    log_info("[STEP:architecture_design] Starting")
    log_debug(f"[STEP:architecture_design] INPUT:\n{prd[:500]}{'...' if len(prd) > 500 else ''}")

    result = run_architecture_design_workflow(prd)
    output = result.get("content", "")

    log_info("[STEP:architecture_design] Complete")
    log_debug(f"[STEP:architecture_design] OUTPUT:\n{output[:500]}{'...' if len(output) > 500 else ''}")

    return StepOutput(content=output, success=True)


def run_implementation(step_input: StepInput) -> StepOutput:
    """Software Engineer implements code."""
    original_request = step_input.input if isinstance(step_input.input, str) else ""
    architecture = step_input.previous_step_content or ""

    log_info("[STEP:implementation] Starting")
    log_debug(f"[STEP:implementation] INPUT (original_request):\n{original_request}")
    log_debug(f"[STEP:implementation] INPUT (architecture):\n{architecture[:500]}{'...' if len(architecture) > 500 else ''}")

    spec = f"""<original_request>
{original_request}
</original_request>

<architecture>
{architecture}
</architecture>

<instructions>
Implement the code based on the architecture above.
Use GitHub MCP tools to save your code to the repository specified in the original request.
</instructions>"""

    result = run_implementation_cycle(spec)
    output = result.get("content", "")

    log_info("[STEP:implementation] Complete")
    log_debug(f"[STEP:implementation] OUTPUT:\n{output[:500]}{'...' if len(output) > 500 else ''}")

    return StepOutput(content=output, success=True)


software_development_workflow = Workflow(
    name="Software Development",
    stream=False,
    description="Discovery → Architecture → Implementation",
    steps=[
        Step(name="product_discovery", executor=run_product_discovery),
        Step(name="architecture_design", executor=run_architecture),
        Step(name="implementation", executor=run_implementation),
    ]
)


def run_software_development(request: str) -> dict:
    """Run the complete workflow with a request string."""
    log_info("[WORKFLOW:software_development] ========================================")
    log_info("[WORKFLOW:software_development] ========== STARTING ==========")
    log_info("[WORKFLOW:software_development] ========================================")
    log_debug(f"[WORKFLOW:software_development] INPUT:\n{request}")

    result = software_development_workflow.run(input=request)
    output = result.content or ""

    log_info("[WORKFLOW:software_development] ========================================")
    log_info("[WORKFLOW:software_development] ========== COMPLETE ==========")
    log_info("[WORKFLOW:software_development] ========================================")
    log_debug(f"[WORKFLOW:software_development] OUTPUT:\n{output}")

    return {"success": True, "content": output}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    result = run_software_development(args.request)
    print(result["content"])

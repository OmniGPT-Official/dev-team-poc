"""
Software Development Workflow

Flow: Product Discovery -> Architecture Design
Input: User request (string)
Output: Architecture document (string)

Uses grouped steps pattern - composes Steps from sub-workflows directly.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Workflow
from agno.utils.log import log_info, log_debug

from workflows.product_discovery_workflow import product_discovery_steps
from workflows.architecture_design_workflow import architecture_design_steps


# Compose workflow from grouped steps (no nested workflow calls)
software_development_workflow = Workflow(
    name="Software Development",
    stream=False,
    description="Discovery -> Architecture (creates PRD and technical design)",
    steps=[
        product_discovery_steps,      # Analysis -> PRD creation
        architecture_design_steps,    # PRD -> Technical architecture
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

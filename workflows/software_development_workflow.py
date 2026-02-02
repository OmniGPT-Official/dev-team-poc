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

"""
Workflows Module

Workflows are equipped to teams/agents via WorkflowTools.
Use workflow.run(input="...") for direct execution.
"""

from workflows.product_discovery_workflow import (
    product_discovery_steps,
    discovery_and_requirements_workflow,
)
from workflows.architecture_design_workflow import (
    architecture_design_steps,
    architecture_design_workflow,
)
from workflows.software_development_workflow import (
    software_development_workflow,
)
from workflows.implementation_cycle_workflow import (
    implementation_cycle_workflow,
)

__all__ = [
    # Grouped steps (for composing into larger workflows)
    "product_discovery_steps",
    "architecture_design_steps",
    # Standalone workflows (for WorkflowTools or direct use)
    "discovery_and_requirements_workflow",
    "architecture_design_workflow",
    "software_development_workflow",
    "implementation_cycle_workflow",
]

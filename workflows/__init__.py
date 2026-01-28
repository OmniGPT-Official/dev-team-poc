"""
Workflows Module

This module contains workflow definitions for orchestrating agents.
"""

from workflows.code_review_workflow import code_review_workflow
from workflows.product_discovery_workflow import (
    discovery_and_requirements_workflow,
    product_discovery_workflow,  # Backwards compatibility
    DiscoveryAndRequirementsInput,
    ProductDiscoveryInput,  # Backwards compatibility
    run_discovery_and_requirements
)
from workflows.architecture_design_workflow import (
    architecture_design_workflow,
    ArchitectureDesignInput,
    run_architecture_design
)
from workflows.software_development_workflow import (
    software_development_workflow,
    SoftwareDevelopmentInput,
    run_software_development
)

__all__ = [
    "code_review_workflow",
    "discovery_and_requirements_workflow",
    "product_discovery_workflow",
    "DiscoveryAndRequirementsInput",
    "ProductDiscoveryInput",
    "run_discovery_and_requirements",
    "architecture_design_workflow",
    "ArchitectureDesignInput",
    "run_architecture_design",
    "software_development_workflow",
    "SoftwareDevelopmentInput",
    "run_software_development"
]

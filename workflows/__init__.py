"""
Workflows Module

Only 2 workflows:
- product_requirements_workflow: Creates PRD or Feature Spec + Google Doc
- software_development_workflow: End-to-end development (PRD -> Architecture -> Implementation)
"""

from workflows.product_requirements_workflow import (
    product_requirements_workflow,
    run_product_requirements,
)
from workflows.software_development_workflow import (
    software_development_workflow,
    run_software_development,
)

__all__ = [
    "product_requirements_workflow",
    "run_product_requirements",
    "software_development_workflow",
    "run_software_development",
]

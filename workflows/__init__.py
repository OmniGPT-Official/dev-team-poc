"""
Workflows Module

Only 2 workflows:
- product_requirements_workflow: Creates PRD or Feature Spec + Google Doc
- software_development_workflow: Implementation only (takes Google Docs URL as input)
"""

from workflows.product_requirements_workflow import (
    product_requirements_workflow,
    run_product_requirements,
)
from workflows.software_development_workflow import (
    software_development_workflow,
)

__all__ = [
    "product_requirements_workflow",
    "run_product_requirements",
    "software_development_workflow",
]

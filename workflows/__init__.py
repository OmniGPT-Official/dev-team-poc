"""
Workflows Module

Workflows:
- product_requirements_workflow: Creates PRD or Feature Spec + Google Doc
- software_development_workflow: Implementation only (takes Google Docs URL as input)
- hr_workflow: 3-step HR hiring pipeline (gather requirements, write JD, post job)
"""

from workflows.product_requirements_workflow import (
    product_requirements_workflow,
    run_product_requirements,
)
from workflows.software_development_workflow import (
    software_development_workflow,
)
from workflows.hr_workflow import hr_workflow

__all__ = [
    "product_requirements_workflow",
    "run_product_requirements",
    "software_development_workflow",
    "hr_workflow",
]

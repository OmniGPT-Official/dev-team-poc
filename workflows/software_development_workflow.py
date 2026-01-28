"""
Software Development Workflow

A comprehensive workflow that orchestrates product discovery and architecture design.

Nested Workflows:
1. Product Discovery - Creates PRD
2. Architecture Design - Creates technical architecture and tickets

Steps:
1. Product Discovery - Run product discovery workflow to create PRD
2. Architecture Design - Run architecture design workflow to create tickets

Usage:
    from workflows.software_development_workflow import software_development_workflow, SoftwareDevelopmentInput

    workflow_input = SoftwareDevelopmentInput(
        product_name="AI Assistant",
        product_context="Help sales teams automate follow-up emails",
        scope="product",
        enable_research=True
    )

    result = software_development_workflow.run(input=workflow_input)
"""

import os
import sys
import re
import json
from datetime import datetime
from typing import Optional
from loguru import logger
from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow.step import Step
from agno.workflow.types import StepInput, StepOutput
from agno.workflow.workflow import Workflow
from agno.utils.log import log_error, log_info

from workflows.product_discovery_workflow import (
    discovery_and_requirements_workflow,
    DiscoveryAndRequirementsInput
)
from workflows.architecture_design_workflow import (
    architecture_design_workflow,
    ArchitectureDesignInput
)


# ============================================================================
# INPUT MODEL
# ============================================================================

class SoftwareDevelopmentInput(BaseModel):
    """Input model for Software Development Workflow."""
    product_name: str = Field(..., description="Name of the product/feature")
    product_context: str = Field(..., description="Description of what needs to be built/enhanced")
    target_audience: Optional[str] = Field(None, description="Who will use this")
    user_prompt: Optional[str] = Field(None, description="Original user request/prompt")

    # Scope of work
    scope: str = Field(
        "feature",
        description="Type of work: 'product' (complete product from scratch), 'feature' (single feature)"
    )

    # Research control - only for products from scratch
    enable_research: bool = Field(False, description="Conduct problem/market research (searches Google)")
    enable_competitor_analysis: bool = Field(False, description="Conduct competitor analysis")


# ============================================================================
# STEP 1: PRODUCT DISCOVERY
# ============================================================================

def run_product_discovery(step_input: StepInput) -> StepOutput:
    """Run product discovery workflow to create PRD."""
    try:
        # Debug: log what we received
        log_info(f"[SOFTWARE DEV] Received input type: {type(step_input.input)}")
        log_info(f"[SOFTWARE DEV] Input content: {str(step_input.input)[:200]}...")

        # Handle different input types
        if isinstance(step_input.input, SoftwareDevelopmentInput):
            workflow_input = step_input.input
        elif isinstance(step_input.input, dict):
            workflow_input = SoftwareDevelopmentInput(**step_input.input)
        elif isinstance(step_input.input, str):
            # Try to parse as JSON first
            try:
                input_dict = json.loads(step_input.input)
                workflow_input = SoftwareDevelopmentInput(**input_dict)
            except (json.JSONDecodeError, TypeError):
                # If not JSON, treat as plain text description
                # Check if there's metadata with parameters
                product_name = getattr(step_input, 'product_name', None) or "Unnamed Product"
                scope = getattr(step_input, 'scope', None) or "product"

                # Use the plain text as product_context
                workflow_input = SoftwareDevelopmentInput(
                    product_name=product_name,
                    product_context=step_input.input,
                    scope=scope,
                    enable_research=getattr(step_input, 'enable_research', False),
                    enable_competitor_analysis=getattr(step_input, 'enable_competitor_analysis', False),
                    user_prompt=step_input.input
                )
        else:
            return StepOutput(
                content=f"Invalid input type: {type(step_input.input)}. Expected SoftwareDevelopmentInput, dict, or JSON string.",
                success=False
            )

        log_info(f"[SOFTWARE DEV] Starting Product Discovery for: {workflow_input.product_name}")

        # Create input for product discovery workflow
        discovery_input = DiscoveryAndRequirementsInput(
            product_name=workflow_input.product_name,
            product_context=workflow_input.product_context,
            target_audience=workflow_input.target_audience,
            user_prompt=workflow_input.user_prompt,
            scope=workflow_input.scope,
            enable_research=workflow_input.enable_research,
            enable_competitor_analysis=workflow_input.enable_competitor_analysis
        )

        # Run product discovery workflow
        result = discovery_and_requirements_workflow.run(input=discovery_input)

        # WorkflowRunOutput doesn't have 'success', check if it completed
        if result and result.content:
            log_info("[SOFTWARE DEV] Product Discovery completed")

            # Extract PRD file path from result
            prd_file_path = None
            if "saved to:" in result.content:
                # Extract path between backticks
                match = re.search(r'`([^`]+\.md)`', result.content)
                if match:
                    prd_file_path = match.group(1)

            # Store both content and file path
            output_content = result.content
            if prd_file_path:
                output_content += f"\n\n__PRD_FILE_PATH__:{prd_file_path}"

            return StepOutput(content=output_content, success=True)
        else:
            return StepOutput(content="Product Discovery failed", success=False)

    except Exception as e:
        log_error(f"[SOFTWARE DEV] Product Discovery Error: {str(e)}")
        return StepOutput(content=f"Product Discovery error: {str(e)}", success=False)


product_discovery_step = Step(
    name="product_discovery",
    description="Run product discovery workflow to create PRD",
    executor=run_product_discovery
)


# ============================================================================
# STEP 2: ARCHITECTURE DESIGN
# ============================================================================

def run_architecture_design(step_input: StepInput) -> StepOutput:
    """Run architecture design workflow to create technical architecture and tickets."""
    try:
        # Handle different input types
        if isinstance(step_input.input, SoftwareDevelopmentInput):
            workflow_input = step_input.input
        elif isinstance(step_input.input, dict):
            workflow_input = SoftwareDevelopmentInput(**step_input.input)
        elif isinstance(step_input.input, str):
            # Try to parse as JSON first
            try:
                input_dict = json.loads(step_input.input)
                workflow_input = SoftwareDevelopmentInput(**input_dict)
            except (json.JSONDecodeError, TypeError):
                # If not JSON, treat as plain text description
                product_name = getattr(step_input, 'product_name', None) or "Unnamed Product"
                scope = getattr(step_input, 'scope', None) or "product"

                workflow_input = SoftwareDevelopmentInput(
                    product_name=product_name,
                    product_context=step_input.input,
                    scope=scope,
                    enable_research=getattr(step_input, 'enable_research', False),
                    enable_competitor_analysis=getattr(step_input, 'enable_competitor_analysis', False),
                    user_prompt=step_input.input
                )
        else:
            return StepOutput(
                content=f"Invalid input type: {type(step_input.input)}. Expected SoftwareDevelopmentInput, dict, or JSON string.",
                success=False
            )

        # Get PRD content from previous step
        prd_result = step_input.get_step_content("product_discovery")

        if not prd_result:
            return StepOutput(content="No PRD content available", success=False)

        log_info(f"[SOFTWARE DEV] Starting Architecture Design for: {workflow_input.product_name}")

        # Extract PRD file path if available
        prd_file_path = None
        if "__PRD_FILE_PATH__:" in prd_result:
            parts = prd_result.split("__PRD_FILE_PATH__:")
            prd_file_path = parts[1].strip()
            prd_content = parts[0]
        else:
            prd_content = prd_result

        # Remove the saved file message for cleaner content
        if "saved to:" in prd_content:
            prd_content = prd_content.split("---")[0].strip()

        # Create input for architecture design workflow
        architecture_input = ArchitectureDesignInput(
            prd_content=prd_content,
            product_name=workflow_input.product_name,
            prd_file_path=prd_file_path
        )

        # Run architecture design workflow
        result = architecture_design_workflow.run(input=architecture_input)

        # WorkflowRunOutput doesn't have 'success', check if it completed
        if result and result.content:
            log_info("[SOFTWARE DEV] Architecture Design completed")
            return StepOutput(content=result.content, success=True)
        else:
            return StepOutput(content="Architecture Design failed", success=False)

    except Exception as e:
        log_error(f"[SOFTWARE DEV] Architecture Design Error: {str(e)}")
        return StepOutput(content=f"Architecture Design error: {str(e)}", success=False)


architecture_design_step = Step(
    name="architecture_design",
    description="Run architecture design workflow to create tickets",
    executor=run_architecture_design
)


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

software_development_workflow = Workflow(
    name="Software Development Workflow",
    stream=False,
    description="""Complete software development workflow:

    Nested Workflows:
    1. Product Discovery - Creates PRD from requirements
    2. Architecture Design - Creates technical architecture and tickets

    Flow:
    - Takes product requirements as input
    - Runs product discovery to create PRD
    - Passes PRD to architecture design for technical planning
    - Creates both PRD and ticket.md files

    Output: PRD + Architecture ticket files""",
    steps=[
        product_discovery_step,
        architecture_design_step,
    ]
)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def run_software_development(
    product_name: str,
    product_context: str,
    target_audience: Optional[str] = None,
    user_prompt: Optional[str] = None,
    scope: str = "feature",
    enable_research: bool = False,
    enable_competitor_analysis: bool = False
) -> dict:
    """
    Run the complete software development workflow.

    Args:
        product_name: Name of the product/feature
        product_context: Description of what needs to be built
        target_audience: Who will use this (optional)
        user_prompt: Original user request (optional)
        scope: 'product' (from scratch) or 'feature'
        enable_research: Conduct market research (only for products)
        enable_competitor_analysis: Conduct competitor analysis (only for products)

    Returns:
        dict: Paths to generated PRD and ticket files

    Examples:
        # Product from scratch with research
        >>> result = run_software_development(
        ...     product_name="AI Email Assistant",
        ...     product_context="Help sales write follow-ups",
        ...     scope="product",
        ...     enable_research=True
        ... )

        # Simple feature
        >>> result = run_software_development(
        ...     product_name="Dark Mode Toggle",
        ...     product_context="Add dark mode to settings",
        ...     scope="feature"
        ... )
    """
    workflow_input = SoftwareDevelopmentInput(
        product_name=product_name,
        product_context=product_context,
        target_audience=target_audience,
        user_prompt=user_prompt,
        scope=scope,
        enable_research=enable_research,
        enable_competitor_analysis=enable_competitor_analysis
    )

    log_info(f"Starting software development workflow: {product_name} ({scope})")
    result = software_development_workflow.run(input=workflow_input)

    return {
        "success": result.success,
        "content": result.content
    }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Software Development Workflow")
    parser.add_argument("--product-name", required=True)
    parser.add_argument("--product-context", required=True)
    parser.add_argument("--target-audience")
    parser.add_argument("--user-prompt")
    parser.add_argument("--scope", choices=["product", "feature"], default="feature")
    parser.add_argument("--enable-research", action="store_true")
    parser.add_argument("--enable-competitor-analysis", action="store_true")

    args = parser.parse_args()

    result = run_software_development(
        product_name=args.product_name,
        product_context=args.product_context,
        target_audience=args.target_audience,
        user_prompt=args.user_prompt,
        scope=args.scope,
        enable_research=args.enable_research,
        enable_competitor_analysis=args.enable_competitor_analysis
    )

    logger.info(f"Workflow completed!")
    print(result["content"])

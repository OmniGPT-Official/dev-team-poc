"""
Software Development Workflow

A comprehensive workflow that orchestrates the complete software development lifecycle.

Nested Workflows:
1. Discovery and Requirements (Product Lead) - Creates PRD
2. Architecture Design (Lead Engineer) - Creates technical architecture
3. Implementation Cycle (Software Engineer + Reviews) - Implements code with review loop

Flow:
    User Prompt → Product Lead (PRD) → Lead Engineer (Architecture) → Implementation Cycle

Output:
    - product_lead_prd_[name]_[timestamp].md
    - lead_engineer_architecture_[name]_[timestamp].md
    - software_engineer_implementation_[name]_[timestamp].py

Usage:
    from workflows.software_development_workflow import software_development_workflow, SoftwareDevelopmentInput

    workflow_input = SoftwareDevelopmentInput(
        product_name="AI Assistant",
        product_context="Help sales teams automate follow-up emails",
        scope="product",
        enable_research=True,
        enable_implementation=True
    )

    result = software_development_workflow.run(input=workflow_input)
"""

import os
import sys
import re
import json
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
from workflows.implementation_cycle_workflow import (
    implementation_cycle_workflow,
    ImplementationCycleInput,
    ProjectContext,  # Import from implementation_cycle_workflow to ensure type compatibility
)


class SoftwareDevelopmentInput(BaseModel):
    """Input model for Software Development Workflow."""
    product_name: str = Field(..., description="Name of the product/feature")
    product_context: str = Field(..., description="Description of what needs to be built/enhanced")
    target_audience: Optional[str] = Field(None, description="Who will use this")
    user_prompt: Optional[str] = Field(None, description="Original user request/prompt")

    # Project integration context
    project_context: Optional[ProjectContext] = Field(None, description="External project integration context (GitHub, Vercel, Supabase)")

    # Scope of work
    scope: str = Field(
        "feature",
        description="Type of work: 'product' (complete product from scratch), 'feature' (single feature)"
    )

    # Research control - only for products from scratch
    enable_research: bool = Field(False, description="Conduct problem/market research (searches Google)")
    enable_competitor_analysis: bool = Field(False, description="Conduct competitor analysis")

    # Implementation control
    enable_implementation: bool = Field(True, description="Run implementation cycle after architecture design")


# ============================================================================
# STEP 1: PRODUCT DISCOVERY (Product Lead)
# ============================================================================

def run_product_discovery(step_input: StepInput) -> StepOutput:
    """Run product discovery workflow (Product Lead creates PRD)."""
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

        log_info(f"[SOFTWARE DEV] Starting Product Discovery (Product Lead) for: {workflow_input.product_name}")

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

        # Run product discovery workflow (Product Lead)
        result = discovery_and_requirements_workflow.run(input=discovery_input)

        if result and result.content:
            log_info("[SOFTWARE DEV] Product Discovery completed (Product Lead)")

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
    description="Product Lead runs discovery workflow to create PRD",
    executor=run_product_discovery
)


# ============================================================================
# STEP 2: ARCHITECTURE DESIGN (Lead Engineer)
# ============================================================================

def run_architecture_design(step_input: StepInput) -> StepOutput:
    """Run architecture design workflow (Lead Engineer creates architecture)."""
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
            return StepOutput(content="No PRD content available from Product Lead", success=False)

        log_info(f"[SOFTWARE DEV] Starting Architecture Design (Lead Engineer) for: {workflow_input.product_name}")

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

        # Run architecture design workflow (Lead Engineer)
        result = architecture_design_workflow.run(input=architecture_input)

        if result and result.content:
            log_info("[SOFTWARE DEV] Architecture Design completed (Lead Engineer)")
            return StepOutput(content=result.content, success=True)
        else:
            return StepOutput(content="Architecture Design failed", success=False)

    except Exception as e:
        log_error(f"[SOFTWARE DEV] Architecture Design Error: {str(e)}")
        return StepOutput(content=f"Architecture Design error: {str(e)}", success=False)


architecture_design_step = Step(
    name="architecture_design",
    description="Lead Engineer runs architecture workflow to create technical design",
    executor=run_architecture_design
)


# ============================================================================
# STEP 3: IMPLEMENTATION CYCLE (Software Engineer + Reviews)
# ============================================================================

def run_implementation_cycle(step_input: StepInput) -> StepOutput:
    """Run implementation cycle workflow (development + code review + security review)."""
    try:
        # Handle different input types
        if isinstance(step_input.input, SoftwareDevelopmentInput):
            workflow_input = step_input.input
        elif isinstance(step_input.input, dict):
            workflow_input = SoftwareDevelopmentInput(**step_input.input)
        elif isinstance(step_input.input, str):
            try:
                input_dict = json.loads(step_input.input)
                workflow_input = SoftwareDevelopmentInput(**input_dict)
            except (json.JSONDecodeError, TypeError):
                product_name = getattr(step_input, 'product_name', None) or "Unnamed Product"
                workflow_input = SoftwareDevelopmentInput(
                    product_name=product_name,
                    product_context=step_input.input,
                    scope="feature"
                )
        else:
            return StepOutput(
                content=f"Invalid input type: {type(step_input.input)}",
                success=False
            )

        # Get architecture content from previous step
        architecture_result = step_input.get_step_content("architecture_design")

        if not architecture_result:
            return StepOutput(content="No architecture content available from Lead Engineer", success=False)

        log_info(f"[SOFTWARE DEV] Starting Implementation Cycle for: {workflow_input.product_name}")

        # Extract architecture file path if available
        architecture_file_path = None
        if "saved to:" in architecture_result:
            match = re.search(r'`([^`]+\.md)`', architecture_result)
            if match:
                architecture_file_path = match.group(1)

        # Clean up architecture content
        architecture_content = architecture_result
        if "---" in architecture_content:
            # Get the main content before the "saved to" section
            parts = architecture_content.split("---")
            if len(parts) > 1:
                architecture_content = "---".join(parts[:-1]).strip()

        # Create input for implementation cycle workflow
        implementation_input = ImplementationCycleInput(
            technical_document=architecture_content,
            product_name=workflow_input.product_name,
            task_description=f"Implement {workflow_input.product_name}: {workflow_input.product_context}",
            architecture_file_path=architecture_file_path,
            project_context=workflow_input.project_context
        )

        # Run implementation cycle workflow
        result = implementation_cycle_workflow.run(input=implementation_input)

        if result and result.content:
            log_info("[SOFTWARE DEV] Implementation Cycle completed")
            return StepOutput(content=result.content, success=True)
        else:
            return StepOutput(content="Implementation Cycle failed", success=False)

    except Exception as e:
        log_error(f"[SOFTWARE DEV] Implementation Cycle Error: {str(e)}")
        return StepOutput(content=f"Implementation Cycle error: {str(e)}", success=False)


implementation_cycle_step = Step(
    name="implementation_cycle",
    description="Software Engineer implements code with code review and security review loop",
    executor=run_implementation_cycle
)


# ============================================================================
# CONDITION: Check if implementation is enabled
# ============================================================================

def should_run_implementation(step_input: StepInput) -> bool:
    """Determine if implementation cycle should run based on input."""
    try:
        if isinstance(step_input.input, SoftwareDevelopmentInput):
            return step_input.input.enable_implementation
        elif isinstance(step_input.input, dict):
            return step_input.input.get("enable_implementation", True)
        # Default to True for backwards compatibility
        return True
    except Exception:
        return True


# Import Condition for conditional execution
from agno.workflow.condition import Condition


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

software_development_workflow = Workflow(
    name="Software Development Workflow",
    stream=False,
    description="""Complete software development workflow:

    Nested Workflows:
    1. Discovery and Requirements (Product Lead) - Creates PRD
    2. Architecture Design (Lead Engineer) - Creates technical architecture
    3. Implementation Cycle (Software Engineer + Reviews) - Implements code with review loop

    Flow:
    - User Prompt → Product Lead analyzes and creates PRD
    - PRD → Lead Engineer creates technical architecture
    - Architecture → Software Engineer implements with code review and security review

    Output:
    - product_lead_prd_[name]_[timestamp].md
    - lead_engineer_architecture_[name]_[timestamp].md
    - software_engineer_implementation_[name]_[timestamp].py""",
    steps=[
        product_discovery_step,
        architecture_design_step,
        Condition(
            name="implementation_condition",
            description="Run implementation cycle if enabled",
            evaluator=should_run_implementation,
            steps=[implementation_cycle_step],
        ),
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
    enable_competitor_analysis: bool = False,
    enable_implementation: bool = True,
    github_repo: Optional[str] = None,
    github_owner: Optional[str] = None,
    vercel_project: Optional[str] = None,
    vercel_team: Optional[str] = None,
    supabase_project: Optional[str] = None,
    supabase_org: Optional[str] = None,
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
        enable_implementation: Run implementation cycle (default True)
        github_repo: GitHub repository name (required for implementation)
        github_owner: GitHub owner/organization (required for implementation)
        vercel_project: Vercel project name (optional)
        vercel_team: Vercel team/org slug (optional)
        supabase_project: Supabase project name/ref (optional)
        supabase_org: Supabase organization (optional)

    Returns:
        dict: Result with success status and content

    Examples:
        # Product from scratch with research and implementation
        >>> result = run_software_development(
        ...     product_name="AI Email Assistant",
        ...     product_context="Help sales write follow-ups",
        ...     scope="product",
        ...     enable_research=True,
        ...     enable_implementation=True,
        ...     github_repo="ai-email-assistant",
        ...     github_owner="my-org"
        ... )

        # Simple feature (PRD and architecture only)
        >>> result = run_software_development(
        ...     product_name="Dark Mode Toggle",
        ...     product_context="Add dark mode to settings",
        ...     scope="feature",
        ...     enable_implementation=False
        ... )
    """
    # Build project context if GitHub details provided
    project_ctx = None
    if github_repo and github_owner:
        project_ctx = ProjectContext(
            github_repo=github_repo,
            github_owner=github_owner,
            vercel_project=vercel_project,
            vercel_team=vercel_team,
            supabase_project=supabase_project,
            supabase_org=supabase_org,
        )

    workflow_input = SoftwareDevelopmentInput(
        product_name=product_name,
        product_context=product_context,
        target_audience=target_audience,
        user_prompt=user_prompt,
        project_context=project_ctx,
        scope=scope,
        enable_research=enable_research,
        enable_competitor_analysis=enable_competitor_analysis,
        enable_implementation=enable_implementation
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
    parser.add_argument("--enable-implementation", action="store_true", default=True)
    parser.add_argument("--no-implementation", action="store_true", help="Skip implementation cycle")
    parser.add_argument("--github-repo", help="GitHub repository name")
    parser.add_argument("--github-owner", help="GitHub owner/organization")
    parser.add_argument("--vercel-project", help="Vercel project name")
    parser.add_argument("--vercel-team", help="Vercel team/org slug")
    parser.add_argument("--supabase-project", help="Supabase project name/ref")
    parser.add_argument("--supabase-org", help="Supabase organization")

    args = parser.parse_args()

    result = run_software_development(
        product_name=args.product_name,
        product_context=args.product_context,
        target_audience=args.target_audience,
        user_prompt=args.user_prompt,
        scope=args.scope,
        enable_research=args.enable_research,
        enable_competitor_analysis=args.enable_competitor_analysis,
        enable_implementation=not args.no_implementation,
        github_repo=args.github_repo,
        github_owner=args.github_owner,
        vercel_project=args.vercel_project,
        vercel_team=args.vercel_team,
        supabase_project=args.supabase_project,
        supabase_org=args.supabase_org,
    )

    logger.info(f"Workflow completed!")
    print(result["content"])

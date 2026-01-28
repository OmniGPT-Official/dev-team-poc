"""
Architecture Design Workflow

A simple workflow for creating technical architecture from PRD.

Steps:
1. Architecture Design - Lead engineer creates technical architecture
2. Ticket Creation - Generate ticket.md file

Usage:
    from workflows.architecture_design_workflow import architecture_design_workflow, ArchitectureDesignInput

    workflow_input = ArchitectureDesignInput(
        prd_content="[PRD content here]",
        product_name="AI Assistant"
    )

    result = architecture_design_workflow.run(input=workflow_input)
"""

import os
import sys
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

from agents.lead_engineer import lead_engineer_agent


# ============================================================================
# INPUT MODEL
# ============================================================================

class ArchitectureDesignInput(BaseModel):
    """Input model for Architecture Design Workflow."""
    prd_content: str = Field(..., description="PRD content from product discovery")
    product_name: str = Field(..., description="Name of the product/feature")
    prd_file_path: Optional[str] = Field(None, description="Path to PRD file")


# ============================================================================
# STEP 1: ARCHITECTURE DESIGN
# ============================================================================

def create_architecture(step_input: StepInput) -> StepOutput:
    """Lead engineer creates technical architecture from PRD."""
    try:
        workflow_input: ArchitectureDesignInput = step_input.input

        architecture_prompt = f"""Based on the following PRD, create a technical architecture design:

**Product/Feature:** {workflow_input.product_name}

**PRD:**
{workflow_input.prd_content}

**Create a technical architecture document with:**

1. **System Overview** (2-3 sentences)
   - High-level technical approach
   - Key architectural decisions

2. **Components & Responsibilities**
   - List 3-5 main components
   - Each component: name + brief responsibility (1 sentence)

3. **Data Flow**
   - How data moves through the system
   - Key interactions between components

4. **Technology Stack**
   - Languages/frameworks
   - Key libraries/services
   - Infrastructure requirements

5. **API Design** (if applicable)
   - Key endpoints
   - Request/response formats

6. **Implementation Tasks**
   - Break down into 5-8 specific, actionable tickets
   - Each ticket: clear title + brief description

**Format as a clear, structured markdown document.**
"""

        log_info(f"[ARCHITECTURE] Creating architecture for: {workflow_input.product_name}")
        result = lead_engineer_agent.run(architecture_prompt)

        if result.content:
            log_info("[ARCHITECTURE] Architecture design completed")
            return StepOutput(content=result.content, success=True)
        else:
            return StepOutput(content="Architecture design failed", success=False)

    except Exception as e:
        log_error(f"[ARCHITECTURE] Error: {str(e)}")
        return StepOutput(content=f"Architecture error: {str(e)}", success=False)


architecture_step = Step(
    name="architecture_design",
    description="Create technical architecture from PRD",
    executor=create_architecture
)


# ============================================================================
# STEP 2: TICKET CREATION
# ============================================================================

def create_ticket(step_input: StepInput) -> StepOutput:
    """Create ticket.md file with architecture and implementation tasks."""
    try:
        workflow_input: ArchitectureDesignInput = step_input.input

        # Get architecture from previous step
        architecture = step_input.get_step_content("architecture_design")

        log_info("[TICKET] Creating ticket.md file")

        # Save to ticket.md
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = workflow_input.product_name.lower().replace(" ", "_").replace("/", "_")[:50]
        filename = f"ticket_{safe_name}_{timestamp}.md"

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(project_root, filename)

        # Format the ticket content
        ticket_content = f"""# Architecture & Implementation Ticket

**Product/Feature:** {workflow_input.product_name}
**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

{architecture}

---

**Status:** Ready for Implementation
**PRD Reference:** {workflow_input.prd_file_path if workflow_input.prd_file_path else 'N/A'}
"""

        with open(filepath, "w") as f:
            f.write(ticket_content)

        log_info(f"[TICKET] Saved to: {filepath}")

        output = f"""✅ **Architecture & Implementation Ticket Created**

**File:** `{filepath}`

---

{architecture}
"""

        return StepOutput(content=output, success=True)

    except Exception as e:
        log_error(f"[TICKET] Error: {str(e)}")
        return StepOutput(content=f"Ticket creation error: {str(e)}", success=False)


ticket_creation_step = Step(
    name="ticket_creation",
    description="Create ticket.md file with architecture",
    executor=create_ticket
)


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

architecture_design_workflow = Workflow(
    name="Architecture Design Workflow",
    stream=False,
    description="""Architecture design workflow:

    Steps:
    1. Architecture Design - Lead engineer creates technical architecture
    2. Ticket Creation - Generate ticket.md file

    Input: PRD content
    Output: ticket.md file with architecture and implementation tasks""",
    steps=[
        architecture_step,
        ticket_creation_step,
    ]
)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def run_architecture_design(
    prd_content: str,
    product_name: str,
    prd_file_path: Optional[str] = None
) -> str:
    """
    Run the architecture design workflow.

    Args:
        prd_content: PRD content from product discovery
        product_name: Name of the product/feature
        prd_file_path: Optional path to PRD file

    Returns:
        str: Path to generated ticket file
    """
    workflow_input = ArchitectureDesignInput(
        prd_content=prd_content,
        product_name=product_name,
        prd_file_path=prd_file_path
    )

    log_info(f"Starting architecture design workflow: {product_name}")
    result = architecture_design_workflow.run(input=workflow_input)

    # Extract file path
    if "File:**" in result.content:
        filepath = result.content.split("`")[1]
        return filepath

    return result.content


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Architecture Design Workflow")
    parser.add_argument("--prd-file", required=True, help="Path to PRD file")
    parser.add_argument("--product-name", required=True, help="Product/feature name")

    args = parser.parse_args()

    # Read PRD content
    with open(args.prd_file, "r") as f:
        prd_content = f.read()

    result = run_architecture_design(
        prd_content=prd_content,
        product_name=args.product_name,
        prd_file_path=args.prd_file
    )

    logger.info(f"Workflow completed! Ticket: {result}")

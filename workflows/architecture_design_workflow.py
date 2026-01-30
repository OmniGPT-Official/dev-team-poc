"""
Architecture Design Workflow

A workflow for creating technical architecture from PRD.
All steps are executed by the Lead Engineer agent.

Steps:
1. Architecture Design - Lead Engineer creates technical architecture

Input: PRD content
Output: Architecture file (lead_engineer_architecture_[product_name]_[timestamp].md)

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
import asyncio
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
# ASYNC HELPER - Run async agent calls from sync workflow steps
# ============================================================================

# Persistent event loop for running async code from sync context
_event_loop = None


def get_or_create_event_loop():
    """Get existing event loop or create a new one."""
    global _event_loop
    if _event_loop is None or _event_loop.is_closed():
        _event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_event_loop)
    return _event_loop


def run_async(coro):
    """
    Run an async coroutine from synchronous code.
    Uses a persistent event loop to avoid 'Event loop is closed' errors.
    """
    loop = get_or_create_event_loop()
    return loop.run_until_complete(coro)


# ============================================================================
# INPUT MODEL
# ============================================================================

class ArchitectureDesignInput(BaseModel):
    """Input model for Architecture Design Workflow."""
    prd_content: str = Field(..., description="PRD content from product discovery")
    product_name: str = Field(..., description="Name of the product/feature")
    prd_file_path: Optional[str] = Field(None, description="Path to PRD file")


# ============================================================================
# STEP 1: ARCHITECTURE DESIGN (Lead Engineer)
# ============================================================================

def create_architecture(step_input: StepInput) -> StepOutput:
    """Lead Engineer creates technical architecture from PRD."""
    try:
        workflow_input: ArchitectureDesignInput = step_input.input

        architecture_prompt = f"""As the Lead Engineer, create a technical architecture design based on the following PRD:

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
   - Break down into 5-8 specific, actionable tasks
   - Each task: clear title + brief description
   - Order by dependency (what needs to be done first)

7. **Technical Risks & Mitigations**
   - Identify 2-3 key technical risks
   - Propose mitigation strategies

**Format as a clear, structured markdown document.**
"""

        log_info(f"[ARCHITECTURE] Lead Engineer creating architecture for: {workflow_input.product_name}")
        # Run async agent with MCP tools
        result = run_async(lead_engineer_agent.arun(architecture_prompt))

        if result.content:
            log_info("[ARCHITECTURE] Architecture design completed by Lead Engineer")

            # Save to file with new naming format: lead_engineer_architecture_[name]_[timestamp].md
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = workflow_input.product_name.lower().replace(" ", "_").replace("/", "_")[:50]
            filename = f"lead_engineer_architecture_{safe_name}_{timestamp}.md"

            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            filepath = os.path.join(project_root, filename)

            # Format the architecture content with metadata
            architecture_content = f"""# Technical Architecture

**Product/Feature:** {workflow_input.product_name}
**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Created By:** Lead Engineer

---

{result.content}

---

**PRD Reference:** {workflow_input.prd_file_path if workflow_input.prd_file_path else 'N/A'}
"""

            with open(filepath, "w") as f:
                f.write(architecture_content)

            log_info(f"[ARCHITECTURE] Saved to: {filepath}")

            output = f"""{architecture_content}

---

**Architecture saved to:** `{filepath}`"""

            return StepOutput(content=output, success=True)
        else:
            return StepOutput(content="Architecture design failed", success=False)

    except Exception as e:
        log_error(f"[ARCHITECTURE] Error: {str(e)}")
        return StepOutput(content=f"Architecture error: {str(e)}", success=False)


architecture_step = Step(
    name="architecture_design",
    description="Lead Engineer creates technical architecture from PRD",
    executor=create_architecture
)


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

architecture_design_workflow = Workflow(
    name="Architecture Design Workflow",
    stream=False,
    description="""Architecture design workflow (all steps by Lead Engineer):

    Steps:
    1. Architecture Design - Lead Engineer creates technical architecture

    Input: PRD content from Product Lead
    Output: Architecture file (lead_engineer_architecture_[name]_[timestamp].md)""",
    steps=[
        architecture_step,
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
        str: Path to generated architecture file
    """
    workflow_input = ArchitectureDesignInput(
        prd_content=prd_content,
        product_name=product_name,
        prd_file_path=prd_file_path
    )

    log_info(f"Starting architecture design workflow: {product_name}")
    result = architecture_design_workflow.run(input=workflow_input)

    # Extract file path
    if "saved to:" in result.content:
        filepath = result.content.split("`")[-2]
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

    logger.info(f"Workflow completed! Architecture: {result}")

"""
Discovery and Requirements Workflow

A flexible workflow for defining goals and requirements for any scope of work.

Steps:
1. Analysis - Analyze the request and determine what's needed
2. Research (Conditional) - Market + Competitor research (only for products from scratch)
3. Synthesis - Synthesize findings and prepare requirements
4. PRD Creation - Create appropriate document based on scope

Features:
- Independent research control (enable_research, enable_competitor_analysis)
- Dynamic PRD format: product (structured) vs feature (simple)
- No hallucination - only uses provided information
- Research runs in parallel when enabled

Usage:
    from workflows.product_discovery_workflow import discovery_and_requirements_workflow, DiscoveryAndRequirementsInput

    # Product from scratch with research
    workflow_input = DiscoveryAndRequirementsInput(
        product_name="AI Assistant",
        product_context="Help sales teams automate follow-up emails",
        scope="product",
        enable_research=True,
        enable_competitor_analysis=True
    )

    # Simple feature, no research
    workflow_input = DiscoveryAndRequirementsInput(
        product_name="Dark Mode Toggle",
        product_context="Add dark mode to settings",
        scope="feature"
    )

    result = discovery_and_requirements_workflow.run(input=workflow_input)
"""

import os
import sys
from datetime import datetime
from typing import Optional
from loguru import logger
from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.workflow.condition import Condition
from agno.workflow.step import Step
from agno.workflow.types import StepInput, StepOutput
from agno.workflow.workflow import Workflow
from agno.utils.log import log_error, log_info

from agno.agent import Agent
from agno.models.anthropic import Claude
from agents.research_agent import research_agent
from instructions.product_lead_instructions import PRODUCT_LEAD_INSTRUCTIONS


# ============================================================================
# INPUT MODEL
# ============================================================================

class DiscoveryAndRequirementsInput(BaseModel):
    """Input model for Discovery and Requirements Workflow."""
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

# Keep old name for backwards compatibility
ProductDiscoveryInput = DiscoveryAndRequirementsInput


# ============================================================================
# STEP 1: ANALYSIS
# ============================================================================

analysis_agent = Agent(
    name="Requirements Analyst",
    model=Claude(id="claude-sonnet-4-5"),
    instructions="""You are a requirements analyst. Your task is to:

1. ANALYZE THE REQUEST:
   - Understand what is being asked
   - Identify the scope (product from scratch vs feature)
   - Determine what information is provided vs missing
   - Assess if research would be valuable

2. OUTPUT:
   - **Scope**: Product from scratch or feature/enhancement
   - **Key Information**: What we know
   - **Gaps**: What information is missing
   - **Research Recommendation**: Whether research would help (yes/no and why)

Be concise. No hallucination - only analyze what's provided."""
)

def analyze_request(step_input: StepInput) -> StepOutput:
    """Analyze the request to understand scope and information gaps."""
    try:
        workflow_input: DiscoveryAndRequirementsInput = step_input.input

        analysis_prompt = f"""Analyze this product/feature request:

**Name:** {workflow_input.product_name}
**Context:** {workflow_input.product_context}
**Scope:** {workflow_input.scope.capitalize()}
**Target Audience:** {workflow_input.target_audience or 'Not specified'}
**User Request:** {workflow_input.user_prompt or 'Not specified'}

Provide a brief analysis following your instructions."""

        log_info(f"[ANALYSIS] Analyzing request for: {workflow_input.product_name}")
        result = analysis_agent.run(analysis_prompt)

        if result.content:
            log_info("[ANALYSIS] Analysis completed")
            return StepOutput(content=result.content, success=True)
        else:
            return StepOutput(content="Analysis failed", success=False)

    except Exception as e:
        log_error(f"[ANALYSIS] Error: {str(e)}")
        return StepOutput(content=f"Analysis error: {str(e)}", success=False)


analysis_step = Step(
    name="analysis",
    description="Analyze the request and identify information gaps",
    executor=analyze_request
)


# ============================================================================
# STEP 2: RESEARCH (CONDITIONAL - Only for products from scratch)
# ============================================================================

market_research_agent = Agent(
    name="Market Researcher",
    model=Claude(id="claude-sonnet-4-5"),
    instructions="""You conduct market research. Search Google for:
- Problem domain information
- Existing solutions and approaches
- User needs and pain points
- Best practices and patterns
- Market trends

**CRITICAL**: Only report what you actually find. Do NOT hallucinate.""",
    markdown=True,
)

competitor_research_agent = Agent(
    name="Competitor Researcher",
    model=Claude(id="claude-sonnet-4-5"),
    instructions="""You conduct competitor analysis. Search for:
- Top 3-5 competitors or similar solutions
- Their features, pricing, positioning
- Feature comparison matrix
- Competitive gaps and opportunities

**CRITICAL**: Only report what you actually find. Do NOT hallucinate.""",
    markdown=True,
  
)

def conduct_research(step_input: StepInput) -> StepOutput:
    """
    Conduct market and competitor research in parallel.
    Only runs if scope is 'product' AND research is enabled.
    """
    try:
        workflow_input: DiscoveryAndRequirementsInput = step_input.input

        # Build research prompt
        context = f"""
**Product:** {workflow_input.product_name}
**Context:** {workflow_input.product_context}
**Target Audience:** {workflow_input.target_audience or 'Not specified'}
"""

        results = []

        # Market research if enabled
        if workflow_input.enable_research:
            log_info("[RESEARCH] Conducting market research...")
            market_prompt = f"{context}\n\nConduct market research on this problem domain. Search Google for existing solutions, user needs, and best practices."
            market_result = market_research_agent.run(market_prompt)
            if market_result.content:
                results.append(f"## Market Research\n\n{market_result.content}")

        # Competitor research if enabled
        if workflow_input.enable_competitor_analysis:
            log_info("[RESEARCH] Conducting competitor analysis...")
            competitor_prompt = f"{context}\n\nConduct competitor analysis. Search for top competitors, their features, and positioning."
            competitor_result = competitor_research_agent.run(competitor_prompt)
            if competitor_result.content:
                results.append(f"## Competitor Analysis\n\n{competitor_result.content}")

        if results:
            combined = "\n\n---\n\n".join(results)
            log_info("[RESEARCH] Research completed")
            return StepOutput(content=combined, success=True)
        else:
            return StepOutput(content="No research conducted", success=True)

    except Exception as e:
        log_error(f"[RESEARCH] Error: {str(e)}")
        return StepOutput(content=f"Research error: {str(e)}", success=False)


research_step = Step(
    name="research",
    description="Conduct market and competitor research (parallel execution)",
    executor=conduct_research
)


# ============================================================================
# CONDITION: Should we do research?
# ============================================================================

def should_conduct_research(step_input: StepInput) -> bool:
    """
    Research is only conducted for products built from scratch when research is enabled.
    """
    workflow_input: DiscoveryAndRequirementsInput = step_input.input

    # Research only for products from scratch with research enabled
    is_product_from_scratch = workflow_input.scope == "product"
    research_enabled = workflow_input.enable_research or workflow_input.enable_competitor_analysis

    should_research = is_product_from_scratch and research_enabled

    if should_research:
        log_info(f"[CONDITION] Research enabled for product from scratch")
    else:
        log_info(f"[CONDITION] Skipping research (scope: {workflow_input.scope}, research: {research_enabled})")

    return should_research


# ============================================================================
# STEP 3: SYNTHESIS
# ============================================================================

synthesis_agent = Agent(
    name="Requirements Synthesizer",
    model=Claude(id="claude-sonnet-4-5"),
    instructions="""You synthesize information to prepare for requirements writing. Your task:

1. REVIEW:
   - Initial analysis
   - Research findings (if available)
   - Information provided by user

2. SYNTHESIZE:
   - Key insights and patterns
   - Critical requirements that can be inferred
   - Important constraints or considerations
   - Open questions that remain

3. OUTPUT:
   Format as:
   - **Key Insights**: 2-4 main takeaways
   - **Core Requirements**: Essential needs identified
   - **Open Questions**: What's still unclear

**CRITICAL**: No hallucination. Only synthesize from provided information."""
)

def synthesize_findings(step_input: StepInput) -> StepOutput:
    """Synthesize analysis and research findings."""
    try:
        workflow_input: DiscoveryAndRequirementsInput = step_input.input

        # Get previous steps content
        analysis = step_input.get_step_content("analysis")
        research = step_input.get_step_content("research")

        has_research = research and "No research conducted" not in research

        synthesis_prompt = f"""Synthesize the following information to prepare for requirements writing:

**Product/Feature:** {workflow_input.product_name}
**Scope:** {workflow_input.scope.capitalize()}

**Initial Analysis:**
{analysis}
"""

        if has_research:
            synthesis_prompt += f"""

**Research Findings:**
{research}
"""

        synthesis_prompt += """

Provide a concise synthesis following your instructions."""

        log_info(f"[SYNTHESIS] Synthesizing findings for: {workflow_input.product_name}")
        result = synthesis_agent.run(synthesis_prompt)

        if result.content:
            log_info("[SYNTHESIS] Synthesis completed")
            return StepOutput(content=result.content, success=True)
        else:
            return StepOutput(content="Synthesis failed", success=False)

    except Exception as e:
        log_error(f"[SYNTHESIS] Error: {str(e)}")
        return StepOutput(content=f"Synthesis error: {str(e)}", success=False)


synthesis_step = Step(
    name="synthesis",
    description="Synthesize analysis and research findings",
    executor=synthesize_findings
)


# ============================================================================
# STEP 4: PRD CREATION
# ============================================================================

def create_requirements_document(step_input: StepInput) -> StepOutput:
    """
    Create requirements document with format based on scope.
    - Product (from scratch): Structured PRD with research
    - Feature: Simple document with goals and acceptance criteria
    """
    try:
        workflow_input: DiscoveryAndRequirementsInput = step_input.input

        # Get all previous steps
        analysis = step_input.get_step_content("analysis")
        research = step_input.get_step_content("research")
        synthesis = step_input.get_step_content("synthesis")

        has_research = research and "No research conducted" not in research

        log_info(f"[PRD] Creating {workflow_input.scope} requirements document")

        # Build prompt based on scope
        if workflow_input.scope == "product":
            # STRUCTURED PRD for products from scratch
            prd_prompt = f"""Create a structured Product Requirements Document.

**Product:** {workflow_input.product_name}
**Context:** {workflow_input.product_context}
**Target Audience:** {workflow_input.target_audience or 'Not specified'}

**Analysis:**
{analysis}

**Synthesis:**
{synthesis}
"""
            if has_research:
                prd_prompt += f"""

**Research:**
{research}
"""

            prd_prompt += """

**Create a structured PRD (1-2 pages) with:**

1. **Overview** (2-3 sentences) - What we're building and why
2. **Problem & Goals** - Problem statement + 2-4 measurable goals
3. **Target Users** - Who will use this (brief)
4. **Requirements**
   - **Must Have (P0)**: Max 5 core requirements
     - Each with 2-3 acceptance criteria
   - **Should Have (P1)**: Max 3 additional requirements
   - **Nice to Have (P2)**: Optional enhancements
5. **Success Metrics** - 2-4 KPIs
6. **Out of Scope** - What we're NOT doing
7. **Open Questions** - Unresolved items

**CRITICAL RULES:**
- **NO HALLUCINATION**: Only use provided information
- **Missing info**: List as open question, don't invent
- **1-2 pages max**: Be concise
- **Research**: Only cite if provided above
- **Actionable**: Focus on what to build"""

        else:
            # SIMPLE DOCUMENT for features
            prd_prompt = f"""Create a simple feature requirements document.

**Feature:** {workflow_input.product_name}
**Context:** {workflow_input.product_context}
**Target Audience:** {workflow_input.target_audience or 'Not specified'}

**Analysis:**
{analysis}

**Synthesis:**
{synthesis}

**Create a simple document (1 page) with:**

1. **What**: What we're building (2 sentences)
2. **Why**: Why this matters (1 sentence)
3. **Goal**: One specific, measurable objective
4. **Acceptance Criteria**:
   - 3-5 clear, testable criteria
   - Format: "Given [context], when [action], then [outcome]"
5. **Out of Scope**: What this won't do
6. **Open Questions**: If any

**CRITICAL RULES:**
- **NO HALLUCINATION**: Only use provided information
- **Keep it simple**: This is a feature, not a product
- **Acceptance criteria**: Clear and testable
- **1 page max**"""

        # Create PRD agent inline to avoid circular import
        prd_agent = Agent(
            name="PRD Creator",
            model=Claude(id="claude-sonnet-4-5"),
            instructions=PRODUCT_LEAD_INSTRUCTIONS,
            markdown=True
        )

        # Run PRD agent
        result = prd_agent.run(prd_prompt)

        if result.content:
            log_info("[PRD] Requirements document created")

            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = workflow_input.product_name.lower().replace(" ", "_").replace("/", "_")[:50]
            filename = f"prd_{safe_name}_{timestamp}.md"

            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            filepath = os.path.join(project_root, filename)

            with open(filepath, "w") as f:
                f.write(result.content)

            log_info(f"[PRD] Saved to: {filepath}")

            output = f"""{result.content}

---

✅ **Requirements Document saved to:** `{filepath}`"""

            return StepOutput(content=output, success=True)
        else:
            return StepOutput(content="PRD creation failed", success=False)

    except Exception as e:
        log_error(f"[PRD] Error: {str(e)}")
        return StepOutput(content=f"PRD creation error: {str(e)}", success=False)


prd_creation_step = Step(
    name="prd_creation",
    description="Create requirements document based on scope",
    executor=create_requirements_document
)


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

discovery_and_requirements_workflow = Workflow(
    name="Discovery and Requirements Workflow",
    stream=False,
    description="""Product discovery and requirements workflow:

    Steps:
    1. Analysis - Analyze request and identify gaps
    2. Research (Conditional) - Market + Competitor research (only for products from scratch)
    3. Synthesis - Synthesize findings
    4. PRD Creation - Create appropriate document (structured for products, simple for features)

    Features:
    - Conditional research (only for products from scratch)
    - Parallel market and competitor research
    - Dynamic format (structured PRD vs simple feature doc)
    - No hallucination - uses only provided information

    Output: Requirements document saved as .md file""",
    steps=[
        analysis_step,
        Condition(
            name="research_condition",
            description="Conduct research only for products from scratch with research enabled",
            evaluator=should_conduct_research,
            steps=[research_step]
        ),
        synthesis_step,
        prd_creation_step,
    ]
)

# Keep old name for backwards compatibility
product_discovery_workflow = discovery_and_requirements_workflow


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def run_discovery_and_requirements(
    product_name: str,
    product_context: str,
    target_audience: Optional[str] = None,
    user_prompt: Optional[str] = None,
    scope: str = "feature",
    enable_research: bool = False,
    enable_competitor_analysis: bool = False
) -> str:
    """
    Run the discovery and requirements workflow.

    Args:
        product_name: Name of the product/feature
        product_context: Description of what needs to be built
        target_audience: Who will use this (optional)
        user_prompt: Original user request (optional)
        scope: 'product' (from scratch) or 'feature'
        enable_research: Conduct market research (only for products)
        enable_competitor_analysis: Conduct competitor analysis (only for products)

    Returns:
        str: Path to generated requirements document

    Examples:
        # Product from scratch with research
        >>> doc = run_discovery_and_requirements(
        ...     product_name="AI Email Assistant",
        ...     product_context="Help sales write follow-ups",
        ...     scope="product",
        ...     enable_research=True,
        ...     enable_competitor_analysis=True
        ... )

        # Simple feature, no research
        >>> doc = run_discovery_and_requirements(
        ...     product_name="Dark Mode Toggle",
        ...     product_context="Add dark mode to settings",
        ...     scope="feature"
        ... )
    """
    workflow_input = DiscoveryAndRequirementsInput(
        product_name=product_name,
        product_context=product_context,
        target_audience=target_audience,
        user_prompt=user_prompt,
        scope=scope,
        enable_research=enable_research,
        enable_competitor_analysis=enable_competitor_analysis
    )

    log_info(f"Starting discovery workflow: {product_name} ({scope})")
    result = discovery_and_requirements_workflow.run(input=workflow_input)

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

    parser = argparse.ArgumentParser(description="Run Discovery and Requirements Workflow")
    parser.add_argument("--product-name", required=True)
    parser.add_argument("--product-context", required=True)
    parser.add_argument("--target-audience")
    parser.add_argument("--user-prompt")
    parser.add_argument("--scope", choices=["product", "feature"], default="feature")
    parser.add_argument("--enable-research", action="store_true")
    parser.add_argument("--enable-competitor-analysis", action="store_true")

    args = parser.parse_args()

    result = run_discovery_and_requirements(
        product_name=args.product_name,
        product_context=args.product_context,
        target_audience=args.target_audience,
        user_prompt=args.user_prompt,
        scope=args.scope,
        enable_research=args.enable_research,
        enable_competitor_analysis=args.enable_competitor_analysis
    )

    logger.info(f"Workflow completed! Document: {result}")

"""
Product Lead Agent Configuration

The Product Lead creates PRDs and can orchestrate the software development workflow.
Before starting the workflow, the Product Lead gathers project context:
- GitHub repository and owner/org
- Vercel project and team (optional)
- Supabase project and org (optional)
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from instructions.product_lead_instructions import PRODUCT_LEAD_INSTRUCTIONS


# Create the base product lead agent
product_lead_agent = Agent(
    name="Product Lead",
    role="Creates PRDs, structured tickets, product descriptions, goal setting (OKRs), and RICE prioritization. Can orchestrate software development workflows.",
    model=Claude(id="claude-sonnet-4-5"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=PRODUCT_LEAD_INSTRUCTIONS
)


# ============================================================================
# WORKFLOW TOOLS SETUP (called after all imports are complete)
# ============================================================================

def add_workflow_tools():
    """
    Add Software Development workflow tools to the product lead agent.
    This is called after all modules are imported to avoid circular dependencies.
    """
    from agno.tools.workflow import WorkflowTools
    from workflows.software_development_workflow import software_development_workflow

    # Create workflow tools
    workflow_tools = WorkflowTools(
        workflow=software_development_workflow,
    )

    # Add tools to agent
    product_lead_agent.tools = [workflow_tools]

    # Enhance instructions with workflow orchestration capability
    product_lead_agent.instructions = f"""{PRODUCT_LEAD_INSTRUCTIONS}

**ADDITIONAL CAPABILITY: Software Development Workflow Orchestration**

You have access to the Software Development workflow tool that automates the complete process:

1. **CRITICAL - Gather Project Context FIRST**:
   Before triggering the workflow, you MUST ask the user for the following project context:

   **Required:**
   - **GitHub Repository**: Name of the GitHub repo (e.g., "my-app")
   - **GitHub Owner/Org**: Owner or organization name (e.g., "my-org" or "username")

   **Optional (ask if relevant):**
   - **Vercel Project**: Name of the Vercel project
   - **Vercel Team/Org**: Vercel team or org slug
   - **Supabase Project**: Name/ref of the Supabase project
   - **Supabase Org**: Supabase organization name

   Example questions to ask:
   - "What GitHub repository should I use? Please provide the repo name and owner/org."
   - "Are you using Vercel for deployment? If so, what's the project name and team?"
   - "Are you using Supabase? If so, what's the project name and organization?"

2. **Understand Requirements**:
   - Listen to user requests for products or features
   - Ask clarifying questions if needed
   - Determine scope (product from scratch vs feature)

3. **Trigger Software Development Workflow**:
   - Use the Software Development workflow tool to initiate the process
   - **ALWAYS include project_context** with the gathered GitHub/Vercel/Supabase info
   - The workflow will automatically:
     * Create a Product Requirements Document (PRD)
     * Generate technical architecture
     * Create implementation code (stored in GitHub)
   - Pass appropriate parameters based on scope

4. **Communicate Results**:
   - Share the PRD and architecture ticket with the user
   - Explain what was created and next steps
   - Provide GitHub file paths for easy access

5. **Decision Making**:
   - For products from scratch: Consider enabling research
   - For features: Keep it simple, no research needed
   - Always be clear about scope and approach

**Workflow Parameters:**
- product_name: Clear, descriptive name
- product_context: What needs to be built
- scope: "product" (from scratch) or "feature" (single feature)
- enable_research: true for products from scratch (optional)
- enable_competitor_analysis: true for competitive products (optional)
- project_context: Object containing:
  - github_repo: Repository name (REQUIRED)
  - github_owner: Owner/org name (REQUIRED)
  - vercel_project: Vercel project name (optional)
  - vercel_team: Vercel team slug (optional)
  - supabase_project: Supabase project name (optional)
  - supabase_org: Supabase org name (optional)

**Your goal:** Gather project context first, then guide users from idea to actionable implementation plan efficiently.
"""


# ============================================================================
# CONVENIENCE FUNCTION FOR DIRECT USE
# ============================================================================

def run_product_lead(user_message: str, stream: bool = True):
    """
    Run the product lead agent with a user message.

    Args:
        user_message: User's request for product/feature development
        stream: Whether to stream the response

    Returns:
        Agent response with PRD and architecture ticket

    Example:
        >>> response = run_product_lead(
        ...     "Create a blog post scheduling system for content creators"
        ... )
    """
    # Ensure workflow tools are added
    if not product_lead_agent.tools:
        add_workflow_tools()

    return product_lead_agent.print_response(user_message, stream=stream)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Talk to Product Lead Agent")
    parser.add_argument("message", help="Your message to the product lead")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming")

    args = parser.parse_args()

    print("🚀 Product Lead Agent\n")
    print("=" * 60)

    run_product_lead(args.message, stream=not args.no_stream)

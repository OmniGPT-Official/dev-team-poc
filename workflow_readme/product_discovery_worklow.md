# Product Discovery Workflow

A streamlined workflow using **2 agents** to create comprehensive Product Requirements Documents (PRDs) backed by market research.

## Overview

**Agents Used:**
1. **Research Agent** - Conducts market research and competitor analysis
2. **Product Lead** - Synthesizes research and creates PRD

**Output:** `prd_<product_name>_<timestamp>.md` file

## Workflow Steps

```
┌─────────────────────────────────────────────────┐
│  Step 1: Market Research                       │
│  ─────────────────────────                      │
│  Agent: Research Agent                          │
│  Tasks:                                         │
│  • Market trends analysis                       │
│  • User needs & pain points                     │
│  • Competitor analysis (optional)               │
│  • Feature comparison                           │
│  • Strategic recommendations                    │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  Step 2: PRD Creation                          │
│  ────────────────────                           │
│  Agent: Product Lead                            │
│  Tasks:                                         │
│  • Synthesize research findings                 │
│  • Extract strategic insights                   │
│  • Create comprehensive PRD                     │
│  • Save as prd.md file                          │
└─────────────────────────────────────────────────┘
```

## Usage

### Option 1: Command Line (Easiest)

```bash
# Basic usage
python workflows/run_product_discovery.py \
    --product-name "AI Email Assistant" \
    --product-context "Helps sales teams write personalized follow-up emails"

# With target audience
python workflows/run_product_discovery.py \
    --product-name "AI Email Assistant" \
    --product-context "Helps sales teams write personalized follow-up emails" \
    --target-audience "B2B sales representatives"

# Skip competitor analysis (faster)
python workflows/run_product_discovery.py \
    --product-name "Dark Mode Feature" \
    --product-context "Add dark mode to the application" \
    --skip-competitors

# Interactive mode (asks you questions)
python workflows/run_product_discovery.py --interactive
```

### Option 2: Python API

```python
from workflows.product_discovery_workflow import run_product_discovery

# Run workflow and get PRD file path
prd_path = run_product_discovery(
    product_name="AI Email Assistant",
    product_context="Helps sales teams write personalized follow-up emails",
    target_audience="B2B sales representatives",
    include_competitor_analysis=True
)

print(f"PRD created at: {prd_path}")
```

### Option 3: As a Tool (for Agents)

```python
from agno.agent import Agent
from agno.models.anthropic import Claude
from tools.product_discovery_tool import ProductDiscoveryToolkit

# Create an agent with product discovery capability
pm_agent = Agent(
    name="Product Manager",
    model=Claude(id="claude-sonnet-4-5"),
    tools=[ProductDiscoveryToolkit()],
    instructions="You help create product requirements using market research"
)

# The agent can now use the tool
pm_agent.print_response(
    "Create a PRD for an AI email assistant for sales teams",
    stream=True
)
```

### Option 4: Direct Workflow Usage

```python
from workflows.product_discovery_workflow import (
    product_discovery_workflow,
    ProductDiscoveryInput
)

# Create input
workflow_input = ProductDiscoveryInput(
    product_name="AI Email Assistant",
    product_context="Helps sales teams write personalized follow-up emails",
    target_audience="B2B sales representatives",
    user_prompt="Build an AI assistant for sales follow-ups",
    include_competitor_analysis=True
)

# Run workflow (streaming)
product_discovery_workflow.print_response(input=workflow_input)

# Or run workflow (non-streaming)
result = product_discovery_workflow.run(input=workflow_input)
print(result.content)
```

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `product_name` | str | Yes | Name of the product or feature |
| `product_context` | str | Yes | Description of what needs to be built |
| `target_audience` | str | No | Who will use this product/feature |
| `user_prompt` | str | No | Original user request (for context) |
| `include_competitor_analysis` | bool | No | Whether to analyze competitors (default: True) |

## Output

The workflow creates a markdown file named `prd_<product_name>_<timestamp>.md` with the following structure:

```markdown
# [Product Name]

## Overview
- Brief description
- Business value

## Problem Statement
- User pain points (backed by research)
- Problem definition

## Strategic Context
- Market insights
- Competitive positioning
- Key opportunities

## Target Audience
- Primary users
- Use cases

## Requirements
### Must Have (P0)
- Core features with acceptance criteria

### Should Have (P1)
- Important but not blocking

### Nice to Have (P2)
- Future enhancements

## Success Metrics
- KPIs and targets

## Out of Scope
- What we're NOT doing

## Open Questions
- Unresolved items
```

## Agent Instructions

### Research Agent
Located at: [`instructions/research_agent_instructions.py`](../instructions/research_agent_instructions.py)

Skills:
- Market research
- Competitor analysis
- Strategic frameworks (SWOT, Porter's Five Forces, Value Proposition Canvas)
- Information synthesis
- Web search using DuckDuckGo

### Product Lead Agent
Located at: [`instructions/product_lead_instructions.py`](../instructions/product_lead_instructions.py)

Skills:
- Research synthesis
- PRD creation
- Strategic insight extraction
- Requirements prioritization (RICE scoring)
- Acceptance criteria definition

## Files Structure

```
workflows/
├── README.md                           # This file
├── product_discovery_workflow.py       # Main workflow definition
└── run_product_discovery.py           # CLI runner script

tools/
└── product_discovery_tool.py          # Tool wrapper for agents

agents/
├── product_lead.py                    # Product Lead agent
└── research_agent.py                  # Research agent

instructions/
├── product_lead_instructions.py       # Product Lead instructions
└── research_agent_instructions.py     # Research Agent instructions
```

## When to Use This Workflow

**Use this workflow when:**
- Building new products or features
- Need market validation before building
- Want research-backed requirements
- Creating comprehensive PRDs
- Understanding competitive landscape

**Don't use this workflow for:**
- Simple bug fixes
- Minor UI tweaks
- Quick changes to existing features
- Tasks where requirements are already clear

## Examples

### Example 1: SaaS Product

```bash
python workflows/run_product_discovery.py \
    --product-name "Task Management App" \
    --product-context "A collaborative task management tool for remote teams" \
    --target-audience "Remote software development teams"
```

### Example 2: Feature Addition

```bash
python workflows/run_product_discovery.py \
    --product-name "AI-Powered Search" \
    --product-context "Add semantic search to our documentation platform" \
    --target-audience "Developers searching for API documentation" \
    --skip-competitors
```

### Example 3: Mobile App

```python
from workflows.product_discovery_workflow import run_product_discovery

prd_path = run_product_discovery(
    product_name="Fitness Tracker App",
    product_context="Mobile app for tracking workouts and nutrition with AI coaching",
    target_audience="Health-conscious millennials aged 25-40",
    user_prompt="Build a fitness app with AI personal trainer",
    include_competitor_analysis=True
)
```

## Customization

### Skip Competitor Analysis

If you want faster results without competitor research:

```bash
python workflows/run_product_discovery.py \
    --product-name "Feature X" \
    --product-context "Description" \
    --skip-competitors
```

### Modify Agent Instructions

Edit the instruction files to customize agent behavior:
- Research Agent: [`instructions/research_agent_instructions.py`](../instructions/research_agent_instructions.py)
- Product Lead: [`instructions/product_lead_instructions.py`](../instructions/product_lead_instructions.py)

### Extend Workflow

To add more steps, edit [`product_discovery_workflow.py`](./product_discovery_workflow.py):

```python
# Add a new step
design_review_step = Step(
    name="Design Review",
    executor=review_design,
    description="Review design specifications"
)

# Add to workflow
product_discovery_workflow = Workflow(
    name="Product Discovery Workflow",
    steps=[
        market_research_step,
        design_review_step,  # New step
        prd_creation_step,
    ]
)
```

## Troubleshooting

### Issue: "No module named 'workflows'"

**Solution:** Run from project root:
```bash
cd /Users/anique/Desktop/Agent-Os
python workflows/run_product_discovery.py --interactive
```

### Issue: Research Agent not finding competitors

**Solution:** The Research Agent uses DuckDuckGo for search. If rate-limited:
1. Wait a few minutes and try again
2. Or skip competitor analysis: `--skip-competitors`
3. Or provide manual context in `product_context`

### Issue: PRD file not created

**Solution:** Check that:
1. You have write permissions in the project directory
2. The workflow completed successfully (check logs)
3. Look for error messages in the console output

## Contributing

To improve this workflow:

1. Update agent instructions for better outputs
2. Add new workflow steps for additional research
3. Integrate with project management tools (Jira, Linear, etc.)
4. Add email notifications when PRD is ready
5. Create templates for different product types

## License

Part of Agent-Os project.

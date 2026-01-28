# Setup Guide - Product Team Lead Agent

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Verify Installation

```bash
python3 -c "from agno.agent import Agent; print('✅ Agno installed successfully')"
```

### 3. Run Test

```bash
python test_product_team_lead.py
```

## Usage Examples

### Example 1: Talk to Product Lead Agent

```python
from agents.product_lead import product_lead_agent

# The agent will automatically trigger the software development workflow
product_lead_agent.print_response(
    "Create a blog post scheduling system for content creators",
    stream=True
)
```

**What happens:**
1. Agent understands your request
2. Triggers Software Development workflow
3. Runs Product Discovery (creates PRD)
4. Runs Architecture Design (creates ticket)
5. Returns both PRD and ticket.md files

### Example 2: Direct Workflow Usage

```python
from workflows.software_development_workflow import run_software_development

result = run_software_development(
    product_name="Blog Post Scheduler",
    product_context="Schedule posts with publish times",
    scope="feature"
)

print(result["content"])
```

### Example 3: Command Line

```bash
# Using the agent
python agents/product_lead.py "Create a task management system"

# Using the workflow directly
python workflows/software_development_workflow.py \
  --product-name "Task Manager" \
  --product-context "Help users organize tasks" \
  --scope feature
```

## Architecture

### Workflow Structure

```
Product Lead Agent
    ↓ (uses WorkflowTools)
Software Development Workflow
    ├── Product Discovery Workflow
    │   ├── Analysis
    │   ├── Research (conditional)
    │   ├── Synthesis
    │   └── PRD Creation → prd_[name]_[timestamp].md
    │
    └── Architecture Design Workflow
        ├── Architecture Design
        └── Ticket Creation → ticket_[name]_[timestamp].md
```

### Files Created

1. **`prd_[name]_[timestamp].md`** - Product Requirements Document
2. **`ticket_[name]_[timestamp].md`** - Technical Architecture & Implementation Tickets

## Key Features

✅ **Nested Workflows** - Product Discovery + Architecture Design
✅ **Automatic Orchestration** - Product Lead triggers everything
✅ **File Outputs** - PRD + Ticket markdown files
✅ **Flexible Scope** - Works for products, features, enhancements
✅ **Conditional Research** - Only when needed
✅ **Simple Interface** - Just talk to the agent

## Configuration

### Change Model

Edit `agents/product_lead.py`:

```python
product_lead_agent = Agent(
    model=Claude(id="claude-opus-4-5"),  # Change model here
    ...
)
```

### Add Custom Steps

Edit workflow files to add steps:

```python
# In workflows/architecture_design_workflow.py

custom_step = Step(
    name="custom_step",
    description="My custom step",
    executor=my_function
)

architecture_design_workflow.steps.append(custom_step)
```

## Testing

### Run Test Script

```bash
python test_product_lead.py
```

### Interactive Testing

```python
from agents.product_lead import product_lead_agent

product_lead_agent.print_response(
    "Your request here",
    stream=True
)
```

## Troubleshooting

### ModuleNotFoundError: No module named 'agno'

**Solution:**
```bash
pip install -r requirements.txt
```

### Workflow not triggering

**Solution:** Ensure WorkflowTools is properly initialized in `agents/product_lead.py`

### Files not created

**Solution:** Check write permissions in the project directory

## Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Run test: `python test_product_lead.py`
3. Try your own requests
4. Review generated PRD and ticket files
5. Customize as needed

## Documentation

- [Software Development Workflow](workflow_readme/software_development_workflow.md) - Complete documentation
- [Product Discovery Workflow](workflow_readme/product_discovery_workflow.md) - PRD creation details

## Support

Check the workflow documentation for detailed information on each component.

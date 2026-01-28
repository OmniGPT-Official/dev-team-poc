# Software Development Workflow - Visual Guide

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                 │
│              "Create a blog post scheduling system"                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PRODUCT LEAD AGENT                                │
│                                                                      │
│  • Understands requirements                                         │
│  • Uses WorkflowTools                                               │
│  • Triggers Software Development Workflow                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              SOFTWARE DEVELOPMENT WORKFLOW                           │
│                   (Main Orchestrator)                               │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │   STEP 1: PRODUCT DISCOVERY WORKFLOW                        │  │
│  │                                                              │  │
│  │   ┌──────────────────────────────────────────────────────┐ │  │
│  │   │  Sub-Step 1: Analysis                                 │ │  │
│  │   │  • Requirements Analyst Agent                         │ │  │
│  │   │  • Analyzes request scope                             │ │  │
│  │   │  • Identifies information gaps                        │ │  │
│  │   └──────────────────────────────────────────────────────┘ │  │
│  │                          ↓                                  │  │
│  │   ┌──────────────────────────────────────────────────────┐ │  │
│  │   │  Sub-Step 2: Research (Conditional)                   │ │  │
│  │   │  • Market Research Agent                              │ │  │
│  │   │  • Competitor Research Agent                          │ │  │
│  │   │  • Only for products from scratch                     │ │  │
│  │   └──────────────────────────────────────────────────────┘ │  │
│  │                          ↓                                  │  │
│  │   ┌──────────────────────────────────────────────────────┐ │  │
│  │   │  Sub-Step 3: Synthesis                                │ │  │
│  │   │  • Requirements Synthesizer Agent                     │ │  │
│  │   │  • Synthesizes findings                               │ │  │
│  │   │  • Prepares for PRD creation                          │ │  │
│  │   └──────────────────────────────────────────────────────┘ │  │
│  │                          ↓                                  │  │
│  │   ┌──────────────────────────────────────────────────────┐ │  │
│  │   │  Sub-Step 4: PRD Creation                             │ │  │
│  │   │  • Product Lead Agent                                 │ │  │
│  │   │  • Creates requirements document                      │ │  │
│  │   │  • Saves PRD to file                                  │ │  │
│  │   └──────────────────────────────────────────────────────┘ │  │
│  │                          ↓                                  │  │
│  │                                                              │  │
│  │  OUTPUT: prd_blog_post_scheduling_20260128_160000.md       │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                             │                                      │
│                             │ (Passes PRD content)                │
│                             ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │   STEP 2: ARCHITECTURE DESIGN WORKFLOW                      │  │
│  │                                                              │  │
│  │   ┌──────────────────────────────────────────────────────┐ │  │
│  │   │  Sub-Step 1: Architecture Design                      │ │  │
│  │   │  • Lead Engineer Agent                                │ │  │
│  │   │  • Reads PRD from previous workflow                   │ │  │
│  │   │  • Creates technical architecture                     │ │  │
│  │   │  • Defines components & data flow                     │ │  │
│  │   │  • Specifies technology stack                         │ │  │
│  │   │  • Breaks down into implementation tasks              │ │  │
│  │   └──────────────────────────────────────────────────────┘ │  │
│  │                          ↓                                  │  │
│  │   ┌──────────────────────────────────────────────────────┐ │  │
│  │   │  Sub-Step 2: Ticket Creation                          │ │  │
│  │   │  • Generates ticket.md file                           │ │  │
│  │   │  • Includes architecture                              │ │  │
│  │   │  • Includes implementation tasks                      │ │  │
│  │   │  • Links to PRD                                       │ │  │
│  │   └──────────────────────────────────────────────────────┘ │  │
│  │                          ↓                                  │  │
│  │                                                              │  │
│  │  OUTPUT: ticket_blog_post_scheduling_20260128_160001.md    │  │
│  └─────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         RESULTS                                      │
│                                                                      │
│  ✅ PRD File: prd_blog_post_scheduling_20260128_160000.md          │
│     • Requirements                                                  │
│     • Goals & acceptance criteria                                   │
│     • Success metrics                                               │
│                                                                      │
│  ✅ Ticket File: ticket_blog_post_scheduling_20260128_160001.md    │
│     • Technical architecture                                        │
│     • Components & data flow                                        │
│     • Implementation tasks                                          │
└─────────────────────────────────────────────────────────────────────┘
```

## Workflow Flow

1. **User Request** → Product Lead Agent
2. **Agent** → Triggers Software Development Workflow
3. **Workflow Step 1** → Product Discovery (4 sub-steps)
   - Analysis → Research (conditional) → Synthesis → PRD Creation
4. **PRD Content** → Passed to Step 2
5. **Workflow Step 2** → Architecture Design (2 sub-steps)
   - Architecture Design → Ticket Creation
6. **Results** → Both files returned to user

## Data Flow

```
User Input
    ↓
[Product Name, Context, Scope]
    ↓
Product Discovery Workflow
    ↓
PRD Content + File Path
    ↓
Architecture Design Workflow
    ↓
Architecture + Ticket File
    ↓
Final Output
```

## Agent Roles

| Agent | Workflow | Step | Purpose |
|-------|----------|------|---------|
| **Product Lead** | - | Orchestration | Triggers main workflow |
| **Requirements Analyst** | Product Discovery | Analysis | Analyzes request scope |
| **Market Researcher** | Product Discovery | Research | Market research |
| **Competitor Researcher** | Product Discovery | Research | Competitor analysis |
| **Requirements Synthesizer** | Product Discovery | Synthesis | Synthesizes findings |
| **Product Lead** | Product Discovery | PRD Creation | Creates PRD |
| **Lead Engineer** | Architecture Design | Architecture | Creates architecture |

## File Outputs

### 1. PRD File (`prd_[name]_[timestamp].md`)

**Structure for Products:**
- Overview
- Problem & Goals
- Target Users
- Requirements (P0/P1/P2)
- Success Metrics
- Out of Scope
- Open Questions

**Structure for Features:**
- What & Why
- Goal
- Acceptance Criteria
- Out of Scope
- Open Questions

### 2. Ticket File (`ticket_[name]_[timestamp].md`)

**Structure:**
- Product/Feature name
- System Overview
- Components & Responsibilities
- Data Flow
- Technology Stack
- API Design
- Implementation Tasks
- Status & PRD Reference

## Usage Patterns

### Pattern 1: Conversational (Recommended)

```python
from agents.product_lead import product_lead_agent

product_lead_agent.print_response(
    "Create a blog post scheduling system",
    stream=True
)
```

### Pattern 2: Direct Workflow

```python
from workflows.software_development_workflow import run_software_development

result = run_software_development(
    product_name="Blog Post Scheduler",
    product_context="Schedule posts with publish times",
    scope="feature"
)
```

### Pattern 3: Individual Workflows

```python
# Just Product Discovery
from workflows.product_discovery_workflow import run_discovery_and_requirements

prd = run_discovery_and_requirements(
    product_name="Blog Post Scheduler",
    product_context="Schedule posts",
    scope="feature"
)

# Just Architecture Design
from workflows.architecture_design_workflow import run_architecture_design

ticket = run_architecture_design(
    prd_content=prd_content,
    product_name="Blog Post Scheduler"
)
```

## Workflow Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `product_name` | str | Yes | - | Product/feature name |
| `product_context` | str | Yes | - | What to build |
| `target_audience` | str | No | None | Who will use it |
| `user_prompt` | str | No | None | Original request |
| `scope` | str | No | "feature" | "product" or "feature" |
| `enable_research` | bool | No | False | Market research |
| `enable_competitor_analysis` | bool | No | False | Competitor research |

## Scope Decision Matrix

| Scenario | Scope | Research | Output |
|----------|-------|----------|--------|
| New product from scratch | `product` | `True` | Full PRD + Research |
| New feature | `feature` | `False` | Simple requirements |
| Enhancement | `feature` | `False` | Simple requirements |
| Bug fix | `feature` | `False` | Simple requirements |

## Benefits

✅ **End-to-End** - Complete process from idea to implementation plan
✅ **Nested** - Clean workflow composition
✅ **Reusable** - Each workflow works independently
✅ **Documented** - Persistent PRD + ticket files
✅ **Flexible** - Works for products, features, enhancements
✅ **Smart** - Conditional research, adaptive format
✅ **Simple** - Just talk to one agent

## Next Steps

1. **Install dependencies** - `pip install -r requirements.txt`
2. **Run test** - `python test_product_lead.py`
3. **Try it** - Talk to the Product Lead agent
4. **Review files** - Check generated PRD and ticket
5. **Customize** - Adjust workflows as needed

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed setup instructions.

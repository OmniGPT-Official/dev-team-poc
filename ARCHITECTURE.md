# Agent Architecture Guide

This document clarifies the different agent orchestration patterns used in this project.

---

## 🏗️ Two Orchestration Patterns

This project uses **TWO different patterns** for organizing multi-agent systems:

### 1. **TEAM Pattern** 👥
A leader agent dynamically delegates to team member agents.

### 2. **WORKFLOW Pattern** 📋
A sequence of steps where agents run independently in order.

---

## Pattern Comparison

| Feature | TEAM Pattern | WORKFLOW Pattern |
|---------|--------------|------------------|
| **Structure** | Leader + Members | Sequential Steps |
| **Coordination** | Dynamic delegation | Fixed sequence |
| **Execution** | Leader decides who runs | Pre-defined order |
| **Communication** | Team members report back | Step outputs feed forward |
| **Parallelism** | Can delegate multiple tasks | Linear progression |
| **Best For** | Complex, dynamic tasks | Predictable, multi-stage processes |

---

## Examples in This Codebase

### ✅ TEAM Pattern Examples

#### **Product Development Team** (`teams/product_team.py`)
```python
product_team = Team(
    name="Product Development Team",
    members=[
        product_lead_agent,      # Member 1
        lead_engineer_agent,     # Member 2
        software_engineer_agent, # Member 3
        security_engineer_agent, # Member 4
    ],
    lead=product_lead_agent,     # The leader delegates to members
)
```

**How it works:**
1. User asks: "Build a new authentication feature"
2. Product Lead (leader) analyzes the request
3. Product Lead **delegates** to Lead Engineer for architecture
4. Lead Engineer **delegates** to Software Engineer for implementation
5. Lead Engineer **delegates** to Security Engineer for review
6. Results flow back to Product Lead
7. Product Lead synthesizes and responds to user

**Key characteristic**: The leader agent actively decides who to involve and when.

---

#### **Content Creation Team** (`content_creation.py`)
```python
content_creation_team = Team(
    name="Content Creation Team",
    members=[
        content_strategist,  # Member 1
        content_writer,      # Member 2
    ],
    lead=content_strategist,  # The strategist leads
)
```

**How it works:**
1. User asks: "Write a blog post about AI trends"
2. Content Strategist (leader) creates strategy
3. Content Strategist **delegates** to Content Writer
4. Content Writer reports back with draft
5. Content Strategist reviews and responds

**Key characteristic**: Dynamic coordination based on the task.

---

### ✅ WORKFLOW Pattern Examples

#### **Sales Follow-Up Workflow** (`workflows/sales_followup_workflow.py`)

**IMPORTANT**: This is **NOT a team**—it's a workflow with sequential steps!

```python
sales_followup_workflow = Workflow(
    name="Sales Follow-Up Workflow",
    steps=[
        Step(name="intake", executor=run_intake),
        Step(name="analyze_sheet", executor=run_analyze_sheet),
        Step(name="gather_context", executor=run_gather_context),
        Step(name="draft_messages", executor=run_draft_messages),
        Step(name="review_and_approve", executor=run_review),
        Step(name="send_and_update", executor=run_send),
        Step(name="generate_report", executor=run_report),
        Step(name="format_output", executor=run_format_output),
    ],
)
```

**How it works:**
1. **Step 1**: `followup_coordinator_agent.run()` - User provides Google Sheet
2. **Step 2**: `sheet_analyzer_agent.run()` - Identify contacts
3. **Step 3**: `context_researcher_agent.run()` - Gather email history
4. **Step 4**: `message_writer_agent.run()` - Draft emails
5. **Step 5**: `followup_coordinator_agent.run()` - Show drafts for approval
6. **Step 6**: `followup_coordinator_agent.run()` - Send approved emails
7. **Step 7**: `campaign_analyst_agent.run()` - Generate insights
8. **Step 8**: Format final output

**Key characteristics**:
- ❌ No leader agent deciding who to call
- ❌ Agents don't communicate with each other
- ✅ Fixed sequence of steps
- ✅ Each step runs independently
- ✅ Output of step N feeds into step N+1

**Why "Follow-Up Workflow Coordinator" is NOT a team leader:**
- It's called at specific steps (intake, review, send)
- It doesn't delegate to other agents
- Other agents run independently in their own steps
- It's just a participant in the workflow

---

#### **Product Requirements Workflow** (`workflows/product_requirements_workflow.py`)

Another example of the WORKFLOW pattern:

```python
product_requirements_workflow = Workflow(
    name="Product Requirements Workflow",
    steps=[
        Step(name="understand_user", executor=run_understand),
        Step(name="create_requirements", executor=run_create_requirements),
        Step(name="review_requirements", executor=run_review),
    ],
)
```

**How it works:**
1. **Step 1**: Understand user needs
2. **Step 2**: Create requirements document
3. **Step 3**: Review and finalize

Linear, predictable, sequential.

---

## When to Use Each Pattern

### Use **TEAM Pattern** when:
- ✅ The task is complex and requires multiple perspectives
- ✅ You need dynamic coordination (leader decides who to involve)
- ✅ Agents need to collaborate and communicate
- ✅ The workflow isn't strictly linear
- ✅ Example: Building a feature (product → architecture → code → security review)

### Use **WORKFLOW Pattern** when:
- ✅ You have a clear, predictable sequence of steps
- ✅ Each step is independent and well-defined
- ✅ Output of one step feeds into the next
- ✅ No need for dynamic coordination
- ✅ Example: Email campaign (read sheet → research → draft → review → send → report)

---

## Common Confusion: Sales Follow-Up

### ❓ Why does it LOOK like a team but ISN'T?

**The confusion:**
```python
followup_coordinator_agent = Agent(
    name="Follow-Up Workflow Coordinator",  # Sounds like a leader!
    role="Handles user interaction and workflow orchestration",
    # ...
)
```

**Why it's NOT a team:**
1. There's no `Team` object with members
2. The coordinator doesn't **delegate** to other agents
3. Other agents run in separate workflow steps
4. It's just called multiple times at different stages
5. The orchestration is done by the **Workflow**, not the agent

**If it were a team, it would look like this:**
```python
# THIS IS NOT HOW IT'S IMPLEMENTED (just an example)
sales_followup_team = Team(
    name="Sales Follow-Up Team",
    members=[
        sheet_analyzer_agent,
        context_researcher_agent,
        message_writer_agent,
        campaign_analyst_agent,
    ],
    lead=followup_coordinator_agent,  # Leader delegates to members
)
```

But it's NOT implemented this way! It's a **Workflow** with sequential steps.

---

## Architecture Decision: Why Workflow for Sales Follow-Up?

From `WORKFLOW_SUMMARY.md`:

> **Current Implementation: WORKFLOW (Sequential Steps)**
> - SEQUENTIAL execution (one step after another)
> - Each agent is STANDALONE (not delegating to others)
> - Predictable, linear flow
> - Good for POC testing
> - Simpler to debug
>
> **NOT a Team architecture** (where a coordinator agent dynamically delegates to worker agents in parallel).
> That would be Iteration 2+.

**Design reasoning:**
- Email campaigns are naturally sequential (read → research → draft → send → report)
- Each step is independent and testable
- Simpler to build and debug for POC
- Future iteration might use Team pattern for more complex scenarios

---

## Summary Table

| System | Pattern | Leader/Coordinator | Members/Steps |
|--------|---------|-------------------|---------------|
| **Product Development** | TEAM | Product Lead | Lead Engineer, Software Engineer, Security Engineer |
| **Content Creation** | TEAM | Content Strategist | Content Writer |
| **Sales Follow-Up** | WORKFLOW | N/A (just a participant) | 8 sequential steps with 5 different agents |
| **Product Requirements** | WORKFLOW | N/A | 3 sequential steps |
| **Software Development** | WORKFLOW | N/A | Multiple sequential steps |

---

## Key Takeaways

1. **"Follow-Up Workflow Coordinator"** is NOT a team leader—just a regular agent called at different workflow steps
2. **Sales Follow-Up uses WORKFLOW architecture**, not TEAM architecture
3. **TEAM = Dynamic delegation** (leader decides who runs when)
4. **WORKFLOW = Sequential steps** (pre-defined order)
5. Both patterns are valid and used in different parts of the codebase

---

## Further Reading

- Team implementation: `teams/product_team.py`
- Workflow implementation: `workflows/sales_followup_workflow.py`
- Agent definitions: `agents/sales_followup_agents.py`
- Workflow summary: `workflows/WORKFLOW_SUMMARY.md`

---

**Questions?** Check the code examples above or compare `teams/product_team.py` (TEAM) with `workflows/sales_followup_workflow.py` (WORKFLOW).

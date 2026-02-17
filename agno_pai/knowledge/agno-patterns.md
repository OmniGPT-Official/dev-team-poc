# Agno Patterns Reference

## 1. Agent Pattern (Atomic Unit)

An Agent is the basic unit. It wraps an LLM with tools, memory, and instructions.

```python
from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.anthropic import Claude
from services.tool_injector import make_tool_hook
from db import db

my_agent = Agent(
    name="My Agent",
    model=Gemini(id="gemini-3-flash-preview"),
    description="One-line description of what this agent does.",
    instructions=[
        "You are a [role] that [does what].",
        "",
        "## Section heading",
        "Instruction line 1.",
        "Instruction line 2.",
    ],
    pre_hooks=[make_tool_hook("google_sheets", "google_gmail")],  # OAuth tools
    db=db,
    update_memory_on_run=True,        # persist memory across sessions
    add_history_to_context=True,      # include conversation history
    num_history_messages=10,          # limit history to avoid token bloat
    add_datetime_to_context=True,     # inject current date/time
    add_name_to_context=True,         # inject user's name
    markdown=True,                    # format responses as markdown
    reasoning=False,                  # disable chain-of-thought (keep False for speed)
)
```

### When to use Agent
- Single-purpose task (reading emails, writing content, calling an API)
- No delegation needed
- One LLM doing one job

---

## 2. Team Pattern — Route Mode (Skill Router)

A Router Team dispatches requests to the right member agent. Works like a skill index.

```python
from agno.team import Team
from agno.models.anthropic import Claude

router_team = Team(
    name="My Router",
    mode="route",                          # key: routes to ONE member
    model=Claude(id="claude-sonnet-4-5-20250929"),  # team leader model
    members=[agent_a, agent_b, agent_c],
    instructions=[
        "Route requests to the right specialist:",
        "- Email/Gmail tasks → EmailAgent",
        "- Content/writing tasks → ContentAgent",
        "- Data/sheets tasks → DataAgent",
    ],
    db=db,
    add_history_to_context=True,
    num_history_messages=10,
    add_datetime_to_context=True,
    markdown=True,
)
```

### When to use Route mode
- You have multiple specialist agents and need to dispatch
- Requests are distinct enough to route cleanly
- One agent handles each request (no collaboration needed)

---

## 3. Team Pattern — Coordinate Mode (Supervisor)

A Coordinator Team delegates subtasks to members and synthesizes results. Like a manager.

```python
from agno.team import Team

coordinator_team = Team(
    name="My Coordinator",
    mode="coordinate",                     # key: delegates to MULTIPLE members
    model=Claude(id="claude-sonnet-4-5-20250929"),
    members=[researcher, writer, reviewer],
    instructions=[
        "You are the team lead. Coordinate members to complete tasks:",
        "1. Delegate research to Researcher",
        "2. Delegate writing to Writer using research output",
        "3. Delegate review to Reviewer",
        "4. Synthesize final output",
    ],
    db=db,
    add_team_history_to_members=True,      # members see team conversation
    show_members_responses=True,           # show each member's output
    add_history_to_context=True,
    num_history_messages=10,
    add_datetime_to_context=True,
    markdown=True,
)
```

### When to use Coordinate mode
- Task needs multiple steps handled by different specialists
- Members need to build on each other's work
- You need a synthesized final output

---

## 4. Team Pattern — Collaborate Mode

All members work together simultaneously, seeing each other's responses.

```python
team = Team(
    name="Debate Team",
    mode="collaborate",                    # all members respond
    model=Claude(id="claude-sonnet-4-5-20250929"),
    members=[agent_a, agent_b],
    instructions=["Facilitate discussion between members."],
    db=db,
)
```

### When to use Collaborate mode
- Brainstorming, debate, multiple perspectives needed
- No single "right answer" — synthesis of views is the goal

---

## 5. Workflow Pattern (Multi-Step Orchestration)

A Workflow is a stateful, multi-step process. Use for complex pipelines.

```python
from agno.workflow import Workflow, RunResponse
from agno.models.google import Gemini
from agno.storage.sqlite import SqliteStorage

class MyWorkflow(Workflow):
    # Declare agents as class attributes
    step_one_agent: Agent = Agent(
        name="Step One",
        model=Gemini(id="gemini-3-flash-preview"),
        instructions=["Do step one."],
    )
    step_two_agent: Agent = Agent(
        name="Step Two",
        model=Gemini(id="gemini-3-flash-preview"),
        instructions=["Do step two using the input."],
    )

    def run(self, input: str) -> RunResponse:
        # Step 1
        result_one = self.step_one_agent.run(input)

        # Persist intermediate state
        self.session_state["step_one_result"] = result_one.content

        # Step 2 uses step 1 output
        result_two = self.step_two_agent.run(
            f"Step one result: {result_one.content}\nNow do step two."
        )

        return RunResponse(content=result_two.content)


# Instantiate with storage for session persistence
workflow = MyWorkflow(
    session_id="my-workflow-session",
    storage=SqliteStorage(table_name="my_workflow", db_file="agno.db"),
)
```

### When to use Workflow
- Sequential steps where each depends on the previous
- Need to persist state between steps
- Complex pipelines (research → write → review → publish)

---

## 6. Available Tool Providers

Inject OAuth/API tools via `make_tool_hook`. List only providers the agent actually needs.

| Provider key       | What it gives the agent         |
|--------------------|----------------------------------|
| `google_sheets`    | Read/write Google Sheets         |
| `google_gmail`     | Send/read Gmail                  |
| `elevenlabs`       | Text-to-speech via ElevenLabs    |
| `supabase_mcp`     | Query Supabase via MCP           |

```python
# Single provider
pre_hooks=[make_tool_hook("google_sheets")]

# Multiple providers
pre_hooks=[make_tool_hook("google_sheets", "google_gmail")]
```

---

## 7. Static Tools + OAuth Tools Together

```python
from my_tools import my_custom_tool

agent = Agent(
    tools=[my_custom_tool],                        # static tools
    pre_hooks=[make_tool_hook("google_sheets")],   # OAuth tools injected at runtime
    db=db,
)
# At runtime: [my_custom_tool, GoogleSheetsTools(...)]
```

---

## 8. Compression Manager (for large data)

Use when the agent reads large datasets (spreadsheets with 100+ rows).

```python
from agno.compression.manager import CompressionManager

compression_manager = CompressionManager(
    model=Gemini(id="gemini-3-flash-preview"),
    compress_tool_results=True,
    compress_tool_results_limit=2,
    compress_tool_call_instructions="Preserve key fields: names, emails, dates. Summarize counts.",
)

agent = Agent(
    ...
    compression_manager=compression_manager,
)
```

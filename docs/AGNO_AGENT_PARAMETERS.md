# Agno Agent Parameters Reference

**Version:** Agno 2.4.8
**Last Updated:** 2026-02-12

This document lists ALL valid parameters for `agno.agent.Agent.__init__()`.
**Use this reference before adding any new parameters to avoid production crashes.**

---

## Core Identity

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | Model \| str \| None | None | LLM model to use |
| `name` | str \| None | None | Agent name |
| `id` | str \| None | None | Agent ID |
| `user_id` | str \| None | None | User identifier |
| `session_id` | str \| None | None | Session identifier |

---

## History & Context Management

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `add_history_to_context` | bool | False | Include conversation history in context |
| `num_history_runs` | int \| None | None | Number of previous runs to include |
| `num_history_messages` | int \| None | None | Number of previous messages to include |
| `max_tool_calls_from_history` | int \| None | None | Max tool calls from history |
| `store_media` | bool | True | Store media messages |
| `store_tool_messages` | bool | True | Store tool messages |
| `store_history_messages` | bool | True | Store history messages |

---

## Memory Management

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `memory_manager` | MemoryManager \| None | None | Memory manager instance |
| `enable_agentic_memory` | bool | False | Enable agentic memory |
| `update_memory_on_run` | bool | False | Update memory after each run |
| `enable_user_memories` | bool \| None | None | Enable user-specific memories |
| `add_memories_to_context` | bool \| None | None | Add memories to context |
| `enable_session_summaries` | bool | False | Enable session summaries |
| `add_session_summary_to_context` | bool \| None | None | Add session summary to context |
| `compress_tool_results` | bool | False | Compress tool results |

---

## Tools & Hooks

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tools` | Sequence[Toolkit \| Callable \| Function \| Dict] \| None | None | Tools available to agent |
| `tool_call_limit` | int \| None | None | Max tool calls per run |
| `tool_choice` | str \| Dict \| None | None | Tool selection strategy |
| `tool_hooks` | List[Callable] \| None | None | Tool execution hooks |
| `pre_hooks` | List[Callable \| BaseGuardrail \| BaseEval] \| None | None | Pre-execution hooks |
| `post_hooks` | List[Callable \| BaseGuardrail \| BaseEval] \| None | None | Post-execution hooks |

---

## Instructions & Context

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `description` | str \| None | None | Agent description |
| `instructions` | str \| List[str] \| Callable \| None | None | Agent instructions |
| `system_message` | str \| Callable \| Message \| None | None | System message |
| `introduction` | str \| None | None | Agent introduction |
| `additional_context` | str \| None | None | Additional context |
| `additional_input` | List[str \| Dict \| BaseModel \| Message] \| None | None | Additional input messages |
| `expected_output` | str \| None | None | Expected output format |

---

## Output Formatting

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `markdown` | bool | False | Use markdown formatting |
| `add_name_to_context` | bool | False | Add agent name to context |
| `add_datetime_to_context` | bool | False | Add datetime to context |
| `add_location_to_context` | bool | False | Add location to context |
| `use_json_mode` | bool | False | Use JSON mode |
| `structured_outputs` | bool \| None | None | Use structured outputs |

---

## Database

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db` | BaseDb \| AsyncBaseDb \| None | None | Database instance |

---

## Knowledge Base

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `knowledge` | KnowledgeProtocol \| None | None | Knowledge base instance |
| `add_knowledge_to_context` | bool | False | Add knowledge to context |
| `search_knowledge` | bool | True | Enable knowledge search |

---

## Reasoning

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `reasoning` | bool | False | Enable reasoning mode |
| `reasoning_model` | Model \| str \| None | None | Model for reasoning |
| `reasoning_agent` | Agent \| None | None | Agent for reasoning |
| `reasoning_min_steps` | int | 1 | Min reasoning steps |
| `reasoning_max_steps` | int | 10 | Max reasoning steps |

---

## Debugging

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `debug_mode` | bool | False | Enable debug mode |
| `debug_level` | Literal[1, 2] | 1 | Debug verbosity |
| `telemetry` | bool | True | Enable telemetry |

---

## ⚠️ Parameters That DO NOT EXIST

**DO NOT USE these parameters - they will crash production:**

- ❌ `read_storage` - Does not exist in Agno 2.4.8
- ❌ `monitoring` - Does not exist in Agno 2.4.8
- ❌ `read_only` - Does not exist
- ❌ `cache_results` - Does not exist
- ❌ `enable_tracing` - Does not exist (use `telemetry` instead)

---

## 🔍 How to Verify Parameters

Before adding a new parameter, verify it exists:

```python
import agno.agent
import inspect

sig = inspect.signature(agno.agent.Agent.__init__)
print(list(sig.parameters.keys()))
```

Or check the full list:

```bash
python3 -c "import agno.agent; import inspect; print(inspect.signature(agno.agent.Agent.__init__))"
```

---

## 📚 Our Agent Patterns

### Pattern 1: Main Orchestrator Agent
```python
Agent(
    name="Campaign Manager",
    model=Gemini(id="gemini-3-flash-preview"),
    description="...",
    instructions=[...],
    tools=[workflow_tools],
    pre_hooks=[inject_user_tools],
    db=db,
    update_memory_on_run=True,  # Remember across sessions
    add_history_to_context=True,  # Needs conversation history
    num_history_messages=10,  # Limit to prevent overflow
    add_datetime_to_context=True,
    markdown=True,
)
```

### Pattern 2: Workflow Step Agent
```python
Agent(
    name="Lead Reader",
    model=Gemini(id="gemini-3-flash-preview"),
    description="...",
    instructions=[...],
    tools=[],
    pre_hooks=[make_tool_hook("google_sheets")],
    db=db,
    add_history_to_context=False,  # ⚠️ CRITICAL: Prevents context overflow
    num_history_messages=5,  # Safety limit
    markdown=True,
)
```

---

**Last verified:** 2026-02-12 with Agno 2.4.8
**If Agno is upgraded, re-verify parameters using inspect.signature()**

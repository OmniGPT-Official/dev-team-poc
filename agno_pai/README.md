# Agno PAI Factory

A meta-agent that generates any Agno agent, team, or workflow on demand — following the project's exact conventions.

## What It Does

You describe what you need in plain English. The factory outputs complete, ready-to-run Python code that fits directly into the project.

```
You: "build me an agent that reads Gmail and creates Google Calendar events"
  ↓
Factory: analyzes → picks the right pattern → generates complete Python file
```

## How to Run

```bash
# Interactive mode (recommended for exploration)
python -m agno_pai

# Single request
python -m agno_pai "build me an agent that monitors Gmail and posts to Slack"
```

## Examples

```
"build me an agent that reads a Google Sheet and sends follow-up emails"
"create a team that researches a topic and writes a LinkedIn post"
"make a workflow that processes job applications and scores them"
"build an agent that calls the ElevenLabs API to generate audio from text"
"create a router team that dispatches HR, engineering, and marketing tasks"
```

## What Gets Generated

The factory always outputs:
1. **Pattern choice** — Agent / Team / Workflow and why
2. **File location** — exactly where to save it
3. **Complete Python code** — copy-paste ready
4. **Usage instructions** — how to import and run

## Knowledge Base

The factory's knowledge lives in `knowledge/`:
- `agno-patterns.md` — all Agno primitives with examples
- `project-conventions.md` — models, flags, providers, file locations

To update what the factory knows, edit these files.

## Architecture

```
agno_pai/
  factory.py              ← the meta-agent (Claude Sonnet)
  main.py                 ← CLI entry point
  knowledge/
    agno-patterns.md      ← Agno Agent/Team/Workflow patterns
    project-conventions.md ← project-specific rules
  README.md
```

## Isolation

This system lives entirely in `agno_pai/`. It does not modify any existing agents, teams, or workflows. Safe to test without affecting production.

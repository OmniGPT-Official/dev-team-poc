---
name: task-execution
description: Task-driven implementation skill. Read TASKS.md from GitHub, execute tasks one at a time, mark each done, commit after every task. Never implement more than one task per cycle. This keeps context small and creates a recoverable, auditable trail.
license: MIT
metadata:
  version: "1.0.0"
  author: agent-os
  tags: ["implementation", "task-management", "context-efficiency", "github"]
---

# Task Execution Skill

Use this skill whenever you are asked to implement a project that has a `TASKS.md` file in its GitHub repository.

## When to Use

- You are the Software Engineer implementing code for a project
- The repository contains a `TASKS.md` file written by the planner
- You need to implement features in a controlled, context-efficient way
- You are resuming a session and need to know where you left off

## Core Principle

**One task = one commit = one focused context.**

Never implement multiple tasks in a single agent turn. After each task:
1. Mark it done in `TASKS.md`
2. Commit `TASKS.md` to GitHub
3. Re-read `TASKS.md` fresh before starting the next task

This means that even if your context window is compressed or cleared, you can always recover by reading `TASKS.md` and finding the first unchecked item.

---

## Execution Process

### Step 1 — Read the Task List
```
Call: get_file_contents(owner, repo, path="TASKS.md")
```
Parse the file. Find the FIRST line matching `- [ ]` — that is your active task.
If ALL tasks are `- [x]`, you are done. Report completion and stop.

### Step 2 — Understand the Task Scope
Read the task description carefully. Identify:
- Which files need to be created or modified
- What dependencies the task has on earlier tasks
- The exact output required (file path, content, commit message)

Do NOT start working until you fully understand the scope of this single task.

### Step 3 — Implement the Task
Use `create_or_update_file` to write each file the task requires.

**Rules:**
- Stay within the task boundary — do not implement files from other tasks
- If the architecture document referenced earlier is needed, keep your read to the relevant section only
- Use conventional commit messages: `feat: add <filename>`, `fix: <what>`, etc.
- For the final task (README), use: `docs: add comprehensive README`

### Step 4 — Mark the Task Done
Immediately after implementation:

1. Re-read `TASKS.md` to get the current file content (including any changes from earlier tasks)
2. Change the line for the completed task from `- [ ]` to `- [x]`
3. Commit the updated `TASKS.md`:
   ```
   create_or_update_file(
       owner=owner,
       repo=repo,
       path="TASKS.md",
       content=<updated content>,
       message="chore: complete task N — <task title>",
       branch="main"
   )
   ```

### Step 5 — Move to Next Task
Re-read `TASKS.md` fresh (do not rely on your in-memory version).
Repeat from Step 1.

---

## Context Window Rules

To keep context small during execution:

1. **Never load the full architecture document again** after the planning step injected it in your initial prompt — use what was provided
2. **After each task, discard your mental model of file contents** — always re-read files from GitHub if you need them again rather than relying on memory
3. **Keep tool call sequences short**: read → implement → write → mark done. Four tool calls per task maximum
4. **If you are unsure what a file should contain**, read the specific section of the architecture that covers it — not the whole document

---

## Recovery from Interruption

If you are restarting after a crash or context compression:

1. Read `TASKS.md` from GitHub
2. All `- [x]` tasks are already done — do not redo them
3. The first `- [ ]` task is your starting point
4. Continue as if you are at Step 3 of a fresh task cycle

---

## Output Format After All Tasks Complete

When all tasks are `- [x]`:

```
## Implementation Complete

All tasks in TASKS.md have been completed and committed:

✅ Task 1: Initialize project structure
✅ Task 2: Set up Supabase client
...
✅ Task N: Write README

Repository: https://github.com/{owner}/{repo}
Files committed: <list main files>
```

---

## Anti-Patterns to Avoid

- **DO NOT** implement files outside the current task boundary
- **❌ NEVER skip marking a task done** — updating `TASKS.md` from `- [ ]` to `- [x]` and committing it is mandatory after EVERY task. If you skip this, the next session will re-implement finished work.
- **DO NOT** rely on your conversation history to track progress — always re-read `TASKS.md`
- **DO NOT** batch multiple tasks into a single commit (except when a task naturally spans 2-3 tightly coupled files)
- **DO NOT** read the full repository file tree on every task — only read what the current task needs

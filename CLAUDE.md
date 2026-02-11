# Dev Team POC

> **DO NOT modify this file** unless explicitly asked by the project lead. This file is manually maintained. If you encounter a merge conflict involving CLAUDE.md, always keep the version on `main`.

Python FastAPI backend using the [Agno](https://github.com/agno-agi/agno) framework for AI agent orchestration. Deployed to Railway.

## Quick Reference

| Topic | Location |
|-------|----------|
| Coding patterns & conventions | `docs/coding-guidelines.md` |
| Adding user credentials (OAuth & API keys) | `docs/adding-user-credentials.md` |
| API key storage architecture | `docs/api-key-storage.md` |
| OAuth token storage architecture | `docs/oauth-token-storage.md` |
| Multi-user auth implementation | `docs/multi-user-auth-implementation.md` |
| Canonical agent example | `email_followup.py` |
| OAuth credential helper | `services/oauth_store.py` |
| API key credential helper | `services/api_key_store.py` |
| Tool injection pre-hook | `services/tool_injector.py` |

## Rules

### Shared dependencies

- **Do not modify `db.py`** without team approval. It is imported across all agents, teams, and workflows.
- **Do not modify `services/oauth_store.py` or `services/api_key_store.py`** without checking downstream impact first.

### Agent creation

- When creating agents, workflows, or equipping tools (OAuth, API keys, PATs), **read `docs/coding-guidelines.md` first**, then read the source files it references (e.g. `email_followup.py`, `services/oauth_store.py`, `services/tool_injector.py`) to understand the actual implementation before writing code.
- Use `Gemini(id="gemini-3-flash-preview")` as the default model for POC agents.
- Always pass `db=db` (from `db.py`) for agent memory.
- OAuth and API-key tools must be injected via **pre-hooks**, never hardcoded.

### Commits and branches

- Branch naming: `feature/<brief-desc>`, `fix/<brief-desc>`, `hotfix/<brief-desc>`
- PR descriptions: focus on customer impact, not technical details. Write for non-technical readers.
- **Never alter git history** (amend, rebase, force-push) on branches already pushed to remote. Always create new commits instead.
- Merge PRs with `--squash --delete-branch` to keep main history clean and remove stale branches.
- **Never push directly to main.** All changes must go through a PR.

### Before creating new files

Always explore the repo file tree first. Place files in the existing structure rather than creating new directories.

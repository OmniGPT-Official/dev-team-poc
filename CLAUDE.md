# Dev Team POC

Python FastAPI backend using the [Agno](https://github.com/agno-agi/agno) framework for AI agent orchestration. Deployed to Railway.

## Quick Reference

| Topic | Location |
|-------|----------|
| Coding patterns & conventions | `docs/coding-guidelines.md` |
| API key storage architecture | `docs/api-key-storage.md` |
| Canonical agent example | `email_followup.py` |
| OAuth credential helper | `services/oauth_store.py` |
| API key credential helper | `services/api_key_store.py` |
| Tool injection pre-hook | `services/tool_injector.py` |

## Rules

### Shared dependencies

- **Do not modify `db.py`** without team approval. It is imported across all agents, teams, and workflows.
- **Do not modify `services/oauth_store.py` or `services/api_key_store.py`** without checking downstream impact first.

### Agent creation

- Use `Gemini(id="gemini-3-flash-preview")` as the default model for POC agents.
- Always pass `db=db` (from `db.py`) for agent memory.
- OAuth and API-key tools must be injected via **pre-hooks**, never hardcoded. See `docs/coding-guidelines.md` for the full pattern.

### Commits and branches

- Branch naming: `feature/<brief-desc>`, `fix/<brief-desc>`, `hotfix/<brief-desc>`
- PR descriptions: focus on customer impact, not technical details. Write for non-technical readers.
- **Never alter git history** (amend, rebase, force-push) on branches already pushed to remote. Always create new commits instead.
- Merge PRs with `--squash --delete-branch` to keep main history clean and remove stale branches.
- **Never push directly to main.** All changes must go through a PR.

### Before creating new files

Always explore the repo file tree first. Place files in the existing structure rather than creating new directories.

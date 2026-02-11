# Agent OS — Software Development Workflow

> **File:** `workflows/software_development_workflow.py`
> **Input:** `ARCHITECTURE_URL` (Google Docs link) | **Output:** Live Vercel URL + GitHub repo URL

```mermaid
flowchart TB
    START(["ARCHITECTURE_URL\n(Google Docs link)"])

    START --> S1["Step 1 · read_architecture\nAgent: —\nTool: GoogleDocsTools.read_document()\n\nFetches architecture doc,\nextracts project name & config"]

    S1 --> S2["Step 2 · create_github_repo\nAgent: —\nTool: GitHubTools.create_repository()\n      GitHubTools.create_or_update_file()\n\nCreates repo, seeds\nREADME + .gitignore"]

    S2 --> LOOP

    subgraph LOOP["Step 3 · implementation_cycle — max 2 iterations"]
        direction TB
        DEV["Step 3a · development\nAgent: Software Engineer (gemini-3-flash)\nTool: GitHubTools.create_or_update_file()\n\nGenerates & commits:\n  index.html\n  css/styles.css\n  js/script.js"]

        DEV --> REV["Step 3b · code_review\nAgent: —\nTool: GitHubTools.list_repository_files()\n\nChecks code files exist\nin the repo"]

        REV --> CHECK{reviews_passed()?}
        CHECK -->|"No"| DEV
    end

    CHECK -->|"Yes"| S4["Step 4 · deploy_to_vercel\nAgent: Vercel Deployer (gemini-2.0-flash)\nTool: VercelDeployTools.deploy_to_vercel()\n\nDeploys repo via Vercel REST API,\npolls until READY"]

    S4 --> S5["Step 5 · create_summary\nAgent: —\n\nReturns project name,\nlive URL + GitHub URL"]

    S5 --> DONE(["Live URL + GitHub URL"])

    style START fill:#4A90D9,color:#fff
    style DONE fill:#2ECC71,color:#fff
    style CHECK fill:#F39C12,color:#fff
```

## Agents

| Agent | Model | Tools | Step |
|-------|-------|-------|------|
| **Software Engineer** | `gemini-3-flash` | `GitHubTools` | 3a — writes code |
| **Vercel Deployer** | `gemini-2.0-flash` | `VercelDeployTools` | 4 — deploys to Vercel |

## Tools

| Toolkit | Key Functions | Step |
|---------|--------------|------|
| **GoogleDocsTools** | `read_document()` | 1 |
| **GitHubTools** | `create_repository()`, `create_or_update_file()`, `list_repository_files()` | 2, 3a, 3b |
| **VercelDeployTools** | `deploy_to_vercel()` → `deploy.js` → Vercel REST API | 4 |

## Output File Structure

```
{repo}/
├── README.md
├── .gitignore
├── index.html         ← links to css/ and js/
├── css/styles.css
├── js/script.js
└── (images: Unsplash URLs inline)
```

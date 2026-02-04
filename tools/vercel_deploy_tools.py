"""
Vercel Deploy Tools

Wraps the deploy.js script (which uses the official @vercel/sdk) as an
Agno Toolkit so any agent can trigger a Vercel deployment by calling a
single function.

Usage in an agent prompt:
    deploy_to_vercel(github_owner="Muhammad-Anique", github_repo="my-repo", project_name="my-project")
"""

import os
import json
import subprocess
from agno.tools.toolkit import Toolkit


# Path to the directory that contains deploy.js + node_modules
_DEPLOY_SCRIPT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "vercel_mcp",
)


class VercelDeployTools(Toolkit):
    """
    Toolkit that exposes a single `deploy_to_vercel` function.

    It shells out to deploy.js which uses @vercel/sdk to:
      1. POST a new git-sourced deployment
      2. Poll until READY
      3. Return the live URL
    """

    def __init__(self, **kwargs):
        tools = [self.deploy_to_vercel]
        super().__init__(name="vercel", tools=tools, **kwargs)

    def deploy_to_vercel(
        self,
        github_owner: str,
        github_repo: str,
        project_name: str,
    ) -> str:
        """
        Deploy a GitHub repository to Vercel and return the live URL.

        Args:
            github_owner: GitHub owner / org  (e.g. "Muhammad-Anique")
            github_repo:  GitHub repo name    (e.g. "--crumble-bakery--softwar-33438")
            project_name: Vercel project name (e.g. "crumble-bakery-deploy-test")

        Returns:
            JSON with either {"success": true, "url": "https://..."} or {"error": true, "message": "..."}
        """
        env = {
            **os.environ,
            "DEPLOY_GITHUB_ORG":     github_owner,
            "DEPLOY_GITHUB_REPO":    github_repo,
            "DEPLOY_PROJECT_NAME":   project_name,
        }

        try:
            result = subprocess.run(
                ["node", "deploy.js"],
                capture_output=True,
                text=True,
                timeout=360,
                cwd=_DEPLOY_SCRIPT_DIR,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return json.dumps({"error": True, "message": "deploy.js timed out after 360s"})
        except FileNotFoundError:
            return json.dumps({"error": True, "message": "node not found — is Node.js installed?"})

        # Print SDK logs (stderr) so they show up in agent output
        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:
            return json.dumps({
                "error": True,
                "message": f"deploy.js exited with code {result.returncode}",
                "stderr": result.stderr[-500:] if result.stderr else "",
            })

        url = result.stdout.strip()
        if url:
            return json.dumps({"success": True, "url": url})

        return json.dumps({"error": True, "message": "Deployment finished but no URL was returned"})

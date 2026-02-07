"""
Vercel Deploy Tools

Wraps the deploy.js script (which uses the Vercel REST API) as an
Agno Toolkit so any agent can trigger a Vercel deployment by calling a
single function.

Usage in an agent prompt:
    deploy_to_vercel(github_owner="Muhammad-Anique", github_repo="my-repo", project_name="my-project")
"""

import os
import json
import subprocess
from agno.tools.toolkit import Toolkit


# Path to the directory that contains deploy.js
_DEPLOY_SCRIPT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "vercel_mcp",
)


def _log(msg: str):
    """Simple local logging."""
    print(f"[VERCEL] {msg}")


class VercelDeployTools(Toolkit):
    """
    Toolkit that exposes a single `deploy_to_vercel` function.

    It shells out to deploy.js which uses the Vercel REST API to:
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
        _log("=" * 50)
        _log("VERCEL DEPLOYMENT STARTING")
        _log("=" * 50)

        # Check VERCEL_TOKEN
        vercel_token = os.environ.get("VERCEL_TOKEN", "")
        if not vercel_token:
            _log("ERROR: VERCEL_TOKEN environment variable is NOT SET!")
            return json.dumps({
                "error": True,
                "message": "VERCEL_TOKEN is not set. Cannot deploy without authentication."
            })

        token_preview = f"{vercel_token[:8]}...{vercel_token[-4:]}" if len(vercel_token) > 12 else "***"
        _log(f"VERCEL_TOKEN is SET: {token_preview}")
        _log(f"GitHub Owner:  {github_owner}")
        _log(f"GitHub Repo:   {github_repo}")
        _log(f"Project Name:  {project_name}")
        _log(f"Deploy Script: {_DEPLOY_SCRIPT_DIR}/deploy.js")

        # Check deploy.js exists
        deploy_js_path = os.path.join(_DEPLOY_SCRIPT_DIR, "deploy.js")
        if not os.path.exists(deploy_js_path):
            _log(f"ERROR: deploy.js NOT FOUND at: {deploy_js_path}")
            return json.dumps({
                "error": True,
                "message": f"deploy.js not found at {deploy_js_path}"
            })
        _log("deploy.js exists")

        # Execute deploy.js
        _log("Executing deploy.js...")

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
                cwd=_DEPLOY_SCRIPT_DIR,
                env=env,
            )
        except FileNotFoundError:
            _log("ERROR: Node.js NOT FOUND - is it installed?")
            return json.dumps({"error": True, "message": "node not found — is Node.js installed?"})
        except Exception as e:
            _log(f"ERROR: Subprocess error: {e}")
            return json.dumps({"error": True, "message": f"Subprocess error: {e}"})

        # Log subprocess output
        if result.stderr:
            _log("--- deploy.js stderr output ---")
            for line in result.stderr.strip().split('\n'):
                print(f"  [VERCEL-JS] {line}")
            _log("--- end stderr ---")

        if result.stdout:
            _log(f"deploy.js stdout: {result.stdout.strip()}")

        _log(f"deploy.js exit code: {result.returncode}")

        # Process result
        if result.returncode != 0:
            error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
            _log(f"ERROR: Deployment FAILED with exit code {result.returncode}")
            return json.dumps({
                "error": True,
                "message": f"deploy.js exited with code {result.returncode}",
                "stderr": error_msg,
            })

        url = result.stdout.strip()
        if url:
            _log("=" * 50)
            _log(f"DEPLOYMENT SUCCESSFUL! Live URL: {url}")
            _log("=" * 50)
            return json.dumps({"success": True, "url": url})

        _log("ERROR: Deployment finished but no URL was returned")
        return json.dumps({"error": True, "message": "Deployment finished but no URL was returned"})

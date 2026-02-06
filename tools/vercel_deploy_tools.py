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


def _cloud_log(level: str, step: str, msg: str, data: dict = None):
    """Log to CloudLogger if available."""
    try:
        from utils.cloud_logger import CloudLogger
        CloudLogger.get_instance()._log_internal(level, step, msg, data)
    except Exception:
        pass
    # Always print to stdout as well
    print(f"[VERCEL] {msg}")


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
        _cloud_log("INFO", "VERCEL", "=" * 50)
        _cloud_log("INFO", "VERCEL", "VERCEL DEPLOYMENT STARTING")
        _cloud_log("INFO", "VERCEL", "=" * 50)

        # =====================================================================
        # STEP 1: Check VERCEL_TOKEN
        # =====================================================================
        vercel_token = os.environ.get("VERCEL_TOKEN", "")
        if not vercel_token:
            _cloud_log("ERROR", "VERCEL", "VERCEL_TOKEN environment variable is NOT SET!")
            _cloud_log("ERROR", "VERCEL", "Please set VERCEL_TOKEN in your environment (Railway/local)")
            return json.dumps({
                "error": True,
                "message": "VERCEL_TOKEN is not set. Cannot deploy without authentication."
            })

        token_preview = f"{vercel_token[:8]}...{vercel_token[-4:]}" if len(vercel_token) > 12 else "***"
        _cloud_log("INFO", "VERCEL", f"VERCEL_TOKEN is SET: {token_preview}")

        # =====================================================================
        # STEP 2: Log deployment parameters
        # =====================================================================
        _cloud_log("INFO", "VERCEL", f"GitHub Owner:  {github_owner}")
        _cloud_log("INFO", "VERCEL", f"GitHub Repo:   {github_repo}")
        _cloud_log("INFO", "VERCEL", f"Project Name:  {project_name}")
        _cloud_log("INFO", "VERCEL", f"Deploy Script: {_DEPLOY_SCRIPT_DIR}/deploy.js")

        # =====================================================================
        # STEP 3: Check deploy.js exists
        # =====================================================================
        deploy_js_path = os.path.join(_DEPLOY_SCRIPT_DIR, "deploy.js")
        if not os.path.exists(deploy_js_path):
            _cloud_log("ERROR", "VERCEL", f"deploy.js NOT FOUND at: {deploy_js_path}")
            return json.dumps({
                "error": True,
                "message": f"deploy.js not found at {deploy_js_path}"
            })
        _cloud_log("INFO", "VERCEL", "deploy.js exists")

        # Check node_modules
        node_modules_path = os.path.join(_DEPLOY_SCRIPT_DIR, "node_modules")
        if not os.path.exists(node_modules_path):
            _cloud_log("WARN", "VERCEL", f"node_modules NOT FOUND at: {node_modules_path}")
            _cloud_log("WARN", "VERCEL", "Running npm install...")
            try:
                install_result = subprocess.run(
                    ["npm", "install"],
                    capture_output=True,
                    text=True,
                    cwd=_DEPLOY_SCRIPT_DIR,
                    timeout=120,
                )
                if install_result.returncode != 0:
                    _cloud_log("ERROR", "VERCEL", f"npm install failed: {install_result.stderr}")
                else:
                    _cloud_log("INFO", "VERCEL", "npm install completed successfully")
            except Exception as e:
                _cloud_log("ERROR", "VERCEL", f"npm install exception: {e}")
        else:
            _cloud_log("INFO", "VERCEL", "node_modules exists")

        # =====================================================================
        # STEP 4: Execute deploy.js
        # =====================================================================
        _cloud_log("INFO", "VERCEL", "Executing deploy.js...")

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
            _cloud_log("ERROR", "VERCEL", "Node.js NOT FOUND - is it installed?")
            return json.dumps({"error": True, "message": "node not found — is Node.js installed?"})
        except Exception as e:
            _cloud_log("ERROR", "VERCEL", f"Subprocess error: {e}")
            return json.dumps({"error": True, "message": f"Subprocess error: {e}"})

        # =====================================================================
        # STEP 5: Log subprocess output
        # =====================================================================
        if result.stderr:
            _cloud_log("INFO", "VERCEL", "--- deploy.js stderr output ---")
            for line in result.stderr.strip().split('\n'):
                _cloud_log("DEBUG", "VERCEL-JS", line)
            _cloud_log("INFO", "VERCEL", "--- end stderr ---")

        if result.stdout:
            _cloud_log("INFO", "VERCEL", f"deploy.js stdout: {result.stdout.strip()}")

        _cloud_log("INFO", "VERCEL", f"deploy.js exit code: {result.returncode}")

        # =====================================================================
        # STEP 6: Process result
        # =====================================================================
        if result.returncode != 0:
            error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
            _cloud_log("ERROR", "VERCEL", f"Deployment FAILED with exit code {result.returncode}")
            _cloud_log("ERROR", "VERCEL", f"Error details: {error_msg}")
            return json.dumps({
                "error": True,
                "message": f"deploy.js exited with code {result.returncode}",
                "stderr": error_msg,
            })

        url = result.stdout.strip()
        if url:
            _cloud_log("INFO", "VERCEL", "=" * 50)
            _cloud_log("INFO", "VERCEL", f"DEPLOYMENT SUCCESSFUL!")
            _cloud_log("INFO", "VERCEL", f"Live URL: {url}")
            _cloud_log("INFO", "VERCEL", "=" * 50)
            return json.dumps({"success": True, "url": url})

        _cloud_log("ERROR", "VERCEL", "Deployment finished but no URL was returned")
        return json.dumps({"error": True, "message": "Deployment finished but no URL was returned"})

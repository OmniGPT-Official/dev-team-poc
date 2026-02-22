"""
Vercel Project Management Tools

Provides comprehensive Vercel project management with GitHub integration:
- Create Vercel projects linked to GitHub repos
- Import existing GitHub repos as Vercel projects
- Configure environment variables
- Automatic deployments on git push via GitHub integration

Uses Vercel REST API v9/v10 for project management.
"""

import os
import json
import requests
from typing import Dict, List, Optional, Any
from agno.tools.toolkit import Toolkit


class VercelProjectTools(Toolkit):
    """
    Toolkit for Vercel project management with GitHub integration.

    Enables DevOps engineers to:
    - Import GitHub repos as Vercel projects (automatic deployments on push)
    - Configure environment variables
    - Manage project settings
    """

    def __init__(self, token: Optional[str] = None, **kwargs):
        """
        Args:
            token: Vercel API token. If not provided, falls back to VERCEL_TOKEN env var.
        """
        self._token = token or os.environ.get("VERCEL_TOKEN", "")
        self._base_url = "https://api.vercel.com"
        tools = [
            self.create_vercel_project,
            self.trigger_deployment,
            self.get_vercel_project,
            self.list_vercel_projects,
            self.update_project_env_vars,
            self.link_github_repo_to_project,
        ]
        super().__init__(name="vercel_project", tools=tools, **kwargs)

    def _headers(self) -> Dict[str, str]:
        """Get API headers with authorization."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def _log(self, msg: str):
        """Simple logging."""
        print(f"[VERCEL-PROJECT] {msg}")

    def create_vercel_project(
        self,
        project_name: str,
        github_repo: str,
        github_owner: Optional[str] = None,
        framework: Optional[str] = None,
        build_command: Optional[str] = None,
        output_directory: Optional[str] = None,
        install_command: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Create a Vercel project linked to a GitHub repository.

        This will:
        1. Create a new Vercel project
        2. Link it to the specified GitHub repository
        3. Set up automatic deployments on git push (via GitHub webhooks)
        4. Configure build settings and environment variables

        Args:
            project_name: Vercel project name (lowercase, alphanumeric with hyphens)
            github_repo: GitHub repository name (e.g., "my-app-12345")
            github_owner: GitHub owner/org (if not provided, uses authenticated user)
            framework: Framework preset (nextjs, vite, create-react-app, static, etc.)
                      If None, Vercel auto-detects
            build_command: Custom build command (e.g., "npm run build")
            output_directory: Build output directory (e.g., "dist", "build", "out")
            install_command: Custom install command (e.g., "npm install")
            env_vars: Environment variables as key-value pairs
                     Example: {"API_KEY": "secret123", "NODE_ENV": "production"}

        Returns:
            JSON string with:
            {
                "success": true,
                "project_id": "prj_xxx",
                "project_name": "my-app",
                "url": "https://my-app.vercel.app",
                "github_link": "https://github.com/owner/repo",
                "message": "Project created and linked to GitHub repo"
            }

        Example:
            create_vercel_project(
                project_name="my-nextjs-app",
                github_repo="my-nextjs-app-12345",
                github_owner="myusername",
                framework="nextjs",
                env_vars={"DATABASE_URL": "postgres://..."}
            )
        """
        self._log("=" * 60)
        self._log("CREATING VERCEL PROJECT WITH GITHUB INTEGRATION")
        self._log("=" * 60)

        if not self._token:
            return json.dumps({
                "error": True,
                "message": "VERCEL_TOKEN is not set"
            })

        # Sanitize project name
        import re
        sanitized_name = re.sub(r'[^a-z0-9._-]', '-', project_name.lower())[:100]
        self._log(f"Project Name: {sanitized_name}")
        self._log(f"GitHub Repo: {github_repo}")
        self._log(f"GitHub Owner: {github_owner or 'auto-detect'}")

        try:
            # Build project settings
            project_settings = {}
            if framework:
                project_settings["framework"] = framework
            if build_command:
                project_settings["buildCommand"] = build_command
            if output_directory:
                project_settings["outputDirectory"] = output_directory
            if install_command:
                project_settings["installCommand"] = install_command

            # Build environment variables (format for Vercel API)
            env_list = []
            if env_vars:
                for key, value in env_vars.items():
                    env_list.append({
                        "key": key,
                        "value": value,
                        "type": "encrypted",  # Encrypt sensitive values
                        "target": ["production", "preview", "development"]  # Available in all environments
                    })

            # Prepare GitHub link payload
            git_repository = {}
            if github_owner and github_repo:
                git_repository = {
                    "type": "github",
                    "repo": f"{github_owner}/{github_repo}"
                }

            # Create project payload
            payload = {
                "name": sanitized_name,
                "framework": framework if framework else None,
            }

            # Add GitHub repository link
            if git_repository:
                payload["gitRepository"] = git_repository

            # Add project settings
            if project_settings:
                payload.update(project_settings)

            # Add environment variables
            if env_list:
                payload["environmentVariables"] = env_list

            self._log(f"Creating project with payload: {json.dumps(payload, indent=2)[:500]}...")

            # Create project via Vercel API
            response = requests.post(
                f"{self._base_url}/v9/projects",
                headers=self._headers(),
                json=payload
            )

            if not response.ok:
                error_data = response.json() if response.text else {}
                self._log(f"ERROR: {response.status_code} - {response.text[:500]}")
                return json.dumps({
                    "error": True,
                    "message": error_data.get("error", {}).get("message", "Failed to create project"),
                    "status_code": response.status_code
                })

            project_data = response.json()
            project_id = project_data.get("id")
            project_name_returned = project_data.get("name")
            project_url = f"https://{project_name_returned}.vercel.app"

            self._log("=" * 60)
            self._log(f"✅ PROJECT CREATED SUCCESSFULLY!")
            self._log(f"Project ID: {project_id}")
            self._log(f"Project Name: {project_name_returned}")
            self._log(f"Project URL: {project_url}")
            if github_owner and github_repo:
                self._log(f"GitHub Link: https://github.com/{github_owner}/{github_repo}")
                self._log("✅ Automatic deployments enabled on git push!")
            self._log("=" * 60)

            return json.dumps({
                "success": True,
                "project_id": project_id,
                "project_name": project_name_returned,
                "url": project_url,
                "github_link": f"https://github.com/{github_owner}/{github_repo}" if github_owner and github_repo else None,
                "message": "Project created and linked to GitHub repo with automatic deployments enabled"
            })

        except Exception as e:
            self._log(f"ERROR: {str(e)}")
            return json.dumps({
                "error": True,
                "message": f"Failed to create project: {str(e)}"
            })

    def trigger_deployment(
        self,
        project_name: str,
        git_branch: str = "main"
    ) -> str:
        """
        Trigger a deployment for a Vercel project from GitHub.

        This creates an initial deployment after linking a GitHub repo.
        Future pushes will auto-deploy via GitHub webhooks.

        Args:
            project_name: Vercel project name
            git_branch: Git branch to deploy (default: "main")

        Returns:
            JSON string with deployment details or error

        Example:
            trigger_deployment(
                project_name="my-app",
                git_branch="main"
            )
        """
        if not self._token:
            return json.dumps({"error": True, "message": "VERCEL_TOKEN is not set"})

        self._log("=" * 60)
        self._log(f"TRIGGERING DEPLOYMENT FOR PROJECT: {project_name}")
        self._log(f"Branch: {git_branch}")
        self._log("=" * 60)

        try:
            # Fetch the project to get the numeric GitHub repoId — required by v13/deployments
            self._log(f"Fetching project to resolve GitHub repoId...")
            project_response = requests.get(
                f"{self._base_url}/v9/projects/{project_name}",
                headers=self._headers()
            )

            if not project_response.ok:
                return json.dumps({
                    "error": True,
                    "message": f"Could not fetch project '{project_name}': {project_response.text[:300]}",
                    "status_code": project_response.status_code,
                })

            link = project_response.json().get("link", {})
            repo_id = link.get("repoId")

            if not repo_id:
                return json.dumps({
                    "error": True,
                    "message": (
                        f"Project '{project_name}' has no linked GitHub repo. "
                        "Call create_vercel_project with github_owner and github_repo first."
                    ),
                })

            self._log(f"Resolved GitHub repoId: {repo_id}")

            # Create deployment via POST /v13/deployments
            payload = {
                "name": project_name,
                "target": "production",
                "gitSource": {
                    "type": "github",
                    "ref": git_branch,
                    "repoId": repo_id,
                },
            }

            self._log(f"Creating deployment...")

            response = requests.post(
                f"{self._base_url}/v13/deployments?forceNew=1",
                headers=self._headers(),
                json=payload
            )

            if not response.ok:
                error_data = response.json() if response.text else {}
                self._log(f"ERROR: {response.status_code} - {response.text[:500]}")
                return json.dumps({
                    "error": True,
                    "message": error_data.get("error", {}).get("message", "Failed to trigger deployment"),
                    "status_code": response.status_code
                })

            deployment_data = response.json()
            deployment_id = deployment_data.get("id")
            deployment_url = deployment_data.get("url")

            if deployment_url and not deployment_url.startswith("http"):
                deployment_url = f"https://{deployment_url}"

            self._log("=" * 60)
            self._log(f"✅ DEPLOYMENT TRIGGERED!")
            self._log(f"Deployment ID: {deployment_id}")
            self._log(f"URL: {deployment_url}")
            self._log(f"Status: Building...")
            self._log("=" * 60)

            return json.dumps({
                "success": True,
                "deployment_id": deployment_id,
                "url": deployment_url,
                "status": "building",
                "message": f"Deployment triggered successfully. Building at {deployment_url}"
            })

        except Exception as e:
            self._log(f"ERROR: {str(e)}")
            return json.dumps({
                "error": True,
                "message": f"Failed to trigger deployment: {str(e)}"
            })

    def get_vercel_project(self, project_name: str) -> str:
        """
        Get details of a Vercel project.

        Args:
            project_name: Vercel project name

        Returns:
            JSON string with project details or error
        """
        if not self._token:
            return json.dumps({"error": True, "message": "VERCEL_TOKEN is not set"})

        try:
            response = requests.get(
                f"{self._base_url}/v9/projects/{project_name}",
                headers=self._headers()
            )

            if not response.ok:
                return json.dumps({
                    "error": True,
                    "message": f"Project not found: {project_name}",
                    "status_code": response.status_code
                })

            return json.dumps(response.json())

        except Exception as e:
            return json.dumps({"error": True, "message": str(e)})

    def list_vercel_projects(self, limit: int = 20) -> str:
        """
        List all Vercel projects.

        Args:
            limit: Maximum number of projects to return (default: 20)

        Returns:
            JSON string with list of projects
        """
        if not self._token:
            return json.dumps({"error": True, "message": "VERCEL_TOKEN is not set"})

        try:
            response = requests.get(
                f"{self._base_url}/v9/projects?limit={limit}",
                headers=self._headers()
            )

            if not response.ok:
                return json.dumps({
                    "error": True,
                    "message": "Failed to list projects",
                    "status_code": response.status_code
                })

            data = response.json()
            projects = data.get("projects", [])

            result = {
                "success": True,
                "count": len(projects),
                "projects": [
                    {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "framework": p.get("framework"),
                        "url": f"https://{p.get('name')}.vercel.app",
                        "created_at": p.get("createdAt")
                    }
                    for p in projects
                ]
            }

            return json.dumps(result)

        except Exception as e:
            return json.dumps({"error": True, "message": str(e)})

    def update_project_env_vars(
        self,
        project_name: str,
        env_vars: Dict[str, str],
        target: Optional[List[str]] = None
    ) -> str:
        """
        Add or update environment variables for a Vercel project.

        Args:
            project_name: Vercel project name
            env_vars: Environment variables to add/update as key-value pairs
            target: Deployment targets (default: ["production", "preview", "development"])

        Returns:
            JSON string with success/error status

        Example:
            update_project_env_vars(
                project_name="my-app",
                env_vars={"API_KEY": "new-secret", "DATABASE_URL": "postgres://..."},
                target=["production", "preview"]
            )
        """
        if not self._token:
            return json.dumps({"error": True, "message": "VERCEL_TOKEN is not set"})

        if not target:
            target = ["production", "preview", "development"]

        try:
            # Get project ID first
            project_response = requests.get(
                f"{self._base_url}/v9/projects/{project_name}",
                headers=self._headers()
            )

            if not project_response.ok:
                return json.dumps({
                    "error": True,
                    "message": f"Project not found: {project_name}"
                })

            project_id = project_response.json().get("id")

            # Add each environment variable
            results = []
            for key, value in env_vars.items():
                payload = {
                    "key": key,
                    "value": value,
                    "type": "encrypted",
                    "target": target
                }

                response = requests.post(
                    f"{self._base_url}/v10/projects/{project_id}/env",
                    headers=self._headers(),
                    json=payload
                )

                if response.ok:
                    results.append({"key": key, "status": "added"})
                else:
                    error_data = response.json() if response.text else {}
                    results.append({
                        "key": key,
                        "status": "failed",
                        "error": error_data.get("error", {}).get("message", "Unknown error")
                    })

            self._log(f"Updated {len([r for r in results if r['status'] == 'added'])} environment variables")

            return json.dumps({
                "success": True,
                "project_name": project_name,
                "results": results
            })

        except Exception as e:
            return json.dumps({"error": True, "message": str(e)})

    def link_github_repo_to_project(
        self,
        project_name: str,
        github_owner: str,
        github_repo: str
    ) -> str:
        """
        Link an existing Vercel project to a GitHub repository.

        This enables automatic deployments when you push to the GitHub repo.

        Args:
            project_name: Existing Vercel project name
            github_owner: GitHub owner/org
            github_repo: GitHub repository name

        Returns:
            JSON string with success/error status
        """
        if not self._token:
            return json.dumps({"error": True, "message": "VERCEL_TOKEN is not set"})

        try:
            payload = {
                "gitRepository": {
                    "type": "github",
                    "repo": f"{github_owner}/{github_repo}"
                }
            }

            response = requests.patch(
                f"{self._base_url}/v9/projects/{project_name}",
                headers=self._headers(),
                json=payload
            )

            if not response.ok:
                error_data = response.json() if response.text else {}
                return json.dumps({
                    "error": True,
                    "message": error_data.get("error", {}).get("message", "Failed to link GitHub repo"),
                    "status_code": response.status_code
                })

            self._log(f"✅ Linked {github_owner}/{github_repo} to project {project_name}")
            self._log("✅ Automatic deployments enabled on git push!")

            return json.dumps({
                "success": True,
                "project_name": project_name,
                "github_link": f"https://github.com/{github_owner}/{github_repo}",
                "message": "GitHub repo linked successfully. Automatic deployments enabled on git push."
            })

        except Exception as e:
            return json.dumps({"error": True, "message": str(e)})

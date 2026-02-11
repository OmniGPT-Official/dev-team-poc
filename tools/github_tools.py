"""
GitHub Tools - Direct API Implementation

A reliable GitHub toolkit using direct REST API calls instead of MCP.
This avoids the TaskGroup async issues with the MCP implementation.
"""

import os
import base64
import json
from typing import Optional, List, Dict, Any
import requests
from agno.tools.toolkit import Toolkit


class GitHubTools(Toolkit):
    """
    GitHub toolkit using direct REST API calls.

    Usage:
        github_tools = GitHubTools(token="ghp_xxx")
        # Or set GITHUB_TOKEN environment variable
    """

    def __init__(
        self,
        token: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize GitHub tools.

        Args:
            token: GitHub personal access token. If not provided, uses GITHUB_TOKEN env var.
        """
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        tools = [
            self.get_authenticated_user,
            self.search_repositories,
            self.get_repository,
            self.create_repository,
            self.list_repository_files,
            self.get_file_contents,
            self.create_or_update_file,
            self.delete_file,
            self.list_branches,
            self.create_branch,
            self.list_commits,
            self.create_issue,
            self.list_issues,
            self.get_issue,
            self.create_pull_request,
            self.list_pull_requests,
            self.get_pull_request,
        ]

        super().__init__(
            name="github",
            tools=tools,
            **kwargs
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make a request to the GitHub API."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
                timeout=30
            )

            if response.status_code == 204:
                return {"success": True}

            if response.status_code >= 400:
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "message": response.text
                }

            return response.json()
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_authenticated_user(self) -> str:
        """
        Get the authenticated user's information.

        Returns:
            JSON string with user information
        """
        result = self._request("GET", "/user")
        return json.dumps(result, indent=2)

    def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 10,
        page: int = 1
    ) -> str:
        """
        Search for GitHub repositories.

        Args:
            query: Search query (e.g., "python machine learning")
            sort: Sort by (stars, forks, help-wanted-issues, updated)
            order: Order (asc or desc)
            per_page: Results per page (max 100)
            page: Page number

        Returns:
            JSON string with search results
        """
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": per_page,
            "page": page
        }
        result = self._request("GET", "/search/repositories", params=params)

        # Simplify output
        if "items" in result:
            simplified = {
                "total_count": result.get("total_count", 0),
                "repositories": [
                    {
                        "full_name": r["full_name"],
                        "description": r.get("description", "")[:100] if r.get("description") else "",
                        "stars": r.get("stargazers_count", 0),
                        "url": r.get("html_url", "")
                    }
                    for r in result["items"]
                ]
            }
            return json.dumps(simplified, indent=2)

        return json.dumps(result, indent=2)

    def get_repository(self, owner: str, repo: str) -> str:
        """
        Get repository information.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name

        Returns:
            JSON string with repository information
        """
        result = self._request("GET", f"/repos/{owner}/{repo}")
        return json.dumps(result, indent=2)

    def create_repository(
        self,
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = True,
        org: str = ""
    ) -> str:
        """
        Create a new repository.

        Args:
            name: Repository name
            description: Repository description
            private: Whether the repo should be private
            auto_init: Initialize with a README
            org: Organization name (optional). If provided, creates repo under org instead of user.

        Returns:
            JSON string with created repository information
        """
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init
        }

        # If org is specified, create under organization; otherwise create under authenticated user
        if org:
            endpoint = f"/orgs/{org}/repos"
        else:
            endpoint = "/user/repos"

        result = self._request("POST", endpoint, data=data)
        return json.dumps(result, indent=2)

    def list_repository_files(
        self,
        owner: str,
        repo: str,
        path: str = "",
        ref: str = "main"
    ) -> str:
        """
        List files in a repository directory.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Directory path (empty for root)
            ref: Branch or commit ref

        Returns:
            JSON string with file list
        """
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref} if ref else {}
        result = self._request("GET", endpoint, params=params)

        if isinstance(result, list):
            files = [
                {
                    "name": f["name"],
                    "path": f["path"],
                    "type": f["type"],
                    "size": f.get("size", 0)
                }
                for f in result
            ]
            return json.dumps(files, indent=2)

        return json.dumps(result, indent=2)

    def get_file_contents(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "main"
    ) -> str:
        """
        Get the contents of a file.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            ref: Branch or commit ref

        Returns:
            File contents as string
        """
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref} if ref else {}
        result = self._request("GET", endpoint, params=params)

        if "content" in result:
            try:
                content = base64.b64decode(result["content"]).decode("utf-8")
                return content
            except:
                return json.dumps(result, indent=2)

        return json.dumps(result, indent=2)

    def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
        sha: Optional[str] = None
    ) -> str:
        """
        Create or update a file in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            content: File content (will be base64 encoded)
            message: Commit message
            branch: Branch name
            sha: SHA of file being replaced (required for updates, optional for creates)

        Returns:
            JSON string with commit information
        """
        # If no SHA provided, try to get it (for updates)
        if not sha:
            existing = self._request("GET", f"/repos/{owner}/{repo}/contents/{path}", params={"ref": branch})
            if "sha" in existing:
                sha = existing["sha"]

        data = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch
        }
        if sha:
            data["sha"] = sha

        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        result = self._request("PUT", endpoint, data=data)

        if "commit" in result:
            return json.dumps({
                "success": True,
                "commit_sha": result["commit"]["sha"],
                "commit_url": result["commit"]["html_url"]
            }, indent=2)

        return json.dumps(result, indent=2)

    def delete_file(
        self,
        owner: str,
        repo: str,
        path: str,
        message: str,
        branch: str = "main"
    ) -> str:
        """
        Delete a file from a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            message: Commit message
            branch: Branch name

        Returns:
            JSON string with result
        """
        # Get current SHA
        existing = self._request("GET", f"/repos/{owner}/{repo}/contents/{path}", params={"ref": branch})
        if "sha" not in existing:
            return json.dumps({"error": True, "message": "File not found"})

        data = {
            "message": message,
            "sha": existing["sha"],
            "branch": branch
        }

        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        result = self._request("DELETE", endpoint, data=data)
        return json.dumps(result, indent=2)

    def list_branches(self, owner: str, repo: str) -> str:
        """
        List branches in a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            JSON string with branch list
        """
        result = self._request("GET", f"/repos/{owner}/{repo}/branches")

        if isinstance(result, list):
            branches = [b["name"] for b in result]
            return json.dumps(branches, indent=2)

        return json.dumps(result, indent=2)

    def create_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        from_branch: str = "main"
    ) -> str:
        """
        Create a new branch.

        Args:
            owner: Repository owner
            repo: Repository name
            branch_name: New branch name
            from_branch: Branch to create from

        Returns:
            JSON string with result
        """
        # Get SHA of source branch
        ref_result = self._request("GET", f"/repos/{owner}/{repo}/git/refs/heads/{from_branch}")
        if "object" not in ref_result:
            return json.dumps({"error": True, "message": f"Branch {from_branch} not found"})

        sha = ref_result["object"]["sha"]

        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }

        result = self._request("POST", f"/repos/{owner}/{repo}/git/refs", data=data)
        return json.dumps(result, indent=2)

    def list_commits(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        per_page: int = 10,
        page: int = 1
    ) -> str:
        """
        List commits in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            per_page: Results per page
            page: Page number

        Returns:
            JSON string with commit list
        """
        params = {
            "sha": branch,
            "per_page": per_page,
            "page": page
        }
        result = self._request("GET", f"/repos/{owner}/{repo}/commits", params=params)

        if isinstance(result, list):
            commits = [
                {
                    "sha": c["sha"][:7],
                    "message": c["commit"]["message"].split("\n")[0][:80],
                    "author": c["commit"]["author"]["name"],
                    "date": c["commit"]["author"]["date"]
                }
                for c in result
            ]
            return json.dumps(commits, indent=2)

        return json.dumps(result, indent=2)

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: Optional[List[str]] = None
    ) -> str:
        """
        Create a new issue.

        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body
            labels: List of label names

        Returns:
            JSON string with created issue
        """
        data = {
            "title": title,
            "body": body
        }
        if labels:
            data["labels"] = labels

        result = self._request("POST", f"/repos/{owner}/{repo}/issues", data=data)
        return json.dumps(result, indent=2)

    def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 10,
        page: int = 1
    ) -> str:
        """
        List issues in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open, closed, all)
            per_page: Results per page
            page: Page number

        Returns:
            JSON string with issue list
        """
        params = {
            "state": state,
            "per_page": per_page,
            "page": page
        }
        result = self._request("GET", f"/repos/{owner}/{repo}/issues", params=params)

        if isinstance(result, list):
            issues = [
                {
                    "number": i["number"],
                    "title": i["title"],
                    "state": i["state"],
                    "user": i["user"]["login"],
                    "created_at": i["created_at"]
                }
                for i in result
            ]
            return json.dumps(issues, indent=2)

        return json.dumps(result, indent=2)

    def get_issue(self, owner: str, repo: str, issue_number: int) -> str:
        """
        Get a specific issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            JSON string with issue details
        """
        result = self._request("GET", f"/repos/{owner}/{repo}/issues/{issue_number}")
        return json.dumps(result, indent=2)

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = ""
    ) -> str:
        """
        Create a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head: Head branch (source)
            base: Base branch (target)
            body: PR body

        Returns:
            JSON string with created PR
        """
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body
        }

        result = self._request("POST", f"/repos/{owner}/{repo}/pulls", data=data)
        return json.dumps(result, indent=2)

    def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 10,
        page: int = 1
    ) -> str:
        """
        List pull requests in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state (open, closed, all)
            per_page: Results per page
            page: Page number

        Returns:
            JSON string with PR list
        """
        params = {
            "state": state,
            "per_page": per_page,
            "page": page
        }
        result = self._request("GET", f"/repos/{owner}/{repo}/pulls", params=params)

        if isinstance(result, list):
            prs = [
                {
                    "number": p["number"],
                    "title": p["title"],
                    "state": p["state"],
                    "user": p["user"]["login"],
                    "head": p["head"]["ref"],
                    "base": p["base"]["ref"]
                }
                for p in result
            ]
            return json.dumps(prs, indent=2)

        return json.dumps(result, indent=2)

    def get_pull_request(self, owner: str, repo: str, pr_number: int) -> str:
        """
        Get a specific pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            JSON string with PR details
        """
        result = self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
        return json.dumps(result, indent=2)


# Convenience function to create GitHub tools with token from env
def get_github_tools(token: Optional[str] = None) -> GitHubTools:
    """Get GitHub tools instance."""
    return GitHubTools(token=token)

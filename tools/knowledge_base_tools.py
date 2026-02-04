"""
Knowledge Base Tools

Tools for querying and managing the project knowledge base.
Used by the Product Team to access existing project context.
"""

import json
from typing import List, Optional
from agno.tools import Toolkit

from utils.knowledge_base import get_knowledge_base, ProjectContext


class KnowledgeBaseTools(Toolkit):
    """
    Tools for interacting with the project knowledge base.

    Provides capabilities to:
    - Search for existing projects
    - Get project context and history
    - List all projects
    - Get feature specifications
    - Check if a project exists
    """

    def __init__(self, **kwargs):
        tools = [
            self.search_projects,
            self.get_project_context,
            self.list_all_projects,
            self.get_project_features,
            self.check_project_exists,
            self.get_project_by_repository,
        ]

        super().__init__(
            name="knowledge_base",
            tools=tools,
            instructions="""Use these tools to query the project knowledge base:
- search_projects: Find projects by name or description
- get_project_context: Get full context for a project (PRD, architecture, features)
- list_all_projects: List all projects in the knowledge base
- get_project_features: Get all features for a project
- check_project_exists: Check if a project with given repo exists
- get_project_by_repository: Get project by GitHub owner/repo""",
            add_instructions=True,
            **kwargs
        )

        self._kb = get_knowledge_base()

    def search_projects(self, query: str) -> str:
        """
        Search for projects in the knowledge base by name or description.

        Args:
            query: Search term to find matching projects

        Returns:
            JSON string with matching projects
        """
        projects = self._kb.search_projects(query)

        if not projects:
            return json.dumps({
                "found": False,
                "message": f"No projects found matching '{query}'",
                "projects": []
            })

        results = []
        for p in projects:
            results.append({
                "project_id": p.project_id,
                "name": p.project_name,
                "type": p.project_type,
                "repository": f"{p.github_owner}/{p.github_repo}",
                "status": p.status,
                "features_count": len(p.features),
                "description": p.description[:200] if p.description else ""
            })

        return json.dumps({
            "found": True,
            "count": len(results),
            "projects": results
        }, indent=2)

    def get_project_context(self, project_id: str) -> str:
        """
        Get the full context for a project including PRD, architecture, and features.

        Args:
            project_id: The unique project identifier

        Returns:
            Formatted project context summary
        """
        summary = self._kb.get_project_context_summary(project_id)
        return summary

    def list_all_projects(self, status: Optional[str] = None) -> str:
        """
        List all projects in the knowledge base.

        Args:
            status: Optional filter by status ('active', 'completed', 'archived')

        Returns:
            JSON string with all projects
        """
        projects = self._kb.list_projects(status=status)

        if not projects:
            return json.dumps({
                "count": 0,
                "message": "No projects in knowledge base",
                "projects": []
            })

        results = []
        for p in projects:
            results.append({
                "project_id": p.project_id,
                "name": p.project_name,
                "type": p.project_type,
                "repository": f"{p.github_owner}/{p.github_repo}",
                "status": p.status,
                "features_count": len(p.features),
                "updated_at": p.updated_at
            })

        return json.dumps({
            "count": len(results),
            "projects": results
        }, indent=2)

    def get_project_features(self, project_id: str) -> str:
        """
        Get all features for a specific project.

        Args:
            project_id: The unique project identifier

        Returns:
            JSON string with project features
        """
        features = self._kb.get_features(project_id)

        if not features:
            return json.dumps({
                "count": 0,
                "message": "No features found for this project",
                "features": []
            })

        results = []
        for f in features:
            results.append({
                "feature_id": f.feature_id,
                "name": f.feature_name,
                "description": f.description,
                "priority": f.priority,
                "status": f.status,
                "acceptance_criteria": f.acceptance_criteria
            })

        return json.dumps({
            "count": len(results),
            "features": results
        }, indent=2)

    def check_project_exists(self, github_owner: str, github_repo: str) -> str:
        """
        Check if a project exists in the knowledge base by GitHub repository.

        Args:
            github_owner: GitHub owner or organization name
            github_repo: GitHub repository name

        Returns:
            JSON string indicating if project exists and basic info
        """
        project = self._kb.get_project_by_repo(github_owner, github_repo)

        if not project:
            return json.dumps({
                "exists": False,
                "message": f"No project found for {github_owner}/{github_repo}",
                "is_new_project": True
            })

        return json.dumps({
            "exists": True,
            "is_new_project": False,
            "project_id": project.project_id,
            "name": project.project_name,
            "type": project.project_type,
            "status": project.status,
            "features_count": len(project.features),
            "has_prd": bool(project.prd_content),
            "has_architecture": bool(project.architecture_content)
        }, indent=2)

    def get_project_by_repository(self, github_owner: str, github_repo: str) -> str:
        """
        Get project details by GitHub repository.

        Args:
            github_owner: GitHub owner or organization name
            github_repo: GitHub repository name

        Returns:
            Full project context or not found message
        """
        project = self._kb.get_project_by_repo(github_owner, github_repo)

        if not project:
            return json.dumps({
                "found": False,
                "message": f"No project found for {github_owner}/{github_repo}"
            })

        return self.get_project_context(project.project_id)

"""
Knowledge Base - Supabase integration for storing and retrieving project context.

This module provides utilities for:
- Storing project information (PRDs, architecture docs, code)
- Retrieving historical context for existing products
- Managing project metadata
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class ProjectContext:
    """Project context stored in knowledge base."""
    project_id: str
    project_name: str
    project_type: str  # "new" or "existing"
    github_owner: str
    github_repo: str
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    prd_content: str = ""
    architecture_content: str = ""
    features: List[str] = None
    status: str = "active"  # active, completed, archived

    def __post_init__(self):
        if self.features is None:
            self.features = []
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class FeatureSpec:
    """Feature specification for existing products."""
    feature_id: str
    project_id: str
    feature_name: str
    description: str
    requirements: str
    acceptance_criteria: List[str]
    priority: str  # P0, P1, P2, P3
    status: str  # pending, in_progress, completed
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


class KnowledgeBase:
    """
    Knowledge base for storing and retrieving project context.

    Uses Supabase MCP when available, falls back to local JSON storage.
    """

    def __init__(self, supabase_mcp=None, local_path: str = None):
        """
        Initialize knowledge base.

        Args:
            supabase_mcp: Supabase MCP tools instance (optional)
            local_path: Path for local fallback storage
        """
        self.supabase_mcp = supabase_mcp
        self.local_path = local_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "output",
            "knowledge_base"
        )
        os.makedirs(self.local_path, exist_ok=True)

        # Local cache
        self._projects_cache: Dict[str, ProjectContext] = {}
        self._features_cache: Dict[str, List[FeatureSpec]] = {}

        # Load existing local data
        self._load_local_data()

    def _load_local_data(self):
        """Load data from local JSON files."""
        projects_file = os.path.join(self.local_path, "projects.json")
        if os.path.exists(projects_file):
            with open(projects_file, 'r') as f:
                data = json.load(f)
                for project_data in data.get("projects", []):
                    project = ProjectContext(**project_data)
                    self._projects_cache[project.project_id] = project

        features_file = os.path.join(self.local_path, "features.json")
        if os.path.exists(features_file):
            with open(features_file, 'r') as f:
                data = json.load(f)
                for project_id, features_data in data.get("features", {}).items():
                    self._features_cache[project_id] = [
                        FeatureSpec(**f) for f in features_data
                    ]

    def _save_local_data(self):
        """Save data to local JSON files."""
        # Save projects
        projects_file = os.path.join(self.local_path, "projects.json")
        projects_data = {
            "projects": [asdict(p) for p in self._projects_cache.values()]
        }
        with open(projects_file, 'w') as f:
            json.dump(projects_data, f, indent=2)

        # Save features
        features_file = os.path.join(self.local_path, "features.json")
        features_data = {
            "features": {
                pid: [asdict(f) for f in features]
                for pid, features in self._features_cache.items()
            }
        }
        with open(features_file, 'w') as f:
            json.dump(features_data, f, indent=2)

    def _generate_id(self, *args) -> str:
        """Generate a unique ID from arguments."""
        content = ":".join(str(a) for a in args) + datetime.utcnow().isoformat()
        return hashlib.md5(content.encode()).hexdigest()[:12]

    # =========================================================================
    # PROJECT OPERATIONS
    # =========================================================================

    def create_project(
        self,
        project_name: str,
        project_type: str,
        github_owner: str,
        github_repo: str,
        description: str = "",
    ) -> ProjectContext:
        """
        Create a new project in the knowledge base.

        Args:
            project_name: Name of the project
            project_type: "new" for new project, "existing" for existing product
            github_owner: GitHub owner/org
            github_repo: GitHub repository name
            description: Project description

        Returns:
            Created ProjectContext
        """
        project_id = self._generate_id(project_name, github_owner, github_repo)

        project = ProjectContext(
            project_id=project_id,
            project_name=project_name,
            project_type=project_type,
            github_owner=github_owner,
            github_repo=github_repo,
            description=description,
        )

        self._projects_cache[project_id] = project
        self._save_local_data()

        return project

    def get_project(self, project_id: str) -> Optional[ProjectContext]:
        """Get a project by ID."""
        return self._projects_cache.get(project_id)

    def get_project_by_repo(self, github_owner: str, github_repo: str) -> Optional[ProjectContext]:
        """Get a project by GitHub repository."""
        for project in self._projects_cache.values():
            if project.github_owner == github_owner and project.github_repo == github_repo:
                return project
        return None

    def update_project(
        self,
        project_id: str,
        prd_content: str = None,
        architecture_content: str = None,
        features: List[str] = None,
        status: str = None,
    ) -> Optional[ProjectContext]:
        """Update a project's content."""
        project = self._projects_cache.get(project_id)
        if not project:
            return None

        if prd_content is not None:
            project.prd_content = prd_content
        if architecture_content is not None:
            project.architecture_content = architecture_content
        if features is not None:
            project.features = features
        if status is not None:
            project.status = status

        project.updated_at = datetime.utcnow().isoformat()
        self._save_local_data()

        return project

    def list_projects(self, status: str = None) -> List[ProjectContext]:
        """List all projects, optionally filtered by status."""
        projects = list(self._projects_cache.values())
        if status:
            projects = [p for p in projects if p.status == status]
        return sorted(projects, key=lambda p: p.updated_at, reverse=True)

    # =========================================================================
    # FEATURE OPERATIONS
    # =========================================================================

    def add_feature(
        self,
        project_id: str,
        feature_name: str,
        description: str,
        requirements: str,
        acceptance_criteria: List[str],
        priority: str = "P1",
    ) -> Optional[FeatureSpec]:
        """
        Add a feature spec to a project.

        Args:
            project_id: Project ID
            feature_name: Name of the feature
            description: Feature description
            requirements: Detailed requirements
            acceptance_criteria: List of acceptance criteria
            priority: P0, P1, P2, or P3

        Returns:
            Created FeatureSpec
        """
        if project_id not in self._projects_cache:
            return None

        feature_id = self._generate_id(project_id, feature_name)

        feature = FeatureSpec(
            feature_id=feature_id,
            project_id=project_id,
            feature_name=feature_name,
            description=description,
            requirements=requirements,
            acceptance_criteria=acceptance_criteria,
            priority=priority,
            status="pending",
        )

        if project_id not in self._features_cache:
            self._features_cache[project_id] = []
        self._features_cache[project_id].append(feature)

        # Update project's feature list
        project = self._projects_cache[project_id]
        project.features.append(feature_name)
        project.updated_at = datetime.utcnow().isoformat()

        self._save_local_data()
        return feature

    def get_features(self, project_id: str) -> List[FeatureSpec]:
        """Get all features for a project."""
        return self._features_cache.get(project_id, [])

    def update_feature_status(
        self,
        project_id: str,
        feature_id: str,
        status: str,
    ) -> Optional[FeatureSpec]:
        """Update a feature's status."""
        features = self._features_cache.get(project_id, [])
        for feature in features:
            if feature.feature_id == feature_id:
                feature.status = status
                self._save_local_data()
                return feature
        return None

    # =========================================================================
    # CONTEXT RETRIEVAL
    # =========================================================================

    def get_project_context_summary(self, project_id: str) -> str:
        """
        Get a formatted summary of project context for agents.

        Returns a string containing:
        - Project info
        - Existing PRD (if any)
        - Existing architecture (if any)
        - Implemented features
        """
        project = self._projects_cache.get(project_id)
        if not project:
            return "Project not found."

        features = self._features_cache.get(project_id, [])

        summary = f"""## Project Context: {project.project_name}

**Type:** {project.project_type}
**Repository:** {project.github_owner}/{project.github_repo}
**Status:** {project.status}
**Last Updated:** {project.updated_at}

### Description
{project.description or 'No description available.'}

### Existing Features ({len(features)})
"""

        if features:
            for f in features:
                summary += f"- **{f.feature_name}** [{f.priority}] - {f.status}\n"
        else:
            summary += "No features implemented yet.\n"

        if project.prd_content:
            summary += f"\n### Current PRD\n{project.prd_content[:2000]}{'...' if len(project.prd_content) > 2000 else ''}\n"

        if project.architecture_content:
            summary += f"\n### Current Architecture\n{project.architecture_content[:2000]}{'...' if len(project.architecture_content) > 2000 else ''}\n"

        return summary

    def search_projects(self, query: str) -> List[ProjectContext]:
        """Search projects by name or description."""
        query = query.lower()
        results = []
        for project in self._projects_cache.values():
            if (query in project.project_name.lower() or
                query in project.description.lower() or
                query in project.github_repo.lower()):
                results.append(project)
        return results


# =========================================================================
# SINGLETON INSTANCE
# =========================================================================

_knowledge_base_instance: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """Get or create the singleton knowledge base instance."""
    global _knowledge_base_instance
    if _knowledge_base_instance is None:
        _knowledge_base_instance = KnowledgeBase()
    return _knowledge_base_instance

"""
Project Management Tools

Tools for creating, updating, listing, and searching user projects.
Integrates with Supabase projects table.
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from services.oauth_store import get_supabase_client
from services.project_context import set_current_project_id, get_current_project_id
from services.user_context import get_current_user_id


# ============================================================================
# PROJECT CREATION
# ============================================================================

def create_project(
    project_name: str,
    project_description: str,
    project_type: str = "new"
) -> Dict[str, Any]:
    """Create a new project entry.

    Args:
        project_name: Name of the project
        project_description: What the project does
        project_type: "new" or "existing"

    Returns:
        {
            "success": bool,
            "project_id": str (if successful),
            "message": str
        }
    """
    user_id = get_current_user_id()
    if not user_id:
        return {
            "success": False,
            "project_id": None,
            "message": "No user_id in context"
        }

    try:
        project_id = str(uuid.uuid4())

        data = {
            "id": project_id,
            "user_id": user_id,
            "project_name": project_name,
            "project_description": project_description,
            "project_type": project_type,
            "status": "planning"
        }

        result = (
            get_supabase_client()
            .table("projects")
            .insert(data)
            .execute()
        )

        # Set in context for workflow use
        set_current_project_id(project_id)

        print(f"[project_tools] Created project: {project_id} ({project_name})")

        return {
            "success": True,
            "project_id": project_id,
            "message": f"Project '{project_name}' created successfully"
        }

    except Exception as e:
        print(f"[project_tools] ERROR creating project: {e}")
        return {
            "success": False,
            "project_id": None,
            "message": f"Failed to create project: {str(e)}"
        }


# ============================================================================
# PROJECT UPDATES
# ============================================================================

def update_project(
    project_id: str,
    prd_doc_url: Optional[str] = None,
    architecture_doc_url: Optional[str] = None,
    github_repo_url: Optional[str] = None,
    github_repo_name: Optional[str] = None,
    github_owner: Optional[str] = None,
    vercel_deployment_url: Optional[str] = None,
    vercel_project_id: Optional[str] = None,
    status: Optional[str] = None,
    tech_stack: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Update project with new information as workflow progresses.

    Args:
        project_id: Project UUID
        (all other args are optional updates)

    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        update_data = {}

        if prd_doc_url:
            update_data["prd_doc_url"] = prd_doc_url
            update_data["prd_created_at"] = datetime.utcnow().isoformat()

        if architecture_doc_url:
            update_data["architecture_doc_url"] = architecture_doc_url
            update_data["architecture_created_at"] = datetime.utcnow().isoformat()

        if github_repo_url:
            update_data["github_repo_url"] = github_repo_url
            update_data["repo_created_at"] = datetime.utcnow().isoformat()

        if github_repo_name:
            update_data["github_repo_name"] = github_repo_name

        if github_owner:
            update_data["github_owner"] = github_owner

        if vercel_deployment_url:
            update_data["vercel_deployment_url"] = vercel_deployment_url
            update_data["deployed_at"] = datetime.utcnow().isoformat()

        if vercel_project_id:
            update_data["vercel_project_id"] = vercel_project_id

        if status:
            update_data["status"] = status

        if tech_stack:
            update_data["tech_stack"] = tech_stack

        if not update_data:
            return {
                "success": False,
                "message": "No updates provided"
            }

        result = (
            get_supabase_client()
            .table("projects")
            .update(update_data)
            .eq("id", project_id)
            .execute()
        )

        print(f"[project_tools] Updated project {project_id}: {list(update_data.keys())}")

        return {
            "success": True,
            "message": f"Project updated with: {', '.join(update_data.keys())}"
        }

    except Exception as e:
        print(f"[project_tools] ERROR updating project: {e}")
        return {
            "success": False,
            "message": f"Failed to update project: {str(e)}"
        }


# ============================================================================
# PROJECT RETRIEVAL
# ============================================================================

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Get project details by ID.

    Args:
        project_id: Project UUID

    Returns:
        Project dict or None
    """
    try:
        result = (
            get_supabase_client()
            .table("projects")
            .select("*")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        return result.data[0]

    except Exception as e:
        print(f"[project_tools] ERROR getting project: {e}")
        return None


def list_user_projects(limit: int = 50) -> List[Dict[str, Any]]:
    """List all projects for a user.

    Args:
        limit: Max number of projects to return

    Returns:
        List of project dicts
    """
    user_id = get_current_user_id()
    if not user_id:
        print(f"[project_tools] ERROR: No user_id in context")
        return []

    try:
        result = (
            get_supabase_client()
            .table("projects")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return result.data or []

    except Exception as e:
        print(f"[project_tools] ERROR listing projects: {e}")
        return []


# ============================================================================
# PROJECT SEARCH
# ============================================================================

def search_projects_by_name(search_query: str) -> List[Dict[str, Any]]:
    """Search projects by name/description using full-text search.

    Args:
        search_query: Search query (e.g., "e-commerce", "task manager")

    Returns:
        List of matching projects
    """
    user_id = get_current_user_id()
    if not user_id:
        print(f"[project_tools] ERROR: No user_id in context")
        return []

    try:
        # Use PostgreSQL full-text search
        result = (
            get_supabase_client()
            .table("projects")
            .select("*")
            .eq("user_id", user_id)
            .text_search("project_name,project_description", search_query)
            .limit(10)
            .execute()
        )

        return result.data or []

    except Exception as e:
        print(f"[project_tools] ERROR searching projects: {e}")
        # Fallback to simple LIKE search
        try:
            result = (
                get_supabase_client()
                .table("projects")
                .select("*")
                .eq("user_id", user_id)
                .ilike("project_name", f"%{search_query}%")
                .limit(10)
                .execute()
            )
            return result.data or []
        except:
            return []


def find_project_by_github_url(github_url: str) -> Optional[Dict[str, Any]]:
    """Find a project by GitHub repository URL.

    Args:
        github_url: GitHub repository URL (e.g., "https://github.com/user/repo")

    Returns:
        Project dict if found, None otherwise
    """
    user_id = get_current_user_id()
    if not user_id:
        print(f"[project_tools] ERROR: No user_id in context")
        return None

    # Normalize GitHub URL (remove trailing slashes, .git suffix)
    normalized_url = github_url.rstrip('/').replace('.git', '')

    try:
        # Search by exact match
        result = (
            get_supabase_client()
            .table("projects")
            .select("*")
            .eq("user_id", user_id)
            .eq("github_repo_url", normalized_url)
            .limit(1)
            .execute()
        )

        if result.data:
            print(f"[project_tools] Found project by GitHub URL: {result.data[0]['project_name']}")
            return result.data[0]

        # Fallback: Try LIKE search in case URL format is slightly different
        result = (
            get_supabase_client()
            .table("projects")
            .select("*")
            .eq("user_id", user_id)
            .ilike("github_repo_url", f"%{normalized_url}%")
            .limit(1)
            .execute()
        )

        if result.data:
            print(f"[project_tools] Found project by GitHub URL (fuzzy match): {result.data[0]['project_name']}")
            return result.data[0]

        print(f"[project_tools] No project found for GitHub URL: {normalized_url}")
        return None

    except Exception as e:
        print(f"[project_tools] ERROR finding project by GitHub URL: {e}")
        return None


# ============================================================================
# FEATURE SPECS & TECHNICAL DOCS (ARRAY OPERATIONS)
# ============================================================================

def add_feature_spec(
    project_id: str,
    doc_url: str,
    title: str
) -> Dict[str, Any]:
    """
    Prepend a feature spec document to the project's feature_specs array.

    Args:
        project_id: Project UUID
        doc_url: Google Docs URL
        title: Document title

    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        # Get current feature_specs array
        project = get_project(project_id)
        if not project:
            return {
                "success": False,
                "message": "Project not found"
            }

        feature_specs = project.get("feature_specs", [])

        # Prepend new spec (most recent first)
        new_spec = {
            "url": doc_url,
            "title": title,
            "created_at": datetime.utcnow().isoformat()
        }
        feature_specs.insert(0, new_spec)  # Prepend to beginning

        # Update project
        result = (
            get_supabase_client()
            .table("projects")
            .update({"feature_specs": feature_specs})
            .eq("id", project_id)
            .execute()
        )

        print(f"[project_tools] Added feature spec to project {project_id}: {title}")

        return {
            "success": True,
            "message": f"Feature spec added: {title}"
        }

    except Exception as e:
        print(f"[project_tools] ERROR adding feature spec: {e}")
        return {
            "success": False,
            "message": f"Failed to add feature spec: {str(e)}"
        }


def add_technical_doc(
    project_id: str,
    doc_url: str,
    title: str
) -> Dict[str, Any]:
    """
    Prepend a technical document to the project's technical_docs array.

    Args:
        project_id: Project UUID
        doc_url: Google Docs URL
        title: Document title

    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        # Get current technical_docs array
        project = get_project(project_id)
        if not project:
            return {
                "success": False,
                "message": "Project not found"
            }

        technical_docs = project.get("technical_docs", [])

        # Prepend new doc (most recent first)
        new_doc = {
            "url": doc_url,
            "title": title,
            "created_at": datetime.utcnow().isoformat()
        }
        technical_docs.insert(0, new_doc)  # Prepend to beginning

        # Update project
        result = (
            get_supabase_client()
            .table("projects")
            .update({"technical_docs": technical_docs})
            .eq("id", project_id)
            .execute()
        )

        print(f"[project_tools] Added technical doc to project {project_id}: {title}")

        return {
            "success": True,
            "message": f"Technical doc added: {title}"
        }

    except Exception as e:
        print(f"[project_tools] ERROR adding technical doc: {e}")
        return {
            "success": False,
            "message": f"Failed to add technical doc: {str(e)}"
        }

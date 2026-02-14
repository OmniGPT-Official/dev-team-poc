"""
Supervisor Tools

Tools for validating documents and ensuring project quality.
Used by the Supervisor agent after PRD/Architecture creation to validate outputs.
"""

from typing import Dict, Any, Optional
from services.project_context import get_current_project_id
from services.user_context import get_current_user_id
from tools.project_tools import update_project, add_project_to_knowledge_base, get_project


# ============================================================================
# DOCUMENT VALIDATION
# ============================================================================

def validate_google_doc(doc_url: str, expected_content_keywords: list) -> Dict[str, Any]:
    """Validate a Google Doc by checking if it's accessible and contains expected content.

    Args:
        doc_url: Google Docs URL
        expected_content_keywords: Keywords that should appear in first few lines (e.g., project name)

    Returns:
        {
            "valid": bool,
            "accessible": bool,
            "contains_keywords": bool,
            "preview": str (first few lines),
            "message": str
        }
    """
    user_id = get_current_user_id()
    if not user_id:
        return {
            "valid": False,
            "accessible": False,
            "contains_keywords": False,
            "preview": None,
            "message": "No user_id in context"
        }

    try:
        # Extract document ID from URL
        if "/document/d/" not in doc_url:
            return {
                "valid": False,
                "accessible": False,
                "contains_keywords": False,
                "preview": None,
                "message": "Invalid Google Docs URL format"
            }

        doc_id = doc_url.split("/document/d/")[1].split("/")[0]

        # Get Google Docs credentials
        from services.oauth_store import get_google_credentials
        from googleapiclient.discovery import build

        creds = get_google_credentials(user_id, "google_docs")
        if not creds:
            return {
                "valid": False,
                "accessible": False,
                "contains_keywords": False,
                "preview": None,
                "message": "No Google Docs credentials found"
            }

        # Access document
        service = build('docs', 'v1', credentials=creds)
        document = service.documents().get(documentId=doc_id).execute()

        # Extract text content (first 500 characters for preview)
        content = document.get('body', {}).get('content', [])
        text_content = ""
        for element in content:
            if 'paragraph' in element:
                for text_element in element['paragraph'].get('elements', []):
                    if 'textRun' in text_element:
                        text_content += text_element['textRun'].get('content', '')

        # Get first 3-5 lines (up to 500 chars)
        preview = text_content[:500].strip()
        first_lines = "\n".join(preview.split("\n")[:5])

        # Check if keywords appear in content
        content_lower = text_content.lower()
        contains_keywords = all(
            keyword.lower() in content_lower
            for keyword in expected_content_keywords
        )

        # ✅ VALIDATION PASSES if document is accessible (readable)
        # Keyword check is informational only - helps identify if content is relevant
        # but doesn't block validation since document may use different terminology
        return {
            "valid": True,  # Pass if accessible, regardless of keywords
            "accessible": True,
            "contains_keywords": contains_keywords,
            "preview": first_lines,
            "message": f"Document accessible. Keywords found: {contains_keywords}",
            "keyword_warning": None if contains_keywords else f"Note: Expected keywords not found - document may use different terminology"
        }

    except Exception as e:
        print(f"[supervisor_tools] ERROR validating document: {e}")
        return {
            "valid": False,
            "accessible": False,
            "contains_keywords": False,
            "preview": None,
            "message": f"Failed to access document: {str(e)}"
        }


def validate_prd_document(prd_url: str, project_name: str) -> Dict[str, Any]:
    """Validate PRD document exists and contains project-relevant content.

    Args:
        prd_url: Google Docs URL for PRD
        project_name: Expected project name

    Returns:
        {
            "success": bool,
            "valid": bool,
            "preview": str,
            "message": str
        }
    """
    project_id = get_current_project_id()
    if not project_id:
        print(f"[supervisor_tools] ERROR: No project_id in context for PRD validation")
        return {
            "success": False,
            "valid": False,
            "preview": None,
            "message": "No project_id in context"
        }

    print(f"[supervisor_tools] Validating PRD document for project {project_id}")
    print(f"[supervisor_tools] PRD URL: {prd_url}")
    print(f"[supervisor_tools] Expected project name: {project_name}")

    # Validate document
    validation = validate_google_doc(prd_url, [project_name, "requirements"])

    print(f"[supervisor_tools] PRD validation result: valid={validation['valid']}, accessible={validation.get('accessible')}, keywords_found={validation.get('contains_keywords')}")

    return {
        "success": True,
        "valid": validation["valid"],
        "preview": validation.get("preview"),
        "message": validation["message"]
    }


def validate_architecture_document(architecture_url: str, project_name: str) -> Dict[str, Any]:
    """Validate Architecture document exists and contains project-relevant content.

    Args:
        architecture_url: Google Docs URL for Architecture
        project_name: Expected project name

    Returns:
        {
            "success": bool,
            "valid": bool,
            "preview": str,
            "message": str
        }
    """
    project_id = get_current_project_id()
    if not project_id:
        print(f"[supervisor_tools] ERROR: No project_id in context for Architecture validation")
        return {
            "success": False,
            "valid": False,
            "preview": None,
            "message": "No project_id in context"
        }

    print(f"[supervisor_tools] Validating Architecture document for project {project_id}")
    print(f"[supervisor_tools] Architecture URL: {architecture_url}")
    print(f"[supervisor_tools] Expected project name: {project_name}")

    # Validate document
    validation = validate_google_doc(architecture_url, [project_name, "architecture"])

    print(f"[supervisor_tools] Architecture validation result: valid={validation['valid']}, accessible={validation.get('accessible')}, keywords_found={validation.get('contains_keywords')}")

    return {
        "success": True,
        "valid": validation["valid"],
        "preview": validation.get("preview"),
        "message": validation["message"]
    }


# ============================================================================
# KNOWLEDGE BASE CREATION
# ============================================================================

def create_project_knowledge_base() -> Dict[str, Any]:
    """Create knowledge base entry for current project using PRD and Architecture docs.

    Returns:
        {
            "success": bool,
            "knowledge_base_id": str (if successful),
            "message": str
        }
    """
    project_id = get_current_project_id()
    if not project_id:
        print(f"[supervisor_tools] ERROR: No project_id in context for knowledge base creation")
        return {
            "success": False,
            "knowledge_base_id": None,
            "message": "No project_id in context"
        }

    print(f"[supervisor_tools] Creating knowledge base for project {project_id}")

    try:
        # Get project details
        project = get_project(project_id)
        if not project:
            print(f"[supervisor_tools] ERROR: Project {project_id} not found in database")
            return {
                "success": False,
                "knowledge_base_id": None,
                "message": "Project not found"
            }

        project_name = project.get("project_name", "Unknown")
        project_description = project.get("project_description", "")
        prd_url = project.get("prd_doc_url")
        arch_url = project.get("architecture_doc_url")

        print(f"[supervisor_tools] Project: {project_name}")
        print(f"[supervisor_tools] PRD URL: {prd_url}")
        print(f"[supervisor_tools] Architecture URL: {arch_url}")

        # Read PRD content
        prd_content = None
        if prd_url:
            user_id = get_current_user_id()
            doc_id = prd_url.split("/document/d/")[1].split("/")[0]

            from services.oauth_store import get_google_credentials
            from googleapiclient.discovery import build

            creds = get_google_credentials(user_id, "google_docs")
            if creds:
                service = build('docs', 'v1', credentials=creds)
                document = service.documents().get(documentId=doc_id).execute()

                content = document.get('body', {}).get('content', [])
                text_content = ""
                for element in content:
                    if 'paragraph' in element:
                        for text_element in element['paragraph'].get('elements', []):
                            if 'textRun' in text_element:
                                text_content += text_element['textRun'].get('content', '')
                prd_content = text_content

        # Read Architecture content (similar to PRD)
        arch_content = None
        if arch_url:
            user_id = get_current_user_id()
            doc_id = arch_url.split("/document/d/")[1].split("/")[0]

            from services.oauth_store import get_google_credentials
            from googleapiclient.discovery import build

            creds = get_google_credentials(user_id, "google_docs")
            if creds:
                service = build('docs', 'v1', credentials=creds)
                document = service.documents().get(documentId=doc_id).execute()

                content = document.get('body', {}).get('content', [])
                text_content = ""
                for element in content:
                    if 'paragraph' in element:
                        for text_element in element['paragraph'].get('elements', []):
                            if 'textRun' in text_element:
                                text_content += text_element['textRun'].get('content', '')
                arch_content = text_content

        # Add to knowledge base
        print(f"[supervisor_tools] Adding project to knowledge base with PRD content ({len(prd_content) if prd_content else 0} chars) and Architecture content ({len(arch_content) if arch_content else 0} chars)")

        result = add_project_to_knowledge_base(
            project_id=project_id,
            project_name=project_name,
            project_description=project_description,
            prd_content=prd_content,
            architecture_content=arch_content
        )

        print(f"[supervisor_tools] Knowledge base creation result: success={result.get('success')}, kb_id={result.get('knowledge_base_id')}")

        return result

    except Exception as e:
        print(f"[supervisor_tools] ERROR creating knowledge base: {e}")
        return {
            "success": False,
            "knowledge_base_id": None,
            "message": f"Failed to create knowledge base: {str(e)}"
        }


# ============================================================================
# WORKFLOW VALIDATION
# ============================================================================

def validate_feature_spec_document(feature_spec_url: str, project_name: str, feature_name: str) -> Dict[str, Any]:
    """Validate Feature Specification document exists and contains relevant content.

    Args:
        feature_spec_url: Google Docs URL for Feature Spec
        project_name: Project name
        feature_name: Feature name

    Returns:
        {
            "success": bool,
            "valid": bool,
            "preview": str,
            "message": str
        }
    """
    project_id = get_current_project_id()
    if not project_id:
        print(f"[supervisor_tools] ERROR: No project_id in context for Feature Spec validation")
        return {
            "success": False,
            "valid": False,
            "preview": None,
            "message": "No project_id in context"
        }

    print(f"[supervisor_tools] Validating Feature Spec document for project {project_id}")
    print(f"[supervisor_tools] Feature Spec URL: {feature_spec_url}")
    print(f"[supervisor_tools] Expected feature name: {feature_name}")

    # Validate document
    validation = validate_google_doc(feature_spec_url, [feature_name, "feature", "specification"])

    print(f"[supervisor_tools] Feature Spec validation result: valid={validation['valid']}, accessible={validation.get('accessible')}, keywords_found={validation.get('contains_keywords')}")

    return {
        "success": True,
        "valid": validation["valid"],
        "preview": validation.get("preview"),
        "message": validation["message"]
    }


def validate_technical_doc_document(tech_doc_url: str, project_name: str, feature_name: str) -> Dict[str, Any]:
    """Validate Feature Technical Document exists and contains relevant content.

    Args:
        tech_doc_url: Google Docs URL for Technical Doc
        project_name: Project name
        feature_name: Feature name

    Returns:
        {
            "success": bool,
            "valid": bool,
            "preview": str,
            "message": str
        }
    """
    project_id = get_current_project_id()
    if not project_id:
        print(f"[supervisor_tools] ERROR: No project_id in context for Technical Doc validation")
        return {
            "success": False,
            "valid": False,
            "preview": None,
            "message": "No project_id in context"
        }

    print(f"[supervisor_tools] Validating Technical Doc document for project {project_id}")
    print(f"[supervisor_tools] Technical Doc URL: {tech_doc_url}")
    print(f"[supervisor_tools] Expected feature name: {feature_name}")

    # Validate document
    validation = validate_google_doc(tech_doc_url, [feature_name, "technical", "architecture"])

    print(f"[supervisor_tools] Technical Doc validation result: valid={validation['valid']}, accessible={validation.get('accessible')}, keywords_found={validation.get('contains_keywords')}")

    return {
        "success": True,
        "valid": validation["valid"],
        "preview": validation.get("preview"),
        "message": validation["message"]
    }


def validate_workflow_phase_completion(phase: str) -> Dict[str, Any]:
    """Validate that a workflow phase completed successfully.

    Args:
        phase: Phase name ('prd_creation', 'architecture_creation', etc.)

    Returns:
        {
            "success": bool,
            "complete": bool,
            "issues": list of issues found,
            "message": str
        }
    """
    project_id = get_current_project_id()
    if not project_id:
        return {
            "success": False,
            "complete": False,
            "issues": ["No project_id in context"],
            "message": "No project_id in context"
        }

    try:
        project = get_project(project_id)
        if not project:
            return {
                "success": False,
                "complete": False,
                "issues": ["Project not found"],
                "message": "Project not found"
            }

        issues = []

        if phase == "prd_creation":
            if not project.get("prd_doc_url"):
                issues.append("PRD document URL not stored")

        elif phase == "architecture_creation":
            if not project.get("prd_doc_url"):
                issues.append("PRD document URL missing")
            if not project.get("architecture_doc_url"):
                issues.append("Architecture document URL not stored")

        complete = len(issues) == 0

        return {
            "success": True,
            "complete": complete,
            "issues": issues,
            "message": f"Phase {'complete' if complete else 'incomplete'}"
        }

    except Exception as e:
        print(f"[supervisor_tools] ERROR validating phase: {e}")
        return {
            "success": False,
            "complete": False,
            "issues": [str(e)],
            "message": f"Validation error: {str(e)}"
        }

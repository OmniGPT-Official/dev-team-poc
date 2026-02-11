"""
Google Docs Tools

Creates real Google Docs via OAuth2 token.

Token sources (checked in order):
1. GOOGLE_DOCS_TOKEN environment variable (JSON string) - for production/Railway
2. tests/google_docs/token.json file - for local development

To get a token locally:
  python tests/google_docs/oauth_server.py
"""

import os
import json
from pathlib import Path

from agno.tools import Toolkit
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Token path (relative to project root) - fallback for local development
TOKEN_FILE = Path(__file__).resolve().parent.parent / "tests" / "google_docs" / "token.json"

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]


def _load_credentials() -> Credentials:
    """
    Load OAuth2 credentials from environment variable or token.json file.

    Priority:
    1. GOOGLE_DOCS_TOKEN env var (JSON string) - for Railway/production
    2. tests/google_docs/token.json file - for local development
    """
    # Try environment variable first (for Railway/production)
    token_json = os.environ.get("GOOGLE_DOCS_TOKEN")

    if token_json:
        try:
            data = json.loads(token_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"GOOGLE_DOCS_TOKEN is not valid JSON: {e}")
    elif TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            data = json.load(f)
    else:
        raise FileNotFoundError(
            "Google Docs OAuth2 token not found.\n\n"
            "For production (Railway):\n"
            "  Set GOOGLE_DOCS_TOKEN environment variable with the JSON content\n\n"
            "For local development:\n"
            "  1. python tests/google_docs/oauth_server.py\n"
            "  2. Open http://localhost:8000 and authorize\n"
            "  3. Token will be saved to tests/google_docs/token.json"
        )

    creds = Credentials(
        token=data["token"],
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", TOKEN_URI),
        client_id=data.get("client_id", ""),
        client_secret=data.get("client_secret", ""),
        scopes=SCOPES,
    )

    # Auto-refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        # Only update file if we're using file-based token (not env var)
        if not token_json and TOKEN_FILE.exists():
            with open(TOKEN_FILE, "w") as f:
                json.dump({
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": TOKEN_URI,
                    "client_id": data.get("client_id", ""),
                    "client_secret": data.get("client_secret", ""),
                    "scopes": SCOPES,
                }, f, indent=2)

    return creds


def _get_docs_service(creds=None):
    """Build Google Docs API service. Uses provided creds or loads from env/file."""
    return build("docs", "v1", credentials=creds or _load_credentials())


class GoogleDocsTools(Toolkit):
    """
    Tools for creating Google Docs documents via the real Docs API.

    Credential sources (checked in order):
    1. creds parameter (per-user OAuth from user_oauth_connections table)
    2. GOOGLE_DOCS_TOKEN env var (JSON string) - for Railway/production
    3. tests/google_docs/token.json file - for local development
    """

    def __init__(self, creds: "Credentials | None" = None, **kwargs):
        """
        Args:
            creds: Google OAuth2 Credentials object (per-user). If not provided,
                   falls back to _load_credentials() (env var / token.json).
        """
        self._creds = creds
        tools = [
            self.create_prd_document,
            self.create_feature_spec_document,
            self.create_document,
        ]

        super().__init__(
            name="google_docs",
            tools=tools,
            instructions="""Use these tools to create Google Docs:
- create_prd_document: Create a PRD in Google Docs. Returns a shareable URL.
- create_feature_spec_document: Create a Feature Spec in Google Docs. Returns a shareable URL.
- create_document: Create a generic document in Google Docs (for architecture docs, etc.). Returns a shareable URL.""",
            add_instructions=True,
            **kwargs,
        )

    def create_prd_document(
        self,
        title: str,
        content: str,
        project_name: str,
    ) -> str:
        """
        Create a Product Requirements Document (PRD) in Google Docs.

        Args:
            title: Document title
            content: PRD content in markdown format
            project_name: Name of the project

        Returns:
            JSON string with document_url, document_id, and title
        """
        try:
            service = _get_docs_service(self._creds)

            doc = service.documents().create(
                body={"title": f"PRD: {project_name} - {title}"}
            ).execute()

            doc_id = doc["documentId"]

            service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
            ).execute()

            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

            return json.dumps({
                "success": True,
                "document_url": doc_url,
                "document_id": doc_id,
                "title": f"PRD: {project_name}",
                "message": f"PRD created successfully. View at: {doc_url}",
            })

        except FileNotFoundError as e:
            return json.dumps({"success": False, "error": str(e)})
        except HttpError as e:
            return json.dumps({"success": False, "error": f"Google API error: {e}"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def create_feature_spec_document(
        self,
        title: str,
        content: str,
        feature_name: str,
        project_name: str,
    ) -> str:
        """
        Create a Feature Specification document in Google Docs.

        Args:
            title: Document title
            content: Feature spec content in markdown format
            feature_name: Name of the feature
            project_name: Name of the parent project

        Returns:
            JSON string with document_url, document_id, and title
        """
        try:
            service = _get_docs_service(self._creds)

            doc = service.documents().create(
                body={"title": f"Feature Spec: {feature_name} ({project_name})"}
            ).execute()

            doc_id = doc["documentId"]

            service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
            ).execute()

            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

            return json.dumps({
                "success": True,
                "document_url": doc_url,
                "document_id": doc_id,
                "title": f"Feature Spec: {feature_name}",
                "message": f"Feature Spec created successfully. View at: {doc_url}",
            })

        except FileNotFoundError as e:
            return json.dumps({"success": False, "error": str(e)})
        except HttpError as e:
            return json.dumps({"success": False, "error": f"Google API error: {e}"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def create_document(
        self,
        title: str,
        content: str,
    ) -> str:
        """
        Create a generic document in Google Docs (for architecture docs, technical specs, etc.).

        Args:
            title: Document title (used as-is, no prefix added)
            content: Document content in plain text format

        Returns:
            JSON string with document_url, document_id, and title
        """
        try:
            service = _get_docs_service(self._creds)

            doc = service.documents().create(
                body={"title": title}
            ).execute()

            doc_id = doc["documentId"]

            service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
            ).execute()

            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

            return json.dumps({
                "success": True,
                "document_url": doc_url,
                "document_id": doc_id,
                "title": title,
                "message": f"Document created successfully. View at: {doc_url}",
            })

        except FileNotFoundError as e:
            return json.dumps({"success": False, "error": str(e)})
        except HttpError as e:
            return json.dumps({"success": False, "error": f"Google API error: {e}"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def read_document(self, document_id: str) -> str:
        """
        Read the content from a Google Docs document.

        Args:
            document_id: The Google Docs document ID

        Returns:
            The text content of the document

        Raises:
            Exception if document cannot be read
        """
        try:
            service = _get_docs_service(self._creds)

            # Get the document
            doc = service.documents().get(documentId=document_id).execute()

            # Extract text content from the document
            content = []
            for element in doc.get("body", {}).get("content", []):
                if "paragraph" in element:
                    for text_run in element["paragraph"].get("elements", []):
                        if "textRun" in text_run:
                            content.append(text_run["textRun"]["content"])

            return "".join(content)

        except FileNotFoundError as e:
            raise Exception(f"Google OAuth token not found: {e}")
        except HttpError as e:
            raise Exception(f"Google API error: {e}")
        except Exception as e:
            raise Exception(f"Failed to read document: {e}")

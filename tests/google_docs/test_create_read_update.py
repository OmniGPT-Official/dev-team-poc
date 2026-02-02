#!/usr/bin/env python3
"""
Google Docs API Test - Create, Read, Update

Uses the OAuth2 token stored at tests/google_docs/token.json
(created by oauth_server.py) to exercise the Docs API.

Run:
    cd <project-root>
    source venv/bin/activate
    python tests/google_docs/test_create_read_update.py

Prerequisites:
    1. Start the OAuth server:   python tests/google_docs/oauth_server.py
    2. Authorize in browser:     http://localhost:8000/authorize
    3. Token is saved to:        tests/google_docs/token.json
    4. Then run this script.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ---------------------------------------------------------------------------
# Configuration - Set these in your .env file or environment variables
# ---------------------------------------------------------------------------
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError(
        "Missing Google OAuth credentials. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
    )
TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

TOKEN_FILE = Path(__file__).resolve().parent / "token.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_credentials() -> Credentials:
    """Load and auto-refresh credentials from token.json."""
    if not TOKEN_FILE.exists():
        print(f"ERROR: Token file not found: {TOKEN_FILE}")
        print()
        print("To create a token:")
        print("  1. python tests/google_docs/oauth_server.py")
        print("  2. Open http://localhost:8000/authorize")
        print("  3. Grant permissions")
        print("  4. Re-run this script")
        sys.exit(1)

    with open(TOKEN_FILE) as f:
        data = json.load(f)

    creds = Credentials(
        token=data["token"],
        refresh_token=data.get("refresh_token"),
        token_uri=TOKEN_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        print("Token expired - refreshing...")
        creds.refresh(GoogleRequest())
        with open(TOKEN_FILE, "w") as f:
            json.dump({
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": TOKEN_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scopes": SCOPES,
            }, f, indent=2)
        print("Token refreshed and saved")

    return creds


def extract_text(doc: dict) -> str:
    """Extract plain text from a Google Docs document."""
    text = ""
    for el in doc.get("body", {}).get("content", []):
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                if "textRun" in run:
                    text += run["textRun"].get("content", "")
    return text


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("  Google Docs API - Create, Read, Update Test")
    print("=" * 70)

    # Authenticate
    print("\n[Auth] Loading credentials...")
    creds = load_credentials()
    service = build("docs", "v1", credentials=creds)
    print("[Auth] Authenticated successfully")

    # -- TEST 1: Create ----------------------------------------------------
    print("\n" + "-" * 70)
    print("[TEST 1] Creating a new Google Document")
    print("-" * 70)

    title = f"Test Doc - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]
    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

    print(f"  Document ID:  {doc_id}")
    print(f"  Title:        {title}")
    print(f"  URL:          {doc_url}")

    # -- TEST 2: Read (empty) ----------------------------------------------
    print("\n" + "-" * 70)
    print("[TEST 2] Reading the empty document")
    print("-" * 70)

    doc = service.documents().get(documentId=doc_id).execute()
    text = extract_text(doc).strip()
    print(f"  Content: {text if text else '(empty)'}")

    # -- TEST 3: Update with text ------------------------------------------
    print("\n" + "-" * 70)
    print("[TEST 3] Inserting text content")
    print("-" * 70)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body_text = (
        f"Hello from Google Docs API!\n\n"
        f"Timestamp: {ts}\n\n"
        f"This document was created and updated programmatically.\n"
    )

    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertText": {"location": {"index": 1}, "text": body_text}}]},
    ).execute()
    print(f"  Inserted {len(body_text)} characters")

    # -- TEST 4: Read updated content --------------------------------------
    print("\n" + "-" * 70)
    print("[TEST 4] Reading updated document")
    print("-" * 70)

    doc = service.documents().get(documentId=doc_id).execute()
    text = extract_text(doc).strip()
    print()
    print(text)

    # -- TEST 5: Append more content ---------------------------------------
    print("\n" + "-" * 70)
    print("[TEST 5] Appending additional content")
    print("-" * 70)

    # Get current end index
    end_index = 1
    for el in doc.get("body", {}).get("content", []):
        if "endIndex" in el:
            end_index = el["endIndex"]

    append_text = (
        f"\n--- Update ---\n"
        f"Appended at: {datetime.now().strftime('%H:%M:%S')}\n"
        f"The document was successfully updated!\n"
    )

    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertText": {"location": {"index": end_index - 1}, "text": append_text}}]},
    ).execute()
    print(f"  Appended {len(append_text)} characters")

    # -- TEST 6: Final read ------------------------------------------------
    print("\n" + "-" * 70)
    print("[TEST 6] Final document content")
    print("-" * 70)

    doc = service.documents().get(documentId=doc_id).execute()
    text = extract_text(doc).strip()
    print()
    print(text)

    # -- Summary -----------------------------------------------------------
    print("\n" + "=" * 70)
    print("  ALL TESTS PASSED")
    print("=" * 70)
    print(f"  Document URL: {doc_url}")
    print(f"  Token file:   {TOKEN_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except HttpError as e:
        print(f"\nGoogle API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

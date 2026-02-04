#!/usr/bin/env python3
"""
Google OAuth Token Generator

This script helps you generate a refresh token for Gmail and Google Sheets access.
Run this ONCE to get your refresh token, then add it to .env file.
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scopes required for Gmail and Google Sheets
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/spreadsheets',
]

def get_credentials():
    """Generate OAuth credentials with refresh token."""

    print("\n" + "="*80)
    print("Google OAuth Token Generator")
    print("="*80 + "\n")

    # Get client credentials from user
    print("Enter your OAuth Client ID:")
    client_id = input("> ").strip()

    print("\nEnter your OAuth Client Secret:")
    client_secret = input("> ").strip()

    # Create client config
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    # Save to temporary file
    with open('.client_secret_temp.json', 'w') as f:
        json.dump(client_config, f)

    print("\n" + "="*80)
    print("Opening browser for authentication...")
    print("="*80 + "\n")

    # Run OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        '.client_secret_temp.json',
        scopes=SCOPES
    )

    creds = flow.run_local_server(port=0)

    print("\n" + "="*80)
    print("✅ SUCCESS! Copy these values to your .env file:")
    print("="*80 + "\n")

    print(f"GOOGLE_OAUTH_CLIENT_ID=\"{client_id}\"")
    print(f"GOOGLE_OAUTH_CLIENT_SECRET=\"{client_secret}\"")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN=\"{creds.refresh_token}\"")

    print("\n" + "="*80)
    print("Add these lines to /tmp/dev-team-poc-clean/.env")
    print("="*80 + "\n")

    # Clean up temp file
    import os
    os.remove('.client_secret_temp.json')

if __name__ == "__main__":
    try:
        get_credentials()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you:")
        print("1. Enabled Gmail API and Google Sheets API")
        print("2. Created OAuth Desktop credentials")
        print("3. Entered the correct Client ID and Secret")

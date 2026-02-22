"""
Standalone script to decrypt access and refresh tokens from a JSON file.
Uses AES-256-GCM decryption matching the project's token_decryption.py logic.

Usage:
    python decrypt_tokens.py <path_to_json_file>

Requires:
    pip install cryptography
"""

import os
import sys
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "")


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token in iv:authTag:encryptedData hex format using AES-256-GCM."""
    if not encrypted_token or ":" not in encrypted_token:
        return encrypted_token

    if not ENCRYPTION_KEY or len(ENCRYPTION_KEY) != 64:
        raise ValueError("TOKEN_ENCRYPTION_KEY must be a 64-character hex string (32 bytes)")

    parts = encrypted_token.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid token format: expected 3 parts, got {len(parts)}")

    iv_hex, auth_tag_hex, encrypted_hex = parts

    iv = bytes.fromhex(iv_hex)
    auth_tag = bytes.fromhex(auth_tag_hex)
    encrypted_data = bytes.fromhex(encrypted_hex)

    key_bytes = bytes.fromhex(ENCRYPTION_KEY)
    aesgcm = AESGCM(key_bytes)

    decrypted_bytes = aesgcm.decrypt(iv, encrypted_data + auth_tag, None)
    return decrypted_bytes.decode("utf-8")


def main():
    if len(sys.argv) < 2:
        print("Usage: python decrypt_token_script.py <path_to_json_file>")
        sys.exit(1)

    json_file = sys.argv[1]

    with open(json_file, "r") as f:
        data = json.load(f)

    # Handle both a single tool object, a list of tools, or a dict with "tools" key
    if isinstance(data, dict) and "tools" in data:
        tools = data["tools"]
    elif isinstance(data, list):
        tools = data
    else:
        tools = [data]

    for tool in tools:
        name = tool.get("connection_name", tool.get("name", "Unknown"))
        print(f"\n{'='*60}")
        print(f"Tool: {name}")
        print(f"{'='*60}")

        # Root-level tokens
        for key in ("access_token", "refresh_token"):
            if tool.get(key):
                try:
                    decrypted = decrypt_token(tool[key])
                    print(f"\n{key.upper().replace('_', ' ')}:")
                    print(decrypted)
                except Exception as e:
                    print(f"\n{key.upper().replace('_', ' ')}: FAILED - {e}")

        # Callback metadata tokens and scope
        callback = tool.get("callback_metadata", {})
        if callback:
            # Display scope first
            if callback.get("scope"):
                print(f"\nSCOPES:")
                scopes = callback["scope"].split()
                for scope in scopes:
                    print(f"  - {scope}")

            # Decrypt tokens
            for key in ("access_token", "refresh_token"):
                if callback.get(key):
                    try:
                        decrypted = decrypt_token(callback[key])
                        print(f"\nCALLBACK {key.upper().replace('_', ' ')}:")
                        print(decrypted)
                    except Exception as e:
                        print(f"\nCALLBACK {key.upper().replace('_', ' ')}: FAILED - {e}")


if __name__ == "__main__":
    main()
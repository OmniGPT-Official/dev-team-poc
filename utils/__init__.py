"""
Agent-OS Utilities Package

This package provides utility modules for the Agent-OS system.

Main components:
- SmartGitHubMCP: Drop-in replacement for MCPTools with caching and smart fetching
- GitHubMCPWrapper: Lower-level wrapper for custom integrations
- EmailTracker: Duplicate prevention for email sending
"""

# Smart MCP wrapper (recommended for agents)
from utils.smart_github_mcp import (
    SmartGitHubMCP,
    create_smart_github_mcp,
    PolicyConfig as MCPPolicyConfig,
    PRESET_POLICIES,
    FetchPolicy,
    Cache,
    ContentProcessor,
)

# Lower-level wrapper (for custom integrations)
from utils.github_mcp_wrapper import (
    GitHubMCPWrapper,
    PolicyConfig,
    POLICIES,
    create_wrapper,
    smart_fetch_file,
    GitHubMCPError,
)

# Email tracker for duplicate prevention
from utils.email_tracker import (
    mark_email_sent,
    check_email_sent,
    get_sent_count,
    get_sent_list,
    reset_tracker,
)

__all__ = [
    # Smart MCP (recommended)
    "SmartGitHubMCP",
    "create_smart_github_mcp",
    "MCPPolicyConfig",
    "PRESET_POLICIES",
    "FetchPolicy",
    "Cache",
    "ContentProcessor",
    # Lower-level wrapper
    "GitHubMCPWrapper",
    "PolicyConfig",
    "POLICIES",
    "create_wrapper",
    "smart_fetch_file",
    "GitHubMCPError",
    # Email tracker
    "mark_email_sent",
    "check_email_sent",
    "get_sent_count",
    "get_sent_list",
    "reset_tracker",
]

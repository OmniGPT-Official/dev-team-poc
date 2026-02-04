"""
Smart GitHub MCP - A wrapper for MCPTools with policy-based fetching and caching.

This module provides a drop-in replacement for MCPTools that:
1. Intercepts GitHub API calls and applies smart policies
2. Caches responses to reduce API calls and tokens
3. Truncates large files intelligently
4. Provides batch operations

Usage:
    from utils.smart_github_mcp import SmartGitHubMCP

    # Replace this:
    # github_mcp = MCPTools(command="npx -y @modelcontextprotocol/server-github", ...)

    # With this:
    github_mcp = SmartGitHubMCP(
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        policy="code_review",  # or "quick_check", "full_read", "minimal"
    )

    # Use as normal in agent tools
    agent = Agent(tools=[github_mcp, ...])
"""

import os
import json
import hashlib
import time
import base64
import asyncio
import re
import threading
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import OrderedDict

from agno.tools.mcp import MCPTools

logger = logging.getLogger(__name__)
from agno.tools.toolkit import Toolkit
from agno.tools.function import Function


# =============================================================================
# CONFIGURATION & POLICIES
# =============================================================================

class FetchPolicy(Enum):
    FULL = "full"
    SMART = "smart"
    MINIMAL = "minimal"
    METADATA_ONLY = "metadata_only"


@dataclass
class PolicyConfig:
    """Configuration for fetch policies."""
    name: str = "default"
    max_tokens: int = 4000
    max_chars: int = 16000
    max_file_size: int = 100_000  # 100KB
    max_lines: int = 500
    head_lines: int = 100
    tail_lines: int = 50
    context_lines: int = 10
    cache_ttl_seconds: int = 300
    max_cache_entries: int = 100
    include_imports: bool = True
    include_signatures: bool = True


# Preset policies
PRESET_POLICIES = {
    "code_review": PolicyConfig(
        name="code_review",
        max_tokens=8000,
        max_chars=32000,
        max_lines=800,
    ),
    "quick_check": PolicyConfig(
        name="quick_check",
        max_tokens=1000,
        max_chars=4000,
        max_lines=100,
        head_lines=50,
        tail_lines=20,
    ),
    "full_read": PolicyConfig(
        name="full_read",
        max_tokens=16000,
        max_chars=64000,
        max_lines=2000,
    ),
    "minimal": PolicyConfig(
        name="minimal",
        max_tokens=500,
        max_chars=2000,
        max_lines=0,
        head_lines=30,
        tail_lines=10,
    ),
}


# =============================================================================
# CACHE IMPLEMENTATION
# =============================================================================

@dataclass
class CacheEntry:
    value: Any
    created_at: float
    ttl: int
    sha: Optional[str] = None
    size: int = 0

    def is_valid(self, sha: Optional[str] = None) -> bool:
        if time.time() - self.created_at > self.ttl:
            return False
        if sha and self.sha and sha != self.sha:
            return False
        return True


class Cache:
    """LRU cache with TTL."""

    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def key(self, *args, **kwargs) -> str:
        """Generate cache key."""
        parts = [str(a) for a in args]
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.md5(":".join(parts).encode()).hexdigest()

    def get(self, key: str, sha: Optional[str] = None) -> Optional[Any]:
        if key not in self._cache:
            self.misses += 1
            return None

        entry = self._cache[key]
        if not entry.is_valid(sha):
            del self._cache[key]
            self.misses += 1
            return None

        self._cache.move_to_end(key)
        self.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None, sha: Optional[str] = None, size: int = 0):
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

        self._cache[key] = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl=ttl or self._default_ttl,
            sha=sha,
            size=size,
        )

    def invalidate(self, pattern: Optional[str] = None) -> int:
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            return count
        keys = [k for k in self._cache if pattern in k]
        for k in keys:
            del self._cache[k]
        return len(keys)

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {
            "entries": len(self._cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{(self.hits / total * 100):.1f}%" if total > 0 else "0%",
            "total_bytes": sum(e.size for e in self._cache.values()),
        }


# =============================================================================
# CONTENT PROCESSOR
# =============================================================================

class ContentProcessor:
    """Process and truncate content intelligently."""

    IMPORT_PATTERNS = [
        r'^import\s+', r'^from\s+\w+\s+import',  # Python
        r'^const\s+.*=\s*require', r'^import\s+.*from',  # JS/TS
        r'^use\s+', r'^#include',  # Rust/C
        r'^package\s+', r'^import\s+"',  # Go/Java
    ]

    SIGNATURE_PATTERNS = {
        'py': [r'^class\s+\w+', r'^def\s+\w+', r'^async\s+def\s+\w+'],
        'js': [r'^class\s+\w+', r'^function\s+\w+', r'^const\s+\w+\s*=\s*\('],
        'ts': [r'^class\s+\w+', r'^function\s+\w+', r'^interface\s+\w+', r'^type\s+\w+'],
        'tsx': [r'^class\s+\w+', r'^function\s+\w+', r'^interface\s+\w+'],
        'go': [r'^func\s+', r'^type\s+\w+\s+struct'],
        'rs': [r'^fn\s+', r'^struct\s+', r'^impl\s+'],
        'java': [r'^public\s+class', r'^private\s+class'],
    }

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return len(text) // 4

    @classmethod
    def smart_truncate(
        cls,
        content: str,
        config: PolicyConfig,
        file_path: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Intelligently truncate content."""
        lines = content.split('\n')
        total_lines = len(lines)
        total_chars = len(content)

        metadata = {
            "original_lines": total_lines,
            "original_chars": total_chars,
            "original_tokens": cls.estimate_tokens(content),
            "truncated": False,
        }

        # No truncation needed
        if total_chars <= config.max_chars and total_lines <= config.max_lines:
            return content, metadata

        metadata["truncated"] = True
        result_parts = []

        # Get file extension
        ext = file_path.split('.')[-1] if file_path and '.' in file_path else ""

        # 1. Extract imports (always keep at top)
        if config.include_imports:
            imports = cls._extract_imports(lines)
            if imports:
                result_parts.append("# === IMPORTS ===")
                result_parts.extend(imports)
                result_parts.append("")

        # 2. Extract class/function signatures
        if config.include_signatures and ext in cls.SIGNATURE_PATTERNS:
            signatures = cls._extract_signatures(lines, ext)
            if signatures and len('\n'.join(signatures)) < config.max_chars * 0.2:
                result_parts.append("# === SIGNATURES ===")
                result_parts.extend(signatures)
                result_parts.append("")

        # 3. Calculate remaining budget
        current_size = len('\n'.join(result_parts))
        remaining = config.max_chars - current_size

        # 4. Add head content (60% of remaining)
        head_budget = int(remaining * 0.6)
        head_lines = []
        char_count = 0
        start_idx = 0

        # Skip lines already in imports
        import_count = len([l for l in result_parts if l and not l.startswith("#")])
        for line in lines[import_count:]:
            if char_count + len(line) + 1 > head_budget:
                break
            head_lines.append(line)
            char_count += len(line) + 1

        if head_lines:
            result_parts.append("# === CONTENT START ===")
            result_parts.extend(head_lines)

        # 5. Add truncation marker
        lines_in_result = len([l for l in result_parts if l and not l.startswith("#")])
        remaining_lines = total_lines - lines_in_result - config.tail_lines
        if remaining_lines > 0:
            result_parts.append(f"\n... [{remaining_lines} lines truncated] ...\n")

        # 6. Add tail content (40% of remaining)
        tail_budget = int(remaining * 0.4)
        tail_lines = []
        char_count = 0
        for line in reversed(lines[-config.tail_lines:]):
            if char_count + len(line) + 1 > tail_budget:
                break
            tail_lines.insert(0, line)
            char_count += len(line) + 1

        if tail_lines:
            result_parts.append("# === CONTENT END ===")
            result_parts.extend(tail_lines)

        result = '\n'.join(result_parts)
        metadata["result_lines"] = result.count('\n') + 1
        metadata["result_chars"] = len(result)
        metadata["result_tokens"] = cls.estimate_tokens(result)
        metadata["tokens_saved"] = metadata["original_tokens"] - metadata["result_tokens"]

        return result, metadata

    @classmethod
    def _extract_imports(cls, lines: List[str], max_lines: int = 50) -> List[str]:
        imports = []
        for line in lines[:max_lines]:
            stripped = line.strip()
            if any(re.match(p, stripped) for p in cls.IMPORT_PATTERNS):
                imports.append(line)
            elif imports and stripped == "":
                imports.append(line)
            elif imports and not stripped.startswith("#") and not stripped.startswith("//"):
                break
        return imports

    @classmethod
    def _extract_signatures(cls, lines: List[str], ext: str) -> List[str]:
        patterns = cls.SIGNATURE_PATTERNS.get(ext, [])
        signatures = []
        for line in lines:
            stripped = line.strip()
            if any(re.match(p, stripped) for p in patterns):
                signatures.append(line)
        return signatures[:20]

    @staticmethod
    def extract_line_range(
        content: str,
        start: int,
        end: int,
        context: int = 5
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract specific line range with context."""
        lines = content.split('\n')
        total = len(lines)

        start_idx = max(0, start - 1 - context)
        end_idx = min(total, end + context)

        result = []
        for i, line in enumerate(lines[start_idx:end_idx], start=start_idx + 1):
            marker = ">>>" if start <= i <= end else "   "
            result.append(f"{marker} {i:4d} | {line}")

        return '\n'.join(result), {
            "range": (start, end),
            "with_context": (start_idx + 1, end_idx),
            "total_lines": total,
        }


# =============================================================================
# SMART GITHUB MCP WRAPPER
# =============================================================================

class SmartGitHubMCP(Toolkit):
    """
    Smart GitHub MCP wrapper with caching and policy-based fetching.

    This is a drop-in replacement for MCPTools that adds:
    - Intelligent content truncation to save tokens
    - LRU caching with TTL
    - Batch operations
    - Statistics tracking
    """

    def __init__(
        self,
        github_token: Optional[str] = None,
        policy: str = "code_review",
        custom_policy: Optional[PolicyConfig] = None,
        enable_cache: bool = True,
        cache_ttl: int = 300,
        max_cache_entries: int = 100,
        timeout_seconds: int = 60,
    ):
        super().__init__(name="smart_github_mcp")

        # Check multiple env var names for GitHub token
        self.token = github_token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
        self.policy = custom_policy or PRESET_POLICIES.get(policy, PRESET_POLICIES["code_review"])
        self.cache = Cache(max_cache_entries, cache_ttl) if enable_cache else None
        self.processor = ContentProcessor()
        self.timeout = timeout_seconds

        # Log token status (masked for security)
        if self.token:
            logger.info(f"SmartGitHubMCP initialized with token: {self.token[:4]}...{self.token[-4:]}")
        else:
            logger.warning("SmartGitHubMCP initialized WITHOUT GitHub token - API calls will fail!")

        # Initialize underlying MCP
        self._mcp = MCPTools(
            command="npx -y @modelcontextprotocol/server-github",
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": self.token},
            timeout_seconds=timeout_seconds,
        )

        # Stats
        self._stats = {
            "api_calls": 0,
            "cache_hits": 0,
            "bytes_fetched": 0,
            "bytes_returned": 0,
            "tokens_saved": 0,
        }

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register wrapped tool functions."""
        # Smart file fetching
        self.register(Function(
            name="get_file_contents",
            description="""Get file contents from a GitHub repository with smart truncation.

Parameters:
- owner: Repository owner (user or org)
- repo: Repository name
- path: File path in repository
- branch: (optional) Branch name, defaults to main
- start_line: (optional) Start line for partial fetch
- end_line: (optional) End line for partial fetch
- fetch_mode: (optional) "smart" (default), "full", "minimal", or "metadata"

Returns file content optimized for token efficiency.""",
            entrypoint=self.get_file_contents,
        ))

        # Repository check with caching
        self.register(Function(
            name="get_repository",
            description="""Check if a repository exists.

Parameters:
- owner: Repository owner
- repo: Repository name

Returns repository info if exists, error if not.""",
            entrypoint=self.get_repository,
        ))

        # File creation/update
        self.register(Function(
            name="create_or_update_file",
            description="""Create or update a file in a GitHub repository.

Parameters:
- owner: Repository owner
- repo: Repository name
- path: File path
- content: File content
- message: Commit message
- branch: (optional) Branch name
- sha: (optional) SHA of file being replaced (for updates)

Automatically handles SHA retrieval for updates.""",
            entrypoint=self.create_or_update_file,
        ))

        # Repository creation
        self.register(Function(
            name="create_repository",
            description="""Create a new GitHub repository.

Parameters:
- name: Repository name
- description: (optional) Repository description
- private: (optional) Whether repo is private (default: false)

Returns created repository info.""",
            entrypoint=self.create_repository,
        ))

        # Batch file fetch
        self.register(Function(
            name="batch_get_files",
            description="""Fetch multiple files in a single operation.

Parameters:
- owner: Repository owner
- repo: Repository name
- paths: List of file paths to fetch
- fetch_mode: (optional) "smart", "minimal", or "metadata"

Returns dict mapping paths to contents.""",
            entrypoint=self.batch_get_files,
        ))

        # Search with smart content
        self.register(Function(
            name="search_code",
            description="""Search code in a repository.

Parameters:
- owner: Repository owner
- repo: Repository name
- query: Search query
- max_results: (optional) Max results to return (default: 5)

Returns matching files with relevant snippets.""",
            entrypoint=self.search_code,
        ))

        # List repository contents
        self.register(Function(
            name="list_repository_contents",
            description="""List files and directories in a GitHub repository path.

Parameters:
- owner: Repository owner
- repo: Repository name
- path: (optional) Directory path, defaults to root ""
- branch: (optional) Branch name, defaults to main

Returns list of files and directories at the specified path.""",
            entrypoint=self.list_repository_contents,
        ))

        # Cache management
        self.register(Function(
            name="cache_stats",
            description="Get cache statistics and performance metrics.",
            entrypoint=self.get_cache_stats,
        ))

        self.register(Function(
            name="invalidate_cache",
            description="""Invalidate cached data.

Parameters:
- pattern: (optional) Pattern to match (invalidates all if not provided)

Use after making changes to ensure fresh data.""",
            entrypoint=self.invalidate_cache,
        ))

    async def _call_mcp_async(self, tool_name: str, **kwargs) -> Any:
        """Call underlying MCP tool (async implementation)."""
        self._stats["api_calls"] += 1
        logger.debug(f"Calling MCP tool: {tool_name} with kwargs: {list(kwargs.keys())}")

        # Use the MCP tools context manager
        async with self._mcp:
            # Get the tool and call it
            tools = self._mcp.functions
            logger.debug(f"Available MCP tools: {[t.name for t in tools]}")
            for tool in tools:
                if tool.name == tool_name:
                    result = await tool.aentrypoint(**kwargs)
                    logger.debug(f"MCP tool {tool_name} returned successfully")
                    return result

        raise ValueError(f"Tool '{tool_name}' not found in MCP. Available: {[t.name for t in self._mcp.functions]}")

    def _call_mcp_sync(self, tool_name: str, **kwargs) -> Any:
        """Call MCP tool synchronously using a fresh event loop in a dedicated thread."""
        result = None
        exception = None

        def run_in_thread():
            nonlocal result, exception
            try:
                # Create a completely new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(self._call_mcp_async(tool_name, **kwargs))
                finally:
                    # Clean up properly
                    try:
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    except Exception:
                        pass
                    loop.close()
            except Exception as e:
                logger.error(f"MCP call to {tool_name} failed: {e}")
                exception = e

        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=self.timeout)

        if thread.is_alive():
            logger.error(f"MCP call to {tool_name} timed out after {self.timeout}s")
            raise TimeoutError(f"MCP call to {tool_name} timed out after {self.timeout}s")

        if exception:
            logger.error(f"MCP call to {tool_name} raised exception: {exception}")
            raise exception

        return result

    def get_file_contents(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        fetch_mode: str = "smart",
    ) -> str:
        """Get file contents with smart truncation and caching."""
        cache_key = f"file:{owner}/{repo}/{path}:{branch or 'main'}"

        # Check cache
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._stats["cache_hits"] += 1
                content = cached["content"]

                # Apply mode to cached content
                if start_line and end_line:
                    result, _ = self.processor.extract_line_range(content, start_line, end_line)
                    return f"[CACHED] Lines {start_line}-{end_line} of {path}:\n\n{result}"
                elif fetch_mode == "smart":
                    result, meta = self.processor.smart_truncate(content, self.policy, path)
                    if meta["truncated"]:
                        return f"[CACHED] {path} (truncated: {meta['tokens_saved']} tokens saved):\n\n{result}"
                    return f"[CACHED] {path}:\n\n{result}"
                elif fetch_mode == "minimal":
                    lines = content.split('\n')
                    head = '\n'.join(lines[:self.policy.head_lines])
                    tail = '\n'.join(lines[-self.policy.tail_lines:])
                    return f"[CACHED] {path} (minimal - {len(lines)} total lines):\n\nHEAD:\n{head}\n\n...\n\nTAIL:\n{tail}"
                elif fetch_mode == "metadata":
                    lines = content.split('\n')
                    return f"[CACHED] {path}: {len(lines)} lines, {len(content)} chars"
                return f"[CACHED] {path}:\n\n{content}"

        # Fetch from GitHub
        try:
            kwargs = {"owner": owner, "repo": repo, "path": path}
            if branch:
                kwargs["branch"] = branch
            result = self._call_mcp_sync("get_file_contents", **kwargs)

            # Parse response
            content = self._extract_content(result)
            sha = self._extract_sha(result)

            if content is None:
                return f"Error: Could not fetch {path}"

            self._stats["bytes_fetched"] += len(content)

            # Cache full content
            if self.cache:
                self.cache.set(cache_key, {"content": content, "sha": sha}, sha=sha, size=len(content))

            # Apply fetch mode
            if start_line and end_line:
                result, _ = self.processor.extract_line_range(content, start_line, end_line)
                return f"Lines {start_line}-{end_line} of {path}:\n\n{result}"
            elif fetch_mode == "smart":
                result, meta = self.processor.smart_truncate(content, self.policy, path)
                self._stats["bytes_returned"] += len(result)
                self._stats["tokens_saved"] += meta.get("tokens_saved", 0)
                if meta["truncated"]:
                    return f"{path} (truncated: {meta['tokens_saved']} tokens saved):\n\n{result}"
                return f"{path}:\n\n{result}"
            elif fetch_mode == "minimal":
                lines = content.split('\n')
                head = '\n'.join(lines[:self.policy.head_lines])
                tail = '\n'.join(lines[-self.policy.tail_lines:])
                return f"{path} (minimal - {len(lines)} total lines):\n\nHEAD:\n{head}\n\n...\n\nTAIL:\n{tail}"
            elif fetch_mode == "metadata":
                lines = content.split('\n')
                return f"{path}: {len(lines)} lines, {len(content)} chars"

            self._stats["bytes_returned"] += len(content)
            return f"{path}:\n\n{content}"

        except Exception as e:
            return f"Error fetching {path}: {str(e)}"

    def _extract_content(self, response: Any) -> Optional[str]:
        """Extract content from MCP response."""
        if isinstance(response, str):
            # Try to decode if base64
            try:
                return base64.b64decode(response).decode('utf-8')
            except Exception:
                return response
        if isinstance(response, dict):
            content = response.get("content") or response.get("text") or response.get("data")
            if content:
                try:
                    return base64.b64decode(content).decode('utf-8')
                except Exception:
                    return content
        if hasattr(response, 'content'):
            return response.content
        return str(response) if response else None

    def _extract_sha(self, response: Any) -> Optional[str]:
        """Extract SHA from response."""
        if isinstance(response, dict):
            return response.get("sha")
        if hasattr(response, 'sha'):
            return response.sha
        return None

    def get_repository(self, owner: str, repo: str) -> str:
        """Check repository existence with caching."""
        cache_key = f"repo:{owner}/{repo}"

        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._stats["cache_hits"] += 1
                return f"[CACHED] Repository {owner}/{repo} exists"

        try:
            result = self._call_mcp_sync("get_repository", owner=owner, repo=repo)

            if self.cache:
                self.cache.set(cache_key, {"exists": True}, ttl=600)

            return f"Repository {owner}/{repo} exists. Info: {json.dumps(result, indent=2) if isinstance(result, dict) else result}"

        except Exception as e:
            error_str = str(e).lower()
            if "404" in error_str or "not found" in error_str:
                return f"Repository {owner}/{repo} does NOT exist (404)"
            return f"Error checking repository: {str(e)}"

    def list_repository_contents(
        self,
        owner: str,
        repo: str,
        path: str = "",
        branch: Optional[str] = None,
    ) -> str:
        """List files and directories at a path in the repository."""
        cache_key = f"contents:{owner}/{repo}/{path}:{branch or 'main'}"

        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._stats["cache_hits"] += 1
                return f"[CACHED] Contents of {owner}/{repo}/{path or '/'}:\n{cached}"

        try:
            kwargs = {"owner": owner, "repo": repo, "path": path}
            if branch:
                kwargs["branch"] = branch
            result = self._call_mcp_sync("get_file_contents", **kwargs)

            # Format the result
            if isinstance(result, list):
                items = []
                for item in result:
                    item_type = item.get("type", "file")
                    item_name = item.get("name", "unknown")
                    icon = "📁" if item_type == "dir" else "📄"
                    items.append(f"  {icon} {item_name}")
                output = '\n'.join(items)
            else:
                output = str(result)

            if self.cache:
                self.cache.set(cache_key, output, ttl=300)

            return f"Contents of {owner}/{repo}/{path or '/'}:\n{output}"

        except Exception as e:
            return f"Error listing contents: {str(e)}"

    def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
        sha: Optional[str] = None,
    ) -> str:
        """Create or update file with automatic SHA handling."""
        # Try to get SHA from cache if not provided
        if not sha and self.cache:
            cache_key = f"file:{owner}/{repo}/{path}:{branch or 'main'}"
            cached = self.cache.get(cache_key)
            if cached:
                sha = cached.get("sha")

        try:
            kwargs = {
                "owner": owner,
                "repo": repo,
                "path": path,
                "content": content,
                "message": message,
            }
            if branch:
                kwargs["branch"] = branch
            if sha:
                kwargs["sha"] = sha
            result = self._call_mcp_sync("create_or_update_file", **kwargs)

            # Invalidate cache
            if self.cache:
                self.cache.invalidate(f"file:{owner}/{repo}/{path}")

            return f"Successfully saved {path}. Commit: {message}"

        except Exception as e:
            return f"Error saving {path}: {str(e)}"

    def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = False,
    ) -> str:
        """Create a new repository."""
        try:
            kwargs = {"name": name}
            if description:
                kwargs["description"] = description
            kwargs["private"] = private
            result = self._call_mcp_sync("create_repository", **kwargs)
            return f"Repository {name} created successfully"

        except Exception as e:
            return f"Error creating repository: {str(e)}"

    def batch_get_files(
        self,
        owner: str,
        repo: str,
        paths: List[str],
        fetch_mode: str = "smart",
    ) -> str:
        """Fetch multiple files efficiently."""
        results = []
        for path in paths:
            content = self.get_file_contents(owner, repo, path, fetch_mode=fetch_mode)
            results.append(f"### {path}\n{content}\n")

        return "\n---\n".join(results)

    def search_code(
        self,
        owner: str,
        repo: str,
        query: str,
        max_results: int = 5,
    ) -> str:
        """Search code with smart content extraction."""
        try:
            result = self._call_mcp_sync(
                "search_code",
                owner=owner,
                repo=repo,
                query=query,
            )

            # Parse results
            items = result if isinstance(result, list) else result.get("items", [])
            items = items[:max_results]

            output = [f"Search results for '{query}' in {owner}/{repo}:\n"]
            for item in items:
                path = item.get("path", "unknown")
                output.append(f"- {path}")

            return '\n'.join(output)

        except Exception as e:
            return f"Search error: {str(e)}"

    def get_cache_stats(self) -> str:
        """Get cache and performance statistics."""
        stats = {
            "api_calls": self._stats["api_calls"],
            "cache_hits": self._stats["cache_hits"],
            "bytes_fetched": f"{self._stats['bytes_fetched']:,}",
            "bytes_returned": f"{self._stats['bytes_returned']:,}",
            "tokens_saved": f"{self._stats['tokens_saved']:,}",
        }

        if self.cache:
            stats["cache"] = self.cache.stats()

        return json.dumps(stats, indent=2)

    def invalidate_cache(self, pattern: Optional[str] = None) -> str:
        """Invalidate cache entries."""
        if self.cache:
            count = self.cache.invalidate(pattern)
            return f"Invalidated {count} cache entries"
        return "Cache not enabled"


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_smart_github_mcp(
    policy: str = "code_review",
    enable_cache: bool = True,
    github_token: Optional[str] = None,
) -> SmartGitHubMCP:
    """
    Factory function to create SmartGitHubMCP.

    Args:
        policy: One of "code_review", "quick_check", "full_read", "minimal"
        enable_cache: Whether to enable caching
        github_token: GitHub token (defaults to GITHUB_TOKEN env var)

    Returns:
        Configured SmartGitHubMCP instance
    """
    return SmartGitHubMCP(
        github_token=github_token,
        policy=policy,
        enable_cache=enable_cache,
    )

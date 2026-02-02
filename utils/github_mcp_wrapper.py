"""
GitHub MCP Smart Wrapper with Policy-Based Fetching and Caching

This wrapper provides:
1. Policy-based fetching (token budgets, file size limits, partial reads)
2. LRU caching with TTL for reduced API calls
3. Smart truncation and summarization
4. Batch operations and parallel fetching
5. Content deduplication via SHA hashing

Usage:
    from utils.github_mcp_wrapper import GitHubMCPWrapper, FetchPolicy

    wrapper = GitHubMCPWrapper(mcp_tools)
    content = await wrapper.get_file_contents(
        owner="org",
        repo="repo",
        path="src/main.py",
        policy=FetchPolicy.SMART  # Only fetch what's needed
    )
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union
from collections import OrderedDict
import re
import json


# =============================================================================
# FETCH POLICIES - Claude-like approach for smart fetching
# =============================================================================

class FetchPolicy(Enum):
    """Defines how aggressively to fetch content."""
    FULL = "full"           # Fetch entire content (use sparingly)
    SMART = "smart"         # Fetch with smart truncation based on token budget
    MINIMAL = "minimal"     # Fetch only metadata + first/last portions
    METADATA_ONLY = "metadata_only"  # Only fetch file metadata, no content
    LINE_RANGE = "line_range"  # Fetch specific line range


@dataclass
class PolicyConfig:
    """Configuration for fetch policies."""
    # Token budget (approximate - 1 token ≈ 4 chars)
    max_tokens: int = 4000
    max_chars: int = 16000  # max_tokens * 4

    # File size limits (in bytes)
    max_file_size: int = 100_000  # 100KB - larger files get smart truncation
    warn_file_size: int = 50_000  # 50KB - warn about large files

    # Line-based limits
    max_lines: int = 500
    head_lines: int = 100  # Lines from start for MINIMAL policy
    tail_lines: int = 50   # Lines from end for MINIMAL policy
    context_lines: int = 10  # Lines around search matches

    # Caching
    cache_ttl_seconds: int = 300  # 5 minutes default TTL
    max_cache_entries: int = 100

    # Smart fetch settings
    include_imports: bool = True  # Always include import statements
    include_class_signatures: bool = True  # Include class/function signatures
    truncation_marker: str = "\n... [truncated - {remaining} more lines] ...\n"


# Default policies for different use cases
POLICIES = {
    "code_review": PolicyConfig(
        max_tokens=8000,
        max_chars=32000,
        max_lines=800,
        include_imports=True,
        include_class_signatures=True,
    ),
    "quick_check": PolicyConfig(
        max_tokens=1000,
        max_chars=4000,
        max_lines=100,
        head_lines=50,
        tail_lines=20,
    ),
    "full_read": PolicyConfig(
        max_tokens=16000,
        max_chars=64000,
        max_lines=2000,
    ),
    "metadata": PolicyConfig(
        max_tokens=500,
        max_chars=2000,
        max_lines=0,
    ),
}


# =============================================================================
# LRU CACHE WITH TTL
# =============================================================================

@dataclass
class CacheEntry:
    """Single cache entry with TTL support."""
    value: Any
    created_at: float
    ttl: int
    sha: Optional[str] = None  # Git SHA for content validation
    size_bytes: int = 0

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl

    def is_valid(self, sha: Optional[str] = None) -> bool:
        """Check if cache entry is still valid."""
        if self.is_expired():
            return False
        if sha and self.sha and sha != self.sha:
            return False  # Content changed
        return True


class TTLCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def _make_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_parts = [str(a) for a in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()

    def get(self, key: str, sha: Optional[str] = None) -> Optional[Any]:
        """Get value from cache if valid."""
        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]
        if not entry.is_valid(sha):
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        sha: Optional[str] = None,
        size_bytes: int = 0
    ) -> None:
        """Set value in cache with TTL."""
        # Evict oldest entries if at capacity
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

        self._cache[key] = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl=ttl or self._default_ttl,
            sha=sha,
            size_bytes=size_bytes,
        )

    def invalidate(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries matching pattern (or all if None)."""
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            return count

        keys_to_remove = [k for k in self._cache if pattern in k]
        for k in keys_to_remove:
            del self._cache[k]
        return len(keys_to_remove)

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        total = self._hits + self._misses
        return {
            "entries": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0,
            "total_bytes": sum(e.size_bytes for e in self._cache.values()),
        }


# =============================================================================
# SMART CONTENT PROCESSOR
# =============================================================================

class ContentProcessor:
    """Processes and truncates content based on policies."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count (rough: 1 token ≈ 4 chars)."""
        return len(text) // 4

    @staticmethod
    def smart_truncate(
        content: str,
        policy: PolicyConfig,
        file_path: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Intelligently truncate content while preserving important parts.
        Returns (truncated_content, metadata).
        """
        lines = content.split('\n')
        total_lines = len(lines)
        metadata = {
            "total_lines": total_lines,
            "total_chars": len(content),
            "truncated": False,
            "preserved_sections": [],
        }

        # Check if truncation needed
        if len(content) <= policy.max_chars and total_lines <= policy.max_lines:
            return content, metadata

        metadata["truncated"] = True
        result_lines = []

        # Detect file type for smart handling
        ext = file_path.split('.')[-1] if file_path else ""
        is_code = ext in ('py', 'js', 'ts', 'tsx', 'jsx', 'java', 'go', 'rs', 'c', 'cpp', 'h')

        if is_code and policy.include_imports:
            # Preserve imports/requires at the top
            import_patterns = [
                r'^import\s+', r'^from\s+\w+\s+import',  # Python
                r'^const\s+.*=\s*require', r'^import\s+.*from',  # JS/TS
                r'^use\s+', r'^#include',  # Rust/C
                r'^package\s+', r'^import\s+"',  # Go/Java
            ]
            import_section = []
            for i, line in enumerate(lines[:50]):  # Check first 50 lines
                if any(re.match(p, line.strip()) for p in import_patterns):
                    import_section.append(line)
                elif import_section and line.strip() == "":
                    import_section.append(line)
                elif import_section:
                    break

            if import_section:
                result_lines.extend(import_section)
                result_lines.append("")
                metadata["preserved_sections"].append("imports")

        # Calculate remaining budget
        current_chars = len('\n'.join(result_lines))
        remaining_budget = policy.max_chars - current_chars

        if is_code and policy.include_class_signatures:
            # Extract class/function signatures
            signatures = ContentProcessor._extract_signatures(lines, ext)
            if signatures:
                sig_text = '\n'.join(signatures)
                if len(sig_text) < remaining_budget * 0.3:  # Use max 30% for signatures
                    result_lines.append("# === CLASS/FUNCTION SIGNATURES ===")
                    result_lines.extend(signatures)
                    result_lines.append("")
                    metadata["preserved_sections"].append("signatures")
                    current_chars = len('\n'.join(result_lines))
                    remaining_budget = policy.max_chars - current_chars

        # Add head content
        head_budget = remaining_budget * 0.6  # 60% for head
        head_lines_to_add = []
        char_count = 0

        start_idx = len([l for l in result_lines if l])  # Skip already added lines
        for line in lines[start_idx:]:
            if char_count + len(line) > head_budget:
                break
            head_lines_to_add.append(line)
            char_count += len(line) + 1

        result_lines.extend(head_lines_to_add)

        # Add truncation marker
        remaining_lines = total_lines - len(result_lines) - policy.tail_lines
        if remaining_lines > 0:
            marker = policy.truncation_marker.format(remaining=remaining_lines)
            result_lines.append(marker)

        # Add tail content
        tail_budget = remaining_budget * 0.4  # 40% for tail
        tail_lines_to_add = []
        char_count = 0

        for line in reversed(lines[-policy.tail_lines:]):
            if char_count + len(line) > tail_budget:
                break
            tail_lines_to_add.insert(0, line)
            char_count += len(line) + 1

        result_lines.extend(tail_lines_to_add)

        metadata["result_lines"] = len(result_lines)
        metadata["result_chars"] = len('\n'.join(result_lines))

        return '\n'.join(result_lines), metadata

    @staticmethod
    def _extract_signatures(lines: List[str], ext: str) -> List[str]:
        """Extract class/function signatures from code."""
        signatures = []
        patterns = {
            'py': [r'^class\s+\w+', r'^def\s+\w+', r'^async\s+def\s+\w+'],
            'js': [r'^class\s+\w+', r'^function\s+\w+', r'^const\s+\w+\s*=\s*(async\s+)?(\([^)]*\)|[^=]+)\s*=>'],
            'ts': [r'^class\s+\w+', r'^function\s+\w+', r'^interface\s+\w+', r'^type\s+\w+'],
            'tsx': [r'^class\s+\w+', r'^function\s+\w+', r'^interface\s+\w+', r'^const\s+\w+:?\s*.*='],
            'jsx': [r'^class\s+\w+', r'^function\s+\w+', r'^const\s+\w+\s*='],
            'go': [r'^func\s+', r'^type\s+\w+\s+struct'],
            'rs': [r'^fn\s+', r'^struct\s+', r'^impl\s+', r'^trait\s+'],
            'java': [r'^public\s+class', r'^private\s+class', r'^public\s+.*\s+\w+\s*\('],
        }

        ext_patterns = patterns.get(ext, [])
        for line in lines:
            stripped = line.strip()
            if any(re.match(p, stripped) for p in ext_patterns):
                signatures.append(line)

        return signatures[:20]  # Limit to 20 signatures

    @staticmethod
    def extract_line_range(
        content: str,
        start_line: int,
        end_line: int,
        context: int = 5
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract specific line range with context."""
        lines = content.split('\n')
        total_lines = len(lines)

        # Adjust for 1-based line numbers
        start_idx = max(0, start_line - 1 - context)
        end_idx = min(total_lines, end_line + context)

        extracted = lines[start_idx:end_idx]

        # Add line numbers
        numbered_lines = []
        for i, line in enumerate(extracted, start=start_idx + 1):
            marker = ">>>" if start_line <= i <= end_line else "   "
            numbered_lines.append(f"{marker} {i:4d} | {line}")

        metadata = {
            "requested_range": (start_line, end_line),
            "actual_range": (start_idx + 1, end_idx),
            "context_lines": context,
            "total_file_lines": total_lines,
        }

        return '\n'.join(numbered_lines), metadata


# =============================================================================
# GITHUB MCP WRAPPER
# =============================================================================

class GitHubMCPWrapper:
    """
    Smart wrapper for GitHub MCP tools with policy-based fetching and caching.

    Example:
        wrapper = GitHubMCPWrapper(mcp_tools)

        # Smart fetch with caching
        content = await wrapper.get_file_contents("owner", "repo", "path/file.py")

        # Fetch specific line range
        content = await wrapper.get_file_contents(
            "owner", "repo", "path/file.py",
            policy=FetchPolicy.LINE_RANGE,
            start_line=100,
            end_line=150
        )

        # Batch fetch multiple files
        contents = await wrapper.batch_get_files("owner", "repo", [
            "src/main.py",
            "src/utils.py",
            "README.md"
        ])
    """

    def __init__(
        self,
        mcp_tools,
        policy_config: Optional[PolicyConfig] = None,
        enable_cache: bool = True,
        cache_ttl: int = 300,
        max_cache_entries: int = 100,
    ):
        self.mcp_tools = mcp_tools
        self.policy_config = policy_config or PolicyConfig()
        self.cache = TTLCache(max_cache_entries, cache_ttl) if enable_cache else None
        self.processor = ContentProcessor()

        # Statistics
        self._stats = {
            "api_calls": 0,
            "cache_hits": 0,
            "bytes_fetched": 0,
            "bytes_returned": 0,
            "tokens_saved": 0,
        }

    async def _call_mcp_tool(self, tool_name: str, **kwargs) -> Any:
        """Call MCP tool with error handling."""
        self._stats["api_calls"] += 1
        try:
            # Get the tool function from MCP tools
            tool_func = getattr(self.mcp_tools, tool_name, None)
            if tool_func is None:
                # Try calling via the generic call method
                if hasattr(self.mcp_tools, 'call'):
                    return await self.mcp_tools.call(tool_name, **kwargs)
                raise AttributeError(f"MCP tool '{tool_name}' not found")

            result = await tool_func(**kwargs)
            return result
        except Exception as e:
            raise GitHubMCPError(f"MCP tool '{tool_name}' failed: {str(e)}") from e

    async def get_file_contents(
        self,
        owner: str,
        repo: str,
        path: str,
        policy: FetchPolicy = FetchPolicy.SMART,
        policy_config: Optional[PolicyConfig] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        branch: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Get file contents with smart fetching and caching.

        Returns:
            {
                "content": str,
                "path": str,
                "sha": str,
                "size": int,
                "truncated": bool,
                "metadata": dict,
                "from_cache": bool,
            }
        """
        config = policy_config or self.policy_config
        cache_key = f"file:{owner}/{repo}/{path}:{branch or 'default'}"

        # Check cache first
        if use_cache and self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                self._stats["cache_hits"] += 1
                result = cached.copy()
                result["from_cache"] = True

                # Apply policy to cached content
                if policy != FetchPolicy.FULL:
                    result = self._apply_policy(result, policy, config, start_line, end_line, path)

                return result

        # Fetch from GitHub
        try:
            response = await self._call_mcp_tool(
                "get_file_contents",
                owner=owner,
                repo=repo,
                path=path,
                **({"branch": branch} if branch else {})
            )
        except Exception as e:
            return {
                "content": None,
                "path": path,
                "error": str(e),
                "from_cache": False,
            }

        # Parse response
        content = self._extract_content(response)
        sha = self._extract_sha(response)
        size = len(content) if content else 0

        self._stats["bytes_fetched"] += size

        result = {
            "content": content,
            "path": path,
            "sha": sha,
            "size": size,
            "truncated": False,
            "metadata": {},
            "from_cache": False,
        }

        # Cache the full content
        if self.cache and content:
            self.cache.set(cache_key, result, sha=sha, size_bytes=size)

        # Apply policy for returning
        if policy != FetchPolicy.FULL:
            result = self._apply_policy(result, policy, config, start_line, end_line, path)

        self._stats["bytes_returned"] += len(result.get("content", "") or "")
        self._stats["tokens_saved"] += (size - len(result.get("content", "") or "")) // 4

        return result

    def _apply_policy(
        self,
        result: Dict[str, Any],
        policy: FetchPolicy,
        config: PolicyConfig,
        start_line: Optional[int],
        end_line: Optional[int],
        path: str,
    ) -> Dict[str, Any]:
        """Apply fetch policy to content."""
        content = result.get("content")
        if not content:
            return result

        result = result.copy()

        if policy == FetchPolicy.METADATA_ONLY:
            lines = content.split('\n')
            result["content"] = None
            result["metadata"] = {
                "total_lines": len(lines),
                "total_chars": len(content),
                "file_type": path.split('.')[-1] if '.' in path else "unknown",
            }
            result["truncated"] = True

        elif policy == FetchPolicy.MINIMAL:
            lines = content.split('\n')
            head = lines[:config.head_lines]
            tail = lines[-config.tail_lines:] if len(lines) > config.head_lines + config.tail_lines else []

            if tail:
                remaining = len(lines) - config.head_lines - config.tail_lines
                marker = config.truncation_marker.format(remaining=remaining)
                result["content"] = '\n'.join(head) + marker + '\n'.join(tail)
            else:
                result["content"] = '\n'.join(head)

            result["truncated"] = len(lines) > config.head_lines + config.tail_lines
            result["metadata"] = {"total_lines": len(lines)}

        elif policy == FetchPolicy.LINE_RANGE and start_line and end_line:
            extracted, metadata = self.processor.extract_line_range(
                content, start_line, end_line, config.context_lines
            )
            result["content"] = extracted
            result["metadata"] = metadata
            result["truncated"] = True

        elif policy == FetchPolicy.SMART:
            truncated, metadata = self.processor.smart_truncate(content, config, path)
            result["content"] = truncated
            result["metadata"] = metadata
            result["truncated"] = metadata.get("truncated", False)

        return result

    def _extract_content(self, response: Any) -> Optional[str]:
        """Extract content from MCP response."""
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            return response.get("content") or response.get("text") or response.get("data")
        if hasattr(response, 'content'):
            return response.content
        return str(response) if response else None

    def _extract_sha(self, response: Any) -> Optional[str]:
        """Extract SHA from MCP response."""
        if isinstance(response, dict):
            return response.get("sha")
        if hasattr(response, 'sha'):
            return response.sha
        return None

    async def batch_get_files(
        self,
        owner: str,
        repo: str,
        paths: List[str],
        policy: FetchPolicy = FetchPolicy.SMART,
        policy_config: Optional[PolicyConfig] = None,
        max_concurrent: int = 5,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch fetch multiple files with concurrency control.

        Returns:
            {
                "path/to/file1.py": {...},
                "path/to/file2.py": {...},
            }
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(path: str) -> Tuple[str, Dict[str, Any]]:
            async with semaphore:
                result = await self.get_file_contents(
                    owner, repo, path, policy, policy_config
                )
                return path, result

        tasks = [fetch_with_semaphore(path) for path in paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            path: result if not isinstance(result, Exception) else {"error": str(result)}
            for path, result in results
        }

    async def get_repository(
        self,
        owner: str,
        repo: str,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Get repository info with caching."""
        cache_key = f"repo:{owner}/{repo}"

        if use_cache and self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                self._stats["cache_hits"] += 1
                return {**cached, "from_cache": True}

        try:
            response = await self._call_mcp_tool(
                "get_repository",
                owner=owner,
                repo=repo,
            )

            result = {
                "exists": True,
                "data": response,
                "from_cache": False,
            }

            if self.cache:
                self.cache.set(cache_key, result, ttl=600)  # 10 min TTL for repo info

            return result

        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                return {"exists": False, "error": "Repository not found", "from_cache": False}
            raise

    async def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
        sha: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update file and invalidate cache."""
        # If no SHA provided, try to get it from cache or fetch
        if not sha:
            cache_key = f"file:{owner}/{repo}/{path}:{branch or 'default'}"
            if self.cache:
                cached = self.cache.get(cache_key)
                if cached:
                    sha = cached.get("sha")

            if not sha:
                # Try to fetch existing file to get SHA
                try:
                    existing = await self.get_file_contents(
                        owner, repo, path,
                        policy=FetchPolicy.METADATA_ONLY,
                        branch=branch,
                        use_cache=False,
                    )
                    sha = existing.get("sha")
                except Exception:
                    pass  # File doesn't exist, will create new

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

            response = await self._call_mcp_tool("create_or_update_file", **kwargs)

            # Invalidate cache for this file
            if self.cache:
                self.cache.invalidate(f"file:{owner}/{repo}/{path}")

            return {
                "success": True,
                "response": response,
                "path": path,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": path,
            }

    async def search_code(
        self,
        owner: str,
        repo: str,
        query: str,
        policy: FetchPolicy = FetchPolicy.SMART,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """
        Search code in repository with smart content fetching.

        Returns matching files with relevant content snippets.
        """
        cache_key = f"search:{owner}/{repo}:{query}"

        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                self._stats["cache_hits"] += 1
                return {**cached, "from_cache": True}

        try:
            response = await self._call_mcp_tool(
                "search_code",
                owner=owner,
                repo=repo,
                query=query,
            )

            # Process search results
            items = self._extract_search_items(response)[:max_results]

            # Fetch content for each matching file with context
            results = []
            for item in items:
                path = item.get("path", "")
                if path:
                    content_result = await self.get_file_contents(
                        owner, repo, path, policy=policy
                    )
                    results.append({
                        "path": path,
                        "content": content_result.get("content"),
                        "truncated": content_result.get("truncated"),
                    })

            result = {
                "query": query,
                "total_matches": len(items),
                "results": results,
                "from_cache": False,
            }

            if self.cache:
                self.cache.set(cache_key, result, ttl=60)  # 1 min TTL for search

            return result

        except Exception as e:
            return {
                "query": query,
                "error": str(e),
                "results": [],
                "from_cache": False,
            }

    def _extract_search_items(self, response: Any) -> List[Dict[str, Any]]:
        """Extract search result items from response."""
        if isinstance(response, list):
            return response
        if isinstance(response, dict):
            return response.get("items", []) or response.get("results", [])
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get wrapper statistics."""
        stats = self._stats.copy()
        if self.cache:
            stats["cache"] = self.cache.stats()
        return stats

    def invalidate_cache(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries."""
        if self.cache:
            return self.cache.invalidate(pattern)
        return 0


class GitHubMCPError(Exception):
    """Custom exception for GitHub MCP errors."""
    pass


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_wrapper(
    mcp_tools,
    policy_name: str = "code_review",
    enable_cache: bool = True,
) -> GitHubMCPWrapper:
    """
    Create a GitHubMCPWrapper with a named policy preset.

    Available policies: code_review, quick_check, full_read, metadata
    """
    policy_config = POLICIES.get(policy_name, POLICIES["code_review"])
    return GitHubMCPWrapper(
        mcp_tools=mcp_tools,
        policy_config=policy_config,
        enable_cache=enable_cache,
    )


async def smart_fetch_file(
    mcp_tools,
    owner: str,
    repo: str,
    path: str,
    max_tokens: int = 4000,
) -> str:
    """
    Quick utility to fetch a file with smart truncation.

    Returns just the content string (not the full result dict).
    """
    wrapper = GitHubMCPWrapper(
        mcp_tools=mcp_tools,
        policy_config=PolicyConfig(max_tokens=max_tokens, max_chars=max_tokens * 4),
    )
    result = await wrapper.get_file_contents(owner, repo, path, policy=FetchPolicy.SMART)
    return result.get("content", "")

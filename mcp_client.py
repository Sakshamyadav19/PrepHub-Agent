# mcp_client.py
import os
from langchain_mcp_adapters.client import MultiServerMCPClient

def get_mcp_client():
    return MultiServerMCPClient({
        "gmail": {
            "transport": "stdio",
            "command": "npx",
            "args": [
                "@gongrzhe/server-gmail-autoauth-mcp"
            ]
        },
        "firecrawl-mcp": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "firecrawl-mcp"],
            "env": {
                "FIRECRAWL_API_KEY": os.environ.get("FIRECRAWL_API_KEY", ""),
            }
        },
    })


def get_mcp_client() -> MultiServerMCPClient:
    """Create a fresh client (usually you won't need this directly)."""
    return MultiServerMCPClient(_servers())

# ---------- Simple async cache for tools ----------
_tools_cache: Optional[list] = None
_tools_lock = asyncio.Lock()
_cache_key: Optional[str] = None  # lets us invalidate if HOME or config changes

def _current_key() -> str:
    # If you later key by user/org, include that here.
    return f"{os.environ.get('MCP_GMAIL_HOME','')}"  # blank for single-user

async def get_mcp_tools_cached() -> list:
    """
    Initialize MCP servers once and reuse the bound tools.
    Safe to call from multiple coroutines — guarded by an asyncio.Lock.
    """
    global _tools_cache, _cache_key
    if os.environ.get("MCP_CACHE_DISABLE") == "1":
        # escape hatch for debugging
        client = get_mcp_client()
        return await client.get_tools()

    key = _current_key()
    if _tools_cache is not None and _cache_key == key:
        return _tools_cache

    async with _tools_lock:
        # re-check inside the lock
        if _tools_cache is not None and _cache_key == key:
            return _tools_cache
        client = get_mcp_client()
        _tools_cache = await client.get_tools()
        _cache_key = key
        return _tools_cache

def reset_mcp_tools_cache() -> None:
    """Call this if you change MCP_GMAIL_HOME or want to force a reload."""
    global _tools_cache, _cache_key
    _tools_cache = None
    _cache_key = None
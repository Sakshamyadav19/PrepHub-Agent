# backend/agent/detect_agent.py
import re
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from mcp_client import get_mcp_tools_cached

# High-signal patterns (positive/negative). Tweak as you like.
POSITIVE_PATTERNS = [
    r"\binterview\b",
    r"\bphone\s*screen\b",
    r"\bonsite\b",
    r"\btake[- ]?home\b",
    r"\bassessment\b",
    r"\bnext steps\b",
    r"\bavailability\b",
    r"\bschedule\b",
    r"\brecruiter\b",
    r"\bhiring manager\b",
]
NEGATIVE_PATTERNS = [
    r"\bnewsletter\b",
    r"\bunsubscribe\b",
    r"\bcareer\s+tips\b",
    r"\bthanks for applying\b.*\b(we're moving forward with other candidates|reject|unfortunately)\b",
]

POS_RE = re.compile("|".join(POSITIVE_PATTERNS), re.I)
NEG_RE = re.compile("|".join(NEGATIVE_PATTERNS), re.I)

# Gmail search queries we’ll union together (last 30–45d)
QUERIES = [
    'in:inbox newer_than:45d (subject:(interview OR "phone screen" OR onsite OR assessment OR "take home"))',
    'in:inbox newer_than:45d (subject:(availability OR schedule OR "next steps"))',
    'in:inbox newer_than:45d (from:(@lever.co OR @greenhouse.io OR @ashbyhq.com OR recruiting@* OR jobs@* OR talent@*))',
]

def _title_from_domain(domain: str) -> str:
    # "mail.recruiting.riotgames.com" -> "Riot Games"
    parts = [p for p in domain.split(".") if p not in {"mail", "email", "recruiting", "app"}]
    if len(parts) >= 2:
        base = parts[-2]
    else:
        base = parts[0] if parts else domain
    # split on hyphen/underscore and title-case
    return " ".join(s.capitalize() for s in re.split(r"[-_]", base) if s)

def _is_interview_like(text: str) -> bool:
    if not text:
        return False
    if NEG_RE.search(text):
        return False
    return bool(POS_RE.search(text))

async def _call_tool(tool, payload: Dict[str, Any]) -> Any:
    """Call an MCP tool with a few common arg fallbacks."""
    try:
        return await tool.ainvoke(payload)
    except Exception:
        # Try common alt arg names
        if "query" in payload:
            try:
                return await tool.ainvoke({"q": payload["query"]})
            except Exception:
                pass
        if "thread_id" in payload:
            try:
                return await tool.ainvoke({"id": payload["thread_id"]})
            except Exception:
                pass
        raise

async def _get_gmail_tools():
    tools = await get_mcp_tools_cached()
    # Find gmail search + thread tools by name/description
    search_tool = None
    get_thread_tool = None
    for t in tools:
        n = (getattr(t, "name", "") or "").lower()
        d = (getattr(t, "description", "") or "").lower()
        if not search_tool and ("search" in n or "search" in d) and "gmail" in (n + d):
            search_tool = t
        if not get_thread_tool and ("get_thread" in n or ("thread" in n and "get" in n)) and "gmail" in (n + d):
            get_thread_tool = t
    return search_tool, get_thread_tool

async def _search_thread_ids(search_tool) -> List[str]:
    thread_ids: List[str] = []
    seen = set()
    for q in QUERIES:
        try:
            res = await _call_tool(search_tool, {"query": q})
        except Exception:
            continue
        # Accept common result shapes
        if isinstance(res, list):
            items = res
        else:
            items = res.get("threads") or res.get("items") or []
        for it in items:
            tid = (it.get("thread_id") or it.get("id") or it.get("threadId") or "").strip()
            if tid and tid not in seen:
                seen.add(tid)
                thread_ids.append(tid)
    return thread_ids

async def _fetch_thread(get_thread_tool, thread_id: str) -> Dict[str, Any]:
    try:
        res = await _call_tool(get_thread_tool, {"thread_id": thread_id})
    except Exception:
        return {"thread_id": thread_id}
    return res if isinstance(res, dict) else {"thread_id": thread_id, "raw": res}

def _extract_fields(thread: Dict[str, Any]) -> Dict[str, Any]:
    tid = thread.get("thread_id") or thread.get("id") or thread.get("threadId") or ""
    # Try to read the newest message headers/body/snippet
    msgs = thread.get("messages") or []
    latest = msgs[-1] if msgs else thread
    subject = (latest.get("subject") or thread.get("subject") or "")[:500]
    sender = latest.get("from") or latest.get("sender") or thread.get("from") or ""
    snippet = latest.get("snippet") or ""
    body = latest.get("body") or latest.get("text") or ""

    text = " ".join(str(x) for x in [subject, snippet, body])
    ok = _is_interview_like(text)
    if not ok:
        return {}

    # Guess company
    company = ""
    m = re.search(r"@([A-Za-z0-9\.\-]+)", sender)
    if m:
        company = _title_from_domain(m.group(1))

    # Rough date
    dt_iso = None
    for key in ("date", "internalDate", "timestamp"):
        val = latest.get(key) or thread.get(key)
        if not val:
            continue
        try:
            if isinstance(val, (int, float)):  # epoch ms or s
                if val > 10_000_000_000:
                    val = val / 1000.0
                dt_iso = datetime.fromtimestamp(val, tz=timezone.utc).isoformat()
            else:
                dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
                dt_iso = dt.astimezone(timezone.utc).isoformat()
            break
        except Exception:
            continue

    item = {
        "thread_id": tid,
        "company": company or "",
        "role": "",
        "subject": subject,
        "date": dt_iso or "",
        "sender": sender,
        "recruiter_name": "",
        "meeting_time": "",
    }
    return item

async def run_detect_interviews() -> Dict[str, Any]:
    search_tool, get_thread_tool = await _get_gmail_tools()
    if not search_tool:
        # Fail safe: no search tool found
        return {"interviews": []}

    ids = await _search_thread_ids(search_tool)
    out: List[Dict[str, Any]] = []

    if get_thread_tool:
        # Fetch each thread and apply strict rule-based filter
        tasks = [asyncio.create_task(_fetch_thread(get_thread_tool, tid)) for tid in ids]
        for task in asyncio.as_completed(tasks):
            thread = await task
            item = _extract_fields(thread)
            if item:
                out.append(item)
    else:
        # Fallback: filter using only subjects from search results
        for tid in ids:
            item = {"thread_id": tid, "company": "", "role": "", "subject": "", "date": "", "sender": "", "recruiter_name": "", "meeting_time": ""}
            if _is_interview_like(item["subject"]):
                out.append(item)

    # De-dup by thread_id
    seen = set()
    uniq = []
    for it in sorted(out, key=lambda x: x.get("date") or "", reverse=True):
        if it["thread_id"] in seen:
            continue
        seen.add(it["thread_id"])
        uniq.append(it)

    return {"interviews": uniq}

import os
import re
from typing import Any, Dict, List, Tuple
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from utils.json_parser import safe_extract_json
# IMPORTANT: use the cached tools so MCP servers don't relaunch per request
from mcp_client import get_mcp_tools_cached
from prompts.prep_plan import PREP_THREAD_SYSTEM, PREP_THREAD_USER_TPL

# ----------------------------- Generic company/role path -----------------------------

PREP_SYSTEM = (
    "You are a precise research agent with web tools (Firecrawl). "
    "Return STRICT JSON only. No markdown, no code fences, no commentary. "
    "If a field is unknown, return null or an empty array—but keep the field."
)

PREP_USER_TPL = """Company: {company}
Role: {role}
Tasks:
1) Company snapshot: what they do, size/funding stage (include links in text).
2) Recent news (~6 months): array of items with title, url, and why_it_matters.
3) Team highlights: founders/eng leadership (array with name, role, source url).
4) Tech stack hints: array of technologies (StackShare/blog/job posts if available).

Return JSON exactly with these keys only:
{
  "company": "{company}",
  "role": "{role}",
  "snapshot": "...",
  "news": [{"title":"...","url":"...","why_it_matters":"..."}],
  "team": [{"name":"...","role":"...","source":"url"}],
  "tech_stack": ["...", "..."]
}
"""

SCHEMA_KEYS = {"company", "role", "snapshot", "news", "team", "tech_stack"}

def _coerce_schema(obj: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "company": obj.get("company") or "",
        "role": obj.get("role") or "",
        "snapshot": obj.get("snapshot") or "",
        "news": obj.get("news") if isinstance(obj.get("news"), list) else [],
        "team": obj.get("team") if isinstance(obj.get("team"), list) else [],
        "tech_stack": obj.get("tech_stack") if isinstance(obj.get("tech_stack"), list) else [],
    }

async def run_prep_agent(company: str, role: str):
    tools = await get_mcp_tools_cached()
    llm = init_chat_model(
        "gemini-2.5-pro",
        model_provider="google_genai",
        api_key=os.environ.get("GOOGLE_API_KEY") or "AIzaSyC0p6-LHxNpvVdzfulFb1RiysRDhDgnWRI",
    )
    agent = create_react_agent(llm, tools)

    user_prompt = (
        PREP_USER_TPL
        .replace("{company}", company or "")
        .replace("{role}", role or "")
    )

    result = await agent.ainvoke({"messages": [SystemMessage(PREP_SYSTEM), HumanMessage(user_prompt)]})
    msgs = result.get("messages", [])
    last_ai = next((m for m in reversed(msgs) if isinstance(m, AIMessage)), None)
    content = last_ai.content if last_ai else (msgs[-1].content if msgs else "")

    try:
        return _coerce_schema(safe_extract_json(content))
    except Exception:
        fixer = init_chat_model("gemini-2.0-flash", model_provider="google_genai",
                                api_key=os.environ.get("GOOGLE_API_KEY") or "AIzaSyC0p6-LHxNpvVdzfulFb1RiysRDhDgnWRI")
        repaired = fixer.invoke(
            "Rewrite the following as STRICT JSON with ONLY these keys: "
            "company, role, snapshot, news, team, tech_stack. "
            "If a value is unknown, use null or empty array. "
            "No markdown, no code fences, no comments, no trailing commas.\n\n" + str(content)
        ).content
        return _coerce_schema(safe_extract_json(repaired))

# ----------------------------- Thread-based prep path -----------------------------

# Allowed plan keys (trimmed – no thread_id/interview/contacts/source_links)
ALLOWED_PLAN_KEYS = {
    "company", "role", "company_snapshot", "jd_summary", "core_topics",
    "behavioral", "questions_to_ask", "tech_stack", "resources",
    "next_actions", "schedule_suggestion", "news", "team"
}

def _coerce_prep_plan(obj: dict) -> dict:
    def arr(x): return x if isinstance(x, list) else []
    def as_obj(x, fallback=None): return x if isinstance(x, dict) else (fallback if fallback is not None else {})
    return {
        "company": obj.get("company") or "",
        "role": obj.get("role") or "",
        "company_snapshot": obj.get("company_snapshot") or obj.get("snapshot") or "",
        "jd_summary": as_obj(obj.get("jd_summary"), {"summary": "", "responsibilities": [], "requirements": []}),
        "core_topics": as_obj(obj.get("core_topics"), {"must_know": [], "refresh": []}),
        "behavioral": as_obj(obj.get("behavioral"), {"stories_to_prepare": []}),
        "questions_to_ask": arr(obj.get("questions_to_ask")),
        "tech_stack": arr(obj.get("tech_stack")),
        "resources": arr(obj.get("resources")),
        "next_actions": arr(obj.get("next_actions")),
        "schedule_suggestion": arr(obj.get("schedule_suggestion")),
        "news": arr(obj.get("news")),
        "team": arr(obj.get("team")),
    }

# ---------- Gmail MCP helpers (resilient to tool name variants) ----------

async def _get_gmail_tools() -> Tuple[Any, Any]:
    """Find Gmail search + thread tools by fuzzy matching name/description."""
    tools = await get_mcp_tools_cached()
    search_tool, get_thread_tool = None, None
    for t in tools:
        n = (getattr(t, "name", "") or "").lower()
        d = (getattr(t, "description", "") or "").lower()
        blob = n + " " + d
        if not search_tool and "gmail" in blob and "search" in blob:
            search_tool = t
        if not get_thread_tool and "gmail" in blob and ("get_thread" in blob or ("thread" in blob and "get" in blob) or "messages in thread" in blob):
            get_thread_tool = t
    return search_tool, get_thread_tool

async def _call_tool(tool, payload: Dict[str, Any]) -> Any:
    """Call a tool trying common arg names (MCP servers sometimes differ)."""
    try:
        return await tool.ainvoke(payload)
    except Exception:
        # Try common alternates
        if "thread_id" in payload:
            for k in ("thread_id", "id", "threadId"):
                try:
                    return await tool.ainvoke({k: payload["thread_id"]})
                except Exception:
                    pass
        if "query" in payload:
            for k in ("query", "q"):
                try:
                    return await tool.ainvoke({k: payload["query"]})
                except Exception:
                    pass
        raise

async def _fetch_thread(thread_id: str) -> Dict[str, Any]:
    _, get_thread_tool = await _get_gmail_tools()
    if not get_thread_tool:
        return {}
    try:
        res = await _call_tool(get_thread_tool, {"thread_id": thread_id})
        return res if isinstance(res, dict) else {"raw": res}
    except Exception:
        return {}

_URL_RE = re.compile(r"https?://[^\s)>\]]+", re.I)

def _extract_context(thread: Dict[str, Any]) -> Tuple[str, List[str], str, str]:
    """
    Build a readable text context from the Gmail thread and collect URLs.
    Returns: (context_text, urls, guess_company, guess_role)
    """
    if not isinstance(thread, dict):
        return "", [], "", ""
    messages = thread.get("messages") or []
    parts: List[str] = []
    urls_set = set()
    guess_company, guess_role = "", ""

    for m in messages or [thread]:
        frm = m.get("from") or m.get("sender") or ""
        subj = m.get("subject") or thread.get("subject") or ""
        body = m.get("body") or m.get("text") or m.get("snippet") or ""
        if subj and not guess_role:
            # naive role guess off subject line
            m2 = re.search(r"(?:role|position|title)\s*[:\-]\s*(.+)", subj, re.I)
            if m2:
                guess_role = m2.group(1)[:80]
        if frm and not guess_company:
            dm = re.search(r"@([A-Za-z0-9\.\-]+)", frm)
            if dm:
                domain = dm.group(1)
                bits = [p for p in domain.split(".") if p not in {"mail", "email", "recruiting", "app"}]
                base = bits[-2] if len(bits) >= 2 else (bits[0] if bits else domain)
                guess_company = " ".join(s.capitalize() for s in re.split(r"[-_]", base) if s)

        text_block = f"From: {frm}\nSubject: {subj}\n\n{body}\n"
        parts.append(text_block)

        for u in _URL_RE.findall(text_block):
            urls_set.add(u.strip().rstrip(").,"))

    context_text = "\n\n---\n\n".join(parts)[:16000]  # protect context size
    urls = sorted(urls_set)
    return context_text, urls, guess_company, guess_role

# ---------- Thread-based prep runner ----------

async def run_prep_from_thread(thread_id: str):
    tools = await get_mcp_tools_cached()
    llm = init_chat_model(
        "gemini-2.5-pro",
        model_provider="google_genai",
        api_key=os.environ.get("GOOGLE_API_KEY") or "AIzaSyC0p6-LHxNpvVdzfulFb1RiysRDhDgnWRI",
    )
    agent = create_react_agent(llm, tools)

    # 1) deterministically pull the Gmail thread and build context
    thread = await _fetch_thread(thread_id)
    context_text, urls, guess_company, guess_role = _extract_context(thread)

    # 2) Build prompt with explicit context + URLs.
    #    We avoid .format() to keep all JSON braces literal.
    user_prompt = PREP_THREAD_USER_TPL.replace("{thread_id}", thread_id)
    # Prepend context so the model has real material even if tools fail.
    context_block = (
        "EMAIL THREAD CONTEXT (verbatim):\n"
        "--------------------------------\n" + (context_text or "[no content found]") + "\n\n"
        "CANDIDATE HINTS (best-effort):\n"
        f"- company_guess: {guess_company or 'unknown'}\n"
        f"- role_guess: {guess_role or 'unknown'}\n\n"
        "KNOWN URLS FROM THREAD (you MAY open with web tools if available):\n"
        + "\n".join(f"- {u}" for u in urls[:12]) + "\n\n"
        "Instructions: Prefer using the context above and URLs. "
        "If web tools are unavailable, you may use your general knowledge to complete the brief. "
        "Return STRICT JSON only, exactly with the required keys."
    )

    messages = [SystemMessage(PREP_THREAD_SYSTEM), HumanMessage(context_block + "\n\n" + user_prompt)]

    # 3) Run agent
    result = await agent.ainvoke({"messages": messages})
    msgs = result.get("messages", [])
    last_ai = next((m for m in reversed(msgs) if isinstance(m, AIMessage)), None)
    content = last_ai.content if last_ai else (msgs[-1].content if msgs else "")

    # 4) Parse/repair + coerce so frontend always gets stable fields
    try:
        obj = safe_extract_json(content)
    except Exception:
        fixer = init_chat_model("gemini-2.0-flash", model_provider="google_genai",
                                api_key=os.environ.get("GOOGLE_API_KEY") or "AIzaSyC0p6-LHxNpvVdzfulFb1RiysRDhDgnWRI")
        repaired = fixer.invoke(
            "Convert to STRICT JSON only (no markdown). Keep EXACTLY these keys and nothing else: "
            "company, role, company_snapshot, jd_summary, core_topics, behavioral, "
            "questions_to_ask, tech_stack, resources, next_actions, schedule_suggestion, news, team. "
            "No markdown, no code fences, no comments, no trailing commas.\n\n" + str(content)
        ).content
        obj = safe_extract_json(repaired)

    plan = _coerce_prep_plan(obj)

    # 5) As a last resort, if company/role are still blank, fill from guesses
    if not plan["company"] and guess_company:
        plan["company"] = guess_company
    if not plan["role"] and guess_role:
        plan["role"] = guess_role

    return plan

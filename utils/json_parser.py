# utils/json_parser.py
import json
import re
from typing import Any, Optional

def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        # remove first fence line
        s = re.sub(r"^```(?:json|javascript|js|python)?\s*", "", s, flags=re.IGNORECASE)
        # remove trailing fence
        s = re.sub(r"\s*```$", "", s)
    return s.strip()

def _load_if_json(s: str) -> Optional[Any]:
    try:
        return json.loads(s)
    except Exception:
        return None

def _extract_balanced_block(s: str, opener: str, closer: str) -> Optional[str]:
    start = s.find(opener)
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return None  # unbalanced

def safe_extract_json(text: str):
    """
    Try very hard to recover a valid JSON object or array from messy LLM output.
    Returns a Python object (dict/list). Raises ValueError if nothing valid found.
    """
    if text is None:
        raise ValueError("No text to parse (got None).")

    # Already JSON-ish?
    direct = _load_if_json(text)
    if direct is not None:
        return direct

    s = _strip_code_fences(text)

    # Try again after fence stripping
    direct = _load_if_json(s)
    if direct is not None:
        return direct

    # Try to extract first balanced object
    obj = _extract_balanced_block(s, "{", "}")
    if obj:
        parsed = _load_if_json(obj)
        if parsed is not None:
            return parsed

    # Try to extract first balanced array
    arr = _extract_balanced_block(s, "[", "]")
    if arr:
        parsed = _load_if_json(arr)
        if parsed is not None:
            return parsed

    # As a last resort, try the "first JSON-looking object" regex but tighter (non-greedy)
    m = re.search(r"\{.*?\}", s, flags=re.DOTALL)
    if m:
        parsed = _load_if_json(m.group(0))
        if parsed is not None:
            return parsed

    raise ValueError("No valid JSON found in the string")

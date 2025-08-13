PREP_THREAD_SYSTEM = """You are an interview prep agent with Gmail and web tools.
You MUST read the Gmail thread by thread_id and follow any JD/company links using web tools.
Return STRICT JSON only (no markdown, no commentary)."""

# User prompt template (format with thread_id)
PREP_THREAD_USER_TPL = """Gmail thread_id: {thread_id}
Goals:
1) Read the Gmail thread to infer company, role/title, and interview context.
2) If a job description (JD) link or attachment is present, fetch it and extract key competencies.
3) Create a focused PREP PLAN for the candidate:
   - company_snapshot (1–2 short paragraphs, include links inline)
   - jd_summary: {summary, responsibilities[], requirements[]}
   - core_topics: {must_know[], refresh[]}
   - behavioral: {stories_to_prepare[]}
   - questions_to_ask[] 
   - tech_stack[] 
   - resources[] 
   - next_actions[] 
   - schedule_suggestion: array of {when_utc, duration_min, focus}

Return STRICT JSON only (no markdown). Use exactly these keys:
{
  "company": "...",
  "role": "...",
  "company_snapshot": "...",
  "jd_summary": {"summary":"...", "responsibilities":[], "requirements":[]},
  "core_topics": {"must_know":[], "refresh":[]},
  "behavioral": {"stories_to_prepare":[]},
  "questions_to_ask": [],
  "tech_stack": [],
  "resources": [],
  "next_actions": [],
  "schedule_suggestion": [{"when_utc":"YYYY-MM-DDTHH:MM:SSZ","duration_min":45,"focus":"..."}]
}
"""

# prompts/tracker.py
DETECT_SYSTEM = """You are an email triage agent. Your job is to find interview/job opportunity threads
from the last 30 days using the Gmail tools and return structured JSON only."""

# High-signal Gmail queries the model should try with the gmail search tool:
DETECT_HINTS = [
  'newer_than:30d (subject:(interview) OR subject:(onsite) OR subject:(recruiter))',
  'newer_than:30d (subject:(phone screen) OR subject:(take home) OR subject:(assessment))',
  'newer_than:30d (from:(recruiting@* OR jobs@* OR talent@* OR greenhouse@* OR lever.co))',
]

DETECT_USER = f"""Find interview-related email threads. Use the gmail search tool to run these queries, one by one:
{DETECT_HINTS}
For each thread you deem relevant, extract:
- thread_id
- company (guess from sender/domain if missing)
- role/title
- meeting_time (if present in body)
- recruiter_name, sender, subject, date
Return JSON only:
{{ "interviews": [{{"thread_id":"...", "company":"...", "role":"...", "subject":"...", "date":"...", "sender":"...", "recruiter_name":"", "meeting_time":""}}] }}
"""

PREP_SYSTEM = """You research companies precisely and produce a tight prep brief in JSON only.
Use Firecrawl tools to fetch company website and recent news. Keep it concise but useful."""
PREP_USER_TPL = """Company: {company}
Role: {role}
Tasks:
1) Company snapshot: what they do, size/funding stage (cite sources/links).
2) Recent news (≈ last 6 months) with links and why it matters.
3) Team highlights: founders or eng leadership (sources).
4) Tech stack hints (StackShare, eng blog, job posts if available).

Return JSON:
{{
  "company": "{company}",
  "role": "{role}",
  "snapshot": "...",
  "news": [{{"title":"...","url":"...","why_it_matters":"..."}}],
  "team": [{{"name":"...","role":"...","source":"url"}}],
  "tech_stack": ["...", "..."]
}}
"""

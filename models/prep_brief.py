# models/prep_brief.py

from typing import List, Optional
from pydantic import BaseModel

class PrepBrief(BaseModel):
    company_overview: str
    recent_news: str
    sample_questions: List[str]
    website: Optional[str]
    tone_advice: Optional[str] = "Be professional and enthusiastic."

# models/interview.py

from typing import List, Optional
from pydantic import BaseModel

class Interview(BaseModel):
    id: str
    subject: str
    date: str  # ISO datetime string
    time: str  # Optional separate time field
    interviewer_name: Optional[str]
    interviewer_email: Optional[str]
    company: Optional[str]
    role: Optional[str]
    source: str  # "calendar" or "gmail"
    description: Optional[str] = ""


# mock interviews for now
mock_interviews = [
    {"id": "1", "company": "Google", "role": "Software Engineer"},
    {"id": "2", "company": "Amazon", "role": "Data Scientist"},
    {"id": "3", "company": "OpenAI", "role": "ML Engineer"}
]

def get_interview_by_id(interview_id):
    for interview in mock_interviews:
        if interview["id"] == interview_id:
            return interview
    return None


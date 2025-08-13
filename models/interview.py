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




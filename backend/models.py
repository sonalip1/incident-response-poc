from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class IncidentRequest(BaseModel):
    log_text: str

class IncidentApproval(BaseModel):
    approved: bool

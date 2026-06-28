from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class IncidentRequest(BaseModel):
    log_text: str
    incident_id: Optional[str] = None

class IncidentApproval(BaseModel):
    approved: bool

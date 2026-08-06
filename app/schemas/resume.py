from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class ResumeResponse(BaseModel):
    id: UUID
    job_id: UUID
    file_path: str
    raw_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

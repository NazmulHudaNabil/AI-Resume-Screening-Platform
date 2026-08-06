from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


# ─────────────────────────────────────────────────────
# JobCreate — the data the user sends when creating a job
# ─────────────────────────────────────────────────────

class JobCreate(BaseModel):
    """
    The data you send in the request body when creating a new job.

    Example JSON:
    {
        "title": "Backend Developer",
        "description": "We need a Python developer...",
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "nice_to_have_skills": ["Docker", "Redis"],
        "min_experience_years": 2.0
    }
    """
    title: str = Field(description="Job title, e.g. 'Backend Developer'")
    description: str = Field(description="Full job description text")
    required_skills: List[str] = Field(description="Skills the candidate must have")
    nice_to_have_skills: List[str] = Field(
        default_factory=list,
        description="Optional bonus skills (not required)"
    )
    min_experience_years: Optional[float] = Field(
        default=None,
        description="Minimum years of experience required (optional)"
    )


# ─────────────────────────────────────────────────────
# JobResponse — what the API sends back after creating a job
# ─────────────────────────────────────────────────────

class JobResponse(BaseModel):
    """
    The data the API returns after a job is created or fetched.
    Includes the auto-generated ID and timestamp from the database.
    """
    id: UUID
    title: str
    description: str
    required_skills: List[str]
    nice_to_have_skills: List[str]
    min_experience_years: Optional[Decimal]
    created_at: datetime

    # Needed so Pydantic can read from SQLAlchemy ORM objects directly
    model_config = ConfigDict(from_attributes=True)

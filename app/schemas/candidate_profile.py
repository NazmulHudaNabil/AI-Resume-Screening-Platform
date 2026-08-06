from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime


# ──────────────────────────────────────────────
# CandidateProfile — the shape of data we ask
# the LLM to extract from a raw resume text.
# ──────────────────────────────────────────────

class CandidateProfile(BaseModel):
    """
    Structured information extracted from one resume.

    Every field here maps to something the LLM reads from
    the resume text and outputs in JSON format. We use
    Pydantic to make sure the data is valid before saving it.
    """

    # Candidate's full name (e.g. "Alice Johnson")
    name: str = Field(description="Full name of the candidate")

    # List of technical / soft skills mentioned
    # e.g. ["Python", "FastAPI", "Docker", "Leadership"]
    skills: list[str] = Field(
        default_factory=list,
        description="All skills explicitly mentioned in the resume"
    )

    # Total years of work experience as a decimal
    # e.g. 3.5 means 3 years and 6 months
    experience_years: float = Field(
        default=0.0,
        description="Total years of professional work experience"
    )

    # Degrees / education credentials
    # e.g. ["B.Sc. in Computer Science", "MBA"]
    education: list[str] = Field(
        default_factory=list,
        description="Educational qualifications mentioned in the resume"
    )

    # Job titles / roles held in the past
    # e.g. ["Software Engineer", "Backend Developer"]
    roles: list[str] = Field(
        default_factory=list,
        description="Previous and current job titles or roles"
    )

    # Certifications (optional — many resumes don't have them)
    # e.g. ["AWS Certified Developer", "Google Cloud Professional"]
    certifications: list[str] = Field(
        default_factory=list,
        description="Professional certifications listed in the resume"
    )


# ──────────────────────────────────────────────
# Response schema — what we return from the API
# when someone asks for a candidate profile.
# ──────────────────────────────────────────────

class CandidateProfileResponse(BaseModel):
    """
    The full API response for a candidate profile record,
    including the database ID and timestamps.
    """
    candidate_id: UUID
    resume_id: UUID
    profile: CandidateProfile          # the nested extracted data
    created_at: datetime

    # This tells Pydantic to read data from SQLAlchemy ORM objects
    # (not just plain dicts), which is needed when we return DB rows.
    model_config = ConfigDict(from_attributes=True)

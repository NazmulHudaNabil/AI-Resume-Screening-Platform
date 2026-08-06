import uuid
from sqlalchemy import Column, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base


class CandidateProfile(Base):
    """
    Database table that stores the structured profile extracted
    from each resume by the LLM.

    Each row links back to one resume (resume_id) and holds
    the extracted data (skills, experience, education, etc.)
    as a JSON blob inside the 'profile' column.
    """

    __tablename__ = "candidate_profiles"

    # Primary key — a unique ID for this candidate profile
    candidate_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Link to the original resume row in the 'resumes' table
    resume_id = Column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id"),
        nullable=False,
    )

    # The full extracted profile stored as JSON
    # Example: {"name": "Alice", "skills": ["Python"], "experience_years": 3.0, ...}
    profile = Column(JSONB, nullable=False)

    # Automatically set to the current timestamp when the row is created
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

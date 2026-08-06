import uuid
from sqlalchemy import Column, String, Numeric, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    required_skills = Column(JSONB, nullable=False)
    nice_to_have_skills = Column(JSONB, default=list)
    min_experience_years = Column(Numeric, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

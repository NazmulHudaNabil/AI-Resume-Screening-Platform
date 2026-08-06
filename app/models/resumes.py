import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    raw_text = Column(Text, nullable=False)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

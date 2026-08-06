"""
ranking.py — SQLAlchemy DB Model for the rankings table
=========================================================

This model represents ONE row in the `rankings` table.
Each row stores the scores for one candidate against one job.

The rankings table is the output of Phase 3 (embedding search)
and Phase 4 (hybrid scoring). For Phase 3 we only fill in
semantic_score; the other scores come in Phase 4.

DB schema (mirrors Architecture.md):
    rankings (
        job_id           UUID  → which job
        candidate_id     UUID  → which candidate
        semantic_score   NUMERIC → from vector similarity (Phase 3)
        skill_overlap_score NUMERIC → from skill matching (Phase 4)
        experience_fit_score NUMERIC → from experience comparison (Phase 4)
        final_score      NUMERIC → weighted combination (Phase 4)
        explanation      TEXT  → LLM-generated rationale (Phase 5)
        PRIMARY KEY (job_id, candidate_id)
    )
"""

from sqlalchemy import Column, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class Ranking(Base):
    __tablename__ = "rankings"

    # ── Primary key is a COMPOSITE key (both columns together are unique) ──
    # This means one candidate can only have ONE ranking per job.

    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id"),
        primary_key=True,           # part 1 of the composite PK
        nullable=False,
    )

    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.candidate_id"),
        primary_key=True,           # part 2 of the composite PK
        nullable=False,
    )

    # ── Scores — filled in incrementally across phases ──

    # Phase 3: cosine similarity from Qdrant vector search (0.0 to 1.0)
    semantic_score = Column(Numeric, nullable=True)

    # Phase 4: how many required/nice-to-have skills matched (0.0 to 1.0)
    skill_overlap_score = Column(Numeric, nullable=True)

    # Phase 4: how well experience years fit the job requirement (0.0 to 1.0)
    experience_fit_score = Column(Numeric, nullable=True)

    # Phase 4: weighted combination of all three scores above (0.0 to 1.0)
    final_score = Column(Numeric, nullable=True)

    # Phase 5: LLM-generated explanation text (e.g. "Strong Python match, lacks Docker")
    explanation = Column(Text, nullable=True)

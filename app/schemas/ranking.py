"""
ranking.py (schemas) — Pydantic Schemas for Ranking API responses
==================================================================

These schemas define the shape of data the API sends back
when someone requests ranking results.

After Phase 3 (embedding), the response will have:
  - semantic_score filled
  - skill_overlap_score, experience_fit_score, final_score = None (Phase 4)
  - explanation = None (Phase 5)
"""

from pydantic import BaseModel, ConfigDict
from uuid import UUID
from decimal import Decimal
from typing import Optional


class RankingResponse(BaseModel):
    """
    One entry in the ranked candidate list for a job.

    All score fields are Optional because they are filled in
    across different phases:
      - semantic_score       → Phase 3 (embedding search)
      - skill_overlap_score  → Phase 4 (hybrid ranking)
      - experience_fit_score → Phase 4 (hybrid ranking)
      - final_score          → Phase 4 (hybrid ranking)
      - explanation          → Phase 5 (LLM explanation)
    """
    job_id: UUID
    candidate_id: UUID

    # Cosine similarity from vector search (Phase 3)
    semantic_score: Optional[Decimal] = None

    # Skill matching score (Phase 4)
    skill_overlap_score: Optional[Decimal] = None

    # Experience match score (Phase 4)
    experience_fit_score: Optional[Decimal] = None

    # Final weighted score (Phase 4)
    final_score: Optional[Decimal] = None

    # LLM-generated explanation (Phase 5)
    explanation: Optional[str] = None

    # Lets Pydantic read directly from SQLAlchemy model objects
    model_config = ConfigDict(from_attributes=True)

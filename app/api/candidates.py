"""
candidates.py — Candidate Profile API Routes
=============================================

This file defines the HTTP endpoints for Phase 2:
  - POST /jobs/{job_id}/resumes/{resume_id}/extract
      → Run LLM extraction for one resume, save the profile to DB.
  - GET /candidates/{candidate_id}
      → Fetch a single candidate's extracted profile.
  - DELETE /candidates/{candidate_id}
      → Delete a candidate's profile (GDPR / privacy support).

All routes use:
  - Path parameters validated by FastAPI
  - Async SQLAlchemy for non-blocking DB queries
  - Our CandidateProfileResponse Pydantic schema for output
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.candidate_profile import CandidateProfile as CandidateProfileModel
from app.models.resumes import Resume
from app.schemas.candidate_profile import CandidateProfile, CandidateProfileResponse
from app.services.extraction import extract_candidate_profile

# Set up logging for this module
logger = logging.getLogger(__name__)

# Create the router — all routes in this file share this prefix
router = APIRouter()


# ──────────────────────────────────────────────────────────────────────
# POST /jobs/{job_id}/resumes/{resume_id}/extract
# ──────────────────────────────────────────────────────────────────────

@router.post(
    "/jobs/{job_id}/resumes/{resume_id}/extract",
    response_model=CandidateProfileResponse,
    summary="Extract structured profile from a resume using the LLM",
    description=(
        "Reads raw text from the specified resume, sends it to the Groq LLM, "
        "extracts a structured CandidateProfile (skills, experience, education, etc.), "
        "and saves it to the database."
    ),
)
async def extract_resume_profile(
    job_id: uuid.UUID = Path(..., description="The job this resume belongs to"),
    resume_id: uuid.UUID = Path(..., description="The resume to extract a profile from"),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract and save a structured profile from a single resume.

    Steps:
    1. Look up the resume in the database.
    2. Make sure it belongs to the specified job.
    3. Check if we already extracted a profile for it (to avoid duplicates).
    4. Call the LLM extraction service.
    5. Save the profile to the candidate_profiles table.
    6. Return the saved profile.
    """

    # ── Step 1: Find the resume ──────────────────────────────────────
    resume = await db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(
            status_code=404,
            detail=f"Resume with id={resume_id} not found."
        )

    # ── Step 2: Confirm it belongs to the right job ──────────────────
    if resume.job_id != job_id:
        raise HTTPException(
            status_code=400,
            detail=f"Resume {resume_id} does not belong to job {job_id}."
        )

    # ── Step 3: Check for existing profile (avoid duplicate work) ────
    existing = await db.execute(
        select(CandidateProfileModel).where(
            CandidateProfileModel.resume_id == resume_id
        )
    )
    existing_profile = existing.scalar_one_or_none()

    if existing_profile is not None:
        # Profile already exists — just return it without re-calling the LLM
        logger.info(f"Profile already exists for resume {resume_id}, returning cached.")
        return _to_response(existing_profile)

    # ── Step 4: Call the LLM extraction service ───────────────────────
    logger.info(f"Starting LLM extraction for resume {resume_id} ...")
    try:
        candidate_profile: CandidateProfile = extract_candidate_profile(resume.raw_text)
    except ValueError as e:
        # LLM failed after retries — log the error and return 422
        logger.error(f"Extraction failed for resume {resume_id}: {e}")
        raise HTTPException(
            status_code=422,
            detail=(
                f"Could not extract a valid profile from this resume. "
                f"Error: {str(e)}"
            ),
        )

    # ── Step 5: Save the profile to the database ──────────────────────
    db_profile = CandidateProfileModel(
        resume_id=resume_id,
        # Store the profile as a plain dict (JSON) in the JSONB column
        profile=candidate_profile.model_dump(),
    )
    db.add(db_profile)
    await db.commit()
    await db.refresh(db_profile)

    logger.info(f"Profile saved for resume {resume_id} → candidate_id={db_profile.candidate_id}")

    # ── Step 6: Return the saved profile ─────────────────────────────
    return _to_response(db_profile)


# ──────────────────────────────────────────────────────────────────────
# GET /candidates/{candidate_id}
# ──────────────────────────────────────────────────────────────────────

@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateProfileResponse,
    summary="Get a candidate's extracted profile",
    description="Fetch the full structured profile for a specific candidate by their ID.",
)
async def get_candidate_profile(
    candidate_id: uuid.UUID = Path(..., description="The candidate's unique ID"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single candidate profile from the database."""

    db_profile = await db.get(CandidateProfileModel, candidate_id)

    if db_profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate with id={candidate_id} not found."
        )

    return _to_response(db_profile)


# ──────────────────────────────────────────────────────────────────────
# DELETE /candidates/{candidate_id}
# ──────────────────────────────────────────────────────────────────────

@router.delete(
    "/candidates/{candidate_id}",
    status_code=200,
    summary="Delete a candidate's profile (data deletion / GDPR)",
    description=(
        "Permanently removes a candidate's extracted profile from the database. "
        "Use this to fulfill data-deletion requests."
    ),
)
async def delete_candidate_profile(
    candidate_id: uuid.UUID = Path(..., description="The candidate's unique ID to delete"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a candidate profile — supports GDPR-style deletion requests."""

    db_profile = await db.get(CandidateProfileModel, candidate_id)

    if db_profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate with id={candidate_id} not found."
        )

    await db.delete(db_profile)
    await db.commit()

    logger.info(f"Candidate profile {candidate_id} deleted.")
    return {"message": f"Candidate {candidate_id} has been deleted successfully."}


# ──────────────────────────────────────────────────────────────────────
# Helper: convert a DB row → API response schema
# ──────────────────────────────────────────────────────────────────────

def _to_response(db_profile: CandidateProfileModel) -> CandidateProfileResponse:
    """
    Convert a CandidateProfileModel (SQLAlchemy row) into a
    CandidateProfileResponse (Pydantic schema) for the API to return.

    The 'profile' column is stored as a JSON dict in Postgres,
    so we re-validate it through the CandidateProfile schema here.
    """
    return CandidateProfileResponse(
        candidate_id=db_profile.candidate_id,
        resume_id=db_profile.resume_id,
        profile=CandidateProfile.model_validate(db_profile.profile),
        created_at=db_profile.created_at,
    )

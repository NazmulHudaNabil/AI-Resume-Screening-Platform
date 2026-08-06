"""
rankings.py — Rankings API Routes (Phase 3 + Phase 4)
======================================================

This file handles:

  POST /jobs/{job_id}/candidates/{candidate_id}/embed  [Phase 3]
    → Embed one candidate's profile into Qdrant.

  POST /jobs/{job_id}/embed-all                        [Phase 3]
    → Embed ALL extracted candidates for a job in one call.

  GET /jobs/{job_id}/rankings                          [Phase 3 + 4]
    → Retrieve ranked candidates for a job.
      Sorted by final_score (Phase 4) or semantic_score (Phase 3).

  POST /jobs/{job_id}/rank                             [Phase 4] ← NEW
    → Compute hybrid scores (skill + experience + semantic) for all candidates.

Full flow:
  Phase 1: upload resume       → POST /jobs/{id}/resumes
  Phase 2: extract profile     → POST /jobs/{id}/resumes/{id}/extract
  Phase 3: embed candidates    → POST /jobs/{id}/embed-all
  Phase 3: get semantic rank   → GET  /jobs/{id}/rankings
  Phase 4: full hybrid rank    → POST /jobs/{id}/rank
  Phase 4: view final results  → GET  /jobs/{id}/rankings
"""

import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.candidate_profile import CandidateProfile as CandidateProfileModel
from app.models.jobs import Job
from app.models.ranking import Ranking
from app.schemas.ranking import RankingResponse
from app.services.embedding import upsert_candidate_vector, search_candidates

logger = logging.getLogger(__name__)

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────
# POST /jobs/{job_id}/candidates/{candidate_id}/embed
# Embed ONE candidate profile into Qdrant
# ──────────────────────────────────────────────────────────────────────

@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/embed",
    status_code=202,
    summary="Embed a single candidate into the vector store",
    description=(
        "Converts a candidate's extracted profile into a vector (using Gemini embeddings) "
        "and saves it in Qdrant. Run this after Phase 2 extraction is complete. "
        "Returns 202 Accepted immediately; embedding runs in the background."
    ),
)
async def embed_candidate(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Embed one candidate's profile into Qdrant (background task)."""

    db_profile = await db.get(CandidateProfileModel, candidate_id)
    if db_profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate {candidate_id} not found. Run extraction first."
        )

    from app.models.resumes import Resume
    resume = await db.get(Resume, db_profile.resume_id)
    if resume is None or resume.job_id != job_id:
        raise HTTPException(
            status_code=400,
            detail=f"Candidate {candidate_id} does not belong to job {job_id}."
        )

    background_tasks.add_task(
        upsert_candidate_vector,
        candidate_id=candidate_id,
        job_id=job_id,
        profile=db_profile.profile,
    )

    logger.info(f"Scheduled embedding for candidate {candidate_id} (job {job_id}).")
    return {
        "message": "Embedding started in the background.",
        "candidate_id": str(candidate_id),
        "job_id": str(job_id),
    }


# ──────────────────────────────────────────────────────────────────────
# POST /jobs/{job_id}/embed-all
# Embed ALL candidates for a job in one shot
# ──────────────────────────────────────────────────────────────────────

@router.post(
    "/jobs/{job_id}/embed-all",
    status_code=202,
    summary="Embed ALL extracted candidates for a job",
    description=(
        "Finds all candidate profiles linked to this job and schedules them "
        "all for embedding into Qdrant. Run this after you've extracted profiles "
        "for all uploaded resumes. Returns 202 immediately."
    ),
)
async def embed_all_candidates(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Embed all candidates for a job — a convenience batch route."""

    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    from app.models.resumes import Resume

    result = await db.execute(
        select(Resume.id).where(Resume.job_id == job_id)
    )
    resume_ids = [row[0] for row in result.all()]

    if not resume_ids:
        return {"message": "No resumes found for this job. Upload resumes first.", "scheduled": 0}

    result = await db.execute(
        select(CandidateProfileModel).where(
            CandidateProfileModel.resume_id.in_(resume_ids)
        )
    )
    profiles = result.scalars().all()

    if not profiles:
        return {"message": "No extracted profiles found. Run extraction first.", "scheduled": 0}

    for profile in profiles:
        background_tasks.add_task(
            upsert_candidate_vector,
            candidate_id=profile.candidate_id,
            job_id=job_id,
            profile=profile.profile,
        )

    count = len(profiles)
    logger.info(f"Scheduled embedding for {count} candidates (job {job_id}).")
    return {
        "message": f"Embedding started for {count} candidates in the background.",
        "scheduled": count,
        "job_id": str(job_id),
    }


# ──────────────────────────────────────────────────────────────────────
# POST /jobs/{job_id}/rank   ← NEW Phase 4
# Compute hybrid scores for all candidates of a job
# ──────────────────────────────────────────────────────────────────────

@router.post(
    "/jobs/{job_id}/rank",
    response_model=List[RankingResponse],
    summary="Run hybrid ranking for all candidates (Phase 4)",
    description=(
        "For every candidate who has a semantic_score (from Phase 3 embedding), "
        "this computes skill_overlap_score, experience_fit_score, and final_score. "
        "Results are saved to the rankings table and returned sorted by final_score (best first). "
        "Run GET /jobs/{job_id}/rankings first to populate semantic scores."
    ),
)
async def run_hybrid_ranking(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Phase 4: Compute full hybrid scores for all candidates of a job.

    Steps:
    1. Load the job (need required_skills, nice_to_have_skills, min_experience_years).
    2. Find all ranking rows for this job (they have semantic_score from Phase 3).
    3. For each candidate, load their profile and compute skill + experience scores.
    4. Compute final_score = weighted combination of all 3 scores.
    5. Save all scores back to the rankings table and return sorted results.
    """
    from app.services.ranking import (
        compute_skill_overlap,
        compute_experience_fit,
        compute_final_score,
    )

    # Step 1: Load the job
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    required_skills     = job.required_skills     or []
    nice_to_have_skills = job.nice_to_have_skills or []
    min_experience      = float(job.min_experience_years) if job.min_experience_years else None

    # Step 2: Find all ranking rows for this job
    result = await db.execute(
        select(Ranking).where(Ranking.job_id == job_id)
    )
    ranking_rows = result.scalars().all()

    if not ranking_rows:
        raise HTTPException(
            status_code=404,
            detail=(
                "No candidates found in the rankings table for this job. "
                "Run Phase 3 first: POST /jobs/{job_id}/embed-all, "
                "then GET /jobs/{job_id}/rankings to populate semantic scores."
            ),
        )

    # Steps 3-4: Score each candidate
    for row in ranking_rows:
        profile_row = await db.get(CandidateProfileModel, row.candidate_id)
        if profile_row is None:
            continue  # skip if profile is missing

        profile          = profile_row.profile
        candidate_years  = float(profile.get("experience_years", 0.0))

        # Fetch the original raw resume text so we don't miss skills in the summary/experience sections
        from app.models.resumes import Resume
        resume_row = await db.get(Resume, profile_row.resume_id)
        full_resume_text = resume_row.raw_text if resume_row else " ".join(profile.get("skills", []))

        skill_score = compute_skill_overlap(
            candidate_skills=[full_resume_text],
            required_skills=required_skills,
            nice_to_have_skills=nice_to_have_skills,
        )
        experience_score = compute_experience_fit(
            candidate_years=candidate_years,
            required_years=min_experience,
        )
        semantic = float(row.semantic_score) if row.semantic_score is not None else 0.0

        final = compute_final_score(
            semantic_score=semantic,
            skill_overlap_score=skill_score,
            experience_fit_score=experience_score,
        )

        # Save scores back to the DB row
        row.skill_overlap_score  = skill_score
        row.experience_fit_score = experience_score
        row.final_score          = final

    # Step 5: Commit and return sorted results
    await db.commit()

    result = await db.execute(
        select(Ranking)
        .where(Ranking.job_id == job_id)
        .order_by(Ranking.final_score.desc())
    )
    rankings = result.scalars().all()

    logger.info(f"Phase 4 done for job {job_id}: {len(rankings)} candidates scored.")
    return rankings


# ──────────────────────────────────────────────────────────────────────
# GET /jobs/{job_id}/rankings
# Return ranked candidates for a job
# ──────────────────────────────────────────────────────────────────────

@router.get(
    "/jobs/{job_id}/rankings",
    response_model=List[RankingResponse],
    summary="Get ranked candidates for a job",
    description=(
        "Returns candidates for a job ordered by final_score (if Phase 4 has run) "
        "or semantic_score (if only Phase 3 has run). "
        "Use ?top_k=N to control how many results to return (default: 20)."
    ),
)
async def get_rankings(
    job_id: uuid.UUID,
    top_k: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    Search Qdrant for top candidates, save semantic scores to Postgres,
    then return the full ranked list.
    """

    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    job_text = f"{job.title}\n{job.description}"

    try:
        search_results = search_candidates(
            job_description=job_text,
            job_id=job_id,
            top_k=top_k,
        )
    except Exception as e:
        error_msg = str(e)
        if "Not found: Collection" in error_msg:
            # Collection hasn't been created yet by the background tasks.
            # Safe to return empty list while we wait.
            return []
            
        logger.error(f"Qdrant search failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=(
                "Could not reach the vector store. "
                "Make sure Qdrant is running and candidates have been embedded. "
                f"Error: {error_msg}"
            ),
        )

    if not search_results:
        return []

    # Save/update semantic scores
    for result in search_results:
        candidate_id   = uuid.UUID(result["candidate_id"])
        semantic_score = result["semantic_score"]

        existing = await db.execute(
            select(Ranking).where(
                Ranking.job_id == job_id,
                Ranking.candidate_id == candidate_id,
            )
        )
        ranking_row = existing.scalar_one_or_none()

        if ranking_row is None:
            ranking_row = Ranking(
                job_id=job_id,
                candidate_id=candidate_id,
                semantic_score=semantic_score,
            )
            db.add(ranking_row)
        else:
            # Update the existing row's semantic score
            ranking_row.semantic_score = semantic_score

    await db.commit()

    # Step 4: Fetch and return the rankings, ordered by semantic_score (best first)
    result = await db.execute(
        select(Ranking)
        .where(Ranking.job_id == job_id)
        .order_by(Ranking.semantic_score.desc())   # desc = highest first
        .limit(top_k)
    )
    rankings = result.scalars().all()

    logger.info(f"Returning {len(rankings)} rankings for job {job_id}.")
    return rankings

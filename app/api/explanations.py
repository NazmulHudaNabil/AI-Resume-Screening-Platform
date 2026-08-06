"""
explanations.py — Explanation API Routes (Phase 5)
====================================================

Routes:
  POST /jobs/{job_id}/candidates/{candidate_id}/explain
    → Generate (or return cached) explanation for ONE candidate.

  POST /jobs/{job_id}/explain-all
    → Generate explanations for ALL ranked candidates of a job.
      Runs in the background so the caller doesn't wait.

Both routes require that Phase 4 has already run (candidates need
a final_score in the rankings table before we can explain them).
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
from app.services.explanation import generate_explanation

logger = logging.getLogger(__name__)

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────
# POST /jobs/{job_id}/candidates/{candidate_id}/explain
# Generate explanation for ONE candidate
# ──────────────────────────────────────────────────────────────────────

@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/explain",
    response_model=RankingResponse,
    summary="Generate explanation for one candidate (Phase 5)",
    description=(
        "Uses Groq LLM to write a 2–3 sentence explanation of why this candidate "
        "scored the way they did. The explanation is cached in Redis for 24 hours. "
        "Requires Phase 4 (POST /jobs/{job_id}/rank) to have run first."
    ),
)
async def explain_candidate(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate and save an explanation for a single candidate.

    Steps:
    1. Load the job (need title, description, required_skills).
    2. Load the candidate's ranking row (need the scores).
    3. Load the candidate's profile (need skills, experience, etc.).
    4. Call the explanation service (checks Redis cache first).
    5. Save the explanation to the ranking row in Postgres.
    6. Return the updated ranking row.
    """

    # ── Step 1: Load the job ──────────────────────────────────────────
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    # ── Step 2: Load the ranking row ──────────────────────────────────
    result = await db.execute(
        select(Ranking).where(
            Ranking.job_id == job_id,
            Ranking.candidate_id == candidate_id,
        )
    )
    ranking = result.scalar_one_or_none()

    if ranking is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No ranking found for candidate {candidate_id} in job {job_id}. "
                "Run Phase 3 (embed) and Phase 4 (rank) first."
            ),
        )

    if ranking.final_score is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "This candidate has no final_score yet. "
                "Run Phase 4 first: POST /jobs/{job_id}/rank"
            ),
        )

    # ── Step 3: Load the candidate's profile ─────────────────────────
    profile_row = await db.get(CandidateProfileModel, candidate_id)
    if profile_row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate profile {candidate_id} not found."
        )
        
    from app.models.resumes import Resume
    resume_row = await db.get(Resume, profile_row.resume_id)
    full_resume_text = resume_row.raw_text if resume_row else " ".join(profile_row.profile.get("skills", []))

    # ── Step 4: Generate explanation (uses Redis cache) ───────────────
    try:
        explanation_text = generate_explanation(
            job_id=str(job_id),
            candidate_id=str(candidate_id),
            job_title=job.title,
            job_description=job.description,
            required_skills=job.required_skills or [],
            profile=profile_row.profile,
            full_resume_text=full_resume_text,
            semantic_score=float(ranking.semantic_score or 0),
            skill_overlap_score=float(ranking.skill_overlap_score or 0),
            experience_fit_score=float(ranking.experience_fit_score or 0),
            final_score=float(ranking.final_score or 0),
        )
    except Exception as e:
        logger.error(f"Failed to generate explanation for {candidate_id}: {e}")
        explanation_text = "Error: Explanation could not be generated (likely due to LLM rate limits). Please try again later."

    # ── Step 5: Save to Postgres ──────────────────────────────────────
    ranking.explanation = explanation_text
    await db.commit()
    await db.refresh(ranking)

    logger.info(f"Explanation saved for candidate {candidate_id} (job {job_id}).")

    # ── Step 6: Return the updated ranking row ────────────────────────
    return ranking


# ──────────────────────────────────────────────────────────────────────
# POST /jobs/{job_id}/explain-all
# Generate explanations for ALL ranked candidates of a job
# ──────────────────────────────────────────────────────────────────────

@router.post(
    "/jobs/{job_id}/explain-all",
    status_code=202,
    summary="Generate explanations for all candidates (Phase 5)",
    description=(
        "Generates LLM explanations for every candidate who has a final_score "
        "for this job. Runs in the background — returns 202 immediately. "
        "Requires Phase 4 (POST /jobs/{job_id}/rank) to have run first."
    ),
)
async def explain_all_candidates(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Queue explanation generation for all ranked candidates of a job.

    Steps:
    1. Load the job.
    2. Find all ranking rows for this job that have a final_score.
    3. Schedule a background task to generate explanations for each.
    4. Return 202 immediately.
    """

    # Step 1: Load the job
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    # Step 2: Find all ranked candidates for this job
    result = await db.execute(
        select(Ranking).where(
            Ranking.job_id == job_id,
            Ranking.final_score.is_not(None),   # only candidates with a score
        )
    )
    ranking_rows = result.scalars().all()

    if not ranking_rows:
        return {
            "message": (
                "No ranked candidates found for this job. "
                "Run Phase 4 first: POST /jobs/{job_id}/rank"
            ),
            "scheduled": 0,
        }

    # Step 3: Schedule a single background task for all of them
    # We pass the job_id so the background function can query the DB itself
    background_tasks.add_task(
        _generate_all_explanations_task,
        job_id=job_id,
    )

    count = len(ranking_rows)
    logger.info(f"Scheduled explanation generation for {count} candidates (job {job_id}).")

    return {
        "message": f"Explanation generation started for {count} candidates in the background.",
        "scheduled": count,
        "job_id": str(job_id),
    }


# ──────────────────────────────────────────────────────────────────────
# BACKGROUND TASK — runs after the response is sent
# ──────────────────────────────────────────────────────────────────────

async def _generate_all_explanations_task(job_id: uuid.UUID) -> None:
    """
    Background task: generate and save explanations for all candidates of a job.

    This runs AFTER the API response is sent to the user, so they don't have
    to wait for all the LLM calls to complete.
    """
    from app.db.session import async_session_maker

    async with async_session_maker() as db:
        # Load the job
        job = await db.get(Job, job_id)
        if job is None:
            logger.error(f"Background task: job {job_id} not found.")
            return

        # Find all ranked candidates
        result = await db.execute(
            select(Ranking).where(
                Ranking.job_id == job_id,
                Ranking.final_score.is_not(None),
            )
        )
        ranking_rows = result.scalars().all()

        # Generate explanation for each candidate
        for ranking in ranking_rows:
            profile_row = await db.get(CandidateProfileModel, ranking.candidate_id)
            if profile_row is None:
                continue

            from app.models.resumes import Resume
            resume_row = await db.get(Resume, profile_row.resume_id)
            full_resume_text = resume_row.raw_text if resume_row else " ".join(profile_row.profile.get("skills", []))

            try:
                explanation_text = generate_explanation(
                    job_id=str(job_id),
                    candidate_id=str(ranking.candidate_id),
                    job_title=job.title,
                    job_description=job.description,
                    required_skills=job.required_skills or [],
                    profile=profile_row.profile,
                    full_resume_text=full_resume_text,
                    semantic_score=float(ranking.semantic_score or 0),
                    skill_overlap_score=float(ranking.skill_overlap_score or 0),
                    experience_fit_score=float(ranking.experience_fit_score or 0),
                    final_score=float(ranking.final_score or 0),
                )
                ranking.explanation = explanation_text

            except Exception as e:
                logger.error(
                    f"Failed to generate explanation for candidate "
                    f"{ranking.candidate_id}: {e}"
                )
                ranking.explanation = "Error: Explanation could not be generated (likely due to LLM rate limits). Please try again later."
                continue  # skip this one, try the next

        await db.commit()
        logger.info(
            f"Background task done: explanations generated for job {job_id}."
        )

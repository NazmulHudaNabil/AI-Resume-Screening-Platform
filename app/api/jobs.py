"""
jobs.py — Job API Routes
========================

This file handles everything related to Jobs.
A Job must exist FIRST before you can upload resumes to it.

Routes defined here:
  - POST /jobs        → Create a new job posting
  - GET  /jobs        → List all jobs
  - GET  /jobs/{id}   → Get one job by its ID
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.jobs import Job
from app.schemas.job import JobCreate, JobResponse
from app.api.deps import get_current_user, rate_limiter

# All routes in this file will be grouped under the "jobs" tag in Swagger
router = APIRouter()


# ──────────────────────────────────────────────────────────────────────
# POST /jobs
# Create a brand-new job posting
# ──────────────────────────────────────────────────────────────────────

@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=201,                    # 201 = "Created" (not just 200 = "OK")
    summary="Create a new job posting",
    description=(
        "Creates a new job in the database. "
        "The returned job ID is what you need to upload resumes."
    ),
)
async def create_job(
    job_data: JobCreate,                # the JSON body sent by the user
    db: AsyncSession = Depends(get_db), # database connection (auto-injected)
    current_user: dict = Depends(get_current_user), # JWT auth required
):
    """
    Create a new job posting.

    Steps:
    1. Take the data the user sent (title, description, skills, etc.)
    2. Create a new Job row in the database
    3. Return the saved job (including the auto-generated ID)

    The job ID in the response is what you pass to:
        POST /api/v1/jobs/{job_id}/resumes
    """

    # Step 1: Build the Job database object from the user's input
    new_job = Job(
        title=job_data.title,
        description=job_data.description,
        required_skills=job_data.required_skills,
        nice_to_have_skills=job_data.nice_to_have_skills,
        min_experience_years=job_data.min_experience_years,
    )

    # Step 2: Save it to the database
    db.add(new_job)        # stage the new row
    await db.commit()      # write it to the database
    await db.refresh(new_job)  # reload it so we get the auto-generated id + created_at

    # Step 3: Return the saved job
    return new_job


# ──────────────────────────────────────────────────────────────────────
# GET /jobs
# List all jobs
# ──────────────────────────────────────────────────────────────────────

@router.get(
    "/jobs",
    response_model=List[JobResponse],
    summary="List all job postings",
    description="Returns a list of all jobs stored in the database.",
    dependencies=[Depends(rate_limiter(times=10, seconds=60))],
)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
):
    """Fetch all jobs from the database."""

    # Run a SELECT * FROM jobs query
    result = await db.execute(select(Job))
    jobs = result.scalars().all()  # .scalars() gets Job objects, .all() makes a list

    return jobs


# ──────────────────────────────────────────────────────────────────────
# GET /jobs/{job_id}
# Get a single job by its ID
# ──────────────────────────────────────────────────────────────────────

@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get a single job by ID",
    description="Fetch the full details of one specific job posting.",
    dependencies=[Depends(rate_limiter(times=10, seconds=60))],
)
async def get_job(
    job_id: uuid.UUID,                  # taken from the URL path
    db: AsyncSession = Depends(get_db),
):
    """Look up a single job by its UUID."""

    # db.get() is a shortcut: SELECT * FROM jobs WHERE id = job_id
    job = await db.get(Job, job_id)

    if job is None:
        # 404 = "Not Found"
        raise HTTPException(
            status_code=404,
            detail=f"Job with id={job_id} not found."
        )

    return job

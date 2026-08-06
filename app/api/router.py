from fastapi import APIRouter

# Phase 0 — Job postings (must create a job BEFORE uploading resumes)
from app.api.jobs import router as jobs_router

# Phase 1 — Resume ingestion
from app.api.resumes import router as resumes_router

# Phase 2 — Candidate profile extraction
from app.api.candidates import router as candidates_router

# Phase 3 — Embedding & Vector Store (rankings)
from app.api.rankings import router as rankings_router

# Phase 5 — Explanation Generation
from app.api.explanations import router as explanations_router

# Auth — JWT Token generation
from app.api.auth import router as auth_router

# ----------------------------------------------------------------
# The main API router.
# All routes registered here will be available under /api/v1/...
#
# Full route list:
#   POST   /api/v1/jobs                                            ← create a job
#   GET    /api/v1/jobs                                            ← list all jobs
#   GET    /api/v1/jobs/{job_id}                                   ← get one job
#   POST   /api/v1/jobs/{job_id}/resumes                          ← upload resumes
#   POST   /api/v1/jobs/{job_id}/resumes/{id}/extract             ← run LLM extraction
#   POST   /api/v1/jobs/{job_id}/candidates/{id}/embed            ← embed one candidate
#   POST   /api/v1/jobs/{job_id}/embed-all                        ← embed all candidates
#   GET    /api/v1/jobs/{job_id}/rankings                         ← get ranked list
#   POST   /api/v1/jobs/{job_id}/rank                             ← run hybrid scoring
#   POST   /api/v1/jobs/{job_id}/candidates/{id}/explain          ← explain one candidate
#   POST   /api/v1/jobs/{job_id}/explain-all                      ← explain all candidates
#   GET    /api/v1/candidates/{candidate_id}                      ← view profile
#   DELETE /api/v1/candidates/{candidate_id}                      ← delete profile
# ----------------------------------------------------------------
api_router = APIRouter(prefix="/api/v1")

# Auth: JWT Token generation
api_router.include_router(auth_router, tags=["auth"])

# Phase 0: Jobs — register FIRST (dependency for everything else)
api_router.include_router(jobs_router, tags=["jobs"])

# Phase 1: Resumes — upload + ingest
api_router.include_router(resumes_router, tags=["resumes"])

# Phase 2: Candidates — extract, get, delete profiles
api_router.include_router(candidates_router, tags=["candidates"])

# Phase 3 & 4: Rankings — embed into Qdrant + hybrid scoring
api_router.include_router(rankings_router, tags=["rankings"])

# Phase 5: Explanations — LLM explanation + Redis cache
api_router.include_router(explanations_router, tags=["explanations"])

"""
embedding.py — Embedding & Vector Store Service (Phase 3)
==========================================================

This module handles two jobs:
  1. EMBED TEXT — Convert a piece of text (candidate profile or job description)
                  into a list of numbers (a "vector") using Google Gemini's
                  embedding model. Vectors capture the *meaning* of text.

  2. STORE & SEARCH — Save those vectors in Qdrant (a vector database) and
                      later search for the most similar ones.

Why do we need embeddings?
  - Two resumes can say the same thing in different words.
    e.g. "5 years building web services" vs "Senior backend engineer, half a decade exp."
  - Normal keyword matching misses this. Embeddings understand *meaning*.
  - We embed both the job description AND each candidate profile, then measure
    how "close" they are in meaning → that's the semantic score.

Qdrant collection name: "candidates"
  - Each point (item) in the collection = one candidate profile
  - Payload (extra data stored with each point):
      { "candidate_id": "...", "job_id": "...", "skills": [...] }
"""

import logging
import uuid
from typing import Optional

from google import genai
from google.genai import types as genai_types
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from app.core.config import settings

# Logger for this module
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────

# The name of our collection inside Qdrant (like a table name in SQL)
COLLECTION_NAME = "candidates"

# Google Gemini's text-embedding model
# "gemini-embedding-2" outputs 3072-dimensional vectors
EMBEDDING_MODEL = "gemini-embedding-2"

# The size of the vectors this model produces
VECTOR_SIZE = 3072


# ─────────────────────────────────────────────────────────────────────
# CLIENT SETUP
# Build the Qdrant and Gemini clients once, reuse everywhere
# ─────────────────────────────────────────────────────────────────────

def get_qdrant_client() -> QdrantClient:
    """
    Create and return a Qdrant client.

    Uses the cloud endpoint if configured, otherwise falls back to local.
    Local Qdrant: runs via docker-compose on http://localhost:6333
    Cloud Qdrant: set QDRANT_CLUSTER_ENDPOINT and QDRANT_API_KEY in .env
    """
    # If a cloud endpoint is set in .env, use it
    if settings.qdrant_cluster_endpoint:
        logger.info("Connecting to Qdrant Cloud ...")
        return QdrantClient(
            url=settings.qdrant_cluster_endpoint,
            api_key=settings.qdrant_api_key,
        )

    # Otherwise fall back to local Qdrant (docker-compose)
    logger.info(f"Connecting to local Qdrant at {settings.qdrant_url} ...")
    return QdrantClient(url=settings.qdrant_url)


def _get_genai_client() -> genai.Client:
    """Create and return a configured Gemini client using our API key from .env."""
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set in .env. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )
    return genai.Client(api_key=settings.gemini_api_key)


# ─────────────────────────────────────────────────────────────────────
# STEP 1: EMBED TEXT
# Turn a string of text into a list of 768 numbers
# ─────────────────────────────────────────────────────────────────────

def embed_text(text: str) -> list[float]:
    """
    Convert text into a vector (list of 768 floats) using Gemini embeddings.

    What is a vector?
    -----------------
    Imagine mapping every possible sentence onto a big map.
    Sentences with similar meanings end up near each other on the map.
    A vector is just the "coordinates" of a sentence on that map.

    Example:
        embed_text("Python developer with FastAPI experience")
        → [0.023, -0.145, 0.872, ...]   (768 numbers)

    Args:
        text: Any string — a resume profile summary or job description.

    Returns:
        A list of 768 floats representing the meaning of the text.
    """
    client = _get_genai_client()

    logger.info(f"Embedding text ({len(text)} chars) ...")

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=genai_types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",  # optimized for search/retrieval
        ),
    )

    # result.embeddings[0].values is the list of 768 floats
    return result.embeddings[0].values


# ─────────────────────────────────────────────────────────────────────
# STEP 2: BUILD THE TEXT TO EMBED FOR A CANDIDATE
# We combine the candidate's profile fields into one readable string
# ─────────────────────────────────────────────────────────────────────

def build_candidate_text(profile: dict) -> str:
    """
    Build a single text string from a candidate's extracted profile.

    Instead of embedding raw JSON (which is hard for the model to understand),
    we build a natural-language summary of the candidate.

    Example output:
        "Name: Alice Johnson
         Skills: Python, FastAPI, Docker, PostgreSQL
         Experience: 4.0 years
         Education: B.Sc. Computer Science
         Roles: Backend Developer, Software Engineer
         Certifications: AWS Certified Developer"

    Args:
        profile: A dict from the CandidateProfile (stored in DB as JSONB).

    Returns:
        A human-readable string summarizing the candidate.
    """
    lines = [
        f"Name: {profile.get('name', 'Unknown')}",
        f"Skills: {', '.join(profile.get('skills', []))}",
        f"Experience: {profile.get('experience_years', 0)} years",
        f"Education: {', '.join(profile.get('education', []))}",
        f"Roles: {', '.join(profile.get('roles', []))}",
        f"Certifications: {', '.join(profile.get('certifications', []))}",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# STEP 3: ENSURE COLLECTION EXISTS
# Create the Qdrant "candidates" collection if it doesn't exist yet
# ─────────────────────────────────────────────────────────────────────

def ensure_collection_exists(client: QdrantClient) -> None:
    """
    Make sure the "candidates" collection exists in Qdrant.
    If it already exists, do nothing. If not, create it.

    Think of a Qdrant collection like a database table —
    it needs to exist before you can insert data into it.

    We use:
      - VECTOR_SIZE = 3072   (must match the embedding model output size)
      - Distance = COSINE   (how to measure similarity between vectors)
        Cosine similarity ranges from -1 (opposite) to 1 (identical meaning)
    """
    existing = client.get_collections().collections
    existing_names = [c.name for c in existing]

    if COLLECTION_NAME not in existing_names:
        logger.info(f"Creating Qdrant collection '{COLLECTION_NAME}' ...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,       # 3072 numbers per vector
                distance=Distance.COSINE,  # measure by angle/direction, not distance
            ),
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="job_id",
            field_schema="keyword"
        )
        logger.info(f"Collection '{COLLECTION_NAME}' created successfully.")
    else:
        logger.info(f"Collection '{COLLECTION_NAME}' already exists.")


# ─────────────────────────────────────────────────────────────────────
# STEP 4: UPSERT (SAVE) A CANDIDATE VECTOR INTO QDRANT
# ─────────────────────────────────────────────────────────────────────

def upsert_candidate_vector(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    profile: dict,
) -> None:
    """
    Embed a candidate's profile and save it to Qdrant.

    "Upsert" = Insert if new, Update if already exists.
    We use candidate_id as the unique point ID in Qdrant.

    What gets saved:
      - The 3072-dimensional vector (the "meaning" of the candidate's profile)
      - Payload metadata: candidate_id, job_id, skills[]
        (used later to filter searches to one specific job)

    Args:
        candidate_id: UUID of the candidate profile row in Postgres.
        job_id:       UUID of the job this candidate applied for.
        profile:      The JSONB profile dict from the DB (skills, experience, etc.)
    """
    # Build the text summary and embed it
    text = build_candidate_text(profile)
    vector = embed_text(text)

    # Connect to Qdrant
    client = get_qdrant_client()
    ensure_collection_exists(client)

    # PointStruct = one item to store in Qdrant
    point = PointStruct(
        id=str(candidate_id),   # unique ID for this point
        vector=vector,          # the 3072 embedding numbers
        payload={               # extra metadata stored alongside the vector
            "candidate_id": str(candidate_id),
            "job_id": str(job_id),
            "skills": profile.get("skills", []),
        },
    )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[point],
    )

    logger.info(
        f"Upserted candidate {candidate_id} into Qdrant "
        f"(job_id={job_id})"
    )


# ─────────────────────────────────────────────────────────────────────
# STEP 5: SEARCH — find top-k candidates for a job description
# ─────────────────────────────────────────────────────────────────────

def search_candidates(
    job_description: str,
    job_id: uuid.UUID,
    top_k: int = 50,
) -> list[dict]:
    """
    Embed the job description and find the top-k most similar candidates
    in Qdrant — but ONLY candidates who applied for THIS specific job.

    How it works:
      1. Embed the job description text → get a 3072-dim vector
      2. Ask Qdrant: "find the points whose vector is most similar to this"
      3. Filter results to only include this job's candidates
      4. Return the top_k results, each with a similarity score

    Args:
        job_description: The full text of the job description.
        job_id:          Only return candidates for this job.
        top_k:           How many top candidates to return (default 50).

    Returns:
        A list of dicts, each containing:
          {
            "candidate_id": "...",
            "job_id": "...",
            "skills": [...],
            "semantic_score": 0.87   ← cosine similarity (0 to 1, higher = better)
          }
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    # Step 1: Embed the job description
    logger.info(f"Embedding job description for search (job_id={job_id}) ...")
    query_vector = embed_text(job_description)

    # Step 2: Connect to Qdrant
    client = get_qdrant_client()

    # Step 3: Search with a filter — only candidates from this job
    # Filter: only return points where payload["job_id"] == job_id
    job_filter = Filter(
        must=[
            FieldCondition(
                key="job_id",
                match=MatchValue(value=str(job_id)),
            )
        ]
    )

    logger.info(f"Searching Qdrant for top {top_k} candidates ...")
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=job_filter,
        limit=top_k,
        with_payload=True,   # include the metadata in results
    )

    # Step 4: Format and return the results
    candidates = []
    for hit in results.points:
        candidates.append({
            "candidate_id": hit.payload["candidate_id"],
            "job_id": hit.payload["job_id"],
            "skills": hit.payload.get("skills", []),
            "semantic_score": round(hit.score, 4),  # cosine similarity score
        })

    logger.info(f"Found {len(candidates)} candidates via semantic search.")
    return candidates

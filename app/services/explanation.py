"""
explanation.py — LLM Explanation Service (Phase 5)
====================================================

This module generates a short, human-readable explanation for each
ranked candidate — telling the recruiter WHY this candidate scored
the way they did.

How it works:
  1. Build a prompt from: job description + candidate profile + score breakdown
  2. Send it to Groq LLM (llama-3.3-70b-versatile)
     → If the primary key fails (rate limit, quota), retry with fallback key
  3. Cache the result in Redis (so we don't re-call the LLM for the same candidate)
  4. Return the explanation text

Model used: llama-3.3-70b-versatile (same model for both primary and fallback keys)

Redis cache key format:
  "explanation:{job_id}:{candidate_id}:{profile_hash}"

  profile_hash = MD5 of the profile dict, so if the profile changes,
  the cache is automatically invalidated (old key is never matched).

Cache TTL: 24 hours
"""

import hashlib
import json
import logging

import redis
from groq import Groq, APIError

from app.core.config import settings

logger = logging.getLogger(__name__)

# How long to keep explanations in Redis (seconds)
CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours

# The LLM model — same model used by extraction.py
LLM_MODEL = "llama-3.3-70b-versatile"


# ─────────────────────────────────────────────────────────────────────
# REDIS CLIENT
# ─────────────────────────────────────────────────────────────────────

def get_redis_client():
    """
    Create and return a Redis client.
    Prefers Upstash REST API for maximum cloud compatibility.
    Falls back to standard REDIS_URL otherwise.
    """
    if settings.upstash_redis_rest_url and settings.upstash_redis_rest_token:
        from upstash_redis import Redis as UpstashRedis
        return UpstashRedis(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token
        )

    url = settings.redis_url.strip('"').strip("'")
    if url.startswith("http"):
        raise ValueError(
            "You provided an HTTP REST URL for REDIS_URL. Please set UPSTASH_REDIS_REST_URL instead."
        )

    ssl_kwargs = {"ssl_cert_reqs": "none"} if url.startswith("rediss://") else {}
    return redis.from_url(
        url,
        decode_responses=True,  # always return strings, not bytes
        **ssl_kwargs
    )


# ─────────────────────────────────────────────────────────────────────
# CACHE KEY BUILDER
# ─────────────────────────────────────────────────────────────────────

def _make_cache_key(job_id: str, profile: dict, full_resume_text: str) -> str:
    """
    Build a unique Redis key for this (job, profile, resume) combination.

    We hash the extracted profile and the raw resume text. This guarantees that
    if the EXACT same resume is uploaded again for the same job, it will hit the cache
    even though the candidate_id is brand new!

    Example key:
      "explanation:abc-123:a1b2c3d4"
    """
    content_to_hash = json.dumps(profile, sort_keys=True) + full_resume_text
    content_hash = hashlib.md5(content_to_hash.encode("utf-8")).hexdigest()[:12]

    return f"explanation:{job_id}:{content_hash}"


# ─────────────────────────────────────────────────────────────────────
# THE PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────

def _build_prompt(
    job_title: str,
    job_description: str,
    required_skills: list[str],
    profile: dict,
    full_resume_text: str,
    semantic_score: float,
    skill_overlap_score: float,
    experience_fit_score: float,
    final_score: float,
) -> str:
    """
    Build the message sent to the LLM.
    """
    candidate_skills = ", ".join(profile.get("skills", [])) or "none listed"
    
    import re
    def get_words(text: str) -> set[str]:
        words = re.findall(r'[a-z0-9]+', text)
        return {w for w in words if len(w) > 2 or w in ('c', 'go', 'r', 'qa', 'ux', 'ui')}

    matched = []
    missing = []
    for req in required_skills:
        req_lower = req.lower().strip()
        req_words = get_words(req_lower)
        
        is_match = False
        # Check against the ENTIRE raw resume text
        for cand in [full_resume_text]:
            cand_lower = cand.lower().strip()
            # Direct substring
            if req_lower in cand_lower or cand_lower in req_lower:
                is_match = True
                break
            
            # Word-level intersection
            cand_words = get_words(cand_lower)
            shared = req_words & cand_words
            if len(shared) >= 1 and len(req_words) > 0:
                is_match = True
                break
                
        if is_match:
            matched.append(req)
        else:
            missing.append(req)

    return f"""You are a recruiting assistant. Write a 2-3 sentence explanation of why this candidate
scored the way they did for the job below. Be specific — mention actual skills.
Do NOT use generic filler like "strong candidate" or "great fit". Reference real matched/missing skills.

JOB TITLE: {job_title}
JOB DESCRIPTION: {job_description[:500]}
REQUIRED SKILLS: {', '.join(required_skills) or 'not specified'}

CANDIDATE PROFILE:
- Name: {profile.get('name', 'Unknown')}
- Skills: {candidate_skills}
- Experience: {profile.get('experience_years', 0)} years
- Roles: {', '.join(profile.get('roles', [])) or 'none listed'}
- Education: {', '.join(profile.get('education', [])) or 'none listed'}

SCORE BREAKDOWN:
- Semantic match: {semantic_score:.0%}
- Skill overlap:  {skill_overlap_score:.0%}  (matched: {matched or 'none'}, missing: {missing or 'none'})
- Experience fit: {experience_fit_score:.0%}
- FINAL SCORE:    {final_score:.0%}

Write the explanation now (2-3 sentences, specific, no generic filler):"""


# ─────────────────────────────────────────────────────────────────────
# GROQ CALLER WITH TRUE FALLBACK
# ─────────────────────────────────────────────────────────────────────

def _call_groq_with_fallback(prompt: str) -> str:
    """
    Call Groq LLM. If the primary key fails, automatically retry with the fallback key.

    Both keys use the same model: llama-3.3-70b-versatile

    Why two keys?
      Groq's free tier has rate limits. If the primary key hits its rate limit
      mid-request, the fallback key gives us a second chance — so the request
      succeeds instead of failing with an error.

    Attempt 1: GROQ_API_KEY        (primary)
    Attempt 2: GROQ_FALLBACK_API_KEY (fallback — only tried if attempt 1 fails)

    Raises ValueError if both keys are missing or both calls fail.
    """
    # Build a list of (label, api_key) to try in order
    keys_to_try = []
    if settings.groq_api_key:
        keys_to_try.append(("primary", settings.groq_api_key))
    if settings.groq_fallback_api_key:
        keys_to_try.append(("fallback", settings.groq_fallback_api_key))

    if not keys_to_try:
        raise ValueError(
            "No Groq API key configured. "
            "Set GROQ_API_KEY in your .env file."
        )

    last_error = ""

    for key_name, api_key in keys_to_try:
        try:
            logger.info(f"Calling Groq LLM with {key_name} key (model={LLM_MODEL}) ...")

            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model=LLM_MODEL,
                temperature=0.3,  # slightly creative, but not random
                max_tokens=200,   # 2-3 sentences is well under 200 tokens
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )
            text = response.choices[0].message.content.strip()
            logger.info(f"Groq call succeeded with {key_name} key.")
            return text

        except APIError as e:
            last_error = str(e)
            next_step = "Trying fallback key ..." if key_name == "primary" else "No more keys to try."
            logger.warning(f"Groq {key_name} key failed (APIError): {last_error}. {next_step}")

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Groq {key_name} key failed (unexpected error): {last_error}")

    # Both attempts failed
    raise ValueError(
        f"Groq LLM call failed with all available keys. Last error: {last_error}"
    )


# ─────────────────────────────────────────────────────────────────────
# MAIN FUNCTION — generate_explanation()
# ─────────────────────────────────────────────────────────────────────

def generate_explanation(
    job_id: str,
    candidate_id: str,
    job_title: str,
    job_description: str,
    required_skills: list[str],
    profile: dict,
    full_resume_text: str,
    semantic_score: float,
    skill_overlap_score: float,
    experience_fit_score: float,
    final_score: float,
) -> str:
    """
    Generate (or retrieve from cache) a short explanation for one candidate.
    """

    # ── Step 1: Build cache key ───────────────────────────────────────
    cache_key = _make_cache_key(job_id, profile, full_resume_text)

    # ── Step 2: Check Redis cache ─────────────────────────────────────
    r = None
    try:
        r = get_redis_client()
        cached = r.get(cache_key)
        if cached:
            logger.info(f"Cache HIT for candidate {candidate_id} — returning cached explanation.")
            return cached
        logger.info(f"Cache MISS for candidate {candidate_id} — calling LLM.")
    except Exception as e:
        # If Redis is down, skip caching but don't crash the whole request
        logger.warning(f"Redis unavailable, skipping cache: {e}")
        r = None

    # ── Step 3: Build prompt and call Groq (with fallback) ────────────
    prompt = _build_prompt(
        job_title=job_title,
        job_description=job_description,
        required_skills=required_skills,
        profile=profile,
        full_resume_text=full_resume_text,
        semantic_score=semantic_score,
        skill_overlap_score=skill_overlap_score,
        experience_fit_score=experience_fit_score,
        final_score=final_score,
    )

    explanation = _call_groq_with_fallback(prompt)
    logger.info(f"LLM generated explanation for candidate {candidate_id}.")

    # ── Step 4: Save to Redis cache (24h TTL) ────────────────────────
    if r is not None:
        try:
            r.setex(cache_key, CACHE_TTL_SECONDS, explanation)
            logger.info(f"Explanation cached for candidate {candidate_id} (TTL=24h).")
        except Exception as e:
            logger.warning(f"Could not write to Redis cache: {e}")

    # ── Step 5: Return the explanation ────────────────────────────────
    return explanation

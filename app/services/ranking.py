"""
ranking.py — Hybrid Scoring Service (Phase 4)
==============================================

This module calculates THREE scores for each candidate against a job,
then blends them into one final_score.

The three scores:
  1. semantic_score      — already computed in Phase 3 (from Qdrant)
  2. skill_overlap_score — how many required/bonus skills the candidate has
  3. experience_fit_score — how well the candidate's experience years match

Final formula (from Architecture.md):
  final = w1 * semantic + w2 * skill_overlap + w3 * experience_fit

Default weights: w1=0.5, w2=0.35, w3=0.15

All scores are floats between 0.0 and 1.0.
All functions are pure Python — no database, no HTTP calls — easy to test!
"""


# ─────────────────────────────────────────────────────────────────────
# DEFAULT WEIGHTS
# These control how much each score contributes to the final score.
# They must add up to 1.0.
# ─────────────────────────────────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "semantic": 0.5,         # 50% — how relevant the resume text is (Phase 3)
    "skill_overlap": 0.35,   # 35% — skills matching
    "experience_fit": 0.15,  # 15% — experience years matching
}


# ─────────────────────────────────────────────────────────────────────
# SCORE 1: SKILL OVERLAP
# ─────────────────────────────────────────────────────────────────────

def compute_skill_overlap(
    candidate_skills: list[str],
    required_skills: list[str],
    nice_to_have_skills: list[str],
) -> float:
    """
    Calculate how well a candidate's skills match the job requirements.

    Formula (from Architecture.md):
      score = (matched_required * 2 + matched_nice_to_have)
              / (total_required * 2 + total_nice_to_have)

    Why multiply required by 2?
      Required skills are more important than nice-to-have skills,
      so we give them double weight in the formula.

    Examples:
      Job needs: Python, FastAPI (required), Docker (nice to have)
      Candidate has: Python, Docker

      matched_required    = 1  (only Python matched)
      matched_nice_to_have = 1  (Docker matched)
      total_required      = 2
      total_nice_to_have  = 1

      score = (1*2 + 1) / (2*2 + 1) = 3/5 = 0.6

    Args:
        candidate_skills:    List of skills from the candidate's profile.
        required_skills:     Skills the job requires (must-have).
        nice_to_have_skills: Bonus skills (good-to-have but not required).

    Returns:
        A float between 0.0 (no match) and 1.0 (perfect match).
    """
    # If the job has no skill requirements, give everyone a perfect score
    if not required_skills and not nice_to_have_skills:
        return 1.0

    # Lowercase and strip
    candidate_skills_lower = [s.lower().strip() for s in candidate_skills]
    required_skills_lower  = [s.lower().strip() for s in required_skills]
    nice_skills_lower      = [s.lower().strip() for s in nice_to_have_skills]

    import re

    def get_words(text: str) -> set[str]:
        # Extract alphanumeric words longer than 2 chars
        words = re.findall(r'[a-z0-9]+', text)
        return {w for w in words if len(w) > 2 or w in ('c', 'go', 'r', 'qa', 'ux', 'ui')}

    def count_matches(target_skills, candidate_skills):
        matches = 0
        for target in target_skills:
            target_words = get_words(target)
            for cand in candidate_skills:
                # 1. Direct substring match (catches exact matches and "docker" in "basic docker knowledge")
                if target in cand or cand in target:
                    matches += 1
                    break
                
                # 2. Word-level overlap (catches "rest api design" matching "rest api development")
                cand_words = get_words(cand)
                shared_words = target_words & cand_words
                
                # If they share at least one meaningful word (e.g. "jwt", "api", "github")
                if len(shared_words) >= 1 and len(target_words) > 0:
                    matches += 1
                    break
        return matches

    matched_required     = count_matches(required_skills_lower, candidate_skills_lower)
    matched_nice_to_have = count_matches(nice_skills_lower, candidate_skills_lower)

    # Numerator and denominator from the formula
    numerator   = (matched_required * 2) + matched_nice_to_have
    denominator = (len(required_skills_lower) * 2) + len(nice_skills_lower)

    # Avoid division by zero (shouldn't happen given the check above, but safe)
    if denominator == 0:
        return 0.0

    return round(numerator / denominator, 4)


# ─────────────────────────────────────────────────────────────────────
# SCORE 2: EXPERIENCE FIT
# ─────────────────────────────────────────────────────────────────────

def compute_experience_fit(
    candidate_years: float,
    required_years: float | None,
) -> float:
    """
    Calculate how well the candidate's experience years match the job.

    Rules:
      - If the job has no experience requirement → score = 1.0 (everyone passes)
      - If candidate meets or exceeds the requirement → score = 1.0
      - If candidate is under the requirement → score decays linearly to 0
        The decay is: score = candidate_years / required_years
        Example: need 4 years, have 2 years → score = 2/4 = 0.5

    Why linear decay instead of a hard cutoff?
      A hard cutoff (0 or 1) is too harsh. A candidate with 3.5 years applying
      for a 4-year role is still a good candidate. Linear decay is fair and simple.

    Examples:
      required=4, candidate=4  → 1.0  (exact match)
      required=4, candidate=6  → 1.0  (overqualified still gets full score)
      required=4, candidate=2  → 0.5  (half the required experience)
      required=4, candidate=0  → 0.0  (no experience)
      required=None, candidate=anything → 1.0 (no requirement)

    Args:
        candidate_years: How many years of experience the candidate has.
        required_years:  Minimum years the job requires (None = no requirement).

    Returns:
        A float between 0.0 and 1.0.
    """
    # No requirement → full score for everyone
    if required_years is None or required_years <= 0:
        return 1.0

    # Candidate meets or exceeds the requirement → full score
    if candidate_years >= required_years:
        return 1.0

    # Candidate is under the requirement → linear decay
    # e.g. need 4 years, have 2 → score = 2/4 = 0.5
    score = candidate_years / required_years

    # Clamp to [0.0, 1.0] just to be safe
    return round(max(0.0, min(1.0, score)), 4)


# ─────────────────────────────────────────────────────────────────────
# FINAL SCORE: WEIGHTED COMBINATION
# ─────────────────────────────────────────────────────────────────────

def compute_final_score(
    semantic_score: float,
    skill_overlap_score: float,
    experience_fit_score: float,
    weights: dict | None = None,
) -> float:
    """
    Combine all three scores into one final score using weighted average.

    Formula:
      final = w1 * semantic + w2 * skill_overlap + w3 * experience_fit

    Default weights: semantic=0.5, skill_overlap=0.35, experience_fit=0.15

    Why these defaults?
      - Semantic score (50%) captures overall relevance — the most important signal.
      - Skill overlap (35%) gives concrete, verifiable skill matching.
      - Experience fit (15%) is a softer signal (years alone don't tell the full story).

    You can pass custom weights per job to change the balance.
    For example, for senior roles you might want experience_fit=0.30.

    Args:
        semantic_score:       0.0–1.0 from Qdrant cosine similarity.
        skill_overlap_score:  0.0–1.0 from compute_skill_overlap().
        experience_fit_score: 0.0–1.0 from compute_experience_fit().
        weights:              Optional dict with keys "semantic", "skill_overlap",
                              "experience_fit". Defaults to DEFAULT_WEIGHTS.

    Returns:
        A float between 0.0 and 1.0 (rounded to 4 decimal places).
    """
    w = weights or DEFAULT_WEIGHTS

    final = (
        w["semantic"]         * semantic_score
        + w["skill_overlap"]  * skill_overlap_score
        + w["experience_fit"] * experience_fit_score
    )

    # Clamp to [0.0, 1.0] to handle any floating point edge cases
    return round(max(0.0, min(1.0, final)), 4)

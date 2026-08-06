"""
test_ranking.py — Unit Tests for Phase 4 Scoring Functions
===========================================================

We test the three pure Python functions from app/services/ranking.py:
  - compute_skill_overlap()
  - compute_experience_fit()
  - compute_final_score()

These tests need NO database, NO server, NO Qdrant — just plain Python.
Run them with:  uv run pytest tests/test_ranking.py -v
"""

import pytest
from app.services.ranking import (
    compute_skill_overlap,
    compute_experience_fit,
    compute_final_score,
)


# ─────────────────────────────────────────────────────────────────────
# TESTS FOR compute_skill_overlap()
# ─────────────────────────────────────────────────────────────────────

class TestSkillOverlap:

    def test_perfect_match(self):
        """Candidate has ALL required skills → score = 1.0"""
        score = compute_skill_overlap(
            candidate_skills=["Python", "FastAPI", "Docker"],
            required_skills=["Python", "FastAPI", "Docker"],
            nice_to_have_skills=[],
        )
        assert score == 1.0

    def test_no_match(self):
        """Candidate has NONE of the required skills → score = 0.0"""
        score = compute_skill_overlap(
            candidate_skills=["Java", "Spring"],
            required_skills=["Python", "FastAPI"],
            nice_to_have_skills=[],
        )
        assert score == 0.0

    def test_partial_required_match(self):
        """Candidate has 1 of 2 required skills, no nice-to-have.
        Formula: (1*2 + 0) / (2*2 + 0) = 2/4 = 0.5
        """
        score = compute_skill_overlap(
            candidate_skills=["Python"],
            required_skills=["Python", "FastAPI"],
            nice_to_have_skills=[],
        )
        assert score == 0.5

    def test_required_plus_nice_to_have(self):
        """Candidate has 1 required + 1 nice-to-have out of 2 required + 1 nice.
        Formula: (1*2 + 1) / (2*2 + 1) = 3/5 = 0.6
        """
        score = compute_skill_overlap(
            candidate_skills=["Python", "Docker"],
            required_skills=["Python", "FastAPI"],
            nice_to_have_skills=["Docker"],
        )
        assert score == 0.6

    def test_case_insensitive(self):
        """'python' and 'PYTHON' should be treated as the same skill."""
        score = compute_skill_overlap(
            candidate_skills=["PYTHON", "FASTAPI"],
            required_skills=["python", "fastapi"],
            nice_to_have_skills=[],
        )
        assert score == 1.0

    def test_no_requirements_gives_perfect_score(self):
        """If the job has no skill requirements, everyone gets 1.0."""
        score = compute_skill_overlap(
            candidate_skills=["Python"],
            required_skills=[],
            nice_to_have_skills=[],
        )
        assert score == 1.0

    def test_empty_candidate_skills(self):
        """Candidate with no skills gets 0.0."""
        score = compute_skill_overlap(
            candidate_skills=[],
            required_skills=["Python", "FastAPI"],
            nice_to_have_skills=[],
        )
        assert score == 0.0


# ─────────────────────────────────────────────────────────────────────
# TESTS FOR compute_experience_fit()
# ─────────────────────────────────────────────────────────────────────

class TestExperienceFit:

    def test_exact_match(self):
        """Candidate has exactly the required years → 1.0"""
        score = compute_experience_fit(candidate_years=4.0, required_years=4.0)
        assert score == 1.0

    def test_over_qualified(self):
        """Candidate has MORE than required → still 1.0 (no penalty)"""
        score = compute_experience_fit(candidate_years=8.0, required_years=4.0)
        assert score == 1.0

    def test_half_the_required(self):
        """Candidate has half the required experience → 0.5"""
        score = compute_experience_fit(candidate_years=2.0, required_years=4.0)
        assert score == 0.5

    def test_no_experience(self):
        """Candidate has 0 years, job needs 4 → 0.0"""
        score = compute_experience_fit(candidate_years=0.0, required_years=4.0)
        assert score == 0.0

    def test_no_requirement(self):
        """Job has no experience requirement (None) → everyone gets 1.0"""
        score = compute_experience_fit(candidate_years=2.0, required_years=None)
        assert score == 1.0

    def test_zero_requirement(self):
        """Job requires 0 years → everyone gets 1.0"""
        score = compute_experience_fit(candidate_years=0.0, required_years=0.0)
        assert score == 1.0

    def test_fractional_years(self):
        """3 years out of required 4 → 0.75"""
        score = compute_experience_fit(candidate_years=3.0, required_years=4.0)
        assert score == 0.75


# ─────────────────────────────────────────────────────────────────────
# TESTS FOR compute_final_score()
# ─────────────────────────────────────────────────────────────────────

class TestFinalScore:

    def test_all_perfect_scores(self):
        """All three scores = 1.0 → final = 1.0"""
        score = compute_final_score(
            semantic_score=1.0,
            skill_overlap_score=1.0,
            experience_fit_score=1.0,
        )
        assert score == 1.0

    def test_all_zero_scores(self):
        """All three scores = 0.0 → final = 0.0"""
        score = compute_final_score(
            semantic_score=0.0,
            skill_overlap_score=0.0,
            experience_fit_score=0.0,
        )
        assert score == 0.0

    def test_default_weights(self):
        """
        Verify default weight formula:
        final = 0.5 * 0.8 + 0.35 * 0.6 + 0.15 * 1.0
              = 0.4  + 0.21  + 0.15
              = 0.76
        """
        score = compute_final_score(
            semantic_score=0.8,
            skill_overlap_score=0.6,
            experience_fit_score=1.0,
        )
        assert score == 0.76

    def test_custom_weights(self):
        """Custom weights should override the defaults."""
        score = compute_final_score(
            semantic_score=1.0,
            skill_overlap_score=0.0,
            experience_fit_score=0.0,
            weights={"semantic": 1.0, "skill_overlap": 0.0, "experience_fit": 0.0},
        )
        assert score == 1.0

    def test_score_is_clamped_to_1(self):
        """Even if weights add up oddly, score should not exceed 1.0."""
        score = compute_final_score(
            semantic_score=1.0,
            skill_overlap_score=1.0,
            experience_fit_score=1.0,
            weights={"semantic": 0.6, "skill_overlap": 0.6, "experience_fit": 0.6},
        )
        assert score == 1.0  # clamped

    def test_score_is_clamped_to_0(self):
        """Score should never go below 0.0."""
        score = compute_final_score(
            semantic_score=-1.0,  # bad input
            skill_overlap_score=0.0,
            experience_fit_score=0.0,
        )
        assert score == 0.0  # clamped

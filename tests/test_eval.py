"""
test_eval.py — Unit Tests for Phase 7 Evaluation Harness
==========================================================

Tests the metric functions from eval/metrics.py and verifies
the full eval pipeline runs without errors.

No database, no server, no API — pure Python only.
Run with:  uv run pytest tests/test_eval.py -v
"""

import pytest
import sys
from pathlib import Path

# Ensure project root is on sys.path so eval module can be imported
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.metrics import (
    spearman_rank_correlation,
    precision_at_k,
    ndcg_at_k,
    kendall_tau,
    mean_absolute_error,
    score_in_expected_range,
)
from eval.run_eval import evaluate_scenario, run_full_eval
from eval.labeled_test_set import TEST_SCENARIOS


# ═════════════════════════════════════════════════════════════════════
# TESTS FOR spearman_rank_correlation()
# ═════════════════════════════════════════════════════════════════════

class TestSpearmanCorrelation:

    def test_perfect_agreement(self):
        """Identical rankings → ρ = 1.0"""
        result = spearman_rank_correlation(
            ["A", "B", "C", "D"],
            ["A", "B", "C", "D"],
        )
        assert result == 1.0

    def test_perfect_reversal(self):
        """Completely reversed ranking → ρ = -1.0"""
        result = spearman_rank_correlation(
            ["D", "C", "B", "A"],
            ["A", "B", "C", "D"],
        )
        assert result == -1.0

    def test_partial_agreement(self):
        """Partially matching → ρ between -1 and 1"""
        result = spearman_rank_correlation(
            ["A", "C", "B", "D"],
            ["A", "B", "C", "D"],
        )
        assert -1.0 <= result <= 1.0
        assert result > 0.0  # mostly correct

    def test_single_item(self):
        """One item → trivially perfect"""
        result = spearman_rank_correlation(["A"], ["A"])
        assert result == 1.0

    def test_two_items_correct(self):
        """Two items in correct order → 1.0"""
        result = spearman_rank_correlation(["A", "B"], ["A", "B"])
        assert result == 1.0

    def test_two_items_swapped(self):
        """Two items swapped → -1.0"""
        result = spearman_rank_correlation(["B", "A"], ["A", "B"])
        assert result == -1.0

    def test_empty_list(self):
        """Empty lists → 1.0 (trivially)"""
        result = spearman_rank_correlation([], [])
        assert result == 1.0


# ═════════════════════════════════════════════════════════════════════
# TESTS FOR precision_at_k()
# ═════════════════════════════════════════════════════════════════════

class TestPrecisionAtK:

    def test_perfect_precision(self):
        """System's top-3 exactly matches human's top-3 → 1.0"""
        result = precision_at_k(
            ["A", "B", "C", "D"],
            ["A", "B", "C", "D"],
            k=3,
        )
        assert result == 1.0

    def test_zero_precision(self):
        """System's top-2 has no overlap with human's top-2 → 0.0"""
        result = precision_at_k(
            ["C", "D", "A", "B"],
            ["A", "B", "C", "D"],
            k=2,
        )
        assert result == 0.0

    def test_partial_precision(self):
        """1 out of 2 overlap → 0.5"""
        result = precision_at_k(
            ["A", "C", "B", "D"],
            ["A", "B", "C", "D"],
            k=2,
        )
        assert result == 0.5

    def test_k_equals_list_length(self):
        """k = full list → always 1.0 (same items, different order)"""
        result = precision_at_k(
            ["D", "C", "B", "A"],
            ["A", "B", "C", "D"],
            k=4,
        )
        assert result == 1.0

    def test_k_equals_one(self):
        """k=1, top-1 matches → 1.0"""
        result = precision_at_k(
            ["A", "B", "C"],
            ["A", "C", "B"],
            k=1,
        )
        assert result == 1.0

    def test_k_zero(self):
        """k=0 → 0.0"""
        result = precision_at_k(["A"], ["A"], k=0)
        assert result == 0.0


# ═════════════════════════════════════════════════════════════════════
# TESTS FOR ndcg_at_k()
# ═════════════════════════════════════════════════════════════════════

class TestNDCGAtK:

    def test_perfect_ordering(self):
        """System matches human exactly → NDCG = 1.0"""
        result = ndcg_at_k(
            ["A", "B", "C", "D"],
            ["A", "B", "C", "D"],
            k=3,
        )
        assert result == 1.0

    def test_worst_ordering(self):
        """Reversed ordering → NDCG < 1.0"""
        result = ndcg_at_k(
            ["D", "C", "B", "A"],
            ["A", "B", "C", "D"],
            k=3,
        )
        assert result < 1.0
        assert result > 0.0  # some relevance still present

    def test_partial_ordering(self):
        """One swap → NDCG < 1.0 but > 0.5"""
        result = ndcg_at_k(
            ["A", "C", "B", "D"],
            ["A", "B", "C", "D"],
            k=3,
        )
        assert 0.5 < result < 1.0

    def test_k_zero(self):
        """k=0 → 0.0"""
        result = ndcg_at_k(["A"], ["A"], k=0)
        assert result == 0.0


# ═════════════════════════════════════════════════════════════════════
# TESTS FOR kendall_tau()
# ═════════════════════════════════════════════════════════════════════

class TestKendallTau:

    def test_perfect_agreement(self):
        """Same ordering → τ = 1.0"""
        result = kendall_tau(
            ["A", "B", "C", "D"],
            ["A", "B", "C", "D"],
        )
        assert result == 1.0

    def test_perfect_reversal(self):
        """Reversed → τ = -1.0"""
        result = kendall_tau(
            ["D", "C", "B", "A"],
            ["A", "B", "C", "D"],
        )
        assert result == -1.0

    def test_one_swap(self):
        """One adjacent swap → τ between 0 and 1"""
        result = kendall_tau(
            ["A", "C", "B", "D"],
            ["A", "B", "C", "D"],
        )
        assert 0.0 < result < 1.0

    def test_single_item(self):
        """One item → 1.0"""
        result = kendall_tau(["A"], ["A"])
        assert result == 1.0


# ═════════════════════════════════════════════════════════════════════
# TESTS FOR mean_absolute_error()
# ═════════════════════════════════════════════════════════════════════

class TestMAE:

    def test_perfect_predictions(self):
        """Predictions exactly match expected → MAE = 0.0"""
        result = mean_absolute_error([0.5, 0.8, 1.0], [0.5, 0.8, 1.0])
        assert result == 0.0

    def test_known_error(self):
        """Known differences → MAE = average absolute diff"""
        # |0.6-0.5| + |0.9-0.8| + |0.7-1.0| = 0.1 + 0.1 + 0.3 = 0.5
        # MAE = 0.5 / 3 ≈ 0.1667
        result = mean_absolute_error([0.6, 0.9, 0.7], [0.5, 0.8, 1.0])
        assert abs(result - 0.1667) < 0.001

    def test_empty_list(self):
        """Empty → 0.0"""
        result = mean_absolute_error([], [])
        assert result == 0.0


# ═════════════════════════════════════════════════════════════════════
# TESTS FOR score_in_expected_range()
# ═════════════════════════════════════════════════════════════════════

class TestScoreInRange:

    def test_score_within_range(self):
        assert score_in_expected_range(0.5, (0.3, 0.7)) is True

    def test_score_at_lower_bound(self):
        assert score_in_expected_range(0.3, (0.3, 0.7)) is True

    def test_score_at_upper_bound(self):
        assert score_in_expected_range(0.7, (0.3, 0.7)) is True

    def test_score_below_range(self):
        assert score_in_expected_range(0.2, (0.3, 0.7)) is False

    def test_score_above_range(self):
        assert score_in_expected_range(0.8, (0.3, 0.7)) is False


# ═════════════════════════════════════════════════════════════════════
# INTEGRATION: TEST THE FULL EVAL PIPELINE
# ═════════════════════════════════════════════════════════════════════

class TestFullEvalPipeline:

    def test_evaluate_single_scenario(self):
        """Evaluate one scenario and check all expected fields exist."""
        result = evaluate_scenario(TEST_SCENARIOS[0])

        assert "job_title" in result
        assert "num_candidates" in result
        assert result["num_candidates"] == 6
        assert "candidates" in result
        assert "system_ranking" in result
        assert "human_ranking" in result
        assert "metrics" in result

        metrics = result["metrics"]
        assert "spearman_correlation" in metrics
        assert "precision_at_3" in metrics
        assert "ndcg_at_3" in metrics
        assert "kendall_tau" in metrics
        assert "skill_overlap_mae" in metrics
        assert "experience_fit_mae" in metrics

    def test_evaluate_all_scenarios(self):
        """Run full eval and verify aggregate metrics are reasonable."""
        report = run_full_eval()

        assert report["total_scenarios"] == 3
        assert report["total_candidates"] == 18

        agg = report["aggregate_metrics"]

        # Spearman should be positive (system roughly agrees with human)
        assert agg["spearman_correlation"] > 0.0

        # Precision@3 should be better than random (random = ~0.5 for top-3 of 6)
        assert agg["precision_at_3"] >= 0.33

        # NDCG@3 should be reasonably high
        assert agg["ndcg_at_3"] > 0.5

        # Kendall Tau should be positive
        assert agg["kendall_tau"] > 0.0

        # MAE should be reasonable (not wildly off)
        assert agg["skill_overlap_mae"] < 0.5
        assert agg["experience_fit_mae"] < 0.5

    def test_all_candidates_scored(self):
        """Every candidate should have all score fields populated."""
        for scenario in TEST_SCENARIOS:
            result = evaluate_scenario(scenario)
            for cand in result["candidates"]:
                assert "semantic_score" in cand
                assert "skill_overlap_score" in cand
                assert "experience_fit_score" in cand
                assert "final_score" in cand
                assert "system_rank" in cand
                assert "human_rank" in cand

                # All scores should be in [0.0, 1.0]
                assert 0.0 <= cand["semantic_score"] <= 1.0
                assert 0.0 <= cand["skill_overlap_score"] <= 1.0
                assert 0.0 <= cand["experience_fit_score"] <= 1.0
                assert 0.0 <= cand["final_score"] <= 1.0

    def test_system_ranking_length_matches(self):
        """System ranking should contain all candidates."""
        for scenario in TEST_SCENARIOS:
            result = evaluate_scenario(scenario)
            assert len(result["system_ranking"]) == len(scenario["candidates"])
            assert len(result["human_ranking"]) == len(scenario["candidates"])

    def test_experience_fit_mae_is_zero(self):
        """
        Experience fit MAE should be 0.0 because the expected values are
        computed using the same formula as compute_experience_fit.
        This verifies the scoring function hasn't changed unexpectedly.
        """
        report = run_full_eval()
        agg = report["aggregate_metrics"]
        assert agg["experience_fit_mae"] == 0.0

    def test_best_candidate_ranks_high(self):
        """
        For each scenario, the human's #1 candidate should be in
        the system's top 3 (a basic sanity check).
        """
        for scenario in TEST_SCENARIOS:
            result = evaluate_scenario(scenario)
            human_best_id = result["human_ranking"][0]
            system_top_3 = result["system_ranking"][:3]
            assert human_best_id in system_top_3, (
                f"Human's #1 pick '{human_best_id}' not in system's top 3 "
                f"for '{result['job_title']}'"
            )

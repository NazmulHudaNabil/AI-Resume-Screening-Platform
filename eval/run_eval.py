"""
run_eval.py — Evaluation Harness Runner (Phase 7)
===================================================

Main script that:
  1. Loads the labeled test set (3 JDs × 6 candidates)
  2. Runs the pure Python scoring functions on each candidate
  3. Computes ranking quality metrics (Spearman, Precision@k, NDCG@k, Kendall Tau)
  4. Checks extraction accuracy (skill_overlap and experience_fit scores)
  5. Produces a JSON report + pretty Markdown summary
  6. Exits with non-zero code if metrics fall below thresholds (CI gate)

Usage:
  python -m eval.run_eval           # print report to console
  python -m eval.run_eval --ci      # also check thresholds and exit non-zero on failure
  python -m eval.run_eval --verbose  # show per-candidate detail

No database, no Qdrant, no LLM needed — this runs anywhere.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path so we can import app.services
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from eval.labeled_test_set import TEST_SCENARIOS, TOTAL_SCENARIOS, TOTAL_CANDIDATES
from eval.metrics import (
    spearman_rank_correlation,
    precision_at_k,
    ndcg_at_k,
    kendall_tau,
    mean_absolute_error,
    score_in_expected_range,
)
from app.services.ranking import (
    compute_skill_overlap,
    compute_experience_fit,
    compute_final_score,
)


# ─────────────────────────────────────────────────────────────────────
# REPORT DIRECTORY
# ─────────────────────────────────────────────────────────────────────
REPORTS_DIR = Path(__file__).parent / "reports"
THRESHOLDS_FILE = Path(__file__).parent / "thresholds.json"


# ─────────────────────────────────────────────────────────────────────
# LOAD THRESHOLDS
# ─────────────────────────────────────────────────────────────────────

def load_thresholds() -> dict:
    """Load CI thresholds from thresholds.json."""
    with open(THRESHOLDS_FILE, "r") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────
# CORE: RUN SCORING ON ONE SCENARIO
# ─────────────────────────────────────────────────────────────────────

def evaluate_scenario(scenario: dict, verbose: bool = False) -> dict:
    """
    Run scoring functions on all candidates for one JD and compute metrics.

    Args:
        scenario: One entry from TEST_SCENARIOS (job + candidates).
        verbose:  If True, print per-candidate detail.

    Returns:
        Dict with all computed scores, rankings, and metrics for this scenario.
    """
    job = scenario["job"]
    candidates = scenario["candidates"]

    required_skills = job["required_skills"]
    nice_to_have_skills = job["nice_to_have_skills"]
    min_experience = job.get("min_experience_years")

    # ── Score each candidate ──────────────────────────────────────────
    scored_candidates = []

    for cand in candidates:
        profile = cand["profile"]
        cand_id = cand["id"]

        # Compute the three sub-scores
        skill_score = compute_skill_overlap(
            candidate_skills=profile["skills"],
            required_skills=required_skills,
            nice_to_have_skills=nice_to_have_skills,
        )

        experience_score = compute_experience_fit(
            candidate_years=profile["experience_years"],
            required_years=min_experience,
        )

        # Use the simulated semantic score from the labeled data
        semantic_score = cand["simulated_semantic_score"]

        # Compute the final weighted score
        final_score = compute_final_score(
            semantic_score=semantic_score,
            skill_overlap_score=skill_score,
            experience_fit_score=experience_score,
        )

        # Check if skill score is in expected range
        expected_range = cand["expected_skill_score_range"]
        skill_in_range = score_in_expected_range(skill_score, expected_range)
        expected_midpoint = (expected_range[0] + expected_range[1]) / 2.0

        scored_candidates.append({
            "id": cand_id,
            "name": profile["name"],
            "human_rank": cand["human_rank"],
            "semantic_score": semantic_score,
            "skill_overlap_score": skill_score,
            "experience_fit_score": experience_score,
            "final_score": final_score,
            "skill_in_expected_range": skill_in_range,
            "expected_skill_range": expected_range,
            "expected_skill_midpoint": expected_midpoint,
        })

    # ── Sort by final_score (descending) to get system ranking ────────
    scored_candidates.sort(key=lambda c: c["final_score"], reverse=True)

    # Assign system ranks (1-indexed)
    for i, cand in enumerate(scored_candidates):
        cand["system_rank"] = i + 1

    # ── Build ordered lists for metrics ───────────────────────────────
    system_ranking = [c["id"] for c in scored_candidates]
    human_ranking = sorted(
        [c["id"] for c in scored_candidates],
        key=lambda cid: next(c["human_rank"] for c in scored_candidates if c["id"] == cid),
    )

    # ── Compute ranking metrics ───────────────────────────────────────
    spearman = spearman_rank_correlation(system_ranking, human_ranking)
    p_at_3 = precision_at_k(system_ranking, human_ranking, k=3)
    ndcg_3 = ndcg_at_k(system_ranking, human_ranking, k=3)
    tau = kendall_tau(system_ranking, human_ranking)

    # ── Compute extraction accuracy ───────────────────────────────────
    predicted_skill_scores = [c["skill_overlap_score"] for c in scored_candidates]
    expected_midpoints = [c["expected_skill_midpoint"] for c in scored_candidates]
    skill_mae = mean_absolute_error(predicted_skill_scores, expected_midpoints)

    skills_in_range = sum(1 for c in scored_candidates if c["skill_in_expected_range"])
    skills_accuracy = skills_in_range / len(scored_candidates) if scored_candidates else 0.0

    # ── Compute experience fit MAE ────────────────────────────────────
    # Expected experience scores based on the formula.
    # We look up each scored candidate by ID to ensure correct pairing
    # regardless of sort order.
    cand_lookup = {c["id"]: c for c in candidates}
    expected_exp_scores = []
    actual_exp_scores = []
    for cand_data in scored_candidates:
        actual_exp_scores.append(cand_data["experience_fit_score"])
        cand_info = cand_lookup[cand_data["id"]]
        exp_years = cand_info["profile"]["experience_years"]
        if min_experience is None or min_experience <= 0:
            expected_exp_scores.append(1.0)
        elif exp_years >= min_experience:
            expected_exp_scores.append(1.0)
        else:
            expected_exp_scores.append(round(exp_years / min_experience, 4))

    experience_mae = mean_absolute_error(actual_exp_scores, expected_exp_scores)

    # ── Print verbose detail ──────────────────────────────────────────
    if verbose:
        print(f"\n  {'Name':<20s} {'Human':>5s} {'System':>6s} "
              f"{'Sem':>5s} {'Skill':>6s} {'Exp':>5s} {'Final':>6s} {'Skill OK':>8s}")
        print(f"  {'─'*20} {'─'*5} {'─'*6} {'─'*5} {'─'*6} {'─'*5} {'─'*6} {'─'*8}")
        for c in scored_candidates:
            ok = "✓" if c["skill_in_expected_range"] else "✗"
            print(f"  {c['name']:<20s} {c['human_rank']:>5d} {c['system_rank']:>6d} "
                  f"{c['semantic_score']:>5.2f} {c['skill_overlap_score']:>6.3f} "
                  f"{c['experience_fit_score']:>5.2f} {c['final_score']:>6.3f} "
                  f"{ok:>8s}")

    return {
        "job_title": job["title"],
        "num_candidates": len(scored_candidates),
        "candidates": scored_candidates,
        "system_ranking": system_ranking,
        "human_ranking": human_ranking,
        "metrics": {
            "spearman_correlation": spearman,
            "precision_at_3": p_at_3,
            "ndcg_at_3": ndcg_3,
            "kendall_tau": tau,
            "skill_overlap_mae": skill_mae,
            "skill_accuracy_pct": round(skills_accuracy * 100, 1),
            "experience_fit_mae": experience_mae,
        },
    }


# ─────────────────────────────────────────────────────────────────────
# AGGREGATE RESULTS ACROSS ALL SCENARIOS
# ─────────────────────────────────────────────────────────────────────

def run_full_eval(verbose: bool = False) -> dict:
    """
    Run evaluation across all test scenarios and aggregate results.

    Returns:
        Full evaluation report dict.
    """
    scenario_results = []

    for scenario in TEST_SCENARIOS:
        result = evaluate_scenario(scenario, verbose=verbose)
        scenario_results.append(result)

    # ── Aggregate metrics (average across scenarios) ──────────────────
    n = len(scenario_results)
    avg_metrics = {}
    metric_keys = scenario_results[0]["metrics"].keys()

    for key in metric_keys:
        values = [r["metrics"][key] for r in scenario_results]
        avg_metrics[key] = round(sum(values) / n, 4)

    # ── Per-scenario metrics ──────────────────────────────────────────
    per_scenario = []
    for r in scenario_results:
        per_scenario.append({
            "job_title": r["job_title"],
            "num_candidates": r["num_candidates"],
            "metrics": r["metrics"],
        })

    report = {
        "eval_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": TOTAL_SCENARIOS,
        "total_candidates": TOTAL_CANDIDATES,
        "aggregate_metrics": avg_metrics,
        "per_scenario": per_scenario,
        "scenario_details": scenario_results,
    }

    return report


# ─────────────────────────────────────────────────────────────────────
# GENERATE MARKDOWN SUMMARY
# ─────────────────────────────────────────────────────────────────────

def generate_markdown_report(report: dict, thresholds: dict) -> str:
    """Generate a human-readable Markdown summary of the eval results."""

    agg = report["aggregate_metrics"]
    lines = []

    lines.append("# 📊 Evaluation Report — AI Resume Screening Platform")
    lines.append("")
    lines.append(f"**Generated:** {report['eval_timestamp']}")
    lines.append(f"**Scenarios:** {report['total_scenarios']} job descriptions")
    lines.append(f"**Candidates:** {report['total_candidates']} total")
    lines.append("")

    # ── Aggregate Metrics Table ───────────────────────────────────────
    lines.append("## Aggregate Metrics (averaged across all scenarios)")
    lines.append("")
    lines.append("| Metric | Value | Threshold | Status |")
    lines.append("|--------|-------|-----------|--------|")

    checks = [
        ("Spearman Correlation", agg["spearman_correlation"],
         thresholds["spearman_correlation_min"], "≥"),
        ("Precision@3", agg["precision_at_3"],
         thresholds["precision_at_3_min"], "≥"),
        ("NDCG@3", agg["ndcg_at_3"],
         thresholds["ndcg_at_3_min"], "≥"),
        ("Skill Overlap MAE", agg["skill_overlap_mae"],
         thresholds["skill_overlap_mae_max"], "≤"),
        ("Experience Fit MAE", agg["experience_fit_mae"],
         thresholds["experience_fit_mae_max"], "≤"),
    ]

    all_pass = True
    for name, value, threshold, direction in checks:
        if direction == "≥":
            passed = value >= threshold
        else:
            passed = value <= threshold
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_pass = False
        lines.append(f"| {name} | {value:.4f} | {direction} {threshold:.2f} | {status} |")

    # Extra metrics (informational, no threshold)
    lines.append(f"| Kendall Tau | {agg['kendall_tau']:.4f} | — | ℹ️ |")
    lines.append(f"| Skill Accuracy % | {agg['skill_accuracy_pct']:.1f}% | — | ℹ️ |")

    lines.append("")

    # ── Per-Scenario Breakdown ────────────────────────────────────────
    lines.append("## Per-Scenario Breakdown")
    lines.append("")

    for sc in report["per_scenario"]:
        m = sc["metrics"]
        lines.append(f"### {sc['job_title']} ({sc['num_candidates']} candidates)")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Spearman | {m['spearman_correlation']:.4f} |")
        lines.append(f"| Precision@3 | {m['precision_at_3']:.4f} |")
        lines.append(f"| NDCG@3 | {m['ndcg_at_3']:.4f} |")
        lines.append(f"| Kendall Tau | {m['kendall_tau']:.4f} |")
        lines.append(f"| Skill MAE | {m['skill_overlap_mae']:.4f} |")
        lines.append(f"| Exp. Fit MAE | {m['experience_fit_mae']:.4f} |")
        lines.append(f"| Skill Accuracy | {m['skill_accuracy_pct']:.1f}% |")
        lines.append("")

    # ── Detailed Ranking Comparison ───────────────────────────────────
    lines.append("## Ranking Comparison (System vs Human)")
    lines.append("")

    for sd in report["scenario_details"]:
        lines.append(f"### {sd['job_title']}")
        lines.append("")
        lines.append(f"| Rank | System Pick | Human Pick | Match |")
        lines.append(f"|------|-----------|-----------|-------|")
        for i in range(sd["num_candidates"]):
            sys_id = sd["system_ranking"][i]
            hum_id = sd["human_ranking"][i]
            sys_name = next(c["name"] for c in sd["candidates"] if c["id"] == sys_id)
            hum_name = next(c["name"] for c in sd["candidates"] if c["id"] == hum_id)
            match = "✅" if sys_id == hum_id else "—"
            lines.append(f"| #{i+1} | {sys_name} | {hum_name} | {match} |")
        lines.append("")

    # ── Overall Verdict ───────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    if all_pass:
        lines.append("## ✅ OVERALL: ALL METRICS PASS")
    else:
        lines.append("## ❌ OVERALL: SOME METRICS FAILED — see table above")
    lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# CHECK THRESHOLDS (for CI gate)
# ─────────────────────────────────────────────────────────────────────

def check_thresholds(report: dict, thresholds: dict) -> tuple[bool, list[str]]:
    """
    Check if all aggregate metrics meet the CI thresholds.

    Returns:
        (all_pass: bool, failures: list[str])
    """
    agg = report["aggregate_metrics"]
    failures = []

    if agg["spearman_correlation"] < thresholds["spearman_correlation_min"]:
        failures.append(
            f"Spearman correlation {agg['spearman_correlation']:.4f} "
            f"< threshold {thresholds['spearman_correlation_min']}"
        )

    if agg["precision_at_3"] < thresholds["precision_at_3_min"]:
        failures.append(
            f"Precision@3 {agg['precision_at_3']:.4f} "
            f"< threshold {thresholds['precision_at_3_min']}"
        )

    if agg["ndcg_at_3"] < thresholds["ndcg_at_3_min"]:
        failures.append(
            f"NDCG@3 {agg['ndcg_at_3']:.4f} "
            f"< threshold {thresholds['ndcg_at_3_min']}"
        )

    if agg["skill_overlap_mae"] > thresholds["skill_overlap_mae_max"]:
        failures.append(
            f"Skill overlap MAE {agg['skill_overlap_mae']:.4f} "
            f"> threshold {thresholds['skill_overlap_mae_max']}"
        )

    if agg["experience_fit_mae"] > thresholds["experience_fit_mae_max"]:
        failures.append(
            f"Experience fit MAE {agg['experience_fit_mae']:.4f} "
            f"> threshold {thresholds['experience_fit_mae_max']}"
        )

    return (len(failures) == 0, failures)


# ─────────────────────────────────────────────────────────────────────
# MAIN — CLI entry point
# ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Phase 7 — Evaluation Harness for AI Resume Screening Platform"
    )
    parser.add_argument(
        "--ci", action="store_true",
        help="Run in CI mode: check thresholds and exit with non-zero code on failure.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print per-candidate scoring detail.",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("  Phase 7 — Evaluation Harness")
    print("  AI Resume Screening Platform")
    print("=" * 70)
    print(f"\n  Scenarios: {TOTAL_SCENARIOS} JDs × 6 candidates = {TOTAL_CANDIDATES} total\n")

    # ── Run the eval ──────────────────────────────────────────────────
    report = run_full_eval(verbose=args.verbose)

    # ── Load thresholds ───────────────────────────────────────────────
    thresholds = load_thresholds()

    # ── Generate and print Markdown report ────────────────────────────
    md_report = generate_markdown_report(report, thresholds)
    print(md_report)

    # ── Save reports to disk ──────────────────────────────────────────
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    json_path = REPORTS_DIR / "eval_report.json"
    md_path = REPORTS_DIR / "eval_report.md"

    # Remove scenario_details from JSON (too verbose) — keep per_scenario
    json_report = {
        "eval_timestamp": report["eval_timestamp"],
        "total_scenarios": report["total_scenarios"],
        "total_candidates": report["total_candidates"],
        "aggregate_metrics": report["aggregate_metrics"],
        "per_scenario": report["per_scenario"],
        "thresholds": thresholds,
    }

    with open(json_path, "w") as f:
        json.dump(json_report, f, indent=2)

    with open(md_path, "w") as f:
        f.write(md_report)

    print(f"\n  Reports saved:")
    print(f"    JSON: {json_path}")
    print(f"    MD:   {md_path}")

    # ── CI threshold check ────────────────────────────────────────────
    if args.ci:
        all_pass, failures = check_thresholds(report, thresholds)

        if all_pass:
            print("\n  ✅ CI GATE: All metrics pass thresholds.\n")
            sys.exit(0)
        else:
            print("\n  ❌ CI GATE: Metrics below threshold:")
            for f in failures:
                print(f"    • {f}")
            print()
            sys.exit(1)
    else:
        print("\n  (Run with --ci to enable threshold checking)\n")


if __name__ == "__main__":
    main()

"""
metrics.py — Evaluation Metrics (Phase 7)
==========================================

Pure Python implementations of ranking quality metrics.
No external dependencies required (no scipy, no numpy).

Metrics provided:
  1. spearman_rank_correlation — how well system ranking matches human ranking
  2. precision_at_k           — of system's top-k, how many are in human's top-k?
  3. ndcg_at_k                — normalized discounted cumulative gain (position-aware)
  4. kendall_tau              — pairwise concordance measure
  5. mean_absolute_error      — average absolute difference between predicted and expected scores

All functions take simple Python lists — no special objects needed.
"""

import math


# ─────────────────────────────────────────────────────────────────────
# 1. SPEARMAN RANK CORRELATION
# ─────────────────────────────────────────────────────────────────────

def spearman_rank_correlation(
    system_ranking: list[str],
    human_ranking: list[str],
) -> float:
    """
    Compute Spearman's rank correlation coefficient (ρ) between two rankings.

    Measures how well the system's ranking matches the human's ranking.
    A value of 1.0 = perfect agreement, 0.0 = no correlation, -1.0 = reversed.

    Formula:
        ρ = 1 - (6 × Σ dᵢ²) / (n × (n² - 1))

    where dᵢ = difference between ranks of item i in the two rankings.

    Args:
        system_ranking: Ordered list of candidate IDs (best first) from the system.
        human_ranking:  Ordered list of candidate IDs (best first) from human labels.

    Returns:
        Float between -1.0 and 1.0.

    Example:
        >>> spearman_rank_correlation(["A", "B", "C"], ["A", "B", "C"])
        1.0
        >>> spearman_rank_correlation(["C", "B", "A"], ["A", "B", "C"])
        -1.0
    """
    n = len(system_ranking)
    if n < 2:
        return 1.0  # trivially perfect with 0 or 1 item

    # Build rank maps: id → rank position (1-indexed)
    system_rank_map = {cid: rank + 1 for rank, cid in enumerate(system_ranking)}
    human_rank_map = {cid: rank + 1 for rank, cid in enumerate(human_ranking)}

    # Only score candidates that appear in both rankings
    common = set(system_rank_map.keys()) & set(human_rank_map.keys())
    n = len(common)
    if n < 2:
        return 1.0

    # Sum of squared rank differences
    d_squared_sum = sum(
        (system_rank_map[cid] - human_rank_map[cid]) ** 2
        for cid in common
    )

    # Spearman formula
    rho = 1.0 - (6.0 * d_squared_sum) / (n * (n ** 2 - 1))
    return round(rho, 4)


# ─────────────────────────────────────────────────────────────────────
# 2. PRECISION AT K
# ─────────────────────────────────────────────────────────────────────

def precision_at_k(
    system_ranking: list[str],
    human_ranking: list[str],
    k: int,
) -> float:
    """
    Compute Precision@k: what fraction of the system's top-k candidates
    also appear in the human's top-k?

    This answers: "If I shortlist the system's top k, how many are actually
    good candidates according to the human reviewer?"

    Formula:
        P@k = |system_top_k ∩ human_top_k| / k

    Args:
        system_ranking: Ordered candidate IDs from system (best first).
        human_ranking:  Ordered candidate IDs from human (best first).
        k:              How many top candidates to consider.

    Returns:
        Float between 0.0 and 1.0.

    Example:
        >>> precision_at_k(["A", "B", "C", "D"], ["A", "C", "B", "D"], k=2)
        0.5  # system top-2 = {A,B}, human top-2 = {A,C} → overlap = {A} → 1/2
    """
    if k <= 0:
        return 0.0

    system_top_k = set(system_ranking[:k])
    human_top_k = set(human_ranking[:k])

    overlap = len(system_top_k & human_top_k)
    return round(overlap / k, 4)


# ─────────────────────────────────────────────────────────────────────
# 3. NDCG AT K (Normalized Discounted Cumulative Gain)
# ─────────────────────────────────────────────────────────────────────

def ndcg_at_k(
    system_ranking: list[str],
    human_ranking: list[str],
    k: int,
) -> float:
    """
    Compute NDCG@k — a position-aware ranking quality metric.

    Unlike Precision@k, NDCG rewards placing good candidates at the TOP
    of the list more than placing them lower. It discounts relevance
    by the log of the position.

    How it works:
      1. Assign a relevance score to each candidate based on their
         human rank (best rank → highest relevance).
      2. Compute DCG@k for the system's ordering.
      3. Compute ideal DCG@k (= DCG of the perfect human ordering).
      4. NDCG@k = DCG / ideal_DCG.

    A value of 1.0 = system ordering matches the ideal (human) ordering.

    Args:
        system_ranking: Ordered candidate IDs from system (best first).
        human_ranking:  Ordered candidate IDs from human (best first).
        k:              How many top positions to evaluate.

    Returns:
        Float between 0.0 and 1.0.
    """
    if k <= 0 or not human_ranking:
        return 0.0

    n = len(human_ranking)

    # Relevance scores: human rank 1 → n points, rank 2 → n-1, ..., rank n → 1
    relevance = {cid: n - rank for rank, cid in enumerate(human_ranking)}

    # DCG@k for the system ranking
    dcg = 0.0
    for i, cid in enumerate(system_ranking[:k]):
        rel = relevance.get(cid, 0)
        dcg += rel / math.log2(i + 2)  # i+2 because positions are 1-indexed

    # Ideal DCG@k (best possible ordering = human ranking)
    ideal_dcg = 0.0
    ideal_rels = sorted(relevance.values(), reverse=True)
    for i, rel in enumerate(ideal_rels[:k]):
        ideal_dcg += rel / math.log2(i + 2)

    if ideal_dcg == 0.0:
        return 0.0

    return round(dcg / ideal_dcg, 4)


# ─────────────────────────────────────────────────────────────────────
# 4. KENDALL TAU
# ─────────────────────────────────────────────────────────────────────

def kendall_tau(
    system_ranking: list[str],
    human_ranking: list[str],
) -> float:
    """
    Compute Kendall's Tau — measures pairwise ordering concordance.

    For every pair of candidates (A, B), check if both the system
    and the human agree on who is ranked higher. Count concordant
    vs discordant pairs.

    Formula:
        τ = (concordant - discordant) / total_pairs

    A value of 1.0 = all pairs agree, 0.0 = random, -1.0 = all reversed.

    Args:
        system_ranking: Ordered candidate IDs (best first) from system.
        human_ranking:  Ordered candidate IDs (best first) from human.

    Returns:
        Float between -1.0 and 1.0.
    """
    common = [c for c in system_ranking if c in human_ranking]
    n = len(common)
    if n < 2:
        return 1.0

    # Build rank maps
    system_map = {cid: i for i, cid in enumerate(system_ranking)}
    human_map = {cid: i for i, cid in enumerate(human_ranking)}

    concordant = 0
    discordant = 0

    for i in range(n):
        for j in range(i + 1, n):
            a, b = common[i], common[j]
            sys_diff = system_map[a] - system_map[b]
            hum_diff = human_map[a] - human_map[b]

            if sys_diff * hum_diff > 0:
                concordant += 1
            elif sys_diff * hum_diff < 0:
                discordant += 1
            # tied pairs are neither concordant nor discordant

    total_pairs = concordant + discordant
    if total_pairs == 0:
        return 1.0

    return round((concordant - discordant) / total_pairs, 4)


# ─────────────────────────────────────────────────────────────────────
# 5. MEAN ABSOLUTE ERROR
# ─────────────────────────────────────────────────────────────────────

def mean_absolute_error(
    predicted_scores: list[float],
    expected_midpoints: list[float],
) -> float:
    """
    Compute Mean Absolute Error between predicted scores and expected midpoints.

    Used to check extraction accuracy: how close are the system's skill_overlap
    and experience_fit scores to the expected values from the labeled data?

    Formula:
        MAE = (1/n) × Σ |predicted_i - expected_i|

    Args:
        predicted_scores:   List of scores produced by the scoring functions.
        expected_midpoints: List of expected score midpoints from labeled data.

    Returns:
        Float ≥ 0.0. Lower is better.
    """
    if not predicted_scores:
        return 0.0

    n = len(predicted_scores)
    total_error = sum(
        abs(p - e)
        for p, e in zip(predicted_scores, expected_midpoints)
    )
    return round(total_error / n, 4)


# ─────────────────────────────────────────────────────────────────────
# 6. SCORE IN RANGE CHECK
# ─────────────────────────────────────────────────────────────────────

def score_in_expected_range(
    score: float,
    expected_range: tuple[float, float],
) -> bool:
    """
    Check if a computed score falls within the expected range.

    Used to verify extraction accuracy: the labeled test set defines
    an expected range for each candidate's skill_overlap_score.

    Args:
        score:          The computed score (0.0 to 1.0).
        expected_range: Tuple of (min_expected, max_expected).

    Returns:
        True if min ≤ score ≤ max, False otherwise.
    """
    return expected_range[0] <= score <= expected_range[1]

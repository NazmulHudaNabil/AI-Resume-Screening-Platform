# 📊 Evaluation Report — AI Resume Screening Platform

**Generated:** 2026-08-06T17:21:00.153073+00:00
**Scenarios:** 3 job descriptions
**Candidates:** 18 total

## Aggregate Metrics (averaged across all scenarios)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Spearman Correlation | 0.9619 | ≥ 0.60 | ✅ PASS |
| Precision@3 | 0.8889 | ≥ 0.55 | ✅ PASS |
| NDCG@3 | 0.9812 | ≥ 0.65 | ✅ PASS |
| Skill Overlap MAE | 0.0391 | ≤ 0.20 | ✅ PASS |
| Experience Fit MAE | 0.0000 | ≤ 0.15 | ✅ PASS |
| Kendall Tau | 0.9111 | — | ℹ️ |
| Skill Accuracy % | 100.0% | — | ℹ️ |

## Per-Scenario Breakdown

### Senior Backend Python Developer (6 candidates)

| Metric | Value |
|--------|-------|
| Spearman | 0.9429 |
| Precision@3 | 0.6667 |
| NDCG@3 | 0.9552 |
| Kendall Tau | 0.8667 |
| Skill MAE | 0.0189 |
| Exp. Fit MAE | 0.0000 |
| Skill Accuracy | 100.0% |

### Frontend React Developer (6 candidates)

| Metric | Value |
|--------|-------|
| Spearman | 1.0000 |
| Precision@3 | 1.0000 |
| NDCG@3 | 1.0000 |
| Kendall Tau | 1.0000 |
| Skill MAE | 0.0484 |
| Exp. Fit MAE | 0.0000 |
| Skill Accuracy | 100.0% |

### DevOps / Cloud Engineer (6 candidates)

| Metric | Value |
|--------|-------|
| Spearman | 0.9429 |
| Precision@3 | 1.0000 |
| NDCG@3 | 0.9883 |
| Kendall Tau | 0.8667 |
| Skill MAE | 0.0500 |
| Exp. Fit MAE | 0.0000 |
| Skill Accuracy | 100.0% |

## Ranking Comparison (System vs Human)

### Senior Backend Python Developer

| Rank | System Pick | Human Pick | Match |
|------|-----------|-----------|-------|
| #1 | Alice Chen | Alice Chen | ✅ |
| #2 | Bob Martinez | Bob Martinez | ✅ |
| #3 | Diana Patel | Charlie Kim | — |
| #4 | Charlie Kim | Diana Patel | — |
| #5 | Eve Johnson | Eve Johnson | ✅ |
| #6 | Frank Lee | Frank Lee | ✅ |

### Frontend React Developer

| Rank | System Pick | Human Pick | Match |
|------|-----------|-----------|-------|
| #1 | Grace Wang | Grace Wang | ✅ |
| #2 | Henry Adams | Henry Adams | ✅ |
| #3 | Ivy Thompson | Ivy Thompson | ✅ |
| #4 | Jack Wilson | Jack Wilson | ✅ |
| #5 | Kate Brown | Kate Brown | ✅ |
| #6 | Liam Davis | Liam Davis | ✅ |

### DevOps / Cloud Engineer

| Rank | System Pick | Human Pick | Match |
|------|-----------|-----------|-------|
| #1 | Maya Singh | Maya Singh | ✅ |
| #2 | Olivia Chen | Noah Garcia | — |
| #3 | Noah Garcia | Olivia Chen | — |
| #4 | Peter Jones | Peter Jones | ✅ |
| #5 | Quinn Taylor | Quinn Taylor | ✅ |
| #6 | Rachel White | Rachel White | ✅ |

---

## ✅ OVERALL: ALL METRICS PASS

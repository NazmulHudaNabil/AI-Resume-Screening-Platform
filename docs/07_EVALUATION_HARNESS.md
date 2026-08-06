# 07 Evaluation Harness (Low-Level Design)

## Measuring Quality (`eval/`)

We cannot deploy changes to the ranking algorithm (e.g., changing weights from 0.5 to 0.6) without knowing if it makes things better or worse.

### The Labeled Data
In `eval/dataset.json`, we have 3 real job descriptions and 20 candidate profiles. A human recruiter has manually ranked them (e.g., Candidate A = Rank 1, Candidate B = Rank 2).

### The Math (Spearman Rank Correlation)
When we run `pytest tests/test_eval.py`, the test suite runs the entire hybrid engine on the dataset and outputs an algorithmic ranking.
We then use `scipy.stats.spearmanr(human_ranks, algo_ranks)`.
- A score of `1.0` means the algorithm perfectly matched the human.
- A score of `0.0` means it's random.
- We have an assertion: `assert spearman_score > 0.8`. If the score drops below 0.8, the CI pipeline fails the build, preventing bad math from reaching production.

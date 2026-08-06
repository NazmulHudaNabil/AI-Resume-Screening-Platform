# 05 Hybrid Ranking (Low-Level Design)

## The Scoring Algorithm (`app/services/ranking.py`)

Semantic search is not enough. An LLM might think a junior developer is semantically similar to a senior developer because they use the same keywords. We mathematically blend semantic meaning with hard rules.

### Component 1: Semantic Score (Weight: 0.5)
Returned directly from Qdrant Cosine Similarity. Value between `0.0` and `1.0`.

### Component 2: Skill Overlap (Weight: 0.3)
We take `profile.skills` (e.g., `["Python", "AWS"]`) and `job.required_skills` (`["Python", "Docker"]`).
```python
overlap = len(set(profile.skills).intersection(set(job.required_skills)))
skill_score = overlap / len(job.required_skills) # e.g. 1 / 2 = 0.5
```

### Component 3: Experience Fit (Weight: 0.2)
If the job requires 5 years, and they have 3, they get penalized.
```python
if profile.experience >= job.min_experience:
    exp_score = 1.0
else:
    exp_score = profile.experience / job.min_experience # 3/5 = 0.6
```

### Final Calculation
```python
final_score = (0.5 * semantic) + (0.3 * skill_score) + (0.2 * exp_score)
```
This final float is saved to the Postgres `rankings` table so we don't have to recalculate it on every page refresh.

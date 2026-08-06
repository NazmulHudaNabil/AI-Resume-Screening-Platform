# 06 Explanation Generation (Low-Level Design)

## LLM Justifications (`app/services/explanation.py`)

We want to show the recruiter exactly why a candidate got an 85% match.

### Prompt Engineering
We inject the Job Description, the Candidate Profile, and the three sub-scores (Semantic, Skill, Experience) into a Groq LLM prompt. We explicitly instruct the LLM: *"Do not exceed 3 sentences. State exactly which skills were missing if the skill score is low."*

### Redis Caching Strategy
Calling the LLM for every page load is too slow and expensive. We cache the output in Redis.
**The Cache Key:** 
```python
import hashlib
profile_hash = hashlib.md5(profile_text.encode()).hexdigest()
cache_key = f"explanation:{job_id}:{candidate_id}:{profile_hash}"
```
*Why the hash?* If the candidate updates their resume, the `profile_text` changes, the hash changes, and the cache is automatically busted.
We use `await redis.set(cache_key, explanation, ex=86400)` to set a 24-hour Time-To-Live (TTL).

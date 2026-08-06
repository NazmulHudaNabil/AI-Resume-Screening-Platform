# 03 Structured Extraction (Low-Level Design)

## LLM Gateway (`app/services/extraction.py`)

Raw text is useless for mathematical rule-based scoring. We use LLMs to extract it into a structured format.

### The Pydantic Schema
```python
class CandidateProfile(BaseModel):
    name: str
    skills: List[str]
    total_experience_years: float
    education: List[str]
```

### The LLM Call
We send the raw resume text to Groq/Mistral. We pass the Pydantic schema in the prompt and enforce `response_format={"type": "json_object"}`. 

### Why this matters?
By forcing JSON, we guarantee that `total_experience_years` will be a float (e.g., `5.5`). If the LLM hallucinates and returns `"five years"`, Pydantic throws a `ValidationError`. We catch this error and retry the LLM call up to 3 times with a slightly modified prompt.

Once validated, the JSON is serialized and saved into the `candidate_profiles` PostgreSQL table linked to the `resume_id`.

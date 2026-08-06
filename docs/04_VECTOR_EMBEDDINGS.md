# 04 Vector Embeddings (Low-Level Design)

## The Math Behind Search (`app/services/embedding.py`)

To find if a candidate's profile matches the job description conceptually (e.g., "Software Engineer" matching "Backend Developer"), we use semantic vectors.

### 1. Generating the Vector
We take the extracted `CandidateProfile` JSON and convert it into a string. We send this to Google's `gemini-embedding-2` model.
The API returns a `List[float]` of length exactly **3072**. This array of 3072 numbers represents the "meaning" of the candidate.

### 2. Qdrant Upsertion
We connect to Qdrant using `qdrant_client`.
We upsert the vector into a collection named `candidates`.
**Crucial Step:** We attach a `payload={"job_id": str(job_id), "candidate_id": str(candidate_id)}`.

### 3. Querying (The Dot Product)
When ranking, we embed the Job Description text into its own 3072-dimension vector. We query Qdrant using **Cosine Similarity**. 
We apply a strict filter: `Filter(must=[FieldCondition(key="job_id", match=MatchValue(value=str(job_id)))])`. This ensures we don't accidentally match a candidate from Job A to a search query for Job B.

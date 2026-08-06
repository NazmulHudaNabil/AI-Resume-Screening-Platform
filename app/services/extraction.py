"""
extraction.py — LLM Structured Extraction Service
===================================================

This module takes raw resume text and asks the Groq LLM (Llama 3)
to extract structured data from it (skills, experience, education, etc.).

How it works:
  1. We send the resume text to Groq with a clear JSON-mode prompt.
  2. The LLM returns a JSON string.
  3. We validate that JSON against our CandidateProfile Pydantic schema.
  4. If validation fails, we retry ONCE with the error message appended.
  5. If it fails again, we raise an error so the caller can flag it for review.

We use Groq's API directly via the `groq` Python SDK, which is
fast and free at small scale.
"""

import json
import logging

from groq import Groq, APIError

from app.core.config import settings
from app.schemas.candidate_profile import CandidateProfile

# Set up a logger for this module — logs will appear in the console
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# PROMPT TEMPLATE
# The system message tells the LLM exactly what its job is.
# The user message contains the actual resume text.
# ──────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a resume parser. Your ONLY job is to extract information
from resume text and return it as valid JSON.

Extract the following fields:
- name: The candidate's full name (string)
- skills: All technical and soft skills mentioned (list of strings)
- experience_years: Total years of professional work experience (float, e.g. 3.5)
- education: All degrees and educational qualifications (list of strings)
- roles: All job titles and roles held (list of strings)
- certifications: Any professional certifications (list of strings, empty list if none)

Rules:
- ONLY extract what is EXPLICITLY stated in the resume. Do NOT guess or infer.
- Return ONLY the JSON object, no extra text, no markdown, no code fences.
- If a field has no data, use an empty list [] or 0.0 for experience_years.

Required JSON format:
{
  "name": "string",
  "skills": ["string", ...],
  "experience_years": 0.0,
  "education": ["string", ...],
  "roles": ["string", ...],
  "certifications": ["string", ...]
}"""


def _build_user_message(resume_text: str, previous_error: str = "") -> str:
    """
    Build the user message to send to the LLM.
    On the first attempt, it's just the resume text.
    On a retry, we also include the previous validation error
    so the LLM can correct its output.
    """
    if previous_error:
        # Tell the LLM what went wrong so it can fix it
        return (
            f"PREVIOUS ATTEMPT FAILED WITH THIS ERROR:\n{previous_error}\n\n"
            f"Please fix the JSON and try again.\n\n"
            f"RESUME TEXT:\n{resume_text}"
        )
    return f"RESUME TEXT:\n{resume_text}"


def _call_groq(client: Groq, resume_text: str, previous_error: str = "") -> str:
    """
    Make a single API call to Groq and return the raw text response.

    We use response_format={"type": "json_object"} to tell Groq
    we expect JSON back — this reduces hallucinations and formatting issues.
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",   # fast, high-quality Groq model
        temperature=0.0,                    # 0 = deterministic, no creativity needed
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": _build_user_message(resume_text, previous_error)},
        ],
    )
    # The LLM's reply text is here
    return response.choices[0].message.content


def extract_candidate_profile(resume_text: str) -> CandidateProfile:
    """
    Main function: extract a structured CandidateProfile from raw resume text.

    Strategy:
    - Attempt 1: Send resume to Groq, parse JSON, validate with Pydantic.
    - Attempt 2 (if needed): Retry with the validation error attached.
    - If both fail: raise ValueError → the caller flags this resume for manual review.

    Args:
        resume_text: The plain text content extracted from a PDF or DOCX file.

    Returns:
        A validated CandidateProfile object.

    Raises:
        ValueError: If the LLM cannot produce valid structured output after 2 tries.
    """

    # Build a list of (label, api_key) to try in order
    keys_to_try = []
    if settings.groq_api_key:
        keys_to_try.append(("primary", settings.groq_api_key))
    if settings.groq_fallback_api_key:
        keys_to_try.append(("fallback", settings.groq_fallback_api_key))

    if not keys_to_try:
        raise ValueError(
            "No Groq API key configured. "
            "Set GROQ_API_KEY in your .env file."
        )

    last_error = ""

    # Try up to 2 times for validation/parsing (attempt 0 and attempt 1)
    for attempt in range(2):
        try:
            logger.info(f"Extraction attempt {attempt + 1}/2 ...")

            raw_json_text = None
            
            # Step 1: Call the LLM with fallback support
            for key_name, api_key in keys_to_try:
                try:
                    logger.info(f"Calling Groq LLM with {key_name} key...")
                    client = Groq(api_key=api_key)
                    raw_json_text = _call_groq(client, resume_text, previous_error=last_error)
                    break # Success with this key, break the key loop
                except APIError as e:
                    key_err = str(e)
                    next_step = "Trying fallback key..." if key_name == "primary" else "No more keys."
                    logger.warning(f"Groq {key_name} key failed (APIError): {key_err}. {next_step}")
                    if key_name == "fallback":
                        raise e # If fallback also fails, bubble it up to the outer try/except
                except Exception as e:
                    logger.warning(f"Groq {key_name} key failed (unexpected error): {e}")
                    if key_name == "fallback":
                        raise e

            if not raw_json_text:
                raise ValueError("Both primary and fallback Groq keys failed.")

            # Step 2: Parse the text as JSON
            data = json.loads(raw_json_text)

            # Step 3: Validate with our Pydantic schema
            # If any field is wrong type or missing, Pydantic raises ValidationError
            profile = CandidateProfile.model_validate(data)

            logger.info("Extraction successful.")
            return profile  # ✅ Success — return the validated profile

        except json.JSONDecodeError as e:
            # The LLM returned something that isn't valid JSON
            last_error = f"JSON parse error: {e}"
            logger.warning(f"Attempt {attempt + 1} failed — {last_error}")

        except Exception as e:
            # Pydantic validation error OR Groq API error
            last_error = str(e)
            logger.warning(f"Attempt {attempt + 1} failed — {last_error}")

    # Both attempts failed — raise an error so the caller knows
    raise ValueError(
        f"LLM extraction failed after 2 attempts. Last error: {last_error}"
    )

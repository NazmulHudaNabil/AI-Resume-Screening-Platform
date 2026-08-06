import requests, time

API_URL = 'http://127.0.0.1:8000/api/v1'

def run():
    print("1. Create job")
    res = requests.post(f"{API_URL}/jobs", json={
        "title": "Backend Engineer",
        "description": "Looking for Python backend dev",
        "required_skills": ["Python", "FastAPI"],
        "nice_to_have_skills": ["Docker"],
        "min_experience_years": 3.0
    })
    job_id = res.json()["id"]
    print("Job:", job_id)

    print("2. Upload resume")
    with open("test_resume.docx", "rb") as f:
        res = requests.post(f"{API_URL}/jobs/{job_id}/resumes", files={"files": ("test_resume.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    resume_id = res.json()[0]["id"]
    print("Resume:", resume_id)

    print("3. Extract")
    res = requests.post(f"{API_URL}/jobs/{job_id}/resumes/{resume_id}/extract")
    print("Extract status:", res.status_code, res.text)

    print("4. Embed all")
    res = requests.post(f"{API_URL}/jobs/{job_id}/embed-all")
    print("Embed status:", res.status_code, res.text)
    
    print("Wait 5s...")
    time.sleep(5)

    print("5. Initial Rankings (Phase 3)")
    res = requests.get(f"{API_URL}/jobs/{job_id}/rankings")
    print("Initial rankings:", res.status_code, res.text)

    print("6. Rank (Phase 4)")
    res = requests.post(f"{API_URL}/jobs/{job_id}/rank")
    print("Rank status:", res.status_code, res.text)

    print("7. Explain all (Phase 5)")
    res = requests.post(f"{API_URL}/jobs/{job_id}/explain-all")
    print("Explain status:", res.status_code, res.text)

if __name__ == "__main__":
    run()

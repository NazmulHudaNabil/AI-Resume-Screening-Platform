# 10 Known Gotchas (Low-Level Design)

If you are looking at this code a year from now, keep these specific quirks in mind:

1. **FastAPI Limiter Crash:** Do not attempt to install `fastapi-limiter v0.1.6` with FastAPI >0.109. The internal `route.path` parsing fails on nested routers. Rely on our custom Redis `INCR` implementation in `deps.py`.
2. **PostgreSQL Connections (Neon):** Serverless Postgres scales to zero. The first request after an hour of inactivity might take 2-3 seconds as Neon cold-starts.
3. **Streamlit Session State:** Streamlit re-runs the *entire* python script from top to bottom on every single button click. Always wrap stateful data (like the `access_token`) inside `if "access_token" not in st.session_state:` to prevent it from being wiped on UI interactions.
4. **PDF Magic Bytes vs Extension:** Recruiter platforms often receive `.docx` files renamed to `.pdf` by careless users. Our `b"%PDF-"` sniffing catches this and skips it. Do not remove the sniffing logic, or `pdfplumber` will crash the thread attempting to parse a ZIP file as a PDF.

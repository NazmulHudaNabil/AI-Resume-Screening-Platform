# 02 Ingestion Engine (Low-Level Design)

## File Upload Pipeline (`app/api/resumes.py`)
When the recruiter uploads resumes via `POST /jobs/{job_id}/resumes`:

1. **Memory Buffering**: FastAPI receives the files as `UploadFile`. We call `await file.read()` to load the bytes into RAM.
2. **Validation (Sniffing)**: We do not trust file extensions. We check the raw magic bytes:
   - PDFs must start with `b"%PDF-"`.
   - DOCX files are ZIP archives and must start with `b"PK\x03\x04"`.
3. **Size Limits**: Any file where `len(file_bytes) > 5 * 1024 * 1024` (5MB) is silently skipped to prevent OOM (Out of Memory) crashes.
4. **Parsing**: 
   - PDFs are passed to `pdfplumber`. It iterates over `pdf.pages` and extracts text.
   - DOCX files are passed to `python-docx` which iterates over `document.paragraphs`.
5. **Deduplication**: We query Postgres `SELECT 1 FROM resumes WHERE job_id = X AND raw_text = Y`. If it exists, we skip DB insertion to prevent duplicate candidates.
6. **Persistence**: The raw text is saved to the `resumes` table, and the file bytes are written to disk at `uploads/resumes/{uuid}.pdf`.

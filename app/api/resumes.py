import os
import uuid
from typing import Annotated, List

# UploadFile  = FastAPI's file object (has .filename, .read(), etc.)
# File        = tells FastAPI this is a file upload field (not a plain form field)
# Annotated   = Python's way of attaching extra info (like File) to a type
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.resumes import Resume
from app.schemas.resume import ResumeResponse
from app.services.document_parser import parse_document
from app.api.deps import get_current_user

MAX_FILE_SIZE = 5 * 1024 * 1024 # 5 MB

router = APIRouter()

# Where uploaded files will be saved on disk
UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post(
    "/jobs/{job_id}/resumes",
    response_model=List[ResumeResponse],
    summary="Upload Resumes",
    description="Bulk ingest resumes for a specific job. Extracts text and saves to DB.",
)
async def upload_resumes(
    # ✅ Using Annotated for BOTH job_id and files.
    #
    # Python rule: a parameter WITHOUT a default value cannot come AFTER
    # a parameter WITH a default value.
    #
    # Old broken style:
    #   job_id: uuid.UUID = Path(...)   ← has a "default" (the Path object)
    #   files: Annotated[...]           ← no default → SyntaxError!
    #
    # Fixed style using Annotated for everything:
    #   job_id: Annotated[uuid.UUID, Path(...)]   ← no "= default"
    #   files:  Annotated[List[UploadFile], File(...)]  ← no "= default"
    #   db:     AsyncSession = Depends(get_db)    ← has a default, comes last ✓
    #
    # FastAPI still treats all three as required — nothing changes at runtime.
    job_id: Annotated[uuid.UUID, Path(description="The ID of the job to attach resumes to")],
    files: Annotated[List[UploadFile], File(description="PDF or DOCX files to upload")],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Bulk ingest resumes for a specific job. Extracts text and saves to DB.
    """
    uploaded_resumes = []
    
    for file in files:
        if not (file.filename.lower().endswith('.pdf') or file.filename.lower().endswith('.docx')):
            # In a real app we might want to return an error, but for bulk upload
            # we can just ignore unsupported files or collect errors to return.
            continue
            
        file_bytes = await file.read()

        # File size validation
        if len(file_bytes) > MAX_FILE_SIZE:
            continue # Skip files that are too large

        # File sniffing (magic numbers)
        if file.filename.lower().endswith('.pdf'):
            if not file_bytes.startswith(b"%PDF-"):
                continue # Invalid PDF file signature
        elif file.filename.lower().endswith('.docx'):
            if not file_bytes.startswith(b"PK\x03\x04"):
                continue # Invalid DOCX file signature

        try:
            extracted_text = parse_document(file_bytes, file.filename)
        except ValueError as e:
            continue # skip invalid formats
            
        # Deduplication check: does this exact resume text already exist for this job?
        from sqlalchemy import select
        existing_resume = await db.execute(
            select(Resume).where(
                Resume.job_id == job_id,
                Resume.raw_text == extracted_text
            )
        )
        existing = existing_resume.scalars().first()
        if existing:
            uploaded_resumes.append(existing)
            continue
            
        # Save file to disk
        file_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename)[1]
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
        
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_bytes)
            
        # Save to DB
        resume = Resume(
            job_id=job_id,
            raw_text=extracted_text,
            file_path=file_path
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)
        
        uploaded_resumes.append(resume)
        
    return uploaded_resumes


@router.get(
    "/resumes/{resume_id}",
    response_model=ResumeResponse,
    summary="Get a Resume",
    description="Retrieve the raw text and file path of a previously uploaded resume.",
)
async def get_resume(
    resume_id: uuid.UUID = Path(..., description="The ID of the resume to fetch"),
    db: AsyncSession = Depends(get_db),
):
    resume = await db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume

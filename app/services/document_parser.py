import io
import pdfplumber
import docx

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file using pdfplumber."""
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text.strip()

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file using python-docx."""
    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join([paragraph.text for paragraph in doc.paragraphs]).strip()

def parse_document(file_bytes: bytes, filename: str) -> str:
    """Determine file type and route to appropriate parser."""
    ext = filename.lower()
    if ext.endswith('.pdf'):
        return extract_text_from_pdf(file_bytes)
    elif ext.endswith('.docx'):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError("Unsupported file format. Please upload PDF or DOCX.")

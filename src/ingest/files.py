from typing import Optional
from fastapi import UploadFile
import io

# Optional PDF support
try:
    import fitz  # PyMuPDF
    _HAVE_PYMUPDF = True
except Exception:
    _HAVE_PYMUPDF = False

async def read_txt(file: UploadFile) -> Optional[str]:
    data = await file.read()
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return None

async def read_pdf(file: UploadFile) -> Optional[str]:
    if not _HAVE_PYMUPDF:
        return None
    data = await file.read()
    try:
        doc = fitz.open(stream=io.BytesIO(data), filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text("text"))
        return "\n".join(pages).strip()
    except Exception:
        return None

async def read_any(file: UploadFile) -> Optional[str]:
    ct = (file.content_type or "").lower()
    name = (file.filename or "").lower()

    if name.endswith(".txt") or "text/plain" in ct:
        return await read_txt(file)
    if name.endswith(".pdf") or "pdf" in ct:
        return await read_pdf(file)
    # fallback: try as text
    return await read_txt(file)
from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


class PDFExtractionError(Exception):
    pass


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception as exc:
        raise PDFExtractionError("No se pudo abrir el PDF recibido.") from exc

    extracted_pages = []
    for page in reader.pages:
        extracted_pages.append((page.extract_text() or "").strip())

    text = "\n\n".join(block for block in extracted_pages if block)
    if not text.strip():
        raise PDFExtractionError("No se pudo extraer texto del PDF. Revisa que no sea una imagen escaneada.")
    return text.strip()


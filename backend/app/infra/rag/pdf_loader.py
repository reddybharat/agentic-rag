import io

from pypdf import PdfReader


def load_pdf_pages(data: bytes) -> list[str]:
    """Text of each page, in order; image-only pages come back empty."""
    return [page.extract_text() for page in PdfReader(io.BytesIO(data)).pages]

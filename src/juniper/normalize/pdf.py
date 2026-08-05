import io
import sys

from pypdf import PdfReader

TARIFF_SECTION_MARKER = "LARGE LOAD TARIFFS"


def extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() for page in reader.pages)


def extract_tariff_section(full_text: str) -> str:
    idx = full_text.find(TARIFF_SECTION_MARKER)
    if idx == -1:
        print(
            f"normalize.pdf: {TARIFF_SECTION_MARKER!r} marker not found, "
            "falling back to full text",
            file=sys.stderr,
        )
        return full_text
    return full_text[idx:]


def normalize_pdf_text(text: str) -> str:
    return " ".join(text.split())

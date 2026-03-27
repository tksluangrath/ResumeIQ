import re
from pathlib import Path

import pdfplumber


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    path = Path(pdf_path)

    if not path.exists():
        raise ValueError(f"File not found: {pdf_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.suffix!r}")

    pages: list[str] = []

    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) == 0:
            raise ValueError(f"PDF has no pages: {pdf_path}")

        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

    raw = "\n".join(pages)

    cleaned = re.sub(r"[ \t]+", " ", raw)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()

    return cleaned

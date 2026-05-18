"""Best-effort OCR over PDFs.

Never blocks the upload (research.md §4 spec 001). If anything fails we return
an empty extraction and let the user fill the form manually.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

from repse.config import Settings
from repse.logging import get_logger

log = get_logger(__name__)

# RFC: 3-4 letters, 6 digits (YYMMDD), 3 alphanumerics
RFC_RE = re.compile(r"\b([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3})\b")

# Dates like "12 de marzo de 2026"
_SPANISH_MONTHS: dict[str, int] = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
SPANISH_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class OcrResult:
    raw_text: str
    rfc: str | None
    issued_at: date | None
    valid_until: date | None


def _parse_spanish_dates(text: str) -> list[date]:
    out: list[date] = []
    for day, month_name, year in SPANISH_DATE_RE.findall(text):
        month = _SPANISH_MONTHS.get(month_name.lower())
        if not month:
            continue
        try:
            out.append(date(int(year), month, int(day)))
        except ValueError:
            continue
    return out


def _ocr_image(img: Image.Image, lang: str) -> str:
    return pytesseract.image_to_string(img, lang=lang) or ""


def _ocr_pdf(content: bytes, lang: str) -> str:
    pages = convert_from_bytes(content, dpi=200)
    return "\n".join(_ocr_image(p, lang) for p in pages)


def run_ocr(content: bytes, *, mime_type: str, settings: Settings) -> OcrResult:
    try:
        if mime_type == "application/pdf":
            text = _ocr_pdf(content, settings.tesseract_lang)
        elif mime_type.startswith("image/"):
            text = _ocr_image(Image.open(io.BytesIO(content)), settings.tesseract_lang)
        else:
            return OcrResult(raw_text="", rfc=None, issued_at=None, valid_until=None)
    except Exception as exc:  # best-effort: never raises to the caller
        log.warning("ocr.failed", error=str(exc), mime_type=mime_type)
        return OcrResult(raw_text="", rfc=None, issued_at=None, valid_until=None)

    rfc_match = RFC_RE.search(text.upper())
    dates = sorted(_parse_spanish_dates(text))
    issued = dates[0] if dates else None
    expires = dates[-1] if len(dates) >= 2 else None
    return OcrResult(
        raw_text=text,
        rfc=rfc_match.group(1) if rfc_match else None,
        issued_at=issued,
        valid_until=expires,
    )


def cli(path: str) -> OcrResult:
    """Helper invoked from `python -m repse.documents.ocr <path>`."""
    from repse.config import get_settings

    settings = get_settings()
    data = Path(path).read_bytes()
    suffix = Path(path).suffix.lower()
    mime = "application/pdf" if suffix == ".pdf" else f"image/{suffix.lstrip('.')}"
    return run_ocr(data, mime_type=mime, settings=settings)


if __name__ == "__main__":  # pragma: no cover
    import json
    import sys

    result = cli(sys.argv[1])
    print(
        json.dumps(
            {
                "rfc": result.rfc,
                "issued_at": result.issued_at.isoformat() if result.issued_at else None,
                "valid_until": result.valid_until.isoformat() if result.valid_until else None,
            }
        )
    )

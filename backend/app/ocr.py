"""Simple receipt OCR using Tesseract.

Heuristic: run OCR on the uploaded image, collect all number-like tokens that look
like a money amount, and return the largest one as the probable total. Good enough
for auto-fill; user can always correct.
"""

from __future__ import annotations

import io
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False


# Matches amounts like 1234.56 / 1,234.56 / 123 (tolerates currency prefixes R$)
_AMOUNT_RE = re.compile(r"(?:[Rr]\s*)?(\d{1,3}(?:[,\s]\d{3})+|\d+)(?:[.,](\d{2}))?")


def extract_amount_from_path(path: Path) -> Decimal | None:
    if not _AVAILABLE:
        return None
    try:
        img = Image.open(path)
    except Exception:
        return None
    try:
        text = pytesseract.image_to_string(img)
    except Exception:
        return None
    return _largest_amount(text)


def extract_amount_from_bytes(data: bytes) -> Decimal | None:
    if not _AVAILABLE:
        return None
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        return None
    try:
        text = pytesseract.image_to_string(img)
    except Exception:
        return None
    return _largest_amount(text)


def _largest_amount(text: str) -> Decimal | None:
    biggest: Decimal | None = None
    for m in _AMOUNT_RE.finditer(text):
        whole = m.group(1).replace(",", "").replace(" ", "")
        frac = m.group(2)
        raw = whole + ("." + frac if frac else "")
        try:
            val = Decimal(raw)
        except InvalidOperation:
            continue
        # Ignore tiny numbers (likely item counts, VAT %, etc.)
        if val < Decimal("10"):
            continue
        if biggest is None or val > biggest:
            biggest = val
    return biggest

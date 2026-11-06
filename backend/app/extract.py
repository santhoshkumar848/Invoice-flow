"""Turn raw invoice text (or PDF) into structured fields."""
import io, re
from pypdf import PdfReader

AMT = r"([\d,]+(?:\.\d{1,2})?)"
CUR = r"(?:₹|rs\.?|inr|\$)?\s*"

def pdf_to_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join((p.extract_text() or "") for p in reader.pages)

def _num(s):
    return float(s.replace(",", "")) if s else None

def _find(pattern, text, flags=re.I):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def extract_fields(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    vendor = _find(r"(?:vendor|from|supplier)\s*[:\-]\s*(.+)", text) or (lines[0] if lines else None)
    return {
        "vendor": vendor,
        "invoice_number": _find(r"invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9\-/]+)", text),
        "invoice_date": _find(r"date\s*[:\-]\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text),
        "po_number": _find(r"(?:po|purchase\s*order)\s*(?:no\.?|number|#)?\s*[:\-]?\s*(PO-\d+)", text),
        "tax_id": _find(r"(?:gstin|vat(?:\s*id)?|tax\s*id)\s*[:\-]\s*([A-Z0-9]+)", text),
        "subtotal": _num(_find(r"sub\s*-?total\s*[:\-]?\s*" + CUR + AMT, text)),
        "tax": _num(_find(r"(?:gst|vat|tax)(?:\s*\(?\d+%?\)?)?\s*[:\-]\s*" + CUR + AMT, text)),
        "total": _num(_find(r"^\s*(?:grand\s*)?total(?:\s*due)?\s*[:\-]?\s*" + CUR + AMT, text, re.I | re.M)),
    }

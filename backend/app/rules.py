"""Validation, PO matching, duplicate detection and approval routing."""
from .store import INVOICES, PURCHASE_ORDERS

REQUIRED = ["vendor", "invoice_number", "invoice_date", "subtotal", "tax", "total"]
VALID_TAX_RATES = {0, 5, 12, 18, 28}  # GST slabs; edit per jurisdiction
PO_TOLERANCE = 0.02
AUTO_APPROVE_LIMIT = 10_000
MANAGER_LIMIT = 100_000

def issue(code, severity, message):
    return {"code": code, "severity": severity, "message": message}

def validate(inv: dict) -> list[dict]:
    f, out = inv["fields"], []
    for k in REQUIRED:
        if f.get(k) in (None, ""):
            out.append(issue("MISSING_FIELD", "high", f"Missing {k.replace('_', ' ')}."))
    if None not in (f.get("subtotal"), f.get("tax"), f.get("total")):
        if abs(f["subtotal"] + f["tax"] - f["total"]) > 0.01:
            out.append(issue("TOTAL_MISMATCH", "high",
                f"Subtotal + tax = {f['subtotal'] + f['tax']:.2f} but total is {f['total']:.2f}."))
        if f["subtotal"]:
            rate = round(f["tax"] / f["subtotal"] * 100, 1)
            if rate not in VALID_TAX_RATES:
                out.append(issue("TAX_RATE", "medium", f"Tax rate {rate}% is not a standard rate."))
    if not f.get("tax_id"):
        out.append(issue("NO_TAX_ID", "medium", "Vendor tax ID (GSTIN/VAT) not found."))
    for other in INVOICES.values():
        if other["id"] == inv["id"] or other["status"] == "rejected":
            continue
        of = other["fields"]
        if of.get("vendor") == f.get("vendor") and (
            (f.get("invoice_number") and of.get("invoice_number") == f.get("invoice_number"))
            or (of.get("total") == f.get("total") and of.get("invoice_date") == f.get("invoice_date"))):
            out.append(issue("DUPLICATE", "high", f"Possible duplicate of invoice #{other['id']}."))
            break
    po_no = f.get("po_number")
    if not po_no:
        out.append(issue("NO_PO", "medium", "No purchase order referenced."))
    elif po_no not in PURCHASE_ORDERS:
        out.append(issue("PO_NOT_FOUND", "high", f"{po_no} does not exist."))
    else:
        po = PURCHASE_ORDERS[po_no]
        if f.get("vendor") and f["vendor"].lower() != po["vendor"].lower():
            out.append(issue("PO_VENDOR", "high", f"{po_no} belongs to {po['vendor']}."))
        remaining = po["amount"] - po["billed"]
        if f.get("total") and f["total"] > remaining * (1 + PO_TOLERANCE):
            out.append(issue("PO_AMOUNT", "high",
                f"Total {f['total']:.2f} exceeds remaining PO balance {remaining:.2f}."))
    return out

def route(inv: dict) -> tuple[str, str]:
    """Returns (status, approver). Any issue sends the invoice to human review."""
    if inv["issues"]:
        return "needs_review", "AP specialist"
    total = inv["fields"]["total"]
    if total <= AUTO_APPROVE_LIMIT:
        return "approved", "auto"
    return "pending_approval", "Department manager" if total <= MANAGER_LIMIT else "Finance controller"

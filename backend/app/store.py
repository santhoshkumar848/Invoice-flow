"""In-memory store. Swap for Postgres in production (see README roadmap)."""
from datetime import datetime, timezone
import itertools

_ids = itertools.count(1)
INVOICES: dict[int, dict] = {}

# Seed purchase orders (stand-in for an ERP / accounting-system sync)
PURCHASE_ORDERS = {
    "PO-1001": {"vendor": "Acme Steel Pvt Ltd", "amount": 118000.00, "billed": 0.0},
    "PO-1002": {"vendor": "Bright Packaging Co", "amount": 25000.00, "billed": 0.0},
    "PO-1003": {"vendor": "Nimbus Cloud Services", "amount": 600000.00, "billed": 0.0},
}

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def new_id() -> int:
    return next(_ids)

def reset():
    global _ids
    INVOICES.clear()
    _ids = itertools.count(1)
    for po in PURCHASE_ORDERS.values():
        po["billed"] = 0.0

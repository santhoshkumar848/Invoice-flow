# InvoiceFlow

AI-assisted accounts-payable automation: capture invoices in any layout, extract fields, match purchase orders, check tax, detect duplicates, route approvals, and send only the exceptions to a human.

## The problem
Finance teams receive invoices in many formats and re-key data, match POs, check tax and chase discrepancies by hand. Mistakes cause duplicate payments, late fees and fraud exposure.

## What it does
| Step | Implementation |
|---|---|
| Capture | Upload PDF/text or paste text (`backend/app/extract.py`) |
| Validate | Required fields, subtotal + tax = total, standard tax slabs, tax ID present |
| Match | PO exists, vendor matches, amount within remaining PO balance (2% tolerance) |
| Fraud / duplicates | Same vendor + invoice number, or same vendor + total + date |
| Route | No issues and ≤ ₹10,000 → auto-approved; ≤ ₹1,00,000 → manager; above → controller; any issue → AP specialist |
| Human review | Edit extracted fields, re-check, approve or reject |
| Audit | Every action is logged per invoice |

Thresholds live at the top of `backend/app/rules.py`.

## Sign-in and roles
All API routes require login. Demo accounts (change before deploying, and set the `SECRET_KEY` environment variable):

| Email | Password | Can approve |
|---|---|---|
| ap@invoiceflow.com | ap123 | invoices in AP review |
| manager@invoiceflow.com | manager123 | manager-level and AP review |
| controller@invoiceflow.com | controller123 | everything |

## Run locally
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload      # open http://localhost:8000
PYTHONPATH=. pytest -q             # run tests
```
Or with Docker: `docker build -t invoiceflow . && docker run -p 8000:8000 invoiceflow`

Try `samples/invoice_ok.txt` (clean) and `samples/invoice_problem.txt` (wrong tax, total mismatch, missing tax ID).

## API
`POST /api/invoices` · `GET /api/invoices` · `PATCH /api/invoices/{id}` · `POST /api/invoices/{id}/decision` · `GET /api/purchase-orders` · `GET /api/stats` · Docs at `/docs`

## Roadmap (what to add for production)
- OCR for scanned PDFs and an LLM extraction step for unusual layouts
- PostgreSQL storage and user login with roles
- Connectors for Tally, Zoho Books, QuickBooks, SAP (PO and vendor sync, payment export)
- Email-inbox ingestion, 3-way match with goods receipts, multi-currency

## Business model
Monthly SaaS tiers by invoice volume; enterprise licence with SSO, audit exports and ERP connectors.

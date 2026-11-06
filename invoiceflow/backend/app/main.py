from pathlib import Path
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from . import store
from .auth import current_user, login
from .extract import extract_fields, pdf_to_text
from .rules import validate, route

app = FastAPI(title="InvoiceFlow API")

# Who may approve what, by the approver the rules engine chose
CAN_DECIDE = {"AP specialist": {"ap", "manager", "controller"},
              "Department manager": {"manager", "controller"},
              "Finance controller": {"controller"}}

class Credentials(BaseModel):
    email: str
    password: str

@app.post("/api/login")
def do_login(c: Credentials):
    return login(c.email, c.password)

@app.get("/api/me")
def me(user=Depends(current_user)):
    return user

def process(inv: dict):
    inv["issues"] = validate(inv)
    inv["status"], inv["approver"] = route(inv)
    return inv

def log(inv, event):
    inv["audit"].append({"at": store.now(), "event": event})

@app.post("/api/invoices")
async def upload(file: UploadFile | None = File(None), text: str = Form(""), user=Depends(current_user)):
    if file:
        raw = await file.read()
        text = pdf_to_text(raw) if file.filename.lower().endswith(".pdf") else raw.decode("utf-8", "ignore")
    if not text.strip():
        raise HTTPException(400, "Upload a PDF/text invoice or paste invoice text.")
    inv = {"id": store.new_id(), "source": file.filename if file else "pasted text",
           "raw_text": text, "fields": extract_fields(text), "audit": [], "created_at": store.now()}
    store.INVOICES[inv["id"]] = inv
    process(inv)
    log(inv, f"Uploaded by {user['name']}. Checked: {inv['status']} ({len(inv['issues'])} issues)")
    return inv

@app.get("/api/invoices")
def list_invoices(user=Depends(current_user)):
    return sorted(store.INVOICES.values(), key=lambda i: -i["id"])

def get(iid):
    if iid not in store.INVOICES:
        raise HTTPException(404, "Invoice not found")
    return store.INVOICES[iid]

class Correction(BaseModel):
    fields: dict

@app.patch("/api/invoices/{iid}")
def correct(iid: int, body: Correction, user=Depends(current_user)):
    inv = get(iid)
    inv["fields"].update({k: v for k, v in body.fields.items() if k in inv["fields"]})
    process(inv)
    log(inv, f"Fields corrected by {user['name']}. Re-checked: {inv['status']}")
    return inv

class Decision(BaseModel):
    action: str  # approve | reject
    note: str = ""

@app.post("/api/invoices/{iid}/decision")
def decide(iid: int, d: Decision, user=Depends(current_user)):
    inv = get(iid)
    if user["role"] not in CAN_DECIDE.get(inv["approver"], set()):
        raise HTTPException(403, f"This invoice needs approval from: {inv['approver']}.")
    if d.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be approve or reject")
    inv["status"] = "approved" if d.action == "approve" else "rejected"
    po = store.PURCHASE_ORDERS.get(inv["fields"].get("po_number"))
    if inv["status"] == "approved" and po:
        po["billed"] += inv["fields"].get("total") or 0
    log(inv, f"{inv['status'].capitalize()} by {user['name']}. {d.note}".strip())
    return inv

@app.get("/api/purchase-orders")
def pos(user=Depends(current_user)):
    return store.PURCHASE_ORDERS

@app.get("/api/stats")
def stats(user=Depends(current_user)):
    inv = list(store.INVOICES.values())
    by = lambda s: [i for i in inv if i["status"] == s]
    return {"total": len(inv), "needs_review": len(by("needs_review")),
            "pending_approval": len(by("pending_approval")), "approved": len(by("approved")),
            "rejected": len(by("rejected")),
            "approved_value": sum(i["fields"].get("total") or 0 for i in by("approved"))}

FRONT = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/static", StaticFiles(directory=FRONT), name="static")

@app.get("/login")
def login_page():
    return FileResponse(FRONT / "login.html")

@app.get("/")
def index():
    return FileResponse(FRONT / "index.html")

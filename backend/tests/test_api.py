from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app import store

c = TestClient(app)

def auth(email, pw):
    t = c.post('/api/login', json={'email': email, 'password': pw}).json()['token']
    return {'Authorization': 'Bearer ' + t}

AP = ('ap@invoiceflow.com', 'ap123')
MGR = ('manager@invoiceflow.com', 'manager123')
S = Path(__file__).resolve().parents[2] / "samples"

def setup_function(_): store.reset()

def up(name):
    return c.post("/api/invoices", data={"text": (S / name).read_text()}, headers=auth(*AP)).json()

def test_clean_invoice_goes_to_approver():
    inv = up("invoice_ok.txt")
    assert inv["issues"] == [] and inv["status"] == "pending_approval"

def test_bad_tax_and_total_flagged():
    codes = {i["code"] for i in up("invoice_problem.txt")["issues"]}
    assert {"TOTAL_MISMATCH", "TAX_RATE", "NO_TAX_ID"} <= codes

def test_duplicate_detected():
    up("invoice_ok.txt")
    assert "DUPLICATE" in {i["code"] for i in up("invoice_ok.txt")["issues"]}

def test_correction_reroutes():
    inv = up("invoice_problem.txt")
    r = c.patch(f"/api/invoices/{inv['id']}", json={"fields": {"tax": 18000, "total": 118000, "tax_id": "27AAAAA0000A1Z5"}}, headers=auth(*AP)).json()
    assert r["issues"] == [] and r["status"] == "pending_approval"

def test_login_required_and_bad_password():
    assert c.get("/api/invoices").status_code == 401
    assert c.post("/api/login", json={"email": "ap@invoiceflow.com", "password": "x"}).status_code == 401

def test_only_manager_can_approve_manager_invoice():
    inv = up("invoice_ok.txt")  # routed to Department manager
    url = f"/api/invoices/{inv['id']}/decision"
    assert c.post(url, json={"action": "approve"}, headers=auth(*AP)).status_code == 403
    assert c.post(url, json={"action": "approve"}, headers=auth(*MGR)).json()["status"] == "approved"

"""Simple signed-token auth with roles (stdlib only). Set SECRET_KEY in production."""
import base64, hashlib, hmac, json, os, time
from fastapi import Header, HTTPException

SECRET = os.environ.get("SECRET_KEY", "dev-secret-change-me").encode()
TOKEN_TTL = 8 * 3600

def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()

def _user(name, role, password):
    salt = os.urandom(8).hex()
    return {"name": name, "role": role, "salt": salt, "hash": _hash(password, salt)}

# Demo accounts. Replace with a users table in production.
USERS = {
    "ap@invoiceflow.com": _user("Asha (AP specialist)", "ap", "ap123"),
    "manager@invoiceflow.com": _user("Manoj (Manager)", "manager", "manager123"),
    "controller@invoiceflow.com": _user("Chitra (Controller)", "controller", "controller123"),
}

def login(email: str, password: str) -> dict:
    u = USERS.get(email.strip().lower())
    if not u or not hmac.compare_digest(u["hash"], _hash(password, u["salt"])):
        raise HTTPException(401, "Email or password is incorrect.")
    payload = base64.urlsafe_b64encode(json.dumps(
        {"email": email.strip().lower(), "exp": time.time() + TOKEN_TTL}).encode()).decode()
    sig = hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return {"token": f"{payload}.{sig}", "name": u["name"], "role": u["role"]}

def current_user(authorization: str = Header(default="")) -> dict:
    try:
        payload, sig = authorization.removeprefix("Bearer ").split(".")
        good = hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()
        data = json.loads(base64.urlsafe_b64decode(payload))
        if not hmac.compare_digest(sig, good) or data["exp"] < time.time():
            raise ValueError
        u = USERS[data["email"]]
    except Exception:
        raise HTTPException(401, "Please sign in.")
    return {"email": data["email"], "name": u["name"], "role": u["role"]}

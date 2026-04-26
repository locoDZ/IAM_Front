import json
import base64
import httpx
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from vuln import router as vuln_router
from crypto import (
    verify_password, hash_password,
    encrypt_ticket, decrypt_ticket,
    encrypt_with_session_key, decrypt_with_session_key,
    generate_session_key, build_tgt, build_service_ticket,
    is_expired
)

app = FastAPI(title="KDC Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LOGGING_URL = "http://localhost:8004"

app.include_router(vuln_router)

# Load users DB
USERS_FILE = Path(__file__).parent / "users.json"
with open(USERS_FILE) as f:
    USERS_DB = json.load(f)["users"]

# Replay attack protection: store used ticket IDs
used_ticket_ids: set = set()


# ─── Models ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TicketRequest(BaseModel):
    tgt_token: str
    service: str
    authenticator: str  # encrypted timestamp with session key


class ValidateTicketRequest(BaseModel):
    service_ticket: str
    authenticator: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def log_event(event_type: str, details: dict):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{LOGGING_URL}/log", json={
                "service": "KDC",
                "event_type": event_type,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            }, timeout=2.0)
    except Exception:
        pass  # Don't fail if logging is down


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "KDC running", "port": 8001}


@app.post("/login")
async def login(req: LoginRequest):
    """
    Step 1: Client sends credentials → KDC returns TGT + session key.
    """
    user = USERS_DB.get(req.username)

    if not user or not verify_password(req.password, user["password"]):
        await log_event("LOGIN_FAILED", {"username": req.username, "reason": "Invalid credentials"})
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Generate session key
    session_key = generate_session_key()

    # Build and encrypt TGT
    tgt_payload = build_tgt(req.username, user, session_key)
    encrypted_tgt = encrypt_ticket(tgt_payload)

    # Encrypt session key with user's password hash (so only user can read it)
    user_key = bytes.fromhex(user["password"])[:32]
    encrypted_session_key = encrypt_with_session_key(
        {"session_key": base64.b64encode(session_key).decode()},
        user_key
    )

    await log_event("LOGIN_SUCCESS", {
        "username": req.username,
        "role": user["role"],
        "department": user["department"],
        "ticket_id": tgt_payload["ticket_id"]
    })

    return {
        "tgt": encrypted_tgt,
        "encrypted_session_key": encrypted_session_key,
        "session_key": base64.b64encode(session_key).decode(),  # for demo clarity
        "user": {
            "username": req.username,
            "role": user["role"],
            "department": user["department"],
            "clearance": user["clearance"]
        }
    }


@app.post("/request-ticket")
async def request_ticket(req: TicketRequest):
    """
    Step 2: Client presents TGT + authenticator → KDC returns Service Ticket.
    """
    # Decrypt TGT
    try:
        tgt = decrypt_ticket(req.tgt_token)
    except Exception:
        await log_event("TICKET_REQUEST_FAILED", {"reason": "Invalid or tampered TGT"})
        raise HTTPException(status_code=401, detail="Invalid or tampered TGT")

    # Check TGT expiry
    if is_expired(tgt["expires_at"]):
        await log_event("TICKET_REQUEST_FAILED", {
            "username": tgt.get("username"),
            "reason": "TGT expired"
        })
        raise HTTPException(status_code=401, detail="TGT has expired")

    # Verify authenticator (replay protection)
    session_key = base64.b64decode(tgt["session_key"])
    try:
        auth_data = decrypt_with_session_key(req.authenticator, session_key)
        auth_time = datetime.fromisoformat(auth_data["timestamp"])
        diff = abs((datetime.utcnow() - auth_time).total_seconds())
        if diff > 300:  # 5 minute window
            raise HTTPException(status_code=401, detail="Authenticator timestamp out of window")
    except HTTPException:
        raise
    except Exception:
        await log_event("TICKET_REQUEST_FAILED", {
            "username": tgt.get("username"),
            "reason": "Invalid authenticator"
        })
        raise HTTPException(status_code=401, detail="Invalid authenticator")

    # Check TGT ticket_id not reused
    if tgt["ticket_id"] in used_ticket_ids:
        await log_event("REPLAY_ATTACK_DETECTED", {
            "username": tgt.get("username"),
            "ticket_id": tgt["ticket_id"]
        })
        raise HTTPException(status_code=401, detail="Replay attack detected: ticket already used")

    # Get fresh user data
    user = USERS_DB.get(tgt["username"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate new service session key
    service_session_key = generate_session_key()

    # Build service ticket
    st_payload = build_service_ticket(tgt["username"], user, req.service, service_session_key)
    encrypted_st = encrypt_ticket(st_payload)

    await log_event("TICKET_ISSUED", {
        "username": tgt["username"],
        "service": req.service,
        "ticket_id": st_payload["ticket_id"]
    })

    return {
        "service_ticket": encrypted_st,
        "service_session_key": base64.b64encode(service_session_key).decode(),
        "ticket_id": st_payload["ticket_id"]
    }


@app.post("/validate-ticket")
async def validate_ticket(req: ValidateTicketRequest):
    """
    Step 3: Resource server calls this to validate a service ticket.
    """
    try:
        ticket = decrypt_ticket(req.service_ticket)
    except Exception:
        await log_event("TICKET_VALIDATION_FAILED", {"reason": "Tampered or invalid ticket"})
        raise HTTPException(status_code=401, detail="Invalid or tampered service ticket")

    if ticket.get("type") != "SERVICE_TICKET":
        raise HTTPException(status_code=401, detail="Not a service ticket")

    if is_expired(ticket["expires_at"]):
        await log_event("TICKET_VALIDATION_FAILED", {
            "username": ticket.get("username"),
            "reason": "Service ticket expired"
        })
        raise HTTPException(status_code=401, detail="Service ticket expired")

    # Replay protection
    if ticket["ticket_id"] in used_ticket_ids:
        await log_event("REPLAY_ATTACK_DETECTED", {
            "username": ticket.get("username"),
            "ticket_id": ticket["ticket_id"]
        })
        raise HTTPException(status_code=401, detail="Replay attack detected")

    used_ticket_ids.add(ticket["ticket_id"])

    await log_event("TICKET_VALIDATED", {
        "username": ticket["username"],
        "service": ticket["service"],
        "role": ticket["role"]
    })

    return {
        "valid": True,
        "username": ticket["username"],
        "role": ticket["role"],
        "department": ticket["department"],
        "clearance": ticket["clearance"],
        "service": ticket["service"],
        "expires_at": ticket["expires_at"]
    }


@app.get("/users")
async def list_users():
    """Admin endpoint to list users (without passwords)."""
    return {
        username: {k: v for k, v in data.items() if k not in ("password", "plain_password")}
        for username, data in USERS_DB.items()
    }
class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str        # Admin, Manager, Employee
    department: str  # HR, Finance, IT, Operations
    clearance: str   # secret, confidential, public
    location: str = "internal"

@app.post("/users/create")
async def create_user(req: CreateUserRequest):
    if req.username in USERS_DB:
        raise HTTPException(status_code=400, detail="User already exists")
    if req.role not in ["Admin", "Manager", "Employee"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    if req.department not in ["HR", "Finance", "IT", "Operations"]:
        raise HTTPException(status_code=400, detail="Invalid department")
    if req.clearance not in ["secret", "confidential", "public"]:
        raise HTTPException(status_code=400, detail="Invalid clearance")

    USERS_DB[req.username] = {
        "password": hash_password(req.password),
        "role": req.role,
        "department": req.department,
        "clearance": req.clearance,
        "location": req.location
    }

    # Persist to users.json
    with open(USERS_FILE, "w") as f:
        json.dump({"users": USERS_DB}, f, indent=2)

    await log_event("USER_CREATED", {
        "username": req.username,
        "role": req.role,
        "department": req.department
    })

    return {"success": True, "message": f"User '{req.username}' created"}


@app.delete("/users/{username}")
async def delete_user(username: str):
    if username not in USERS_DB:
        raise HTTPException(status_code=404, detail="User not found")
    if username in ["alice", "bob", "carol", "dave"]:
        raise HTTPException(status_code=403, detail="Cannot delete default users")

    del USERS_DB[username]

    with open(USERS_FILE, "w") as f:
        json.dump({"users": USERS_DB}, f, indent=2)

    await log_event("USER_DELETED", {"username": username})

    return {"success": True, "message": f"User '{username}' deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

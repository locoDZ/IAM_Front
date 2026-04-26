"""
VULNERABLE KDC ENDPOINTS
========================
These endpoints simulate real-world Kerberos vulnerabilities for educational purposes.
Each vulnerability is clearly marked with:
    [VULN] - what the vulnerability is
    [FIX]  - what the secure version does instead
"""

import json
import base64
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from crypto import (
    encrypt_ticket, decrypt_ticket,
    generate_session_key, build_tgt, build_service_ticket,
    is_expired, generate_ticket_id, hash_password
)

router = APIRouter(prefix="/vuln", tags=["Vulnerable Endpoints"])

USERS_FILE = Path(__file__).parent / "users.json"
with open(USERS_FILE) as f:
    USERS_DB = json.load(f)["users"]

# Exposed master secret - simulates krbtgt hash exposure
# [VULN] This secret is hardcoded and exposed via /vuln/krbtgt endpoint
# [FIX]  In secure version, this key never leaves the KDC
KRBTGT_SECRET = "krbtgt-super-secret-2024"

# Weak encryption key for Silver Ticket demo
# [VULN] Service key is static and weak
# [FIX]  Each service should have a unique strong key rotated regularly
SERVICE_KEYS = {
    "hr_service": "weak-hr-key-123",
    "finance_service": "weak-finance-key-456",
    "it_service": "weak-it-key-789",
}

# Users with pre-auth disabled (AS-REP Roasting target)
# [VULN] These users don't require pre-authentication
# [FIX]  All users should require pre-authentication
PREAUTHENTICATION_DISABLED = ["carol", "dave"]

# No replay tracking in vulnerable mode
# [VULN] Used ticket IDs are not tracked
# [FIX]  Secure version tracks all used ticket IDs
used_ticket_ids_vuln: set = set()  # intentionally not checked


# ─── Models ───────────────────────────────────────────────────────────────────

class VulnLoginRequest(BaseModel):
    username: str
    password: str = ""  # [VULN] password is optional for AS-REP Roasting


class VulnTicketRequest(BaseModel):
    tgt_token: str
    service: str
    authenticator: str = ""  # [VULN] authenticator not verified


class VulnValidateRequest(BaseModel):
    service_ticket: str
    # [VULN] no authenticator required at all


class SilverTicketRequest(BaseModel):
    username: str
    role: str
    department: str
    clearance: str
    service: str


class DCsyncRequest(BaseModel):
    role: str  # [VULN] only checks role from request body, not from a validated ticket


# ─── AS-REP Roasting ──────────────────────────────────────────────────────────
"""
AS-REP Roasting:
    [VULN] Users with pre-auth disabled can be targeted without knowing their password.
           Attacker requests a TGT for these users and gets back encrypted data
           they can crack offline.
    [FIX]  /login requires password verification for ALL users (no pre-auth bypass).
           Secure endpoint: POST /login
"""

@router.post("/asrep-roast/{username}")
async def asrep_roast(username: str):
    """
    [ATTACK] AS-REP Roasting
    No password needed — returns encrypted TGT for users with pre-auth disabled.
    Attacker cracks the TGT offline to get the user's password.
    """
    if username not in PREAUTHENTICATION_DISABLED:
        raise HTTPException(
            status_code=403,
            detail=f"User '{username}' has pre-authentication enabled. Try: carol, dave"
        )

    user = USERS_DB.get(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # [VULN] No password check — TGT issued without authentication
    session_key = generate_session_key()
    tgt_payload = build_tgt(username, user, session_key)
    encrypted_tgt = encrypt_ticket(tgt_payload)

    return {
        "vulnerability": "AS-REP Roasting",
        "description": "TGT issued without password verification",
        "affected_user": username,
        "encrypted_tgt": encrypted_tgt,
        "session_key": base64.b64encode(session_key).decode(),
        "warning": "In a real attack, attacker cracks this offline with hashcat",
        "fix": "Enable pre-authentication for all users (enforced in POST /login)"
    }


# ─── Kerberoasting ────────────────────────────────────────────────────────────
"""
Kerberoasting:
    [VULN] Service tickets are encrypted with weak/static service keys.
           Any authenticated user can request a service ticket and crack it offline
           to get the service account password.
    [FIX]  Use strong, rotated service keys. Secure endpoint validates properly.
           Secure endpoint: POST /request-ticket
"""

@router.post("/kerberoast")
async def kerberoast(req: VulnLoginRequest):
    """
    [ATTACK] Kerberoasting
    Authenticated user requests service ticket encrypted with weak service key.
    Attacker cracks it offline to get service account credentials.
    """
    user = USERS_DB.get(req.username)
    if not user or user["password"] != hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # [VULN] Service ticket encrypted with weak static key (not rotated, not strong)
    weak_tickets = {}
    for service, weak_key in SERVICE_KEYS.items():
        session_key = generate_session_key()
        st_payload = build_service_ticket(req.username, user, service, session_key)

        # Simulate weak encryption by encoding with weak key
        import hmac as hmac_lib
        weak_hash = hmac_lib.new(
            weak_key.encode(),
            json.dumps(st_payload).encode(),
            hashlib.sha256
        ).hexdigest()

        weak_tickets[service] = {
            "service_ticket": encrypt_ticket(st_payload),
            "weak_key_hash": weak_hash,
            "service_key_used": weak_key,  # [VULN] key exposed for demo
        }

    return {
        "vulnerability": "Kerberoasting",
        "description": "Service tickets encrypted with weak static keys — crackable offline",
        "username": req.username,
        "service_tickets": weak_tickets,
        "fix": "Use strong randomly generated service keys rotated regularly"
    }


# ─── Golden Ticket ────────────────────────────────────────────────────────────
"""
Golden Ticket:
    [VULN] The krbtgt secret key is exposed. An attacker with this key
           can forge TGTs for ANY user, including domain admins,
           with any expiry, completely bypassing authentication.
    [FIX]  krbtgt secret never leaves the KDC. Secure version has no such endpoint.
"""

@router.get("/krbtgt")
async def expose_krbtgt():
    """
    [ATTACK] Golden Ticket - Step 1: Get krbtgt secret
    In real attacks this comes from DCSync or LSASS dump.
    Here we simulate the exposure.
    """
    return {
        "vulnerability": "Golden Ticket",
        "description": "krbtgt secret exposed — can now forge any TGT",
        "krbtgt_secret": KRBTGT_SECRET,
        "krbtgt_hash": hashlib.sha256(KRBTGT_SECRET.encode()).hexdigest(),
        "warning": "With this key, attacker can forge TGTs for any user",
        "fix": "krbtgt secret must never be exposed. Rotate it immediately after compromise."
    }


@router.post("/golden-ticket")
async def forge_golden_ticket(username: str, role: str = "Admin"):
    """
    [ATTACK] Golden Ticket - Step 2: Forge a TGT for any user with any role
    Uses the exposed krbtgt secret to create a valid-looking TGT.
    """
    # [VULN] Forge TGT using exposed krbtgt secret — no real authentication
    forged_user = {
        "role": role,
        "department": "IT",
        "clearance": "secret",
        "location": "internal"
    }

    session_key = generate_session_key()
    tgt_payload = build_tgt(username, forged_user, session_key)

    # Override expiry to 10 years (golden ticket characteristic)
    tgt_payload["expires_at"] = (datetime.utcnow() + timedelta(days=3650)).isoformat()
    tgt_payload["forged"] = True
    tgt_payload["krbtgt_used"] = KRBTGT_SECRET

    forged_tgt = encrypt_ticket(tgt_payload)

    return {
        "vulnerability": "Golden Ticket",
        "description": f"Forged TGT for '{username}' with role '{role}' — valid for 10 years",
        "forged_tgt": forged_tgt,
        "session_key": base64.b64encode(session_key).decode(),
        "expires_at": tgt_payload["expires_at"],
        "fix": "Secure /login never issues TGTs without password verification"
    }


# ─── Silver Ticket ────────────────────────────────────────────────────────────
"""
Silver Ticket:
    [VULN] Resource server blindly trusts the service ticket without
           validating it with the KDC. Attacker forges a service ticket
           using the exposed service key.
    [FIX]  Resource server always calls KDC /validate-ticket.
           Secure resource server never trusts ticket content directly.
"""

@router.post("/silver-ticket")
async def forge_silver_ticket(req: SilverTicketRequest):
    """
    [ATTACK] Silver Ticket
    Forge a service ticket using the weak service key.
    No KDC interaction needed — bypasses authentication entirely.
    """
    service_key = SERVICE_KEYS.get(req.service)
    if not service_key:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown service. Available: {list(SERVICE_KEYS.keys())}"
        )

    # [VULN] Forge service ticket without KDC involvement
    forged_user = {
        "role": req.role,
        "department": req.department,
        "clearance": req.clearance,
        "location": "internal"
    }

    session_key = generate_session_key()
    st_payload = build_service_ticket(req.username, forged_user, req.service, session_key)
    st_payload["forged"] = True
    st_payload["expires_at"] = (datetime.utcnow() + timedelta(days=30)).isoformat()

    forged_st = encrypt_ticket(st_payload)

    return {
        "vulnerability": "Silver Ticket",
        "description": f"Forged service ticket for '{req.service}' as '{req.username}' with role '{req.role}'",
        "forged_service_ticket": forged_st,
        "service_key_used": service_key,
        "fix": "Resource server must always validate tickets with KDC — never trust blindly"
    }


# ─── Token Replay ─────────────────────────────────────────────────────────────
"""
Token Replay:
    [VULN] Service tickets are accepted multiple times — no replay protection.
           Attacker intercepts a valid ticket and reuses it indefinitely.
    [FIX]  Secure /validate-ticket tracks used ticket IDs and rejects reuse.
"""

@router.post("/validate-ticket-no-replay")
async def validate_no_replay(req: VulnValidateRequest):
    """
    [ATTACK] Token Replay
    Validates a service ticket WITHOUT checking if it was already used.
    Attacker can replay the same ticket multiple times.
    """
    try:
        ticket = decrypt_ticket(req.service_ticket)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid ticket")

    if is_expired(ticket["expires_at"]):
        raise HTTPException(status_code=401, detail="Ticket expired")

    # [VULN] No replay check — ticket_id never tracked
    # used_ticket_ids_vuln intentionally not checked

    return {
        "vulnerability": "Token Replay",
        "description": "Ticket accepted without replay check — can be reused indefinitely",
        "valid": True,
        "username": ticket["username"],
        "role": ticket["role"],
        "ticket_id": ticket["ticket_id"],
        "warning": "This ticket can be replayed as many times as attacker wants",
        "fix": "Secure /validate-ticket tracks ticket IDs and rejects reuse"
    }


# ─── DCSync / Privilege Escalation ────────────────────────────────────────────
"""
DCSync / Hash Dump:
    [VULN] Endpoint dumps all user hashes if requester claims to have 'Admin' role.
           Role is taken from the request body — not from a validated ticket.
           Attacker just sends role=Admin in the body.
    [FIX]  Role must come from a validated KDC ticket, not from user input.
"""

@router.post("/dcsync")
async def dcsync(req: DCsyncRequest):
    """
    [ATTACK] DCSync / Privilege Escalation
    Dumps all user hashes. Role check uses request body — easily spoofed.
    """
    # [VULN] Role taken from request body — attacker sends role=Admin
    if req.role != "Admin":
        raise HTTPException(status_code=403, detail="Requires Admin role")

    # Dump all hashes
    dumped = {}
    for username, data in USERS_DB.items():
        dumped[username] = {
            "ntlm_hash": data["password"],
            "role": data["role"],
            "department": data["department"],
            "clearance": data["clearance"]
        }

    return {
        "vulnerability": "DCSync / Privilege Escalation",
        "description": "All user hashes dumped — role was never verified via KDC ticket",
        "hashes": dumped,
        "fix": "Role must be extracted from a validated KDC service ticket, not request body"
    }

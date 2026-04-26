
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="API Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Service URLs ─────────────────────────────────────────────────────────────
KDC_URL      = "http://localhost:8001"
PDP_URL      = "http://localhost:8002"
RESOURCE_URL = "http://localhost:8003"
LOGGING_URL  = "http://localhost:8004"


# ─── Models ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class TicketRequest(BaseModel):
    tgt_token: str
    service: str

class ResourceRequest(BaseModel):
    service_ticket: str
    name: str
    action: str
    content: Optional[str] = None

class AttackRequest(BaseModel):
    type: str        # asrep, kerberoast, golden, silver, replay, dcsync
    username: Optional[str] = None
    role: Optional[str] = "Admin"
    service: Optional[str] = "hr_service"
    department: Optional[str] = "HR"
    clearance: Optional[str] = "secret"
    tgt_token: Optional[str] = None
    service_ticket: Optional[str] = None
    password: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def log_event(service: str, event_type: str, details: dict):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{LOGGING_URL}/log", json={
                "service": service,
                "event_type": event_type,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            }, timeout=2.0)
    except Exception:
        pass


#async def forward(method: str, url: str, payload: dict) -> dict:
 #   """Forward a request to a microservice."""
  #  async with httpx.AsyncClient() as client:
   #     resp = await client.request(method, url, json=payload, timeout=10.0)
    #    if resp.status_code >= 400:
     ##  return resp.json()
async def forward(method: str, url: str, payload: dict) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, json=payload, timeout=10.0)
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text or "Service error"
            raise HTTPException(status_code=resp.status_code, detail=detail)
        return resp.json()

# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Check health of all services."""
    services = {
        "gateway": "running",
        "kdc": "unknown",
        "pdp": "unknown",
        "resource": "unknown",
        "logging": "unknown"
    }
    async with httpx.AsyncClient() as client:
        for name, url in [("kdc", KDC_URL), ("pdp", PDP_URL),
                          ("resource", RESOURCE_URL), ("logging", LOGGING_URL)]:
            try:
                r = await client.get(f"{url}/health", timeout=2.0)
                services[name] = "running" if r.status_code == 200 else "error"
            except Exception:
                services[name] = "unreachable"
    return services


# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.post("/api/login")
async def login(req: LoginRequest):
    """
    Step 1: Forward login to KDC.
    Returns TGT + session key + user info.
    """
    result = await forward("POST", f"{KDC_URL}/login", {
        "username": req.username,
        "password": req.password
    })

    await log_event("Gateway", "LOGIN", {"username": req.username})

    return {
        "success": True,
        "tgt": result["tgt"],
        "session_key": result["session_key"],
        "user": {
            "username": result["user"]["username"],
            "name": result["user"]["username"].capitalize(),
            "role": result["user"]["role"],
            "department": result["user"]["department"],
            "clearance": result["user"]["clearance"]
        }
    }


@app.post("/api/request-ticket")
async def request_ticket(req: TicketRequest):
    """
    Step 2: Request a service ticket from KDC using TGT.
    """
    result = await forward("POST", f"{KDC_URL}/request-ticket", {
        "tgt_token": req.tgt_token,
        "service": req.service,
        "authenticator": ""
    })

    await log_event("Gateway", "TICKET_REQUESTED", {"service": req.service})

    return {
        "success": True,
        "service_ticket": result["service_ticket"],
        "ticket_id": result["ticket_id"]
    }


# ─── Resource Routes ──────────────────────────────────────────────────────────

@app.post("/api/resource/read")
async def read_resource(req: ResourceRequest):
    """Read a resource — ticket validated by Resource Server → PDP."""
    result = await forward("POST", f"{RESOURCE_URL}/resources/read", {
        "service_ticket": req.service_ticket,
        "name": req.name,
        "type": "file",
        "action": "Read"
    })
    await log_event("Gateway", "RESOURCE_READ", {"resource": req.name})
    return result


@app.post("/api/resource/write")
async def write_resource(req: ResourceRequest):
    """Write to a resource."""
    result = await forward("POST", f"{RESOURCE_URL}/resources/write", {
        "service_ticket": req.service_ticket,
        "name": req.name,
        "type": "file",
        "action": "Write",
        "content": req.content
    })
    await log_event("Gateway", "RESOURCE_WRITE", {"resource": req.name})
    return result


@app.post("/api/resource/delete")
async def delete_resource(req: ResourceRequest):
    """Delete a resource."""
    result = await forward("POST", f"{RESOURCE_URL}/resources/delete", {
        "service_ticket": req.service_ticket,
        "name": req.name,
        "type": "file",
        "action": "Delete"
    })
    await log_event("Gateway", "RESOURCE_DELETE", {"resource": req.name})
    return result


# ─── Attack Demo Routes ───────────────────────────────────────────────────────

@app.post("/api/attack")
async def run_attack(req: AttackRequest):
    """
    Demo endpoint to trigger vulnerable attack endpoints on KDC.
    Used by the frontend attack simulation panel.
    """
    await log_event("Gateway", "ATTACK_DEMO", {"type": req.type, "username": req.username})

    if req.type == "asrep":
        return await forward("POST", f"{KDC_URL}/vuln/asrep-roast/{req.username}", {})

    elif req.type == "kerberoast":
        return await forward("POST", f"{KDC_URL}/vuln/kerberoast", {
            "username": req.username,
            "password": req.password or ""
        })

    elif req.type == "golden":
        return await forward("POST", f"{KDC_URL}/vuln/golden-ticket?username={req.username}&role={req.role}", {})

    elif req.type == "silver":
        return await forward("POST", f"{KDC_URL}/vuln/silver-ticket", {
            "username": req.username,
            "role": req.role,
            "department": req.department,
            "clearance": req.clearance,
            "service": req.service
        })

    elif req.type == "replay":
        return await forward("POST", f"{KDC_URL}/vuln/validate-ticket-no-replay", {
            "service_ticket": req.service_ticket or ""
        })

    elif req.type == "dcsync":
        return await forward("POST", f"{KDC_URL}/vuln/dcsync", {
            "role": req.role or "Admin"
        })

    elif req.type == "krbtgt":
        return await forward("GET", f"{KDC_URL}/vuln/krbtgt", {})

    elif req.type == "tamper":
        return await forward("POST", f"{KDC_URL}/vuln/tamper-ticket", {
            "service_ticket": req.service_ticket or "",
            "new_role": req.role or "Admin"
        })

    elif req.type == "unauthorized":
        return await forward("POST", f"{KDC_URL}/vuln/unauthorized-access", {})

    else:
        raise HTTPException(status_code=400, detail=f"Unknown attack type: {req.type}")


# ─── Logs Route ───────────────────────────────────────────────────────────────

@app.get("/api/logs")
async def get_logs(service: Optional[str] = None, event_type: Optional[str] = None):
    """Get logs from the logging service."""
    async with httpx.AsyncClient() as client:
        params = {}
        if service:
            params["service"] = service
        if event_type:
            params["event_type"] = event_type
        resp = await client.get(f"{LOGGING_URL}/logs", params=params, timeout=5.0)
        return resp.json()


@app.get("/api/logs/suspicious")
async def get_suspicious_logs():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{LOGGING_URL}/logs/suspicious", timeout=5.0)
        return resp.json()


@app.get("/api/logs/stats")
async def get_log_stats():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{LOGGING_URL}/logs/stats", timeout=5.0)
        return resp.json()


# ─── PDP Direct ───────────────────────────────────────────────────────────────

@app.get("/api/policies")
async def get_policies():
    """Get all PDP policies."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{PDP_URL}/policies", timeout=5.0)
        return resp.json()


@app.get("/api/users")
async def get_users():
    """Get all users from KDC."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{KDC_URL}/users", timeout=5.0)
        return resp.json()

class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str
    department: str
    clearance: str
    location: str = "internal"

@app.post("/api/users/create")
async def create_user(req: CreateUserRequest):
    return await forward("POST", f"{KDC_URL}/users/create", req.dict())

@app.delete("/api/users/{username}")
async def delete_user(username: str):
    async with httpx.AsyncClient() as client:
        resp = await client.delete(f"{KDC_URL}/users/{username}", timeout=5.0)
        return resp.json()

if __name__ == "__main__":
    import uvicorn
    import subprocess
    import sys
    import time
    import os

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    services = [
        {"name": "Logging",         "path": os.path.join(BASE_DIR, "../loggin/logging_main.py"),             "port": 8004},
        {"name": "KDC",             "path": os.path.join(BASE_DIR, "../kdc/main.py"),                 "port": 8001},
        {"name": "PDP",             "path": os.path.join(BASE_DIR, "../pdp/PDP.py"),                  "port": 8002},
        {"name": "Resource Server", "path": os.path.join(BASE_DIR, "../resource/Resourse.py"), "port": 8003},
    ]

    processes = []

    print("\nStarting SecureCorp microservices...\n")

    for svc in services:
        print(f"  Starting {svc['name']} on port {svc['port']}...")
        p = subprocess.Popen(
            [sys.executable, svc["path"]],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        processes.append(p)
        time.sleep(1)

    print("\nAll services started. Starting Gateway on port 8000...\n")

    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    finally:
        print("\nShutting down all services...")
        for p in processes:
            p.terminate()
"""
Logging Microservice - Port 8004
Receives log events from all services and stores them.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Logging Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LOGS_FILE = Path(__file__).parent / "logs.json"

# In-memory log store (also persisted to file)
logs: list = []

# Load existing logs on startup
if LOGS_FILE.exists():
    with open(LOGS_FILE) as f:
        try:
            logs = json.load(f)
        except Exception:
            logs = []


# ─── Models ───────────────────────────────────────────────────────────────────

class LogEvent(BaseModel):
    service: str           # KDC, PDP, Resource, Gateway
    event_type: str        # LOGIN_SUCCESS, ACCESS_DENIED, etc.
    details: dict
    timestamp: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def save_logs():
    with open(LOGS_FILE, "w") as f:
        json.dump(logs, f, indent=2)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "Logging running", "port": 8004, "total_logs": len(logs)}


@app.post("/log")
async def receive_log(event: LogEvent):
    """Receive a log event from any service."""
    log_entry = {
        "id": str(uuid.uuid4()),
        "service": event.service,
        "event_type": event.event_type,
        "details": event.details,
        "timestamp": event.timestamp or datetime.utcnow().isoformat()
    }
    logs.append(log_entry)
    save_logs()
    return {"status": "logged", "id": log_entry["id"]}


@app.get("/logs")
async def get_logs(
    service: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100
):
    """Get all logs, optionally filtered by service or event type."""
    filtered = logs

    if service:
        filtered = [l for l in filtered if l["service"] == service]
    if event_type:
        filtered = [l for l in filtered if l["event_type"] == event_type]

    # Return most recent first
    return list(reversed(filtered))[-limit:]


@app.get("/logs/suspicious")
async def get_suspicious():
    """Return only suspicious/attack-related events."""
    suspicious_types = [
        "REPLAY_ATTACK_DETECTED",
        "LOGIN_FAILED",
        "TICKET_VALIDATION_FAILED",
        "ACCESS_DENIED",
        "TICKET_TAMPERING"
    ]
    return [l for l in logs if l["event_type"] in suspicious_types]


@app.get("/logs/stats")
async def get_stats():
    """Return log statistics."""
    stats = {}
    for log in logs:
        et = log["event_type"]
        stats[et] = stats.get(et, 0) + 1
    return {
        "total": len(logs),
        "by_event_type": stats,
        "services": list(set(l["service"] for l in logs))
    }


@app.delete("/logs")
async def clear_logs():
    """Clear all logs (admin only in real system)."""
    logs.clear()
    save_logs()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)

import json
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uvicorn

app = FastAPI(
    title="PDP (Policy Decision Point) Microservice",
    description="Authorization service supporting both RBAC and ABAC modes",
    version="2.0.0"
)

# ── File paths ────────────────────────────────────────────────────────────────
USERS_FILE       = 'users.json'
PERMISSIONS_FILE = 'permisions.json'
RESOURCES_FILE   = 'resourese.json'
POLICY_FILE      = 'Policy.json'

# ── Pydantic models ───────────────────────────────────────────────────────────
class AuthorizeRequest(BaseModel):
    username:  str
    resource:  str
    action:    str
    mode:      str = "rbac"          # "rbac" or "abac"
    time:      Optional[str] = None  # HH:MM  – ABAC only (defaults to system time)

class AuthorizeResponse(BaseModel):
    decision:         str
    mode:             str
    reason:           str
    username:         str
    role:             Optional[str]
    resource:         str
    action:           str
    matched_policies: Optional[list]
    resource_details: Optional[Dict[str, Any]]

class HealthResponse(BaseModel):
    status:  str
    service: str
    modes:   list

# ── Generic helpers ───────────────────────────────────────────────────────────
def load_json(filepath: str) -> Optional[Any]:
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def get_user(username: str) -> Optional[Dict]:
    users = load_json(USERS_FILE)
    if not users:
        return None
    return next((u for u in users if u.get('name') == username), None)

def get_resource(resource_name: str) -> Optional[Dict]:
    resources = load_json(RESOURCES_FILE)
    if not resources:
        return None
    return next((r for r in resources if r.get('resource') == resource_name), None)

# ── RBAC logic ────────────────────────────────────────────────────────────────
def check_rbac(role: str, action: str) -> tuple[bool, str]:
    permissions = load_json(PERMISSIONS_FILE)
    if permissions is None:
        return False, "Permission database unavailable"
    if role not in permissions:
        return False, f"Role '{role}' not found in permission database"
    if action in permissions[role]:
        return True, f"Action '{action}' granted to role '{role}'"
    return False, f"Action '{action}' not permitted for role '{role}'"

# ── ABAC logic ────────────────────────────────────────────────────────────────
def evaluate_condition(condition: Dict, ctx: Dict) -> bool:
    """
    Recursively evaluate a single condition rule or compound AND/OR block.
    ctx  = { "user": {...}, "resource": {...}, "action": str, "environment": {...} }
    """
    op = condition.get("operator")

    # ── Compound operators ────────────────────────────────────────────────────
    if op == "AND":
        return all(evaluate_condition(r, ctx) for r in condition.get("rules", []))
    if op == "OR":
        return any(evaluate_condition(r, ctx) for r in condition.get("rules", []))

    # ── Leaf operators ────────────────────────────────────────────────────────
    attr_path = condition.get("attribute", "")
    left_val  = resolve_attr(attr_path, ctx)

    # value_ref  →  compare two attributes against each other
    if "value_ref" in condition:
        right_val = resolve_attr(condition["value_ref"], ctx)
    else:
        right_val = condition.get("value")

    if op == "EQUAL":
        return str(left_val).lower() == str(right_val).lower()
    if op == "NOT_EQUAL":
        return str(left_val).lower() != str(right_val).lower()
    if op == "IN":
        return left_val in [str(v).lower() for v in right_val]
    if op == "NOT_IN":
        return str(left_val).lower() not in [str(v).lower() for v in right_val]
    if op == "LESS_THAN":
        return time_to_minutes(str(left_val)) < time_to_minutes(str(right_val))
    if op == "GREATER_THAN":
        return time_to_minutes(str(left_val)) > time_to_minutes(str(right_val))

    return False   # unknown operator → condition does not match

def resolve_attr(path: str, ctx: Dict) -> Any:
    """Resolve dot-notation paths like 'user.role' or 'resource.classification'."""
    parts = path.split(".")
    if parts[0] == "action" and len(parts) == 1:
        return ctx.get("action", "")
    obj = ctx
    for p in parts:
        if isinstance(obj, dict):
            obj = obj.get(p, "")
        else:
            return ""
    return obj

def time_to_minutes(t: str) -> int:
    """Convert HH:MM to total minutes for easy comparison."""
    try:
        h, m = t.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return 0

def check_abac(user: Dict, resource: Dict, action: str,
               env_time: str) -> tuple[bool, str, list]:
    """
    Evaluate policies from Policy.json against the request context.
    Returns (allowed: bool, reason: str, matched_policy_ids: list)
    """
    policies_data = load_json(POLICY_FILE)
    if not policies_data:
        return False, "Policy database unavailable", []

    ctx = {
        "user":        user,
        "resource":    resource,
        "action":      action,
        "environment": {"time": env_time}
    }

    policies = sorted(
        policies_data.get("policies", []),
        key=lambda p: p.get("priority", 99)
    )

    matched = []

    # ── Pass 1: explicit ALLOW (low priority numbers = first) ─────────────────
    for pol in policies:
        if pol.get("effect") != "allow":
            continue
        if evaluate_condition(pol.get("conditions", {}), ctx):
            matched.append(pol["id"])
            return True, f"Allowed by policy {pol['id']}: {pol['name']}", matched

    # ── Pass 2: DENY policies ─────────────────────────────────────────────────
    for pol in policies:
        if pol.get("effect") != "deny":
            continue
        if evaluate_condition(pol.get("conditions", {}), ctx):
            matched.append(pol["id"])
            return False, f"Denied by policy {pol['id']}: {pol['name']}", matched

    # ── Default ───────────────────────────────────────────────────────────────
    default = policies_data.get("default_effect", "deny")
    if default == "allow":
        return True, "Allowed by default policy", []
    return False, "Denied by default policy (no matching allow rule)", []

# ── FastAPI endpoints ─────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "PDP Microservice v2 – RBAC + ABAC",
        "docs":    "/docs",
        "health":  "/health",
        "modes":   ["rbac", "abac"]
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    return HealthResponse(status="healthy", service="PDP",
                          modes=["rbac", "abac"])

@app.post("/authorize", response_model=AuthorizeResponse, tags=["Authorization"])
def authorize(request: AuthorizeRequest):
    """
    Unified authorization endpoint.

    - **mode**: `rbac` (default) or `abac`
    - **username**: e.g. `bob`, `alice`, `david`, `emma`
    - **resource**: e.g. `employee_records`, `financial_reports`
    - **action**: `Read`, `Write`, or `Delete`
    - **time**: HH:MM string for ABAC time-based checks (optional; defaults to system time)
    """
    mode = request.mode.lower()
    if mode not in ("rbac", "abac"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode '{request.mode}'. Use 'rbac' or 'abac'."
        )

    # ── Common lookups ────────────────────────────────────────────────────────
    resource_info = get_resource(request.resource)
    if resource_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"decision": "denied",
                    "reason": f"Resource '{request.resource}' not found",
                    "mode": mode}
        )

    user = get_user(request.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"decision": "denied",
                    "reason": f"User '{request.username}' not found",
                    "mode": mode}
        )

    role = user.get("role")
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"decision": "denied",
                    "reason": "User has no role assigned",
                    "mode": mode}
        )

    # ── RBAC branch ───────────────────────────────────────────────────────────
    if mode == "rbac":
        permitted, reason = check_rbac(role, request.action)
        response = AuthorizeResponse(
            decision         = "granted" if permitted else "denied",
            mode             = "rbac",
            reason           = reason,
            username         = request.username,
            role             = role,
            resource         = request.resource,
            action           = request.action,
            matched_policies = None,
            resource_details = resource_info
        )
        if not permitted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=response.dict())
        return response

    # ── ABAC branch ───────────────────────────────────────────────────────────
    env_time = request.time or datetime.now().strftime("%H:%M")
    permitted, reason, matched = check_abac(user, resource_info,
                                            request.action, env_time)
    response = AuthorizeResponse(
        decision         = "granted" if permitted else "denied",
        mode             = "abac",
        reason           = reason,
        username         = request.username,
        role             = role,
        resource         = request.resource,
        action           = request.action,
        matched_policies = matched,
        resource_details = resource_info
    )
    if not permitted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=response.dict())
    return response

# ── Debug / admin endpoints ───────────────────────────────────────────────────
@app.get("/users", tags=["Debug"])
def list_users():
    users = load_json(USERS_FILE)
    if users:
        return [{k: v for k, v in u.items() if k != "password"} for u in users]
    raise HTTPException(status_code=500, detail="Could not load users")

@app.get("/resources", tags=["Debug"])
def list_resources():
    resources = load_json(RESOURCES_FILE)
    if resources:
        return resources
    raise HTTPException(status_code=500, detail="Could not load resources")

@app.get("/roles", tags=["Debug"])
def list_roles():
    permissions = load_json(PERMISSIONS_FILE)
    if permissions:
        return permissions
    raise HTTPException(status_code=500, detail="Could not load permissions")

@app.get("/policies", tags=["Debug"])
def list_policies():
    policies = load_json(POLICY_FILE)
    if policies:
        return policies
    raise HTTPException(status_code=500, detail="Could not load policies")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting PDP Microservice v2  (RBAC + ABAC)")
    print("Port: 8002   Docs: http://localhost:8002/docs")
    uvicorn.run(app, host="0.0.0.0", port=8002)
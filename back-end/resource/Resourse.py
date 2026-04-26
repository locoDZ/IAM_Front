import json
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import uvicorn
import httpx

app = FastAPI(
    title="Resource Microservice",
    description="Handles read, write, and delete operations on resources",
    version="1.0.0"
)
PDP_URL = "http://localhost:8002"
KDC_URL = "http://localhost:8001"
#health check endpoint
@app.get("/health")
def health():
    return {"status": "Resource Server running", "port": 8003}

# ── File paths ────────────────────────────────────────────────────────────────
RESOURCES_FILE   = '../data/resourese.json'
RESOURCES_FOLDER = '../data/files'
# ── Pydantic model ────────────────────────────────────────────────────────────
#add service ticket to this stuff here
class RequestedResource(BaseModel):
    name:    str
    type:    str
    action:  str
    content: Optional[str] = None
    service_ticket: str

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_resources():
    # FIX 5: resourese.json is a plain list, not {"resources": [...]}
    try:
        with open(RESOURCES_FILE, 'r') as f:
            return json.load(f)   # returns a list directly
    except FileNotFoundError:
        return []                 # return empty list, not a dict

def save_resources(resources_data):
    with open(RESOURCES_FILE, 'w') as f:
        json.dump(resources_data, f, indent=4)

def find_resource(name: str, resources_data: list):
    """Return the resource dict if found, else None."""
    return next((r for r in resources_data if r["resource"] == name), None)

#add a function to check authorization with pdp
async def check_authorization(service_ticket: str, resource_name: str, action: str):
    async with httpx.AsyncClient() as client:
        # Step 1: Validate ticket with KDC
        kdc_resp = await client.post(f"{KDC_URL}/validate-ticket", json={
            "service_ticket": service_ticket,
            "authenticator": ""
        })
        if kdc_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid or expired ticket")
        
        ticket_data = kdc_resp.json()

        # Step 2: Build user from ticket data
        user = {
            "name": ticket_data["username"],
            "role": ticket_data["role"],
            "department": ticket_data["department"],
            "clearance": ticket_data["clearance"],
            "location": ticket_data.get("location", "internal")
        }

        # Step 3: Ask PDP with user data directly
        pdp_resp = await client.post(f"{PDP_URL}/authorize-direct", json={
            "user": user,
            "resource": resource_name,
            "action": action,
            "mode": "abac"
        })
        if pdp_resp.status_code != 200:
            detail = pdp_resp.json().get("detail", "Access denied")
            raise HTTPException(status_code=403, detail=detail)
# ── Core logic ────────────────────────────────────────────────────────────────
def read(requested_resource: RequestedResource):
    resources_data = load_resources()
    resource = find_resource(requested_resource.name, resources_data)
    if resource is None:
        return None
    # FIX 1: correct folder path (was "../resource/")
    return RESOURCES_FOLDER + "/" + resource["file"]

def delete(requested_resource: RequestedResource):
    resources_data = load_resources()
    resource = find_resource(requested_resource.name, resources_data)
    if resource is None:
        return None
    os.remove(RESOURCES_FOLDER + "/" + resource["file"])
    resources_data.remove(resource)
    save_resources(resources_data)
    return {"message": f"Resource '{requested_resource.name}' deleted successfully."}

def write(requested_resource: RequestedResource):
    resources_data = load_resources()
    resource = find_resource(requested_resource.name, resources_data)
    if resource is None:
        return None                                      # FIX 4: return None so caller knows it failed
    file_path = RESOURCES_FOLDER + "/" + resource["file"]
    # FIX 2: removed pointless read() call
    # FIX 3: opening with 'w' overwrites automatically, no need to delete first
    with open(file_path, 'w') as f:
        f.write(requested_resource.content)
    return {"message": f"Resource '{requested_resource.name}' updated successfully."}

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.post("/resources/read")
async def read_resource(requested_resource: RequestedResource):
    await check_authorization(requested_resource.service_ticket,
                              requested_resource.name, "Read")
    file_path = read(requested_resource)
    if file_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Resource not found")
    with open(file_path, 'r') as f:
        content = f.read()
    return {"content": content}

@app.post("/resources/write")
async def write_resource(requested_resource: RequestedResource):
    await check_authorization(requested_resource.service_ticket,
                              requested_resource.name, "Write")
    if requested_resource.content is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Content is required for write operation")
    result = write(requested_resource)
    if result is None:                                   # FIX 4: now we catch silent failures
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Resource not found")
    return result

@app.post("/resources/delete")
async def delete_resource(requested_resource: RequestedResource):
    await check_authorization(requested_resource.service_ticket,
                              requested_resource.name, "Delete")
    result = delete(requested_resource)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Resource not found")
    return result

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting Resource Microservice")
    print("Port: 8003   Docs: http://localhost:8003/docs")
    uvicorn.run(app, host="0.0.0.0", port=8003)
import json
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import uvicorn

app = FastAPI(
    title="Resource Microservice",
    description="Handles read, write, and delete operations on resources",
    version="1.0.0"
)

# ── File paths ────────────────────────────────────────────────────────────────
RESOURCES_FILE   = '../data/resourese.json'
RESOURCES_FOLDER = '../data/files'
# ── Pydantic model ────────────────────────────────────────────────────────────
class RequestedResource(BaseModel):
    name:    str
    type:    str
    action:  str
    content: Optional[str] = None

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
def read_resource(requested_resource: RequestedResource):
    file_path = read(requested_resource)
    if file_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Resource not found")
    with open(file_path, 'r') as f:
        content = f.read()
    return {"content": content}

@app.post("/resources/write")
def write_resource(requested_resource: RequestedResource):
    if requested_resource.content is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Content is required for write operation")
    result = write(requested_resource)
    if result is None:                                   # FIX 4: now we catch silent failures
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Resource not found")
    return result

@app.post("/resources/delete")
def delete_resource(requested_resource: RequestedResource):
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
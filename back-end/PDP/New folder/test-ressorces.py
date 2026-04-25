"""
test_resources.py  -  Test suite for the Resource Microservice
Run:  python test_resources.py
Requires the Resource server running on http://localhost:8003
"""

import requests
import json
import os

BASE = "http://localhost:8003/resources"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

passed = 0
failed = 0

def check(label, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  [{GREEN}PASS{RESET}] {label}")
        passed += 1
    else:
        print(f"  [{RED}FAIL{RESET}] {label}")
        print(f"         expected : {expected}")
        print(f"         got      : {actual}")
        failed += 1
    print()

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}{'=' * 60}{RESET}")
print(f"{BOLD}  Resource Microservice Test Suite{RESET}")
print(f"{BOLD}{'=' * 60}{RESET}\n")

# ── TEST 1: Read a resource that exists ───────────────────────────────────────
try:
    resp = requests.post(f"{BASE}/read", json={
        "name":   "employee_records",
        "type":   "file",
        "action": "Read"
    }, timeout=5)
    check(
        "Read existing resource → 200",
        resp.status_code,
        200
    )
    check(
        "Read response has 'content' field",
        "content" in resp.json(),
        True
    )
except requests.exceptions.ConnectionError:
    print(f"  [{YELLOW}ERROR{RESET}] Cannot connect to {BASE}. Is the server running?\n")
    exit()

# ── TEST 2: Read a resource that does NOT exist ───────────────────────────────
resp = requests.post(f"{BASE}/read", json={
    "name":   "ghost_resource",
    "type":   "file",
    "action": "Read"
}, timeout=5)
check(
    "Read non-existent resource → 404",
    resp.status_code,
    404
)

# ── TEST 3: Write without content field ───────────────────────────────────────
resp = requests.post(f"{BASE}/write", json={
    "name":   "employee_records",
    "type":   "file",
    "action": "Write"
    # content is missing on purpose
}, timeout=5)
check(
    "Write with no content → 400",
    resp.status_code,
    400
)

# ── TEST 4: Write to a resource that does NOT exist ───────────────────────────
resp = requests.post(f"{BASE}/write", json={
    "name":    "ghost_resource",
    "type":    "file",
    "action":  "Write",
    "content": "some data"
}, timeout=5)
check(
    "Write to non-existent resource → 404",
    resp.status_code,
    404
)

# ── TEST 5: Write to a resource that exists ───────────────────────────────────
resp = requests.post(f"{BASE}/write", json={
    "name":    "operations_schedule",
    "type":    "file",
    "action":  "Write",
    "content": "updated content 123"
}, timeout=5)
check(
    "Write to existing resource → 200",
    resp.status_code,
    200
)

# ── TEST 6: Read back after write to confirm content changed ──────────────────
resp = requests.post(f"{BASE}/read", json={
    "name":   "operations_schedule",
    "type":   "file",
    "action": "Read"
}, timeout=5)
check(
    "Read after write → content matches what was written",
    resp.json().get("content"),
    "updated content 123"
)

# ── TEST 7: Delete a resource that does NOT exist ─────────────────────────────
resp = requests.post(f"{BASE}/delete", json={
    "name":   "ghost_resource",
    "type":   "file",
    "action": "Delete"
}, timeout=5)
check(
    "Delete non-existent resource → 404",
    resp.status_code,
    404
)

# ── TEST 8: Delete a resource that exists ─────────────────────────────────────
# First create a dummy file so we dont destroy real data
os.makedirs("resources", exist_ok=True)
with open("resources/dummy_test_file.txt", 'w') as f:
    f.write("temporary test file")

# Add it to resourese.json temporarily
with open("resourese.json", 'r') as f:
    data = json.load(f)
data.append({
    "resource":       "dummy_test",
    "department":     "Test",
    "classification": "public",
    "file":           "dummy_test_file.txt"
})
with open("resourese.json", 'w') as f:
    json.dump(data, f, indent=4)

resp = requests.post(f"{BASE}/delete", json={
    "name":   "dummy_test",
    "type":   "file",
    "action": "Delete"
}, timeout=5)
check(
    "Delete existing resource → 200",
    resp.status_code,
    200
)

# ── TEST 9: Confirm file is actually gone after delete ────────────────────────
check(
    "File actually deleted from disk",
    os.path.exists("resources/dummy_test_file.txt"),
    False
)

# ── TEST 10: Read deleted resource → should be 404 now ───────────────────────
resp = requests.post(f"{BASE}/read", json={
    "name":   "dummy_test",
    "type":   "file",
    "action": "Read"
}, timeout=5)
check(
    "Read after delete → 404",
    resp.status_code,
    404
)

# ─────────────────────────────────────────────────────────────────────────────
print(f"{BOLD}  Results: {GREEN}{passed} passed{RESET}  {RED}{failed} failed{RESET}  "
      f"(total {passed + failed}){RESET}\n")
"""
test_rbac.py  –  RBAC test suite for the PDP microservice
Run:  python test_rbac.py
Requires the PDP server running on http://localhost:8002
"""

import requests

BASE = "http://localhost:8002/authorize"

# Colour helpers
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

# ── Test cases ────────────────────────────────────────────────────────────────
# Each entry: (label, payload, expected_decision)
RBAC_TESTS = [
    # ── Admin (bob) ───────────────────────────────────────────────────────────
    (
        "Admin: Read employee_records",
        {"username": "bo", "resource": "employee_records", "action": "Read",   "mode": "rbac"},
        "granted"
    ),
    (
        "Admin: Write employee_records",
        {"username": "bob", "resource": "employee_records", "action": "Write",  "mode": "rbac"},
        "granted"
    ),
    (
        "Admin: Delete employee_records",
        {"username": "bob", "resource": "employee_records", "action": "Delete", "mode": "rbac"},
        "granted"
    ),
    (
        "Admin: Read financial_reports",
        {"username": "bob", "resource": "financial_reports", "action": "Read",  "mode": "rbac"},
        "granted"
    ),

    # ── Manager (alice) ───────────────────────────────────────────────────────
    (
        "Manager: Read employee_records",
        {"username": "alice", "resource": "employee_records", "action": "Read",   "mode": "rbac"},
        "granted"
    ),
    (
        "Manager: Write employee_records",
        {"username": "alice", "resource": "employee_records", "action": "Write",  "mode": "rbac"},
        "granted"
    ),
    (
        "Manager: Delete employee_records  [EXPECT DENY]",
        {"username": "alice", "resource": "employee_records", "action": "Delete", "mode": "rbac"},
        "denied"
    ),

    # ── Employee (david) ──────────────────────────────────────────────────────
    (
        "Employee: Read financial_reports",
        {"username": "david", "resource": "financial_reports", "action": "Read",   "mode": "rbac"},
        "granted"
    ),
    (
        "Employee: Write financial_reports  [EXPECT DENY]",
        {"username": "david", "resource": "financial_reports", "action": "Write",  "mode": "rbac"},
        "denied"
    ),
    (
        "Employee: Delete financial_reports  [EXPECT DENY]",
        {"username": "david", "resource": "financial_reports", "action": "Delete", "mode": "rbac"},
        "denied"
    ),

    # ── Employee (emma) ───────────────────────────────────────────────────────
    (
        "Employee: Read operations_schedule",
        {"username": "emma", "resource": "operations_schedule", "action": "Read",  "mode": "rbac"},
        "granted"
    ),
    (
        "Employee: Write operations_schedule  [EXPECT DENY]",
        {"username": "emma", "resource": "operations_schedule", "action": "Write", "mode": "rbac"},
        "denied"
    ),

    # ── Edge cases ────────────────────────────────────────────────────────────
    (
        "Unknown user  [EXPECT 404]",
        {"username": "ghost", "resource": "employee_records", "action": "Read", "mode": "rbac"},
        "denied"
    ),
    (
        "Unknown resource  [EXPECT 404]",
        {"username": "bob", "resource": "nonexistent_db", "action": "Read", "mode": "rbac"},
        "denied"
    ),
]

# ── Runner ────────────────────────────────────────────────────────────────────
def run_tests(tests, suite_name):
    print(f"\n{BOLD}{'=' * 65}{RESET}")
    print(f"{BOLD}  {suite_name}{RESET}")
    print(f"{BOLD}{'=' * 65}{RESET}\n")

    passed = failed = 0

    for label, payload, expected in tests:
        try:
            resp = requests.post(BASE, json=payload, timeout=5)
            body = resp.json()

            # Normalise: 200 → granted body, 4xx → denied in detail
            if resp.status_code == 200:
                actual = body.get("decision", "denied")
                reason = body.get("reason", "")
                matched = body.get("matched_policies")
            else:
                detail = body.get("detail", {})
                actual  = detail.get("decision", "denied") if isinstance(detail, dict) else "denied"
                reason  = detail.get("reason",   "")       if isinstance(detail, dict) else str(detail)
                matched = detail.get("matched_policies")   if isinstance(detail, dict) else None

            ok = (actual == expected)
            tag = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
            if ok:
                passed += 1
            else:
                failed += 1

            pol_str = f"  policies={matched}" if matched else ""
            print(f"  [{tag}] {label}")
            print(f"         → decision={actual}  expected={expected}  reason={reason[:70]}{pol_str}")
            print()

        except requests.exceptions.ConnectionError:
            print(f"  [{YELLOW}ERROR{RESET}] {label}")
            print(f"         Cannot connect to {BASE}. Is the server running?\n")
            failed += 1
        except Exception as e:
            print(f"  [{YELLOW}ERROR{RESET}] {label}  – {e}\n")
            failed += 1

    print(f"{BOLD}  Results: {GREEN}{passed} passed{RESET}  {RED}{failed} failed{RESET}  "
          f"(total {passed + failed}){RESET}\n")
    return passed, failed


if __name__ == "__main__":
    run_tests(RBAC_TESTS, "RBAC Test Suite")

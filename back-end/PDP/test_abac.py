"""
test_abac.py  –  ABAC test suite for the PDP microservice
Run:  python test_abac.py
Requires the PDP server running on http://localhost:8002
"""

import requests

BASE = "http://localhost:8002/authorize"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

# ── Test cases ────────────────────────────────────────────────────────────────
# Each entry: (label, payload, expected_decision, expected_policy_id_or_None)
ABAC_TESTS = [

    # ── POL-001: Admin Full Access (Internal) ─────────────────────────────────
    (
        "POL-001 | Admin bob @HQ, high clearance → Delete employee_records [ALLOW]",
        {"username": "bob", "resource": "employee_records",  "action": "Delete",
         "mode": "abac", "time": "10:00"},
        "granted", "POL-001"
    ),
    (
        "POL-001 | Admin bob @HQ → Read financial_reports (secret) [ALLOW]",
        {"username": "bob", "resource": "financial_reports", "action": "Read",
         "mode": "abac", "time": "10:00"},
        "granted", "POL-001"
    ),

    # ── POL-002: Department Isolation ─────────────────────────────────────────
    (
        "POL-002 | emma (Operations) reads employee_records (HR dept) [DENY]",
        {"username": "emma", "resource": "employee_records",  "action": "Read",
         "mode": "abac", "time": "10:00"},
        "denied", "POL-002"
    ),
    (
        "POL-002 | david (Finance) reads system_logs (IT dept) [DENY]",
        {"username": "david", "resource": "system_logs",       "action": "Read",
         "mode": "abac", "time": "10:00"},
        "denied", "POL-002"
    ),

    # ── POL-003: Secret – High Clearance Required ─────────────────────────────
    (
        "POL-003 | david (medium clearance) reads financial_reports (secret) [DENY]",
        {"username": "david", "resource": "financial_reports", "action": "Read",
         "mode": "abac", "time": "10:00"},
        "denied", "POL-003"
    ),
    (
        "POL-003 | emma (medium clearance) reads financial_reports (secret) [DENY]",
        {"username": "emma",  "resource": "financial_reports", "action": "Read",
         "mode": "abac", "time": "10:00"},
        "denied", "POL-003"
    ),

    # ── POL-005: Time-Based Access Control ────────────────────────────────────
    (
        "POL-005 | alice (Manager) accesses at 22:00 [DENY – outside hours]",
        {"username": "alice", "resource": "employee_records",  "action": "Read",
         "mode": "abac", "time": "22:00"},
        "denied", "POL-005"
    ),
    (
        "POL-005 | alice (Manager) accesses at 07:59 [DENY – before hours]",
        {"username": "alice", "resource": "employee_records",  "action": "Read",
         "mode": "abac", "time": "07:59"},
        "denied", "POL-005"
    ),
    (
        "POL-005 | bob (Admin) accesses at 22:00 [ALLOW – admin exempt]",
        {"username": "bob",   "resource": "employee_records",  "action": "Read",
         "mode": "abac", "time": "22:00"},
        "granted", "POL-001"
    ),

    # ── POL-006: External Access – Deny Secret Resources ─────────────────────
    (
        "POL-006 | alice (Branch Office) reads financial_reports (secret) [DENY]",
        # Simulate alice being at Branch Office by overriding in payload comment;
        # david is our Branch Office user with Finance dept
        {"username": "david", "resource": "financial_reports", "action": "Read",
         "mode": "abac", "time": "10:00"},
        "denied", "POL-006"
    ),

    # ── POL-007: Remote users denied confidential resources ───────────────────
    (
        "POL-007 | emma (Remote) reads employee_records (confidential) [DENY]",
        {"username": "emma", "resource": "employee_records",  "action": "Read",
         "mode": "abac", "time": "10:00"},
        "denied", "POL-007"
    ),
    (
        "POL-007 | emma (Remote) reads system_logs (confidential) [DENY]",
        {"username": "emma", "resource": "system_logs",        "action": "Read",
         "mode": "abac", "time": "10:00"},
        "denied", "POL-007"
    ),

    # ── POL-008: Public Resource Open Read Access ─────────────────────────────
    (
        "POL-008 | emma (Remote) reads operations_schedule (public) [ALLOW]",
        {"username": "emma",  "resource": "operations_schedule","action": "Read",
         "mode": "abac", "time": "10:00"},
        "granted", "POL-008"
    ),
    (
        "POL-008 | david (Branch Office) reads operations_schedule (public) [ALLOW]",
        {"username": "david", "resource": "operations_schedule","action": "Read",
         "mode": "abac", "time": "10:00"},
        "granted", "POL-008"
    ),

    # ── POL-009: Employee Read-Only Enforcement ───────────────────────────────
    (
        "POL-009 | david (Employee) writes operations_schedule [DENY]",
        {"username": "david", "resource": "operations_schedule","action": "Write",
         "mode": "abac", "time": "10:00"},
        "denied", "POL-009"
    ),
    (
        "POL-009 | emma (Employee) deletes operations_schedule [DENY]",
        {"username": "emma",  "resource": "operations_schedule","action": "Delete",
         "mode": "abac", "time": "10:00"},
        "denied", "POL-009"
    ),

    # ── POL-010: Manager Cannot Delete ───────────────────────────────────────
    (
        "POL-010 | alice (Manager/HR) deletes employee_records [DENY]",
        {"username": "alice", "resource": "employee_records",  "action": "Delete",
         "mode": "abac", "time": "10:00"},
        "denied", "POL-010"
    ),

    # ── Same-dept Manager allowed ─────────────────────────────────────────────
    (
        "Cross-check | alice (Manager/HR) writes employee_records [ALLOW]",
        {"username": "alice", "resource": "employee_records",  "action": "Write",
         "mode": "abac", "time": "10:00"},
        "granted", None
    ),

    # ── Edge: invalid mode ────────────────────────────────────────────────────
    (
        "Edge | invalid mode value [EXPECT 400]",
        {"username": "bob", "resource": "employee_records", "action": "Read", "mode": "xyz"},
        "denied", None
    ),
]


# ── Runner ────────────────────────────────────────────────────────────────────
def run_tests(tests, suite_name):
    print(f"\n{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}  {suite_name}{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}\n")

    passed = failed = 0

    for label, payload, expected_decision, expected_policy in tests:
        try:
            resp = requests.post(BASE, json=payload, timeout=5)
            body = resp.json()

            if resp.status_code == 200:
                actual   = body.get("decision", "denied")
                reason   = body.get("reason", "")
                matched  = body.get("matched_policies", [])
            else:
                detail   = body.get("detail", {})
                actual   = detail.get("decision", "denied") if isinstance(detail, dict) else "denied"
                reason   = detail.get("reason",   "")       if isinstance(detail, dict) else str(detail)
                matched  = detail.get("matched_policies", []) if isinstance(detail, dict) else []

            decision_ok = (actual == expected_decision)
            policy_ok   = (expected_policy is None) or (expected_policy in (matched or []))
            ok          = decision_ok and policy_ok

            tag = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
            if ok:
                passed += 1
            else:
                failed += 1

            pol_str = f"matched={matched}" if matched else "matched=[]"
            exp_pol = f"  expected_policy={expected_policy}" if expected_policy else ""
            print(f"  [{tag}] {label}")
            print(f"         → decision={actual}  expected={expected_decision}  "
                  f"{pol_str}{exp_pol}")
            print(f"         reason: {reason[:80]}")
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
    run_tests(ABAC_TESTS, "ABAC Test Suite")

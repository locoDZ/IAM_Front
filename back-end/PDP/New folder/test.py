import requests

url = "http://localhost:8002/authorize"

test_cases = [
    {"username": "bob", "resource": "employee_records", "action": "Delete"},
    {"username": "alice", "resource": "employee_records", "action": "Write"},
    {"username": "alice", "resource": "employee_records", "action": "Delete"},
    {"username": "david", "resource": "financial_reports", "action": "Read"},
    {"username": "david", "resource": "financial_reports", "action": "Write"},
]

for case in test_cases:
    response = requests.post(url, json=case)
    print(f"{case['username']:6} | {case['action']:6} | {case['resource']:18} | Status: {response.status_code}")
    print(f"         Response: {response.json()}")
    print("-" * 60)
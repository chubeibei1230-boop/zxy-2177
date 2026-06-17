import requests
import json
import sys

BASE = "http://localhost:8127"


def pr(label, r):
    print(f"\n=== {label} ===")
    print(f"Status: {r.status_code}")
    try:
        data = r.json()
        txt = json.dumps(data, ensure_ascii=False, indent=2)
        print(txt[:2500])
    except Exception as e:
        print(f"Parse error: {e}; raw: {r.text[:300]}")
    return r


results = []

r = pr("1. Health Check", requests.get(f"{BASE}/api/health"))
results.append(("Health", r.status_code == 200))

r = pr("2. Login admin", requests.post(f"{BASE}/api/auth/login",
    data={"username": "admin", "password": "admin123"}))
results.append(("Login", r.status_code == 200))
if r.status_code != 200:
    print("Login failed, aborting")
    sys.exit(1)
token = r.json()["access_token"]
hdrs = {"Authorization": f"Bearer {token}"}

r = pr("3. Get current user", requests.get(f"{BASE}/api/auth/me", headers=hdrs))
results.append(("Auth/me", r.status_code == 200))

d1 = {
    "project_name": "项目A-礼盒包装", "customer_name": "顺丰集团",
    "board_spec": "E型瓦楞 350g", "die_number": "DM-2026-001",
    "die_version": "V1.0", "test_round": 1, "owner": "张工", "priority": "高",
    "notes": "首批样品，加急处理",
}
r = pr("4. Create sample #1", requests.post(f"{BASE}/api/samples", json=d1, headers=hdrs))
results.append(("Create#1", r.status_code == 201))
s1 = r.json()["id"] if r.status_code == 201 else None

d2 = {
    "project_name": "项目A-礼盒包装", "customer_name": "顺丰集团",
    "board_spec": "E型瓦楞 350g", "die_number": "DM-2026-001",
    "die_version": "V1.1", "test_round": 1, "owner": "李工", "priority": "普通",
}
r = pr("5. Create sample #2 (another version)", requests.post(f"{BASE}/api/samples", json=d2, headers=hdrs))
results.append(("Create#2", r.status_code == 201))

d3 = {
    "project_name": "项目B-快递盒", "customer_name": "京东物流",
    "board_spec": "B型瓦楞 300g", "die_number": "DM-2026-002",
    "die_version": "V1.0", "test_round": 1, "owner": "王工", "priority": "紧急",
}
r = pr("6. Create sample #3", requests.post(f"{BASE}/api/samples", json=d3, headers=hdrs))
results.append(("Create#3", r.status_code == 201))
s3 = r.json()["id"] if r.status_code == 201 else None

r = pr("7. Duplicate version check (should fail 400)",
    requests.post(f"{BASE}/api/samples", json=d1, headers=hdrs))
results.append(("Duplicate rejected", r.status_code == 400))

if s1:
    r = pr("8. Open sample #1", requests.post(f"{BASE}/api/samples/{s1}/open",
        json={"opener": "张工", "notes": "开始开样"}, headers=hdrs))
    results.append(("Open", r.status_code == 200))

    r = pr("9. Submit test (failed, cracking reported)", requests.post(f"{BASE}/api/samples/{s1}/test", json={
        "round": 1, "folding_result": "折合平整",
        "indentation_result": "压痕清晰", "cracking_description": "边角处轻微开裂",
        "tester": "质检小王", "is_passed": False, "notes": "需要调整",
    }, headers=hdrs))
    results.append(("TestFail", r.status_code == 200))

    r = pr("10. Submit modification", requests.post(f"{BASE}/api/samples/{s1}/modify", json={
        "round": 1, "modification_action": "调整边角刀模角度 0.5度",
        "modifier": "张工", "reason": "测试显示边角开裂", "notes": "按报告调整",
    }, headers=hdrs))
    results.append(("Modify", r.status_code == 200))

    r = pr("11. Submit test round 2 (passed)", requests.post(f"{BASE}/api/samples/{s1}/test", json={
        "round": 2, "folding_result": "折合正常",
        "indentation_result": "压痕深度标准", "cracking_description": "",
        "tester": "质检小王", "is_passed": True,
    }, headers=hdrs))
    results.append(("TestPass", r.status_code == 200))

    r = pr("12. Seal confirm sample #1", requests.post(f"{BASE}/api/samples/{s1}/confirm", json={
        "confirmer": "总工办", "version": "V1.0", "notes": "通过，封样存档",
    }, headers=hdrs))
    results.append(("Confirm", r.status_code == 200))

if s3:
    r = pr("13. Reject sample #3 (should fail - pending_open)",
        requests.post(f"{BASE}/api/samples/{s3}/reject", json={
            "round": 1, "reason": "压痕不清晰", "rejecter": "客户陈经理",
        }, headers=hdrs))
    results.append(("RejectWrongState", r.status_code == 400))

    r = pr("14. Seal confirm #3 without test (should fail 400)",
        requests.post(f"{BASE}/api/samples/{s3}/confirm", json={
            "confirmer": "总工办", "version": "V1.0",
        }, headers=hdrs))
    results.append(("SealNoTest", r.status_code == 400))

r = pr("15. List all samples", requests.get(f"{BASE}/api/samples", headers=hdrs))
results.append(("List", r.status_code == 200 and len(r.json()) >= 3))

r = pr("16. Query by customer_name=顺丰", requests.get(
    f"{BASE}/api/samples?customer_name=%E9%A1%BA%E4%B8%B0", headers=hdrs))
results.append(("QueryByCustomer", r.status_code == 200 and len(r.json()) >= 2))

r = pr("17. Query by status=已封样", requests.get(
    f"{BASE}/api/samples?status=%E5%B7%B2%E5%B0%81%E6%A0%B7", headers=hdrs))
results.append(("QueryByStatus", r.status_code == 200 and len(r.json()) >= 1))

r = pr("18. Query by owner=张工", requests.get(
    f"{BASE}/api/samples?owner=%E5%BC%A0%E5%B7%A5", headers=hdrs))
results.append(("QueryByOwner", r.status_code == 200))

r = pr("19. Detect anomalies", requests.get(f"{BASE}/api/anomalies", headers=hdrs))
results.append(("Anomalies", r.status_code == 200))

r = pr("20. Reject reasons distribution", requests.get(
    f"{BASE}/api/reports/reject-reasons", headers=hdrs))
results.append(("RejectReasons", r.status_code == 200))

r = pr("21. Pending confirm list", requests.get(
    f"{BASE}/api/reports/pending-confirm", headers=hdrs))
results.append(("PendingConfirm", r.status_code == 200))

r = pr("22. Spec risk ranking", requests.get(
    f"{BASE}/api/reports/spec-risk", headers=hdrs))
results.append(("SpecRisk", r.status_code == 200 and len(r.json()) >= 1))

r = pr("23. No auth check (should 401)", requests.get(f"{BASE}/api/samples"))
results.append(("Unauth", r.status_code == 401))

r = pr("24. Wrong password login (should 401)", requests.post(
    f"{BASE}/api/auth/login",
    data={"username": "admin", "password": "wrongpassword"}))
results.append(("WrongPassword", r.status_code == 401))

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
passed = sum(1 for _, ok in results if ok)
total = len(results)
for name, ok in results:
    print(f"  [{'PASS' if ok else 'FAIL'}]  {name}")
print(f"\n{passed}/{total} tests passed")
if passed == total:
    print("ALL TESTS PASSED!")
else:
    print(f"{total - passed} TEST(S) FAILED")

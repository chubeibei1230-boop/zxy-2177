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
        print(txt[:2000])
    except Exception as e:
        print(f"Parse error: {e}; raw: {r.text[:300]}")
    return r


results = []

r = requests.post(f"{BASE}/api/auth/login", data={"username": "admin", "password": "admin123"})
token = r.json()["access_token"]
hdrs = {"Authorization": f"Bearer {token}"}


print("=" * 60)
print("Bug1: 禁止通过 change_status 直接设为已封样")
print("=" * 60)

d = {
    "project_name": "Bug1Test", "customer_name": "测试客户",
    "board_spec": "E瓦楞 300g", "die_number": "DM-BUG1",
    "die_version": "V1.0", "test_round": 1, "owner": "测试员",
}
r = pr("1.1 Create sample", requests.post(f"{BASE}/api/samples", json=d, headers=hdrs))
s1 = r.json()["id"]

requests.post(f"{BASE}/api/samples/{s1}/open", json={"opener": "测试员"}, headers=hdrs)

r = pr("1.2 Try change_status to 已封样 (should FAIL 400)",
    requests.post(f"{BASE}/api/samples/{s1}/status",
        json={"target_status": "已封样", "operator": "测试员"}, headers=hdrs))
bug1_pass = r.status_code == 400 and "封样确认接口" in r.json().get("detail", "")
results.append(("Bug1: 禁止直接切已封样", bug1_pass))
if not bug1_pass:
    print("  >>> BUG1 STILL PRESENT: was able to set SEALED via change_status!")


print("\n" + "=" * 60)
print("Bug2: 已取消记录不可重新激活")
print("=" * 60)

d2 = {
    "project_name": "Bug2Test", "customer_name": "测试客户",
    "board_spec": "E瓦楞 300g", "die_number": "DM-BUG2",
    "die_version": "V1.0", "test_round": 1, "owner": "测试员",
}
r = pr("2.1 Create sample", requests.post(f"{BASE}/api/samples", json=d2, headers=hdrs))
s2 = r.json()["id"]

r = pr("2.2 Cancel sample",
    requests.post(f"{BASE}/api/samples/{s2}/status",
        json={"target_status": "已取消", "operator": "测试员"}, headers=hdrs))

r = pr("2.3 Try reactivate to 待开样 (should FAIL 400)",
    requests.post(f"{BASE}/api/samples/{s2}/status",
        json={"target_status": "待开样", "operator": "测试员"}, headers=hdrs))
bug2_pass = r.status_code == 400 and "不可重新激活" in r.json().get("detail", "")
results.append(("Bug2: 已取消不可重新激活", bug2_pass))

r = pr("2.4 Try reactivate to 打样中 (should FAIL 400)",
    requests.post(f"{BASE}/api/samples/{s2}/status",
        json={"target_status": "打样中", "operator": "测试员"}, headers=hdrs))
bug2_pass2 = r.status_code == 400
results.append(("Bug2: 已取消不可切任何状态", bug2_pass2))

d2_new = {
    "project_name": "Bug2Test", "customer_name": "测试客户",
    "board_spec": "E瓦楞 300g", "die_number": "DM-BUG2",
    "die_version": "V1.0", "test_round": 1, "owner": "测试员",
}
r = pr("2.5 Re-create same version after cancel (should SUCCEED 201)",
    requests.post(f"{BASE}/api/samples", json=d2_new, headers=hdrs))
bug2_recreate = r.status_code == 201
results.append(("Bug2: 取消后可重新创建同版本", bug2_recreate))


print("\n" + "=" * 60)
print("Bug3: 测试失败的记录不应进入待确认清单")
print("=" * 60)

d3 = {
    "project_name": "Bug3Test", "customer_name": "测试客户",
    "board_spec": "B瓦楞 250g", "die_number": "DM-BUG3",
    "die_version": "V1.0", "test_round": 1, "owner": "测试员",
}
r = pr("3.1 Create sample", requests.post(f"{BASE}/api/samples", json=d3, headers=hdrs))
s3 = r.json()["id"]

requests.post(f"{BASE}/api/samples/{s3}/open", json={"opener": "测试员"}, headers=hdrs)

r = pr("3.2 Submit FAILED test result",
    requests.post(f"{BASE}/api/samples/{s3}/test", json={
        "round": 1, "folding_result": "不合格", "cracking_description": "严重开裂",
        "tester": "质检", "is_passed": False,
    }, headers=hdrs))

sample_status = r.json().get("status", "")
print(f"  -> Status after failed test: {sample_status}")
bug3_status = sample_status == "修改中"
results.append(("Bug3: 测试失败状态=修改中", bug3_status))

r = pr("3.3 Pending confirm list should NOT contain failed sample",
    requests.get(f"{BASE}/api/reports/pending-confirm", headers=hdrs))
pending_ids = [s["id"] for s in r.json()]
bug3_pending = s3 not in pending_ids
results.append(("Bug3: 失败测试不出现在待确认清单", bug3_pending))

r = pr("3.4 Submit PASSED test result",
    requests.post(f"{BASE}/api/samples/{s3}/test", json={
        "round": 2, "folding_result": "合格", "cracking_description": "",
        "tester": "质检", "is_passed": True,
    }, headers=hdrs))

sample_status2 = r.json().get("status", "")
print(f"  -> Status after passed test: {sample_status2}")
bug3_status2 = sample_status2 == "待确认"
results.append(("Bug3: 测试通过状态=待确认", bug3_status2))

r = pr("3.5 Pending confirm list should NOW contain passed sample",
    requests.get(f"{BASE}/api/reports/pending-confirm", headers=hdrs))
pending_ids2 = [s["id"] for s in r.json()]
bug3_pending2 = s3 in pending_ids2
results.append(("Bug3: 通过测试出现在待确认清单", bug3_pending2))


print("\n" + "=" * 60)
print("Bug4: 同规格开裂集中统计不应重复计数同一样品")
print("=" * 60)

for i in range(3):
    d4 = {
        "project_name": f"Bug4Test-{i}", "customer_name": "测试客户",
        "board_spec": "C瓦楞 200g", "die_number": f"DM-BUG4-{i}",
        "die_version": "V1.0", "test_round": 1, "owner": "测试员",
    }
    r = requests.post(f"{BASE}/api/samples", json=d4, headers=hdrs)
    sid = r.json()["id"]
    requests.post(f"{BASE}/api/samples/{sid}/open", json={"opener": "测试员"}, headers=hdrs)
    for rnd in range(3):
        requests.post(f"{BASE}/api/samples/{sid}/test", json={
            "round": rnd + 1, "folding_result": "不合格" if rnd < 2 else "合格",
            "cracking_description": f"第{rnd+1}轮开裂报告" if rnd < 2 else "",
            "tester": "质检", "is_passed": rnd >= 2,
        }, headers=hdrs)

r = pr("4.1 Detect anomalies", requests.get(f"{BASE}/api/anomalies", headers=hdrs))
cracking_anomaly = None
for a in r.json():
    if a["type"] == "同规格开裂集中":
        cracking_anomaly = a
        break

if cracking_anomaly:
    count = cracking_anomaly["details"]["sample_count"]
    print(f"  -> Cracking sample count: {count}")
    bug4_pass = count == 3
    results.append(("Bug4: 开裂集中统计=3条(非9条)", bug4_pass))
    if count != 3:
        print(f"  >>> BUG4 STILL PRESENT: expected 3, got {count}")
else:
    bug4_pass = False
    results.append(("Bug4: 开裂集中统计=3条(非9条)", bug4_pass))
    print("  >>> No cracking anomaly detected at all")

r = pr("4.2 Spec risk ranking", requests.get(f"{BASE}/api/reports/spec-risk", headers=hdrs))
c_spec = None
for item in r.json():
    if item["board_spec"] == "C瓦楞 200g":
        c_spec = item
        break
if c_spec:
    print(f"  -> C瓦楞 200g cracking_count: {c_spec['cracking_count']}")
    bug4_risk = c_spec["cracking_count"] == 3
    results.append(("Bug4: 风险排行开裂数=3(非9)", bug4_risk))
else:
    results.append(("Bug4: 风险排行开裂数=3(非9)", False))


print("\n" + "=" * 60)
print("REGRESSION: Basic flow still works")
print("=" * 60)

d5 = {
    "project_name": "回归测试", "customer_name": "回归客户",
    "board_spec": "A瓦楞 400g", "die_number": "DM-REG",
    "die_version": "V1.0", "test_round": 1, "owner": "回归员", "priority": "紧急",
}
r = pr("R1. Create", requests.post(f"{BASE}/api/samples", json=d5, headers=hdrs))
s5 = r.json()["id"]
results.append(("回归: 创建", r.status_code == 201))

r = pr("R2. Open", requests.post(f"{BASE}/api/samples/{s5}/open",
    json={"opener": "回归员"}, headers=hdrs))
results.append(("回归: 开样", r.status_code == 200 and r.json()["status"] == "打样中"))

r = pr("R3. Test pass", requests.post(f"{BASE}/api/samples/{s5}/test", json={
    "round": 1, "folding_result": "合格", "cracking_description": "",
    "tester": "质检", "is_passed": True,
}, headers=hdrs))
results.append(("回归: 测试通过→待确认", r.status_code == 200 and r.json()["status"] == "待确认"))

r = pr("R4. Confirm seal", requests.post(f"{BASE}/api/samples/{s5}/confirm", json={
    "confirmer": "总工", "version": "V1.0",
}, headers=hdrs))
results.append(("回归: 封样确认", r.status_code == 200 and r.json()["status"] == "已封样"))

r = pr("R5. Pending confirm via change_status (should FAIL)",
    requests.post(f"{BASE}/api/samples/{s5}/status",
        json={"target_status": "待确认", "operator": "hack"}, headers=hdrs))
results.append(("回归: 禁止直接切待确认", r.status_code == 400))


print("\n" + "=" * 60)
print("FINAL RESULTS")
print("=" * 60)
passed = sum(1 for _, ok in results if ok)
total = len(results)
for name, ok in results:
    print(f"  [{'PASS' if ok else 'FAIL'}]  {name}")
print(f"\n{passed}/{total} tests passed")
if passed == total:
    print("ALL TESTS PASSED!")
    sys.exit(0)
else:
    print(f"{total - passed} TEST(S) FAILED")
    sys.exit(1)

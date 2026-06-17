import requests
import json

BASE = "http://localhost:8127"


def print_response(label, r):
    print(f"\n=== {label} ===")
    print(f"Status: {r.status_code}")
    try:
        data = r.json()
        print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
    except Exception:
        print(r.text[:500])


print_response("1. Health Check", requests.get(f"{BASE}/api/health"))

r = requests.post(f"{BASE}/api/auth/login", data={"username": "admin", "password": "admin123"})
print_response("2. Login as admin", r)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print_response("3. Get current user", requests.get(f"{BASE}/api/auth/me", headers=headers))

sample_data = {
    "project_name": "项目A-礼盒包装",
    "customer_name": "顺丰集团",
    "board_spec": "E型瓦楞 350g",
    "die_number": "DM-2026-001",
    "die_version": "V1.0",
    "test_round": 1,
    "owner": "张工",
    "priority": "高",
    "notes": "首批样品，加急处理",
}
r = requests.post(f"{BASE}/api/samples", json=sample_data, headers=headers)
print_response("4. Create sample 1", r)
try:
    s1 = r.json()["id"]
except Exception as e:
    print(f"  ERROR extracting id: {e}")
    s1 = None
    print(f"  Full response: {r.text}")

sample_data2 = {
    "project_name": "项目A-礼盒包装",
    "customer_name": "顺丰集团",
    "board_spec": "E型瓦楞 350g",
    "die_number": "DM-2026-001",
    "die_version": "V1.1",
    "test_round": 1,
    "owner": "李工",
    "priority": "普通",
}
r = requests.post(f"{BASE}/api/samples", json=sample_data2, headers=headers)
print_response("5. Create sample 2 (diff version)", r)

sample_data3 = {
    "project_name": "项目B-快递盒",
    "customer_name": "京东物流",
    "board_spec": "B型瓦楞 300g",
    "die_number": "DM-2026-002",
    "die_version": "V1.0",
    "test_round": 1,
    "owner": "王工",
    "priority": "紧急",
}
r = requests.post(f"{BASE}/api/samples", json=sample_data3, headers=headers)
print_response("6. Create sample 3", r)
s3 = r.json()["id"]

print_response("7. Duplicate version check", requests.post(f"{BASE}/api/samples", json=sample_data, headers=headers))

print_response("8. Open sample 1", requests.post(f"{BASE}/api/samples/{s1}/open", json={"opener": "张工", "notes": "开始开样"}, headers=headers))

test_data = {
    "round": 1,
    "folding_result": "折合平整，无明显反弹",
    "indentation_result": "压痕清晰，深度合适",
    "cracking_description": "边角处轻微开裂",
    "tester": "质检小王",
    "is_passed": False,
    "notes": "需要调整刀模角度",
}
print_response("9. Submit test result (failed)", requests.post(f"{BASE}/api/samples/{s1}/test", json=test_data, headers=headers))

modify_data = {
    "round": 1,
    "modification_action": "调整边角刀模角度 0.5度，加厚保护线",
    "modifier": "张工",
    "reason": "测试显示边角开裂",
    "notes": "按测试报告调整",
}
print_response("10. Submit modification", requests.post(f"{BASE}/api/samples/{s1}/modify", json=modify_data, headers=headers))

test_data2 = {
    "round": 2,
    "folding_result": "折合正常，反弹度符合标准",
    "indentation_result": "压痕深度标准",
    "cracking_description": "",
    "tester": "质检小王",
    "is_passed": True,
}
print_response("11. Submit test result round 2 (passed)", requests.post(f"{BASE}/api/samples/{s1}/test", json=test_data2, headers=headers))

reject_data = {
    "round": 1,
    "reason": "压痕不清晰，易断裂",
    "rejecter": "客户陈经理",
    "description": "用户反馈批量使用可能出现问题",
}
print_response("12. Reject sample 3 (should fail - not pending confirm)", requests.post(f"{BASE}/api/samples/{s3}/reject", json=reject_data, headers=headers))

confirm_data = {
    "confirmer": "总工办",
    "version": "V1.0",
    "notes": "通过客户确认，封样存档",
}
print_response("13. Seal confirm sample 1", requests.post(f"{BASE}/api/samples/{s1}/confirm", json=confirm_data, headers=headers))

print_response("14. Query all samples", requests.get(f"{BASE}/api/samples", headers=headers))

print_response("15. Query by customer=顺丰", requests.get(f"{BASE}/api/samples?customer_name=顺丰", headers=headers))

print_response("16. Query by status=待确认", requests.get(f"{BASE}/api/samples?status=待确认", headers=headers))

print_response("17. Detect anomalies", requests.get(f"{BASE}/api/anomalies", headers=headers))

print_response("18. Reject reasons distribution", requests.get(f"{BASE}/api/reports/reject-reasons", headers=headers))

print_response("19. Pending confirm list", requests.get(f"{BASE}/api/reports/pending-confirm", headers=headers))

print_response("20. Spec risk ranking", requests.get(f"{BASE}/api/reports/spec-risk", headers=headers))

print_response("21. No auth test (should 401)", requests.get(f"{BASE}/api/samples"))

print("\n=== All tests completed ===")

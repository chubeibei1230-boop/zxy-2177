import requests
import json

BASE = "http://localhost:8127"


def print_response(label, r):
    print(f"\n=== {label} ===")
    print(f"Status: {r.status_code}")
    try:
        data = r.json()
        print(json.dumps(data, ensure_ascii=False, indent=2)[:5000])
    except Exception:
        print(r.text[:500])


r = requests.post(f"{BASE}/api/auth/login", data={"username": "admin", "password": "admin123"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

sample_data = {
    "project_name": "项目C-电子产品包装盒",
    "customer_name": "华为技术",
    "board_spec": "E型瓦楞 400g",
    "die_number": "DM-2026-TEST-001",
    "die_version": "V1.0",
    "test_round": 1,
    "owner": "赵工",
    "priority": "高",
    "notes": "测试操作留痕功能",
}
r = requests.post(f"{BASE}/api/samples", json=sample_data, headers=headers)
s1 = r.json()["id"]
print(f"Created sample: {s1}")

print_response("1. 开样", requests.post(f"{BASE}/api/samples/{s1}/open", json={"opener": "赵工", "notes": "开始打样"}, headers=headers))

print_response("2. 提交测试(不通过)", requests.post(f"{BASE}/api/samples/{s1}/test", json={
    "round": 1,
    "folding_result": "正常",
    "indentation_result": "偏浅",
    "cracking_description": "有裂缝",
    "tester": "质检小李",
    "is_passed": False,
    "notes": "压痕深度不够",
}, headers=headers))

print_response("3. 提交修改", requests.post(f"{BASE}/api/samples/{s1}/modify", json={
    "round": 1,
    "modification_action": "加深压痕线",
    "modifier": "赵工",
    "reason": "压痕偏浅",
}, headers=headers))

print_response("4. 提交测试(通过)", requests.post(f"{BASE}/api/samples/{s1}/test", json={
    "round": 2,
    "folding_result": "良好",
    "indentation_result": "深度标准",
    "cracking_description": "",
    "tester": "质检小李",
    "is_passed": True,
}, headers=headers))

print_response("5. 退回", requests.post(f"{BASE}/api/samples/{s1}/reject", json={
    "round": 1,
    "reason": "外观瑕疵",
    "rejecter": "客户王经理",
    "description": "边角有轻微毛刺",
}, headers=headers))

print_response("6. 再次提交测试(通过)", requests.post(f"{BASE}/api/samples/{s1}/test", json={
    "round": 3,
    "folding_result": "良好",
    "indentation_result": "深度标准",
    "cracking_description": "",
    "tester": "质检小李",
    "is_passed": True,
}, headers=headers))

print_response("7. 封样确认", requests.post(f"{BASE}/api/samples/{s1}/confirm", json={
    "confirmer": "总工办",
    "version": "V1.0",
    "notes": "最终封样",
}, headers=headers))

print_response("8. 查询该记录时间线", requests.get(f"{BASE}/api/samples/{s1}/timeline", headers=headers))

print_response("9. 查询所有操作日志", requests.get(f"{BASE}/api/operation-logs", headers=headers))

print_response("10. 按项目名称模糊查询(项目C)", requests.get(f"{BASE}/api/operation-logs?project_name=项目C", headers=headers))

print_response("11. 按刀模编号查询(DM-2026-TEST-001)", requests.get(f"{BASE}/api/operation-logs?die_number=DM-2026-TEST-001", headers=headers))

print_response("12. 按客户名称查询(华为)", requests.get(f"{BASE}/api/operation-logs?customer_name=华为", headers=headers))

print_response("13. 按操作人查询(质检小李)", requests.get(f"{BASE}/api/operation-logs?operator=质检小李", headers=headers))

print_response("14. 按操作类型查询(封样确认)", requests.get(f"{BASE}/api/operation-logs?operation_type=封样确认", headers=headers))

print_response("15. 按状态查询(已封样)", requests.get(f"{BASE}/api/operation-logs?status=已封样", headers=headers))

print("\n=== 新功能测试完成 ===")

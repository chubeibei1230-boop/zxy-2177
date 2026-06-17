import requests
import json

BASE = "http://localhost:8127"

r = requests.post(f"{BASE}/api/auth/login", data={"username": "admin", "password": "admin123"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

sample_data = {
    "project_name": "项目D-测试状态调整",
    "customer_name": "测试客户",
    "board_spec": "A型瓦楞",
    "die_number": "DM-TEST-STATUS",
    "die_version": "V1.0",
    "test_round": 1,
    "owner": "测试员",
    "priority": "普通",
}
r = requests.post(f"{BASE}/api/samples", json=sample_data, headers=headers)
s1 = r.json()["id"]
print(f"Created sample: {s1}, status: {r.json()['status']}")

r = requests.post(f"{BASE}/api/samples/{s1}/status", json={
    "target_status": "已取消",
    "operator": "管理员",
    "notes": "项目取消，不再需要打样",
}, headers=headers)
print(f"\nCancel sample status: {r.status_code}")
print(f"New status: {r.json()['status']}")

r = requests.get(f"{BASE}/api/samples/{s1}/timeline", headers=headers)
logs = r.json()
print(f"\n=== Timeline for sample {s1} ===")
for log in logs:
    print(f"  [{log['operation_time']}] {log['operation_type']} - {log['operator']}")
    print(f"    {log['previous_status']} -> {log['current_status']}")
    if log['notes']:
        print(f"    备注: {log['notes']}")
    if log['business_result']:
        print(f"    业务结果: {json.dumps(log['business_result'], ensure_ascii=False)}")
    print()

print("\n=== 查询状态调整类型的操作日志 ===")
r = requests.get(f"{BASE}/api/operation-logs?operation_type=状态调整", headers=headers)
logs = r.json()
for log in logs:
    print(f"  [{log['operation_time']}] {log['project_name']} - {log['die_number']}")
    print(f"    {log['previous_status']} -> {log['current_status']} by {log['operator']}")
    if log['notes']:
        print(f"    备注: {log['notes']}")
    print()

print("状态调整功能验证完成！")

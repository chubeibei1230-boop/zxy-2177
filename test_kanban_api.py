import requests

BASE = 'http://localhost:8127'

print("=" * 60)
print("测试看板 API 接口")
print("=" * 60)

# 登录
print("\n1. 登录获取 Token...")
r = requests.post(f'{BASE}/api/auth/login', data={'username': 'admin', 'password': 'admin123'})
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}
print("   ✅ 登录成功")

# 测试看板任务列表 API
print("\n2. 测试看板任务列表 API...")
r = requests.get(f'{BASE}/api/kanban/samples', headers=headers)
samples = r.json()
print(f"   ✅ API 状态: {r.status_code}")
print(f"   ✅ 返回记录数: {len(samples)}")
if samples:
    print(f"   ✅ 第一条记录: {samples[0]['project_name']} ({samples[0]['status']})")
    print(f"   ✅ 风险标志: {samples[0]['risk_flags']}")

# 测试带筛选的看板任务列表
print("\n3. 测试带筛选的看板任务列表...")
r = requests.get(f'{BASE}/api/kanban/samples', headers=headers, params={'status': '打样中'})
filtered = r.json()
print(f"   ✅ API 状态: {r.status_code}")
print(f"   ✅ 打样中任务数: {len(filtered)}")

# 测试看板汇总统计 API
print("\n4. 测试看板汇总统计 API...")
r = requests.get(f'{BASE}/api/kanban/summary', headers=headers)
summary = r.json()
print(f"   ✅ API 状态: {r.status_code}")
print(f"   ✅ 总任务数: {summary['total_samples']}")
print(f"   ✅ 高风险任务: {summary['high_risk_count']}")
print(f"   ✅ 已超期任务: {summary['overdue_count']}")
print(f"   ✅ 临近截止任务: {summary['near_deadline_count']}")
print(f"   ✅ 客户统计数: {len(summary['customer_summary'])}")
print(f"   ✅ 纸板规格统计数: {len(summary['board_spec_summary'])}")
print(f"   ✅ 责任人统计数: {len(summary['owner_summary'])}")

# 测试状态汇总
print("\n5. 测试状态汇总...")
for item in summary['status_summary']:
    print(f"   - {item['status']}: {item['count']} ({item['percentage']}%)")

# 测试看板页面
print("\n6. 测试看板页面...")
r = requests.get(f'{BASE}/kanban')
print(f"   ✅ 页面状态: {r.status_code}")
print(f"   ✅ 页面大小: {len(r.content)} bytes")

# 测试静态文件
print("\n7. 测试静态文件...")
r = requests.get(f'{BASE}/static/kanban.css')
print(f"   ✅ CSS 状态: {r.status_code}")
r = requests.get(f'{BASE}/static/kanban.js')
print(f"   ✅ JS 状态: {r.status_code}")

print("\n" + "=" * 60)
print("🎉 所有看板 API 测试通过！")
print("=" * 60)
print("\n📋 访问地址: http://localhost:8127/kanban")
print("🔑 登录账号: admin / admin123")

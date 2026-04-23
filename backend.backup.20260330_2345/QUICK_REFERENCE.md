# 计算任务 API - 快速参考

## 🚀 快速开始

### 提交任务
```bash
curl -X POST http://localhost:5001/api/calc-tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "reaction_id": 1,
    "task_type": "optimization",
    "software": "Gaussian",
    "input_data": {"method": "B3LYP", "basis": "6-31G(d)"}
  }'
```

### 查询任务
```bash
curl http://localhost:5001/api/calc-tasks/123
```

### 查看统计
```bash
curl http://localhost:5001/api/calc-tasks/stats
```

---

## 📋 必填字段

| 字段 | 类型 | 示例 |
|------|------|------|
| reaction_id | int | 1 |
| task_type | string | "optimization" |
| input_data | object/string | {"key": "value"} |

---

## ✅ 任务类型

- `optimization` - 几何优化
- `ts` - 过渡态搜索
- `frequency` - 频率计算
- `single_point` - 单点能
- `irc` - 内禀反应坐标

---

## 💻 支持软件

- Gaussian
- ORCA
- Psi4
- NWChem

---

## 📊 响应状态

| 代码 | 含义 |
|------|------|
| 201 | 创建成功 |
| 200 | 查询成功 |
| 400 | 参数错误 |
| 404 | 未找到 |
| 500 | 服务器错误 |

---

## 🔍 测试

```bash
cd kanban-react/backend
python3 test_calc_tasks_api.py
```

---

## 📖 完整文档

查看 `docs/calc_tasks_api.md` 获取详细说明。

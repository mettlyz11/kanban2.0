#!/bin/bash
echo "🔍 部署前检查..."
cd /opt/kanban-react/backend

# 语法检查
python3 -m py_compile app.py || exit 1
echo "✅ 语法检查通过"

# API清单验证
python3 api_manifest.py || exit 1

# API可用性检查
sleep 2
for endpoint in "/api/stats" "/api/company-info/companies"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8086${endpoint}" || echo "000")
    if [ "$status" = "200" ]; then
        echo "✅ ${endpoint}"
    else
        echo "❌ ${endpoint} (HTTP ${status})"
        exit 1
    fi
done

echo "✅ 所有检查通过"

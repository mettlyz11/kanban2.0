#!/bin/bash
# KOI QA Full - 完整看板系统检查

echo 🚀 KOI Full Check - 看板系统完整检查
echo ========================================

cd /opt/kanban-react/frontend
node koi-full-check-v4.cjs 2>&1

exit 0

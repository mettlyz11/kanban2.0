#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键表结构迁移脚本

⚠️ 已弃用 (v2.4.13 - 2026-03-18)
此脚本已不再需要，因为系统已完全迁移到 MySQL/RDS

历史用途：从 SQLite 迁移关键表到 MySQL
"""

import sys

print("=" * 60)
print("⚠️  此迁移脚本已弃用 (v2.4.13)")
print("=" * 60)
print()
print("系统已完全迁移到 MySQL/RDS，不再需要此脚本。")
print()
print("所有表结构已在 RDS MySQL 中创建完成。")
print("如需查看表结构，请连接 MySQL 后执行：")
print("  DESCRIBE tasks;")
print("  DESCRIBE projects;")
print()
sys.exit(0)

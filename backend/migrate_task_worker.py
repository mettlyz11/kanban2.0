#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T109 任务轮询服务 - 数据库迁移脚本

⚠️ 已弃用 (v2.4.13 - 2026-03-18)
此脚本已不再需要，因为系统已完全迁移到 MySQL/RDS

历史用途：添加 task_worker 需要的字段到 tasks 表
"""

import sys

print("=" * 60)
print("⚠️  此迁移脚本已弃用 (v2.4.13)")
print("=" * 60)
print()
print("系统已完全迁移到 MySQL/RDS，不再需要此脚本。")
print()
print("如需添加字段，请直接修改数据库表结构：")
print("  ALTER TABLE tasks ADD COLUMN slurm_job_id INTEGER;")
print("  ALTER TABLE tasks ADD COLUMN slurm_output_file TEXT;")
print("  ALTER TABLE tasks ADD COLUMN retry_count INTEGER DEFAULT 0;")
print()
sys.exit(0)

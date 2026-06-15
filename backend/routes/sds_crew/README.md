# SDS CrewAI 多 Agent 自愈框架

## 文件结构
- routes/sds_crew/__init__.py      # 包入口
- routes/sds_crew/framework.py     # 核心框架 (SDSCrew, SDSAgent)
- routes/sds_crew/agents.py        # 6个Agent实现
- routes/sds_crew/scheduler.py     # 调度器 (SDSScheduler)
- routes/sds_crew/README.md        # 本文件
- start_crewai_sds.py              # 启动入口

## 集成点
| 功能 | 真实调用 | 替代 Mock |
|-----|---------|-----------|
| push_actor_filter | crew_dispatcher push_actor_filter | 无 |
| llm_auditor | crew_dispatcher llm_auditor | 无 |
| actor_db_fix | 直接 DB SQL 修复 | 无 |
| ask_actor | http://127.0.0.1:18791/v1/chat/completions | 无 |

## 使用方式
  # 运行一次自愈周期
  python3 /opt/kanban-react/backend/start_crewai_sds.py

  # 持续运行（每30分钟）
  python3 /opt/kanban-react/backend/start_crewai_sds.py --continuous

  # 运行特定阶段
  python3 /opt/kanban-react/backend/start_crewai_sds.py --stage diagnostic

  # 查看状态
  python3 /opt/kanban-react/backend/start_crewai_sds.py --status

## Systemd 配置建议
保存为 /etc/systemd/system/sds-crewai.service

[Unit]
Description=SDS CrewAI Self-Healing Scheduler
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/kanban-react/backend
ExecStart=/usr/bin/python3 /opt/kanban-react/backend/start_crewai_sds.py --continuous
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target

启用:
  systemctl daemon-reload
  systemctl enable sds-crewai
  systemctl start sds-crewai

## 与现有 cron 关系
- 现有 cron:  调用 /opt/sds1/crews/crew_dispatcher.py run_all
- 新增调度器: 提供更完整的 6-Agent 编排 (诊断-分析-策略-执行-报告-监督)
- 两者可并行运行，数据不会冲突
- 建议逐步将 cron 任务迁移到本框架

#!/usr/bin/env python3
# Retry script for task 564 status update
# The MySQL server was temporarily unavailable during the cron run.
# Run this script when the server is back online.
# Usage: python3 /Users/mettlyz/.openclaw/workspace/output/task-564/retry_db_update.py

import pymysql

execution_log = '执行7大目标季度复盘: 梳理7目标完成度数据,识别4领先目标(T1 70%/T3 75%/T5 83.3%/T7 80%)和3滞后目标(T2 62.5%/T4 42.9%/T6 66.7%).对各滞后目标进行根因分析:T4因研发周期长、人力不足、供应链瓶颈;T2因资源被T1分流、范围蔓延;T6因时间冲突、目标分散.识别协同机会,T4-T5联合研发预估节省50%研发成本.制定T4专项加速方案(三阶段),T2 MVP收缩策略,T6聚焦学习策略.编制Q3月度里程碑计划和风险管理预案.产出4份报告文件并上传附件.'
result_summary = '完成7大目标季度复盘,整体完成度68.6%.T4硅研新材42.9%为最高风险,制定北航合作加速方案.识别T4-T5协同机会预估节省310K每季.产出复盘报告、加速方案、行动计划、资源配置4份文档,Q3目标设定82.1%.'
task_summary = '7大目标季度复盘完成,整体68.6%.T4 42.9%最高风险,制定专项加速方案.协同预估节省310K每季.产出4份文档.'

conn = pymysql.connect(
    host='rm-2zew4su9p966e8x2o.mysql.rds.aliyuncs.com',
    user='kanban', password='Irc210Irc210!',
    database='kanban', charset='utf8mb4',
    connect_timeout=15
)
c = conn.cursor()
c.execute(
    'UPDATE tasks SET status=%s, execution_log=%s, result_summary=%s, task_summary=%s, updated_at=NOW() WHERE id=%s',
    ('completed', execution_log, result_summary, task_summary, 564)
)
print('Updated rows:', c.rowcount)
conn.commit()
conn.close()
print('Task 564 marked as completed')

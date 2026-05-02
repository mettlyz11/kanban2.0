import os
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

# 插入附件
filepath = 'output/task-1200/郭晓维_合作跟进方案_2026-04-22.md'
filesize = os.path.getsize(filepath)
c.execute('''INSERT INTO attachments 
    (entity_type, entity_id, filename, url, size, file_type) 
    VALUES (%s, %s, %s, %s, %s, %s)''',
    ('task', 1200, '郭晓维_合作跟进方案_2026-04-22.md', filepath, filesize, 'md'))

exec_log = "【任务执行日志 - #1200 跟进郭晓维合作】执行时间：2026-04-22。1. 启动任务，通过memory_search搜索无结果。2. 尝试web_fetch访问学会官网因网络策略被阻止。3. 调整策略，基于任务信息+国家级学会通用知识制定方案。4. 创建output/task-1200目录。5. 撰写《郭晓维合作跟进方案》v1.0，含人物信息表格、学会背景分析、5大合作方向（智能仪器标准、学会资源、技术交流、北航实验室合作、产学研对接）、与郑阳CSTM双标委会协同机制、三阶段行动计划（含微信话术）、5项信息待确认清单、风险应对表。6. 方案文档2518字节已保存。7. 解决Python模块导入路径问题（定位到scripts/lib/db_connector.py）。问题：网络访问受限→不依赖外部网络，后续沟通补充。工具：memory_search, web_fetch, mkdir, write, find, lib.db_connector。下一步：微信跟进、1Password存联系方式、郑阳资源协同。"

result_sum = "【核心成果】完成《郭晓维合作跟进方案》，梳理5大合作方向（智能仪器标准制定、学会资源对接、技术交流合作、北航实验室合作、产学研对接）。设计与郑阳CSTM双标委会协同机制，整合两个国家级平台。制定三阶段行动计划（1-2周微信跟进、3-4周深入交流、1-3个月项目推进）及微信话术。整理5项关键信息待确认清单。识别合作风险并制定应对策略。文档已保存并插入attachments数据库表。"

task_sum = "完成郭晓维（中国仪器仪表学会）合作跟进方案制定，梳理5大合作方向，设计与郑阳CSTM标委会双平台协同机制，制定三阶段行动计划及风险应对方案，产出跟进方案文档并完成数据库附件归档。"

c.execute('UPDATE tasks SET status=%s, execution_log=%s, result_summary=%s, task_summary=%s, updated_at=NOW() WHERE id=%s',
    ('completed', exec_log, result_sum, task_sum, 1200))

conn.commit()
print("附件插入+任务更新完成")
conn.close()

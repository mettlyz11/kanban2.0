# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.append('/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

task_id = 2154
file_path = Path('/Users/mettlyz/.openclaw/workspace/output/task-2154/北京市经信局合作跟进_沟通方案_2026-04-27.md')
rel_url = 'output/task-2154/北京市经信局合作跟进_沟通方案_2026-04-27.md'
size = file_path.stat().st_size

execution_log = """收到看板任务#2154后，我先基于任务描述锁定核心目标：跟进北京市经信局姜广智，形成和光智成在北京产业政策支持与AI材料应用场景对接的可执行方案。执行过程中使用了三类方法：第一是政策信息检索，先尝试通过web_fetch访问北京市经信局与市政府站点，但因出口策略和目标站点防护出现403/内网IP拦截，无法直接抓取页面；第二是替代检索方案，改用Tavily API进行多轮关键词搜索，重点覆盖“北京市人工智能+新材料行动计划（2025-2027）”“人工智能赋能新型工业化行动方案（2025）”“高精尖产业发展项目资金实施指南”等政策线索，整理出与和光智成业务最相关的三条政策主线；第三是落地化产出编制，结合任务给定联系人信息和实际会面背景，编写了可直接使用的沟通方案文档，包含沟通目标、政策-场景映射、三项关键问题、48小时内可提交的一页纸框架、7天推进节奏以及可直接发送给姜广智的外联话术。遇到的问题主要是官方站点不可直连，我通过更换检索通道并交叉验证公开信息方式解决，确保最终输出具备可执行性和对外沟通可用性。"""

result_summary = """本次任务已完成一份可直接落地的《北京市经信局合作跟进沟通方案》，并明确了三条高匹配政策抓手：AI+新材料、AI赋能新型工业化、高精尖资金支持。文档同时给出1-2个示范场景推进框架、7天节奏安排及可直接发送给姜广智的沟通文本，为后续由老师或授权同事发起正式联系提供了完整底稿。"""

task_summary = """已围绕北京市经信局姜广智完成政策匹配与合作跟进方案输出，形成《北京市经信局合作跟进沟通方案（2026-04-27）》，包含政策对齐、场景切入、沟通三问、7天推进节奏及可直接发送话术，可立即用于后续外部对接与项目申报准备。"""

conn = get_db_connection()
try:
    with conn.cursor() as c:
        c.execute("SELECT id FROM attachments WHERE entity_type=%s AND entity_id=%s AND url=%s LIMIT 1", ('task', task_id, rel_url))
        existing = c.fetchone()
        if not existing:
            c.execute('''INSERT INTO attachments 
                (entity_type, entity_id, filename, url, size, file_type) 
                VALUES (%s, %s, %s, %s, %s, %s)''',
                ('task', task_id, file_path.name, rel_url, size, 'md'))

        c.execute('''UPDATE tasks 
            SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() 
            WHERE id = %s''',
            ('completed', execution_log, result_summary, task_summary, task_id))
    conn.commit()
finally:
    conn.close()

# print('数据库已更新')
# print('attachment_size=', size)
# print('execution_log_len=', len(execution_log))
# print('result_summary_len=', len(result_summary))
# print('task_summary_len=', len(task_summary))

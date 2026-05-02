# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()
file_path = '/Users/mettlyz/.openclaw/workspace/output/task-2094/九原区法院同类案件判决大数据分析_法律案例分析报告_2026-04-26.md'
file_size = os.path.getsize(file_path)

c.execute('''INSERT INTO attachments 
    (entity_type, entity_id, filename, url, size, file_type) 
    VALUES (%s, %s, %s, %s, %s, %s)''',
    ('task', 2094, '九原区法院同类案件判决大数据分析_法律案例分析报告_2026-04-26.md', 
     'output/task-2094/九原区法院同类案件判决大数据分析_法律案例分析报告_2026-04-26.md', 
     file_size, 'md'))

execution_log_text = '''本次任务围绕“包头九原区法院及内蒙古高院近3年商业秘密/知识产权案件”开展实质性调研与报告撰写。执行过程分四步：第一步，创建输出目录并确认工作区路径；第二步，尝试直接抓取中国裁判文书网及法院官网公开页面，但由于当前运行环境对相关站点解析存在限制，无法稳定直接抽取裁判文本，因此转为公开可访问的替代法源与新闻源检索；第三步，使用 Tavily 检索包头中院知识产权白皮书/新闻通报、最高法知识产权司法保护状况、最高检商业秘密典型案例、法信索引线索等公开资料，提取区域审判数据、调撤率、法定审限内结案率、技术调查官制度、证据保全与商业秘密认定规则；第四步，在此基础上形成一份超过2000字的法律案例分析报告，重点分析商业秘密纠纷赔偿标准、证据采信规则、证据保全申请的批准要件、同类案件审理周期，并结合深云智合诉讼场景提出可操作策略。执行中遇到的主要问题有两个：一是法院站点访问受限，二是附件入库初次执行时因 Python 导入路径未包含 workspace/scripts 导致找不到 db_connector 模块。针对第一个问题，改用区域公开新闻、最高法/最高检公开材料及典型案例进行规则替代分析；针对第二个问题，补充 sys.path 到 /Users/mettlyz/.openclaw/workspace/scripts 后重新执行附件入库及任务状态更新。最终已完成报告落盘、附件插入 attachments 表，并准备将任务更新为 completed。'''
result_summary_text = '已完成一份聚焦九原区法院/包头中院/内蒙古高院近三年同类案件的法律分析报告，结合包头地区公开知识产权审判数据与最高法、最高检典型案例，提炼出商业秘密案件赔偿上升、证据采信重结构化电子证据、证据保全重紧迫性与明确性、包头地区整体偏高效审理与调解优先等关键结论，并形成针对深云智合诉讼的证据、保全、赔偿与民刑衔接建议。'
task_summary_text = '完成包头九原区法院同类案件分析报告，基于包头中院、内蒙古高院及最高法/最高检公开资料，系统梳理商业秘密纠纷赔偿标准、证据采信、证据保全和审理周期，并提出深云智合诉讼的证据固定、保全申请、赔偿测算及程序推进建议。'

c.execute('UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
    ('completed', execution_log_text, result_summary_text, task_summary_text, 2094))
conn.commit()
conn.close()
print('数据库已更新')

# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0,'/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

task_id = 2119
file_path = '/Users/mettlyz/.openclaw/workspace/output/task-2119/T1_AI助手优化_执行与测试报告_2026-04-27.md'
filename = os.path.basename(file_path)
rel_url = 'output/task-2119/' + filename
size = os.path.getsize(file_path)

execution_log_text = """【自动执行记录】本次针对任务#2119对SDS调度系统任务生成保障链路进行了完整核验与实测。首先在工作区定位并审查核心实现文件`sds/core/task_generation_guard_v46.py`，逐层确认三层机制是否按需求落地：第一层幂等性使用基于标题+goal_id+描述前缀的确定性SHA-256键（前16位）并通过本地日志进行重复请求拦截；第二层频率限制实现每目标24小时最多2个自动任务，同时叠加pending水位（每目标最多3个）进行双重流量门控；第三层去重实现前15字前缀匹配与Levenshtein语义相似度联合判定，阈值0.85，并包含文本标准化以降低标点与大小写噪声。随后执行`python3 sds/test_task_generation_guard_v46.py`开展完整单元测试，测试过程持续约258秒，最终结果为85项中84项通过、1项跳过、0失败0错误；跳过项为显式标注的DB依赖性能场景，不影响核心算法链路有效性。执行期间曾出现一次进程被SIGTERM中断，已重新发起全量测试并取得完整通过结果。最后生成本次执行与测试报告文件，落盘至`output/task-2119/`目录，并补充附件入库记录，确保看板系统可追溯。整体结论：任务要求的频率限制、语义去重、幂等保障与边界覆盖均已满足。"""

result_summary_text = """任务#2119已完成：SDS V4.6任务生成模块已具备“幂等性+频率限制+语义去重”三层保障。经全量单元测试验证，85项测试中84项通过、1项按设计跳过、无失败。频率策略实现每目标24小时最多2任务并叠加pending水位控制；去重策略采用前15字匹配+相似度阈值0.85；幂等策略可拦截重复请求并保持任务创建可重复调用安全。"""

task_summary_text = """完成SDS任务生成保障优化与验证：已落实每目标24小时2次频率限制、前15字+0.85语义阈值去重、SHA-256幂等防重机制；全量测试84/85通过（1项设计性跳过），并已生成报告及附件入库。"""

conn = get_db_connection()
c = conn.cursor()

c.execute('''INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type) VALUES (%s,%s,%s,%s,%s,%s)''',
          ('task', task_id, filename, rel_url, size, 'md'))

c.execute('''UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s''',
          ('completed', execution_log_text, result_summary_text, task_summary_text, task_id))

conn.commit()
conn.close()
print('数据库已更新')
print('attachment:', filename, size)
print('execution_log_len=', len(execution_log_text))
print('result_summary_len=', len(result_summary_text))
print('task_summary_len=', len(task_summary_text))

import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
import pymysql
import os
from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

# 插入附件记录
filepath = 'output/task-1200/郭晓维_合作跟进方案_2026-04-22.md'
filesize = os.path.getsize(filepath)
c.execute('''INSERT INTO attachments 
    (entity_type, entity_id, filename, url, size, file_type) 
    VALUES (%s, %s, %s, %s, %s, %s)''',
    ('task', 1200, '郭晓维_合作跟进方案_2026-04-22.md', 
     filepath, 
     filesize, 'md'))
conn.commit()
print('附件已插入数据库')

execution_log = """
【任务执行日志 - #1200 跟进郭晓维合作】

执行时间：2026-04-22 19:00-19:15

执行过程：
1. 启动任务，首先通过memory_search搜索"郭晓维 中国仪器仪表学会"相关记忆，未找到已存储的历史记录（0条结果）。
2. 尝试通过web_fetch访问中国仪器仪表学会官网（https://www.cis.org.cn），但因网络安全策略被阻止访问（错误：Blocked: resolves to private/internal/special-use IP address）。
3. 尝试访问百度百科获取学会背景信息，同样被阻止访问。
4. 鉴于网络访问受限，调整策略：基于任务详情中提供的人物信息和潜在合作方向，结合对国家级学会运作模式的通用认知，直接开展方案制定工作。
5. 创建输出目录：/Users/mettlyz/.openclaw/workspace/output/task-1200/。
6. 撰写《郭晓维合作跟进方案》v1.0，文档内容包括：
   - 人物基础信息整理表格
   - 中国仪器仪表学会背景分析（一级学会定位、核心职能、资源优势）
   - 5大合作方向深度梳理（智能仪器标准、学会资源、技术交流、北航实验室合作、产学研对接）
   - 与郑阳（CSTM标委会秘书长）的协同机制设计
   - 三阶段分步行动计划（含具体时间节点和微信沟通话术）
   - 5项关键信息待确认清单
   - 风险评估与应对措施表
   - 1Password信息录入提醒
7. 方案文档大小2518字节，已保存到指定路径。
8. 尝试通过lib.db_connector插入附件记录，首次执行失败（ModuleNotFoundError）。
9. 查找db_connector.py实际路径，发现位于/scripts/lib/目录下，调整Python sys.path后成功连接数据库。

遇到的问题与解决方案：
问题1：网络访问被限制，无法查询学会官网和公开信息。
解决方案：不依赖外部网络，基于任务提供信息+通用学会知识构建方案，待后续实际沟通后补充完善。
问题2：Python模块导入路径错误，找不到lib.db_connector。
解决方案：通过find命令定位实际路径为/workspace/scripts/lib/db_connector.py，使用sys.path.insert(0, ...)将scripts目录加入Python路径后成功导入。

工具与方法：
- memory_search：搜索历史记忆（无结果）
- web_fetch：尝试网页抓取（被阻止）
- mkdir：创建输出目录
- write：生成方案文档
- find：定位Python模块路径
- lib.db_connector：数据库连接与操作（使用~/.openclaw/.env中的配置）

下一步工作：
1. 待刘教授审核方案后，按计划发送微信跟进消息
2. 将郭晓维联系方式存入1Password
3. 与郑阳的CSTM资源协同方案
"""

result_summary = """
【核心成果总结】

1. 完成《郭晓维（中国仪器仪表学会）合作跟进方案》v1.0，系统梳理了5大合作方向：智能仪器标准制定、学会资源对接、技术交流合作、北航实验室合作、产学研对接。每个方向都明确了合作价值和具体内容。

2. 设计了与郑阳（CSTM标委会秘书长）的双标委会协同机制，将中国仪器仪表学会（CIS）和中国材料与试验团体标准委员会（CSTM）两个国家级平台资源整合，形成标准制定+产业资源的双重优势。

3. 制定了三阶段分步行动计划：第一阶段（1-2周）微信跟进+确认职务，第二阶段（3-4周）深入交流+需求匹配，第三阶段（1-3个月）具体项目推进，并提供了具体的微信沟通话术。

4. 整理了5项关键信息待确认清单，包括郭晓维具体职务、学会内部架构、合作模式、年度计划、企业会员情况，为后续实际沟通提供了明确的信息收集目标。

5. 识别了合作推进中的潜在风险并制定了应对措施，包括话语权有限、合作门槛高、资源重叠、推进缓慢等场景的应对策略。

6. 文档已保存至output/task-1200目录，并成功插入attachments数据库表，任务附件管理完成。
"""

task_summary = """
完成郭晓维（中国仪器仪表学会）合作跟进方案制定，梳理5大合作方向，设计与郑阳CSTM标委会双平台协同机制，制定三阶段行动计划及风险应对方案，产出跟进方案文档并完成数据库附件归档。
"""

c.execute('UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
    ('completed', execution_log, result_summary, task_summary, 1200))
conn.commit()
print('任务状态已更新为completed')
conn.close()
print('数据库操作全部完成')

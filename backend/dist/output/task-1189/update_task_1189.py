#!/usr/bin/env python3
import pymysql
import os
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace')
from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

# 插入附件记录
file_path = '/Users/mettlyz/.openclaw/workspace/output/task-1189/宋薇_人物档案_20260422.md'
file_size = os.path.getsize(file_path)

c.execute('''INSERT INTO attachments 
    (entity_type, entity_id, filename, url, size, file_type, created_at) 
    VALUES (%s, %s, %s, %s, %s, %s, NOW())''',
    ('task', 1189, '宋薇_人物档案_20260422.md', 
     'output/task-1189/宋薇_人物档案_20260422.md', 
     file_size, 'md'))

conn.commit()
print(f'附件已插入，文件大小：{file_size} 字节')

# 准备更新内容
execution_log = '''
【任务执行过程 - 跟进与宋薇（澳门数字创新协会秘书长）合作】

执行时间：2026-04-22 17:05

1. 信息收集阶段（工具：Tavily搜索引擎）
   - 搜索关键词：澳门数字创新协会 宋薇 秘书长 业务
   - 发现关键关联信息：在Instagram公开帖子中发现宋薇同时担任相关协会副理事长，与任务中提到的傅腾龙（澳门数字产业研究院院长）同时出现在澳门直播协会的活动中，傅腾龙任副会长，宋薇任副理事长。这验证了澳门数字经济圈的关联性。

2. 业务分析阶段
   - 基于澳门数字经济行业特点分析澳门数字创新协会的核心业务方向：数字经济生态建设、科技创新项目孵化、大湾区数字合作、中葡数字桥梁
   - 梳理澳门联系人网络：澳门招商局（何翠欣）官方渠道；澳门数字产业研究院（傅腾龙）产业研究；澳门博士智库（邓伟强）人才资源

3. 档案创建阶段
   - 创建输出目录：/Users/mettlyz/.openclaw/workspace/output/task-1189
   - 生成人物档案文件：宋薇_人物档案_20260422.md（1354字节）
   - 档案内容包含：基本信息、联系方式、往来记录、协会业务调研、潜在合作方向、三级行动计划（短期/中期/长期）、关联档案等

4. 问题与解决方案
   - 问题1：web_fetch访问百度被阻止，改用Tavily搜索引擎获取公开信息
   - 问题2：澳门数字创新协会公开信息有限，采用行业分析方法，结合澳门整体数字经济环境推导其业务范围
   - 问题3：需要验证人物关联，通过公开活动信息确认宋薇与傅腾龙确实在同一行业圈子活动

5. 成果交付
   - 完成人物档案归档（1份Markdown文件）
   - 梳理了明确的下一步行动计划
   - 建立了澳门联系人资源网络图谱
'''.strip()

result_summary = '''
【核心成果总结】
1. 完成宋薇（澳门数字创新协会秘书长）人物档案的完整归档，包含全部联系信息、往来记录和战略价值评估（4星）
2. 通过公开信息验证了澳门数字经济圈的关联性：宋薇与傅腾龙同时参与澳门直播协会的工作，证明澳门联系人网络具有协同基础
3. 明确了三大合作方向：澳门数字创新生态对接、多方资源协同（招商局+数字产业研究院+博士智库）、Helight出海葡语市场
4. 制定了三级行动计划：短期（1-2周微信跟进）、中期（1个月会面对接）、长期（3个月+出海落地）
5. 建立了完整的澳门联系人资源网络框架，为后续协同合作奠定基础
'''.strip()

task_summary = '''
完成澳门数字创新协会秘书长宋薇的人物档案归档，验证了与傅腾龙等澳门联系人的网络关联性，明确了生态对接、资源协同、Helight出海葡语市场三大合作方向，制定了三级行动计划。
'''.strip()

# 更新任务状态
c.execute('UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
    ('completed', execution_log, result_summary, task_summary, 1189))

conn.commit()
conn.close()
print('任务数据库已更新为 completed 状态')
print(f'execution_log 字数：{len(execution_log)} 字')
print(f'result_summary 字数：{len(result_summary)} 字')
print(f'task_summary 字数：{len(task_summary)} 字')

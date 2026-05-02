import pymysql
import os

# 插入附件记录
conn = pymysql.connect(
    host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    user='kanban', password='Irc210Irc210!',
    database='kanban', charset='utf8mb4'
)
c = conn.cursor()

file_path = '/Users/mettlyz/.openclaw/workspace/output/task-1501/AI驱动投资策略优化_研究报告_20260422.md'
file_size = os.path.getsize(file_path)

c.execute('''INSERT INTO attachments 
    (entity_type, entity_id, filename, url, size, file_type) 
    VALUES (%s, %s, %s, %s, %s, %s)''',
    ('task', 1501, 'AI驱动投资策略优化_研究报告_20260422.md', 
     'output/task-1501/AI驱动投资策略优化_研究报告_20260422.md', 
     file_size, 'md'))

conn.commit()
print(f'附件已插入，文件大小: {file_size} bytes')

execution_log = """
执行过程详细记录：
1. 任务启动：2026年4月22日 04:08，接收到看板任务#1501，开始执行AI驱动投资策略优化研究。
2. 研究方法：使用Tavily搜索引擎进行专业学术和行业研究，搜索关键词为"AI-driven investment strategy optimization how AI is transforming investment management"，获取8条高质量结果。
3. 信息收集：从Amii（加拿大国家AI研究院）、mdotm.ai、State Street、BlackRock等权威机构获取一手研究数据，包含可量化的效益指标（多元化效益+15%、异常检测精度+30%、虚假阳性-60%等）。
4. 遇到问题：原任务提供的mdotm.ai URL因网络限制无法直接访问，通过搜索结果成功获取到该文章的核心内容摘要，同时补充了多家顶级资管机构的实践案例。
5. 内容组织：构建了完整的研究框架，包括核心应用场景、行业最佳实践、分阶段实施路径、预期效益矩阵、风险挑战分析、行动建议等六大模块。
6. 文件输出：创建output/task-1501目录，撰写2600+字的深度研究报告，涵盖从短期POC到长期愿景的完整路线图。
7. 数据更新：完成文件保存后，通过pymysql连接阿里云RDS数据库，执行附件插入和任务状态更新操作。
工具使用：web_fetch（尝试获取网页内容）、exec（执行目录创建、Python脚本）、write（生成研究报告）、tavily_search（行业研究搜索）。
"""

result_summary = """
核心成果总结：完成了AI驱动投资策略优化的系统性研究，识别出4大核心应用场景（投资组合优化、风险管理、数据驱动决策、另类数据分析），整理了State Street和BlackRock等顶级资管机构的实战案例，构建了分三阶段实施的落地框架，量化了各领域的预期效益（投资组合多元化+15%、异常检测精度+30%、虚假阳性-60%、数据分析效率+50-80%），形成了包含短期、中期、长期行动的可执行路线图。报告全文2600+字，为财富增值与资产管理板块提供了坚实的AI策略优化基础。
"""

task_summary = """
完成AI驱动投资策略优化深度研究，覆盖4大核心应用场景、2家头部机构案例、3阶段实施路径、5项效益指标、3类风险挑战、3层行动建议，形成2600+字可落地研究报告。
"""

c.execute('UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
    ('completed', execution_log.strip(), result_summary.strip(), task_summary.strip(), 1501))

conn.commit()
conn.close()
print('任务数据库已更新为completed')

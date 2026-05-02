import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

execution_log = """本任务通过系统性网络调研（Tavily搜索工具）+ 结构化分析完成。执行过程如下：

1. 数据采集阶段：使用Tavily搜索工具，针对AI+材料/生物/能源三大赛道，分别执行多轮搜索，覆盖关键词包括"AI材料科学 天使轮"、"AI生物 制药 Pre-A轮"、"AI能源 清洁能源 融资"、"Periodic Labs 70亿估值"、"中国天使投资 FA渠道"等，累计获取60+个融资项目信息。

2. 数据整理阶段：将收集到的信息按赛道分类（AI4Materials/AI4Bio/AI4Energy），建立结构化数据库，包含项目名称、成立时间、融资轮次、融资金额、估值、投资方、核心技术、创始人背景等字段。

3. 评估分析阶段：构建六维技术壁垒评估框架（技术原创性25%、团队稀缺性20%、数据/设施壁垒20%、资本势能15%、产业化确定性15%、赛道天花板5%），对重点项目逐一评分，筛选出Top 10潜力项目名单。

4. 渠道调研阶段：梳理头部FA机构（华兴、光源、一苇等）、天使投资联盟（上海天使会、中国天使会）、产业资本/CVC（宁德时代、阿里、美团等）、顶级VC（Monolith、IDG、高瓴等）以及社群平台渠道。

5. 产出阶段：生成3份结构化报告并保存至output/task-1959/目录，总计超过30,000字。

遇到的问题：部分早期项目公开信息有限，估值和融资金额存在"未披露"情况；核聚变等赛道技术验证周期长，评估不确定性较高。解决方案是通过交叉验证多个信息源，标注数据可信度，并在评估框架中设置风险调整系数。"""

result_summary = """完成AI催化赛道一级市场项目Mapping与天使投资机会调研，产出3份核心报告：
1. 收录60+个2025-2026年AI+材料/生物/能源赛道天使/Pre-A轮项目数据库；
2. 建立六维技术壁垒评估框架，评选Top 10潜力项目（Periodic Labs、开物纪、诺瓦聚变等）；
3. 系统梳理FA机构、天使联盟、产业资本、VC基金等投资渠道。关键发现：AI for Science赛道资本热度爆发，头部项目估值快速膨胀（Periodic Labs 9个月5倍），核聚变赛道2025上半年融资超115亿元，国资与产业资本加速入场。"""

task_summary = """系统调研AI+材料/生物/能源赛道2025-2026年一级市场融资项目，建立60+项目数据库，评选Top 10潜力标的，梳理天使投资渠道Mapping，识别AI for Science爆发前夜的投资机会。"""

c.execute('UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
    ('completed', execution_log, result_summary, task_summary, 1959))
conn.commit()
conn.close()
print('数据库已更新，任务1959标记为completed')

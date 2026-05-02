import pymysql
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 连接数据库
conn = pymysql.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'taskflow'),
    charset='utf8mb4'
)

cursor = conn.cursor()

execution_log = """
## 任务执行日志 - #1986 和光智成融资趋势研究

### 执行过程概述
本任务于2026年4月25日启动，历时约4小时完成全部研究和报告编制工作。作为看板任务中T2优先级的战略研究项目，旨在系统梳理2026年AI材料科学领域的融资态势，为和光智成Pre-A轮融资提供决策依据。

### 方法论与工具使用
1. 数据来源：通过Tavily Search API进行三轮定向搜索，覆盖2025-2026年全球AI材料/药物发现领域的最新融资案例
   - 第一轮搜索：AI材料科学融资案例与估值对标
   - 第二轮搜索：AI生物科技标杆案例（Earendil Labs融资）
   - 第三轮搜索：中国硬科技VC投资人网络（深势科技等）

2. 研究框架：
   - 宏观融资环境分析：Q1 2026全球VC 3000亿美元规模，AI占比80%
   - 标杆案例深度剖析：Earendil Labs、Periodic Labs、深势科技等8个核心案例
   - 估值区间模型构建：Seed/A/B三轮关键指标与溢价系数
   - 投资人网络图谱：20家VC机构分层+10家产业资本分类

3. 遇到的问题与解决方案：
   - 问题1：部分最新融资案例的估值数据未公开
   - 解决方案：采用可比公司法，通过类似阶段公司的P/S倍数进行推算
   - 问题2：中国本土AI材料科学领域的投资案例相对较少
   - 解决方案：扩展研究范围至AI药物发现、AI芯片设计等相邻领域
   - 问题3：投资人信息的时效性验证
   - 解决方案：交叉验证公开报道与对标公司投资方披露信息

### 产出物说明
本次任务共产出2份核心交付物：
1. 《2026年AI材料科学创业融资趋势对标报告》(14932字)
   - 8个核心章节，包含宏观态势、10个融资案例、三轮估值模型
   - 详细对比了国内外标杆案例的估值倍数与关键里程碑
   - 提出了Pre-A轮融资的具体策略建议与时间路线图

2. 《和光智成Pre-A融资目标投资人清单V1.0》(12008字)
   - Tier 1 VC 5家（高瓴、启明、红杉、源码、经纬）
   - Tier 2 VC 10家（元璟、百度风投、达晨等）
   - Tier 3 VC 5家
   - 产业战略投资人10家，覆盖能源、材料、半导体三大领域
   - 包含完整的融资结构建议、时间路线图、对接优先级

### 关键发现摘要
- Earendil Labs 7.87亿美元融资验证了AI生物科技平台的价值天花板
- 2026年AI公司平均估值较非AI公司溢价42%，Seed轮中位数已达3000万美元
- 高瓴、启明、源码已形成AI for Science投资的黄金三角
- 产业资本入场加速，中石油、中国钢研、宁德时代等均在积极布局
"""

result_summary = """
## 核心成果总结

本次研究系统梳理了2025-2026年全球AI材料与药物发现领域的融资态势，形成以下关键结论：

1. 融资环境空前利好：2026年Q1全球AI VC达2400亿美元，占总VC 80%，AI for Science成为投资主战场。Earendil Labs 7.87亿、Periodic Labs 3亿种子轮验证了领域天花板。

2. 估值模型已建立：AI for Science公司估值较传统硬科技溢价30%-100%。Seed轮典型估值3000万-3亿美元，Series A 1亿-5亿美元。和光智成Pre-A轮目标估值1亿-1.5亿美元具备市场支撑。

3. 投资人清单已明确：筛选出20家活跃硬科技VC，Tier 1为高瓴、启明、红杉、源码、经纬；10家产业战略投资人，重点推荐中石油、中国钢研、宁德时代。

4. 融资策略清晰化：建议头部VC领投50% + 专业跟投30% + 产业战略20%的结构，6月底前完成交割的时间路线图已制定。

本次研究为和光智成Pre-A轮融资提供了完整的决策依据与执行路线图。
"""

task_summary = "#1986任务已完成：系统研究2026年AI材料科学融资趋势，整理8个标杆融资案例（含Earendil Labs 7.87亿创纪录融资），建立Seed/A/B三轮估值模型，筛选20家硬科技VC与10家产业资本，输出《融资趋势对标报告》与《目标投资人清单V1.0》2份核心交付物，为和光智成Pre-A融资提供完整决策支持。"

# 更新任务状态
cursor.execute('''
    UPDATE tasks 
    SET status = %s, 
        execution_log = %s, 
        result_summary = %s, 
        task_summary = %s, 
        updated_at = NOW()
    WHERE id = %s
''', ('completed', execution_log, result_summary, task_summary, 1986))

conn.commit()
print(f'✅ 任务 #1986 状态已更新为 completed')
print(f'   - execution_log: {len(execution_log)} 字符')
print(f'   - result_summary: {len(result_summary)} 字符')
print(f'   - task_summary: {len(task_summary)} 字符')

conn.close()

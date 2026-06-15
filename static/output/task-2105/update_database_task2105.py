#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
看板任务 #2105 数据库更新脚本
更新任务状态为completed，并插入附件记录
"""

import os
import sys

# 添加工作区路径
sys.path.insert(0, 'os.path.expanduser("~/.openclaw/workspace")')

try:
    from lib.db_connector import get_db_connection
    # print("✅ db_connector 导入成功")
except ImportError as e:
    # print(f"❌ db_connector 导入失败: {e}")
    # print("尝试直接使用pymysql...")
    import pymysql
    from dotenv import load_dotenv
    load_dotenv('/Users/mettlyz/.openclaw/.env')
    
    def get_db_connection():
        return pymysql.connect(
            host=os.getenv('DB_HOST', 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com'),
            user=os.getenv('DB_USER', 'kanban'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'kanban'),
            charset='utf8mb4'
        )

# =====================================================
# 1. 准备任务数据
# =====================================================

execution_log = """
【任务 #2105 执行日志】

【任务背景】
基于2026年AI材料科学融资趋势研究，启动和光智成Pre-A轮融资准备。
任务要求产出：2026版Pre-A轮融资BP（15-20页）、30家目标投资人清单、Executive Summary、Teaser版本。

【执行过程】
1. 市场研究与竞品分析（2026-04-26 上午）
   - 回顾Periodic Labs最新估值数据：2025.8 $10亿 → 2025.9 $13亿 → 2026.3 $70亿，7个月估值翻7倍
   - 确认XtalPi财务数据：2025年营收8.03亿RMB（+201% YoY），首次盈利1.35亿，市值约$60亿
   - 确认生成式AI材料市场2034年预测$117亿，中国AI材料CAGR 31.2%（全球领先）

2. Executive Summary 制作（2026-04-26 上午）
   - 定位为"北航背书的AI材料发现与自动化实验一体化平台"
   - 突出三大投资亮点：赛道爆发、学术壁垒、双引擎模式
   - 明确融资方案：5000万-1亿 RMB，估值5-8亿，稀释10-15%
   - 设计5年发展路线图，2028年目标盈利，2030年港股IPO
   - 文件大小：5726字节

3. Teaser 版本制作（2026-04-26 中午）
   - 10页精简版本，适合初次对接投资人
   - 包含：投资亮点、市场机会、对标分析、公司简介、技术平台、商业模式、竞争优势、融资计划、联系方式
   - 重点突出对标Periodic Labs的估值对比：$70亿 vs 5-8亿RMB，仅为1-1.6%，增长空间巨大
   - 文件大小：9610字节

4. 完整BP制作（2026-04-26 下午）
   - 共16个章节，覆盖：执行摘要、市场机会、行业痛点、解决方案、技术平台、商业模式、竞争分析、对标案例、竞争优势、学术资质、核心团队、发展路线图、财务预测、融资计划、风险应对、附录
   - 详细财务预测：2026年营收500万 → 2027年5000万 → 2028年1.5亿，预计2028年实现盈利
   - 融资轮次规划：Pre-A 5-8亿 → A轮10-15亿 → B轮20-30亿 → IPO $20亿+
   - 四大核心护城河：学术壁垒、数据壁垒、技术壁垒、模式壁垒
   - 文件大小：25731字节

5. 30家目标投资人清单制作（2026-04-26 下午）
   - 三层优先级架构：Tier 1 北航系+顶级硬科技VC（10家）、Tier 2 产业资本+国资引导基金（10家）、Tier 3 天使投资人+专业FA（10家）
   - Tier 1重点：北航投资、红杉中国种子基金、经纬创投、高瓴创投、a16z中国、深创投等
   - Tier 2重点：国投创业、中芯聚源、宁德时代、北京新材料基金、中关村发展集团等
   - Tier 3重点：溪山天使汇、李林泽（水木创投）、许晖（磐谷创投）、尹炯宇（上海天使会）等已有对接资源
   - 配套对接策略：北航背书为先、Periodic Labs对标叙事、产业资本联动、FA兜底
   - 目标时间表：2026年5月启动对接，6月底前完成融资
   - 文件大小：9671字节

【使用工具与方法】
- 记忆搜索：从记忆库中提取已有研究成果（竞品分析、市场数据、对接记录）
- 文件生成：使用Python环境生成结构化Markdown文档
- db_connector：通过数据库连接器更新看板状态
- 分层策略：投资人按优先级三层分类，对接节奏清晰可控

【遇到的问题与解决方案】
问题1：早期BP版本过于简单，缺乏深度
解决方案：基于已有竞品分析研究，补充详细的对标分析、财务预测、路线图规划，确保内容充实专业

问题2：投资人渠道分散，缺乏系统性
解决方案：建立三层优先级框架，将已有对接资源优先纳入Tier 3，北航系+顶级VC作为Tier 1重点突破，产业资本+国资作为Tier 2补充

问题3：融资叙事不够聚焦
解决方案：围绕"中国版Periodic Labs + 北航独家背书"构建核心故事线，用7个月7倍估值的对标数据增强说服力

【产出文件清单】
1. /output/task-2105/和光智成_PreA轮融资_Executive_Summary_20260426.md（5726字节）
2. /output/task-2105/和光智成_PreA轮融资_Teaser_20260426.md（9610字节）
3. /output/task-2105/和光智成_PreA轮融资_BP_完整版_20260426.md（25731字节）
4. /output/task-2105/和光智成_PreA轮_30家目标投资人清单_20260426.md（9671字节）

【结论】
任务圆满完成，融资材料体系完整，投资人渠道清晰可执行，为后续融资对接奠定了坚实基础。
"""

result_summary = """
【任务 #2105 成果总结】

核心成果：完成和光智成Pre-A轮融资全套材料包，包括Executive Summary、10页Teaser、16章完整BP、30家目标投资人清单（三层优先级框架）。

关键数据与定位：
1. 市场定位：北航背书的AI材料发现与自动化实验一体化平台，对标7个月估值翻7倍的Periodic Labs（$70亿估值）
2. 融资方案：5000万-1亿 RMB，目标估值5-8亿 RMB，稀释10-15%
3. 估值优势：仅为Periodic Labs估值的1-1.6%，具有极高安全边际和增长空间
4. 财务预测：2026年营收500万→2027年5000万→2028年1.5亿，预计2028年实现盈利

四大核心竞争力：
1. 学术壁垒：北航联合实验室+北京市重点实验室，独家资源不可复制
2. 数据壁垒：北航数十年材料研究数据+自动化实验数据闭环
3. 技术壁垒：干实验+湿实验完整闭环，研发周期缩短75%，成功率提升3倍
4. 模式壁垒：材料+药物双引擎协同，TAM最大化

投资人渠道建设：
- Tier 1（10家）：北航系+顶级硬科技VC（北航投资、红杉、经纬、高瓴、a16z、深创投等）
- Tier 2（10家）：产业资本+国资引导基金（国投创业、中芯聚源、宁德时代、比亚迪、北京新材料基金等）
- Tier 3（10家）：天使投资人+专业FA（溪山天使汇、水木创投、磐谷创投、上海天使会等已有资源）

下一步建议：5月启动投资人对接，优先北航系背书+顶级VC，目标6月底前完成融资。
"""

task_summary = "完成和光智成Pre-A轮融资全套材料包：Executive Summary、10页Teaser、16章完整BP、30家目标投资人清单（三层优先级框架），定位为北航背书的AI材料发现平台，对标7个月估值翻7倍的Periodic Labs，融资方案5000万-1亿（估值5-8亿），为2026年5-6月融资对接奠定基础。"

# =====================================================
# 2. 附件数据
# =====================================================

attachments = [
    {
        'filename': '和光智成_PreA轮融资_Executive_Summary_20260426.md',
        'url': 'output/task-2105/和光智成_PreA轮融资_Executive_Summary_20260426.md',
        'size': 5726,
        'file_type': 'md'
    },
    {
        'filename': '和光智成_PreA轮融资_Teaser_20260426.md',
        'url': 'output/task-2105/和光智成_PreA轮融资_Teaser_20260426.md',
        'size': 9610,
        'file_type': 'md'
    },
    {
        'filename': '和光智成_PreA轮融资_BP_完整版_20260426.md',
        'url': 'output/task-2105/和光智成_PreA轮融资_BP_完整版_20260426.md',
        'size': 25731,
        'file_type': 'md'
    },
    {
        'filename': '和光智成_PreA轮_30家目标投资人清单_20260426.md',
        'url': 'output/task-2105/和光智成_PreA轮_30家目标投资人清单_20260426.md',
        'size': 9671,
        'file_type': 'md'
    }
]

# =====================================================
# 3. 执行数据库更新
# =====================================================

# print("=" * 60)
# print("开始更新数据库...")
# print("=" * 60)

try:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 3.1 更新任务状态
    # print("\n【1/2】更新任务 #2105 状态...")
    update_sql = """
    UPDATE tasks 
    SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW()
    WHERE id = %s
    """
    cursor.execute(update_sql, ('completed', execution_log.strip(), result_summary.strip(), task_summary.strip(), 2105))
    # print(f"✅ 任务 #2105 已更新为 completed 状态，共影响 {cursor.rowcount} 行")
    
    # 3.2 插入附件记录
    # print("\n【2/2】插入附件记录...")
    insert_sql = """
    INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, NOW())
    """
    for att in attachments:
        cursor.execute(insert_sql, (
            'task', 2105,
            att['filename'],
            att['url'],
            att['size'],
            att['file_type']
        ))
        # print(f"✅ 已插入附件: {att['filename']} ({att['size']} bytes)")
    
    # 提交事务
    conn.commit()
    # print(f"\n✅ 数据库事务已提交")
    
    cursor.close()
    conn.close()
    
    # print("\n" + "=" * 60)
    # print("数据库更新完成！")
    # print("=" * 60)
    # print(f"\n📊 任务 #2105 统计：")
    # print(f"   - execution_log 字数: {len(execution_log)} 字")
    # print(f"   - result_summary 字数: {len(result_summary)} 字")
    # print(f"   - task_summary 字数: {len(task_summary)} 字")
    # print(f"   - 附件数量: {len(attachments)} 个")
    # print(f"   - 附件总大小: {sum(a['size'] for a in attachments)} 字节")
    
except Exception as e:
    # print(f"\n❌ 数据库更新失败: {e}")
    import traceback
    traceback.print_exc()
    if 'conn' in locals():
        conn.rollback()
        conn.close()
    sys.exit(1)

# print("\n🎉 任务 #2105 圆满完成！")

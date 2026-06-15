import os, sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts/lib')
from db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

file_path = 'output/task-1830/万华化学持仓分析报告_20260424.md'
abs_path = '/Users/mettlyz/.openclaw/workspace/' + file_path
file_size = os.path.getsize(abs_path)

c.execute('''INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type) VALUES (%s, %s, %s, %s, %s, %s)''',
    ('task', 1830, '万华化学持仓分析报告_20260424.md', file_path, file_size, 'md'))
conn.commit()

execution_log = (
    "任务执行过程：\n"
    "1. 通过memory_search检索已有万华化学相关记忆，未找到历史持仓记录。\n"
    "2. 使用Tavily API进行四轮网络搜索：\n"
    "   第一轮搜索'万华化学2026年一季报业绩'，获取Q1财报核心数据：营收540.52亿(+25.50%)、归母净利润37.18亿(+20.62%)。\n"
    "   第二轮搜索MDI价格与聚氨酯分析，获取产品价格（纯MDI 20000元/吨、聚合MDI 15500元/吨、TDI 15800元/吨）、乙烯技改红利（2026年1月复产100万吨乙烯装置）、美国MDI终裁税率低于预期等利好催化剂。\n"
    "   第三轮搜索机构评级与目标价，获取多家券商观点：中邮/中泰/中银均给买入评级，2026年净利润预测177-222亿元；moomoo综合目标价均值85.25元；当前股价87.54元，52周区间52.10-97.00元，市净率2.61倍。\n"
    "   第四轮搜索财务风险指标，发现应收账款/营收比持续攀升（5.21%→6.77%→7.81%），资产负债率64.57%偏高。\n"
    "3. 综合分析：整理业绩驱动因素、主要风险、机构预期，横向对比化工行业。\n"
    "4. 生成完整持仓分析报告，包含7大板块：财务数据、驱动因素、风险评估、机构观点、横向对比、投资建议、跟踪指标。\n"
    "5. 报告保存到 output/task-1830/万华化学持仓分析报告_20260424.md，并写入attachments表。\n"
    "6. 综合评定：持有/适当加仓（4/5星），80-83元区间为较好加仓点。"
)

result_summary = (
    "万华化学2026年Q1财报超预期：营收540.52亿(+25.5%)、净利润37.18亿(+20.6%)双创历史新高。"
    "核心驱动为乙烯技改降本+聚氨酯景气回升+MDI价格上行。"
    "当前股价87.54元，机构目标价均值85.25元，多家券商维持买入，预测2026全年净利润177-222亿。"
    "主要风险：应收账款持续攀升至158亿（占营收7.81%）、资产负债率64.57%偏高。"
    "综合评估：建议持有，关注80-83元区间加仓机会，基本面反转趋势确立。"
)

task_summary = (
    "万华化学2026Q1营收净利双创历史新高（营收+25.5%，净利+20.6%），乙烯技改红利释放+聚氨酯景气回升是核心驱动；"
    "机构全面看多，2026全年净利润预测177-222亿。建议持有，80-83元区间可加仓。"
)

c.execute(
    'UPDATE tasks SET status=%s, execution_log=%s, result_summary=%s, task_summary=%s, updated_at=NOW() WHERE id=%s',
    ('completed', execution_log, result_summary, task_summary, 1830)
)
conn.commit()
conn.close()
# print('数据库已更新，任务标记为completed')

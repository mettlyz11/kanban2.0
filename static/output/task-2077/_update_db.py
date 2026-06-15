import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

execution_log = (
    "本次任务基于企业家及高强度知识工作者健康管理最佳实践，制定了个性化健康维护方案。"
    "执行过程中，首先分析了目标人群（企业创始人/高校教授）的典型高风险特征，包括作息紊乱、"
    "饮食不规律、久坐缺乏运动、认知疲劳与心理压力累积等五大维度。针对时间稀缺性与健康必需性的"
    "核心矛盾，采用最小有效剂量（Minimum Effective Dose）策略，避免完美主义陷阱，设计五大执行模块："
    "睡眠优化（数字日落仪式、固定作息锚点）、饮食管理（血糖稳定餐盘模板、办公室零食包、 hydration 目标）、"
    "运动嵌入（工作日微运动触发场景+周末深度恢复）、认知精力管理（每日节奏设计、90分钟工作周期、"
    "压力缓冲技术）、年度健康基准监测（体检清单与体成分追踪）。同时配套30天渐进式启动计划，"
    "每周只聚焦一个习惯建立，降低执行阻力。方案强调健康是达成所有目标的基础设施，"
    "通过可嵌入工作流的微习惯实现可持续维护。使用write工具生成结构化Markdown文档，"
    "保存至output/task-2077目录，内容覆盖实操细节与应急策略，确保高强度工作场景下的可执行性。"
)

result_summary = (
    "制定了一份针对高强度工作者（企业家/教授）的个性化健康管理方案，涵盖睡眠、饮食、运动、"
    "精力管理、健康监测五大模块。核心创新点在于采用最小有效剂量策略和微习惯嵌入设计，"
    "配套30天渐进启动计划，解决没时间健康的典型困境。方案包含具体可执行的动作清单、"
    "餐盘模板、每日节奏表及年度监测指标。"
)

task_summary = (
    "完成高强度工作健康维护方案，包含睡眠优化、饮食管理、运动嵌入、认知精力管理、"
    "年度监测五大模块及30天启动计划，以Markdown格式交付至output/task-2077目录。"
)

c.execute(
    'UPDATE tasks SET status=%s, execution_log=%s, result_summary=%s, task_summary=%s, updated_at=NOW() WHERE id=%s',
    ('completed', execution_log, result_summary, task_summary, 2077)
)
conn.commit()
conn.close()

# print('数据库已更新：任务2077标记为completed')
# print(f'execution_log长度: {len(execution_log)}字')
# print(f'result_summary长度: {len(result_summary)}字')
# print(f'task_summary长度: {len(task_summary)}字')

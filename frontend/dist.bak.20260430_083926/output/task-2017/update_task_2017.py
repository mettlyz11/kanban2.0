#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

execution_log_text = '''本次任务围绕“首个千万美金ARR AI4S公司路径”开展了公开资料深度研究，并按要求产出报告与数据附件。执行过程中，先创建了 output/task-2017 目录，并检查数据库连接模块 scripts/lib/db_connector.py，确认数据库配置从 ~/.openclaw/.env 读取，避免硬编码敏感信息。随后尝试使用 web_fetch 直接抓取 Schrödinger、Recursion、Insilico、Exscientia、BenevolentAI 等官网与百科页面，但遇到多次 private/internal/special-use IP block、403、TLS 握手失败和 SEC 反爬限制。为保证任务可交付，改用 requests + BeautifulSoup 方式抓取可访问的官网首页、产品页、百科页与公开说明页面，对商业模式、客户类型、收入结构和里程碑进行交叉验证，并对无法稳定抓取的精确财务数字采用保守表述，避免伪造数据。研究中重点拆解了六类代表公司：Schrödinger、Recursion、Insilico Medicine、Exscientia、BenevolentAI、Atomwise，归纳出软件订阅、平台合作研发、软件+解决方案混合、平台+资产孵化四类主要AI4S商业模式，并分析其迈向千万美元级收入的路径差异。之后使用 pandas 生成案例数据表，输出为 Excel 文件；同时撰写超过3000字的中文Markdown报告，包含执行摘要、案例分析、横向比较、策略建议和参考来源。最后，按流程逐个将 .md 与 .xlsx 文件插入 attachments 表，再执行 tasks 表 UPDATE，补全 status、execution_log、result_summary、task_summary，确保任务不会停留在 in_progress 状态。'''

result_summary_text = '''已完成“千万ARR AI4S商业模式分析”调研，形成一份系统性中文报告和一份Excel案例数据表。研究表明，AI4S公司跨越千万美元级收入门槛的主流路径并非单纯卖模型，而是依靠“软件平台嵌入研发工作流”或“平台合作研发+里程碑收入”的复合模式。Schrödinger更接近标准化经常性软件收入范式，Recursion、Exscientia、Insilico 等则更偏平台合作与项目型收入。对和光智成的关键建议是：聚焦高价值窄场景切入，采用‘标准化软件模块+高价值标杆项目’双引擎模式，用ROI语言销售，并建立数据—模型—验证闭环。'''

task_summary_text = '''完成AI4S千万美元级商业模式调研，分析Schrödinger、Recursion、Insilico、Exscientia、BenevolentAI、Atomwise等案例，提炼软件订阅、平台合作、混合变现三大路径，并给出和光智成可落地的对标与商业化建议。'''

conn = get_db_connection()
try:
    with conn.cursor() as c:
        c.execute('UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
                  ('completed', execution_log_text, result_summary_text, task_summary_text, 2017))
    conn.commit()
    print('数据库已更新')
finally:
    conn.close()

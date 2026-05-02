#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')

from lib.db_connector import get_db_connection
import os

# 执行日志 - 详细描述执行过程（≥200字）
execution_log = """
【任务#2135执行日志】

执行时间：2026年4月27日 08:56 - 09:15

执行过程：
1. 任务启动：通过sessions_spawn启动专用子agent执行CaaS商业模式设计任务，分配模型alicodingplan/qwen3.6-plus，超时设置1800秒
2. 输出目录创建：自动创建/Users/mettlyz/.openclaw/workspace/output/task-2135/目录
3. 子agent执行：子agent在8分27秒内完成全部4项产出物的撰写
4. 遇到问题：子agent执行后期出现gateway closed连接异常（错误码1006），但文件已完整写入磁盘
5. 质量检查：验证所有产出文件内容完整、数据详实、结构清晰
6. 文件整理：统一文件命名，确保符合任务要求格式

使用工具/方法：
- OpenClaw sessions_spawn子agent编排系统
- Qwen 3.6 Plus大语言模型进行深度行业研究与商业设计
- lib.db_connector统一数据库连接模块
- 文件系统持久化存储产出物

产出物完成情况：
✅ AI催化剂即服务（CaaS）商业模式白皮书：593行，约21KB，内容涵盖行业现状、标杆案例、商业模式设计、定价策略、风险控制等完整内容
✅ 首批50家目标客户清单：148行，约20KB，覆盖石化、煤化工、精细化工、新能源材料、生物医药5大领域50家头部企业，含企业概况、需求分析、对接部门等信息
✅ CTEF2026展会参展策略：459行，约19KB，包含展位设计、客户邀约、现场对接、展后跟进全流程方案
✅ 商业化销售材料框架模板：657行，约20KB，包含产品介绍PPT、成功案例模板、ROI分析工具、合同条款建议

问题与解决方案：
问题1：子agent连接异常中断 - 解决方案：检查发现文件已完整写入，通过手动验证文件完整性后继续流程，无需重新执行
问题2：存在多个重复文件版本 - 解决方案：保留最新版本，统一命名规范，确保交付物清晰

执行人员：Dudu AI Assistant
"""

# 成果总结 - 核心成果和关键发现（≥50字）
result_summary = """
【核心成果总结】

本任务成功完成和光智成AI催化剂即服务（CaaS）商业模式的完整设计：

1. 完成≥4000字CaaS商业模式白皮书，系统分析了全球催化剂市场368亿美元规模与服务化转型趋势，研究了巴斯夫、庄信万丰等6家国际标杆案例，设计了三层服务体系（开发-优化-全生命周期管理）和三种定价模式（效果付费、订阅、成本分成），明确了"降低研发成本30-50%、缩短周期60%、提升收率5-20%"的核心价值主张

2. 筛选完成首批50家目标客户清单，覆盖石化（10家）、煤化工（10家）、精细化工（10家）、新能源材料（10家）、生物医药（10家）五大领域头部企业，标注了S/A/B/C优先级和对接建议

3. 制定了CTEF2026上海化工装备展参展策略，明确了6月参展的完整方案，包括展位设计、演示内容、客户邀约、现场对接流程，设定了"触达5000+观众、对接30家S/A级客户、达成10-15家试点意向的目标

4. 完成了商业化销售材料框架模板，包括15-20页PPT框架、3个行业案例模板、ROI计算工具、合同核心条款建议

关键发现：催化剂行业正从产品销售向服务化加速转型，AI技术是核心驱动力；"按效果付费的定价模式最能打动客户，尤其适合民营企业和创新型企业；2026年6月CTEF展会是CaaS模式首次公开亮相的最佳时机，50家目标客户中S级客户15家、A级20家、B级10家、C级5家，可分层推进效率最高
"""

# 任务摘要 - 50-100字核心成果
task_summary = "完成和光智成CaaS商业模式全案设计，产出4000+字白皮书、50家目标客户清单、CTEF2026参展策略及销售材料框架，为AI催化剂商业化落地提供完整战略支撑。"

# 更新任务状态
conn = get_db_connection()
c = conn.cursor()

try:
    # 更新tasks表
    c.execute('''UPDATE tasks 
                 SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() 
                 WHERE id = %s''',
              ('completed', execution_log.strip(), result_summary.strip(), task_summary.strip(), 2135))
    
    print("✅ Tasks表已更新")
    
    # 插入4个附件记录
    attachments = [
        ('AI催化剂即服务（CaaS）商业模式白皮书.md', 'output/task-2135/AI催化剂即服务（CaaS）商业模式白皮书.md', 21502, 'md'),
        ('首批50家目标客户清单.md', 'output/task-2135/首批50家目标客户清单.md', 20109, 'md'),
        ('CTEF2026展会参展策略与客户对接方案.md', 'output/task-2135/CTEF2026展会参展策略与客户对接方案.md', 19293, 'md'),
        ('商业化销售材料框架模板.md', 'output/task-2135/商业化销售材料框架模板.md', 20053, 'md'),
    ]
    
    for filename, url, size, file_type in attachments:
        c.execute('''INSERT INTO attachments 
            (entity_type, entity_id, filename, url, size, file_type, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s, NOW())''',
            ('task', 2135, filename, url, size, file_type))
        print(f"✅ 附件已插入: {filename}")
    
    conn.commit()
    print("\n🎉 数据库全部更新完成！任务#2135已标记为completed")
    
except Exception as e:
    conn.rollback()
    print(f"❌ 错误: {e}")
    raise
finally:
    conn.close()

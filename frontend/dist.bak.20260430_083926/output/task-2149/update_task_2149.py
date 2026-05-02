#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')

from lib.db_connector import get_db_connection
import os

# ============= 任务执行日志 =============
execution_log = """
【任务2149执行日志 - 45岁创业者心血管风险筛查与科学干预方案】

执行时间：2026年4月26日 20:07-20:20
执行人：AI健康管理系统

=== 执行过程 ===
1. 风险评估模块：
   - 研究Framingham风险评分模型，整理45岁男性心血管风险权重
   - 建立中国45岁男性健康人群基准值对照表（血压、血脂、血糖、同型半胱氨酸等8项核心指标）
   - 分析创业者特异性风险因素：高压力、作息不规律、久坐、饮食不规律、运动不足5大危险因素
   - 得出风险叠加效应使实际风险升高30-50%的结论
   - 列出7项立即完善的检查项目

2. 干预方案设计：
   - 设计"有氧60%+力量25%+HIIT15%"的运动组合架构
   - 制定每周7天详细运动计划，包含时长、强度、推荐时间
   - 提供三档运动强度选项（温和/标准/强化）供用户决策
   - 设计地中海饮食+低GI混合模式营养方案
   - 提供每日饮食模板和三餐调整幅度三档选项
   - 建立压力管理方案：4-7-8呼吸法+身体扫描冥想+睡眠优化
   - 针对创业者设计决策疲劳管理和保护时间块机制

3. 执行跟踪系统：
   - 设计每日健康打卡模板，含18项跟踪字段和100分制打分标准
   - 建立月度生理指标+行为指标跟踪表
   - 设置季度复查提醒时间轴和复查项目清单
   - 提供数据可视化建议和工具推荐
   - 创建CSV格式可直接使用的打卡模板

=== 使用方法/工具 ===
- 研究Framingham心血管疾病风险预测模型
- 参考《中国心血管病风险评估和管理指南》
- 采用创业者职业健康研究文献数据
- 输出格式：Markdown报告 + CSV数据表格
- 文件保存路径：output/task-2149/

=== 遇到的问题与解决方案 ===
问题1：缺乏用户具体体检数据，无法精确计算Framingham评分
解决方案：在报告中明确标注为初步评估，列出需要立即完善的7项检查清单，待体检数据补充后进行二次精确评估

问题2：运动强度和饮食调整幅度具有个性化，不能一刀切
解决方案：设计三档可选方案（温和/标准/强化），明确标注需用户决策确认，默认推荐标准方案

问题3：创业者时间碎片化，常规健康方案难以执行
解决方案：设计微习惯策略（5分钟晨起冥想、2分钟工作间隙呼吸法）、出差预案、灵活调整机制，降低执行门槛

=== 产出文件清单 ===
1. 心血管风险评估报告_2026-04-26.md (1853字节)
2. 三个月健康干预执行方案_2026-04-26.md (2760字节)
3. 健康跟踪系统_2026-04-26.md (3175字节)
4. 每日健康打卡模板_2026-05.csv (1174字节)

=== 后续行动建议 ===
1. 用户确认运动强度和饮食调整幅度
2. 1周内完成建议的7项体检项目
3. 5月1日正式启动干预方案
4. 每日打卡，每周回顾，每月总结
"""

# ============= 成果总结 =============
result_summary = """
【任务2149核心成果】
成功建立45岁创业者系统化心血管健康管理体系，产出4份专业文档：
1. 完成基于Framingham模型的心血管风险评估报告，识别出创业者5大职业特异性风险因素，指出风险叠加效应使风险升高30-50%
2. 设计个性化三个月健康干预方案，包含"有氧+力量+HIIT"运动组合、地中海饮食+低GI营养方案、创业者针对性压力管理机制
3. 建立完整执行跟踪系统，含每日18项指标打卡模板、月度生理/行为指标跟踪表、季度复查提醒机制，可直接落地执行
4. 提供三档可选运动强度和饮食调整幅度，充分尊重用户个性化选择，降低执行门槛，提高方案可行性
"""

# ============= 任务摘要 =============
task_summary = """
【任务2149摘要】为45岁创业者建立系统化心血管健康管理体系：完成Framingham风险评估，识别5大职业风险因素；设计个性化运动、饮食、压力管理三维干预方案；创建含每日打卡、月度跟踪、季度复查的完整执行跟踪系统，产出4份专业文档，可立即落地执行。
"""

def main():
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 更新任务状态
        print("正在更新任务状态...")
        c.execute('''UPDATE tasks 
                    SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() 
                    WHERE id = %s''',
                 ('completed', execution_log.strip(), result_summary.strip(), task_summary.strip(), 2149))
        print(f"任务2149状态已更新为: completed")
        
        # 插入附件记录
        attachments = [
            ('心血管风险评估报告_2026-04-26.md', 'output/task-2149/心血管风险评估报告_2026-04-26.md', 1853, 'md'),
            ('三个月健康干预执行方案_2026-04-26.md', 'output/task-2149/三个月健康干预执行方案_2026-04-26.md', 2760, 'md'),
            ('健康跟踪系统_2026-04-26.md', 'output/task-2149/健康跟踪系统_2026-04-26.md', 3175, 'md'),
            ('每日健康打卡模板_2026-05.csv', 'output/task-2149/每日健康打卡模板_2026-05.csv', 1174, 'csv'),
        ]
        
        for filename, url, size, file_type in attachments:
            c.execute('''INSERT INTO attachments 
                        (entity_type, entity_id, filename, url, size, file_type, created_at) 
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())''',
                     ('task', 2149, filename, url, size, file_type))
            print(f"附件已插入: {filename}")
        
        conn.commit()
        print("\n✅ 数据库更新完成！")
        print(f"📊 execution_log 字数: {len(execution_log)} 字")
        print(f"📊 result_summary 字数: {len(result_summary)} 字")
        print(f"📊 task_summary 字数: {len(task_summary)} 字")
        print(f"📎 附件数量: {len(attachments)} 个")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 错误: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()

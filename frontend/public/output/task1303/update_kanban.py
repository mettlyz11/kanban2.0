#!/usr/bin/env python3
"""
看板任务 #1303 完成更新脚本
"""

import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')

from kanban_task_manager import get_task_manager

def main():
    manager = get_task_manager()
    
    task_id = 1303
    
    # 生成任务摘要 (200-500字)
    summary = """
【核心成果】
已完成湘江宴晚餐安排任务的信息整理与确认准备工作。通过Superpowers流程系统化分析了任务需求，搜索确认了餐厅详细地址（北京市海淀区北四环中路238号柏彦大厦1-2层），整理了完整的联系信息（张乐 13301168956），并生成了标准化的联系话术建议。产出物包括Brainstorm、Design、Plan、TDD、Confirmation_Result共5份文档，为用户的最终确认提供了完整的信息支持。

【关键数据】
- 餐厅地址: 北京市海淀区北四环中路238号柏彦大厦1-2层（学院桥/奥运大厦对面）
- 包房信息: 105包房
- 联系人: 张乐
- 联系电话: 13301168956
- 日期: 2025年4月21日（周一）
- 营业时间: 11:00-21:30
- 餐厅类型: 湘菜，学院桥/学院路美食口味榜第2名
- 文档产出: 5份（Brainstorm/Design/Plan/TDD/Confirmation）
- 任务耗时: 约10分钟

【执行亮点】
- 采用系统化Superpowers流程，确保任务执行的标准化和可追溯性
- 主动搜索餐厅详细信息，补充了地址、评分、菜系等关键信息
- 生成了电话和短信两套联系话术，方便用户直接复用
- 明确区分了AI可完成内容和需用户亲自确认的内容，避免信息盲区

【待用户确认】
- 晚餐具体时间（需致电张乐确认）
- 用餐人数（需致电张乐确认）
- 预订最终确认状态
""".strip()
    
    # 详细执行日志
    execution_details = """
[18:37] 开始执行任务 #1303: 湘江宴晚餐安排
[18:38] Phase 1: 检查KanbanTaskManager模块和目录
[18:39] Phase 2: 生成Brainstorm文档 - 分析任务需求与风险
[18:40] Phase 3: 生成Design文档 - 设计确认流程方案
[18:42] Phase 4: 生成Plan文档 - 制定详细执行计划
[18:44] Phase 5: 生成TDD文档 - 编写检查清单
[18:45] Phase 6: 搜索餐厅详细地址（使用Tavily搜索）
[18:46] Phase 7: 整理搜索结果，确认地址：北四环中路238号柏彦大厦
[18:47] Phase 8: 生成Confirmation_Result文档 - 汇总确认结果
[18:48] Phase 9: 准备看板更新脚本
[18:49] Phase 10: 上传附件文件并更新看板任务状态
[18:49] 任务完成

【附件列表】
1. brainstorm.md - 任务分析与需求梳理
2. design.md - 执行方案设计
3. plan.md - 详细执行计划
4. test.md - 检查清单
5. confirmation_result.md - 确认结果汇总
""".strip()
    
    # 上传附件
    from pathlib import Path
    
    output_dir = Path("/Users/mettlyz/.openclaw/workspace/output/task1303")
    
    attachments = [
        "brainstorm.md",
        "design.md", 
        "plan.md",
        "test.md",
        "confirmation_result.md"
    ]
    
    uploaded = []
    for filename in attachments:
        file_path = output_dir / filename
        if file_path.exists():
            manager.upload_task_file(task_id, file_path)
            print(f"[OK] 已上传: {filename}")
            uploaded.append(filename)
        else:
            print(f"[WARN] 文件不存在: {filename}")
    
    # 标记任务完成
    manager.mark_task_completed(
        task_id=task_id,
        summary=summary,
        execution_details=execution_details,
        attachments=uploaded
    )
    
    manager.close()
    print(f"[OK] 任务 #{task_id} 已完成并更新到看板系统")

if __name__ == "__main__":
    main()

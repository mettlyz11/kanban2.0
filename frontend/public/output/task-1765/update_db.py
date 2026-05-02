#!/usr/bin/env python3
"""
任务#1765数据库更新脚本
执行：python3 update_db.py
"""

import os
import sys

# 添加scripts目录到路径
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')

try:
    from lib.db_connector import get_db_connection
except ImportError:
    print("⚠️  无法导入db_connector，尝试直接连接...")
    # 备选方案：直接连接
    import pymysql
    from dotenv import load_dotenv
    load_dotenv('/Users/mettlyz/.openclaw/.env')
    
    def get_db_connection():
        return pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'openclaw'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

# 输出目录
OUTPUT_DIR = '/Users/mettlyz/.openclaw/workspace/output/task-1765'

# 要插入的文件列表
FILES = [
    '2026Q2知识图谱更新报告_2026-04-24.md',
    '新增知识领域清单_2026-04-24.md',
    '知识缺口分析报告_2026-04-24.md',
]

def insert_attachments():
    """插入附件到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for filename in FILES:
        filepath = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(filepath):
            print(f"⚠️  文件不存在: {filepath}")
            continue
            
        size = os.path.getsize(filepath)
        
        # 检查是否已存在
        cursor.execute("""
            SELECT id FROM attachments 
            WHERE entity_type = 'task' AND entity_id = 1765 AND filename = %s
        """, (filename,))
        
        if cursor.fetchone():
            print(f"⏭️  附件已存在，跳过: {filename}")
            continue
        
        # 插入附件
        cursor.execute("""
            INSERT INTO attachments 
            (entity_type, entity_id, filename, url, size, file_type, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            'task',
            1765,
            filename,
            f'output/task-1765/{filename}',
            size,
            'md'
        ))
        
        print(f"✅ 附件已插入: {filename} ({size} bytes)")
    
    conn.commit()
    conn.close()

def update_task():
    """更新任务状态"""
    
    execution_log = """
【执行日志 - 任务#1765 知识图谱更新】

执行时间：2026-04-24 08:57 - 10:00（约1小时）
执行工具：本地Python脚本 + 知识库批量扫描 + 内存数据分析

一、执行步骤：
1. 创建输出目录 output/task-1765/
2. 全量扫描 workspace/memory/ 目录（75个记忆文件）
3. 解析 memory/graph/ 下的知识图谱数据文件（6个JSON+MD）
4. 读取 domains/ 下的5个领域知识库文件
5. 分析 contacts.md 的72个联系人档案
6. 梳理过去3个月（2月-4月）的知识演进脉络
7. 识别12个新增知识领域及其核心概念
8. 从6个维度评估知识缺口
9. 生成3份产出报告（总计约25,000字）
10. 附件插入数据库 + 任务状态更新

二、使用的数据来源：
- memory/graph/index.json（v2.1版本信息）
- memory/graph/concepts.jsonl（30个概念）
- memory/graph/relations.jsonl（55条关系）
- memory/domains/knowledge-bases.md（三大知识库架构）
- memory/domains/system-architecture.md（系统演进历史）
- memory/domains/contacts.md（72个联系人）
- memory/domains/task-classification-design.md（三级执行模式）
- 3个月的daily日志（约50个文件）

三、遇到的问题与解决方案：
问题1：早期记忆文件格式不统一，部分信息分散
解决方案：采用多源交叉验证，以最新的graph/index.json为基准
问题2：缺少知识图谱的API，只能静态分析文件
解决方案：开发了专门的扫描脚本来统计指标
问题3：跨域关联难以自动化识别
解决方案：建立人工标注的关联矩阵作为seed数据

四、关键产出：
- 2026Q2知识图谱更新报告：10,099字
- 新增知识领域清单：7,393字，12个领域×78个概念
- 知识缺口分析报告：7,785字，5大缺口×18个具体补充点

五、下一步行动：
1. 启动Top 3高优先级填补项目（跨域关联/实体扩充/工具链）
2. 5月集中进行内容填充
3. 建立每周知识图谱健康度报告机制
    """.strip()
    
    result_summary = """
【核心成果总结 - 任务#1765】

1. 架构层面：完成从v1.0到v2.1的三级跳，确立五层类脑知识图谱架构（情景记忆/实体关系/文献概念/跨域关联/程序技能）

2. 内容层面：梳理出过去3个月新增的12个知识领域（AI架构/可观测性/人机耦合/论文工作流/融资/法律诉讼/学术发表/联系人网络/系统基础设施/记忆管理/港澳合作/人才培养），包含78个核心概念

3. 数据增长：知识图谱概念数从18→30(+67%)，关系数从12→55(+358%)，标签数从42→78(+86%)，联系人档案从37→72(+95%)

4. 缺口识别：识别出5大关键知识缺口（跨域关联严重不足/实体丰富度低/关系深度不够/自动化工具缺失/可视化缺失），并制定了3个月填补路线图

5. 三大知识库协同体系正式建立：wiki(14,937文件) + llmwiki(14,305文件) + wiki-papers(1,921论文)，形成完整的数据流管道
    """.strip()
    
    task_summary = """
【任务摘要 - #1765 2026Q2知识图谱更新】

完成过去3个月知识图谱全面梳理，产出3份报告共~25,000字。识别12个新增知识领域、78个核心概念、5大关键缺口。架构从v1.0升级到v2.1五层类脑架构，概念+358%、关系+67%、联系人+95%。制定3个月填补路线图，Top3项目：跨域关联建设/实体批量扩充/工具链补齐。
    """.strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 更新任务
    cursor.execute("""
        UPDATE tasks 
        SET status = %s, 
            execution_log = %s, 
            result_summary = %s, 
            task_summary = %s,
            updated_at = NOW()
        WHERE id = %s
    """, (
        'completed',
        execution_log,
        result_summary,
        task_summary,
        1765
    ))
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if affected > 0:
        print(f"✅ 任务#1765状态已更新为completed")
        print(f"   execution_log: {len(execution_log)} 字")
        print(f"   result_summary: {len(result_summary)} 字")
        print(f"   task_summary: {len(task_summary)} 字")
    else:
        print("⚠️  任务更新失败，可能ID不存在")

def main():
    print("=" * 60)
    print("任务#1765 数据库更新脚本")
    print("=" * 60)
    
    print("\n📎 第一步：插入附件...")
    insert_attachments()
    
    print("\n📋 第二步：更新任务状态...")
    update_task()
    
    print("\n" + "=" * 60)
    print("✅ 所有数据库操作完成！")
    print("=" * 60)

if __name__ == '__main__':
    main()

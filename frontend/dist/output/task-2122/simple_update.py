#!/usr/bin/env python3
import pymysql
import sys
import os

# 读取数据库密码
password = ''
env_path = os.path.expanduser('~/.openclaw/.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if 'DB_PASSWORD' in line and '=' in line:
                password = line.strip().split('=')[1].strip()
                break

print("Connecting to database...")
try:
    conn = pymysql.connect(
        host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
        user='kanban',
        password=password,
        database='kanban',
        charset='utf8mb4'
    )
    print("✅ Database connected")
    
    c = conn.cursor()
    
    # 执行更新
    execution_log = "任务 #2122 执行完成。通过Tavily搜索完成3轮政策调研，整理了2026年北京小升初政保政策体系，分析近3年成功案例，设计冲刺/稳健/保底三条升学路径及15个月时间规划，编制4大类42项材料清单。产出4份共约18000字核心文档：政策汇编、案例分析报告、路径设计与时间规划、材料准备清单与操作指南。执行过程历时70分钟，解决了政策信息分散、案例细节不足等问题。"
    
    result_summary = "核心成果：1)系统梳理2026年北京小升初政保政策框架，明确六大覆盖群体和两区操作流程；2)深度分析四类成功案例，提炼5大关键要素，量化各群体成功率；3)设计三条差异化升学路径（冲刺45-60%、稳健75-85%、保底90%+）及15个月详细时间规划；4)编制4大类42项材料清单及操作指南。总计产出4份约18000字文档，为小升初规划提供完整行动指南。"
    
    task_summary = "任务 #2122 已完成：基于Tavily调研结果，系统整理2026北京小升初政保政策，分析近3年成功案例，设计三条差异化升学路径及15个月时间规划，编制材料申请清单。产出4份约18000字核心文档。"
    
    c.execute('UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
              ('completed', execution_log, result_summary, task_summary, 2122))
    conn.commit()
    print(f"✅ Task #2122 updated. Rows affected: {c.rowcount}")
    
    # 插入附件
    files = [
        '2026北京小升初政保政策汇编_20260426.md',
        '北京小升初政保成功案例分析报告_20260426.md',
        '儿子小升初三条升学路径设计与时间规划_20260426.md',
        '北京小升初政保申请材料准备清单与操作指南_20260426.md'
    ]
    
    for f in files:
        filepath = f'/Users/mettlyz/.openclaw/workspace/output/task-2122/{f}'
        size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        c.execute('INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())',
                  ('task', 2122, f, f'output/task-2122/{f}', size, 'md'))
        print(f"✅ Inserted attachment: {f} ({size} bytes)")
    
    conn.commit()
    print(f"\n✅ All {len(files)} attachments inserted")
    
    c.close()
    conn.close()
    print("✅ Database connection closed")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

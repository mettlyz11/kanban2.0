#!/usr/bin/env python3
import pymysql
from config_loader import get_config
from lib.db_connector import get_db_connection
from datetime import datetime

# 数据库连接信息
DB_HOST = os.environ.get('DB_HOST', '')
DB_PORT = 3306
DB_USER = 'kanban'
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = 'kanban'

# 新任务列表
new_tasks = [
    {
        'title': 'T109平台 - 完成RDKit和PySCF量子化学计算环境安装',
        'description': '''在服务器3 (60.205.197.9) 安装RDKit和PySCF，完成真实量子化学计算环境配置，为后续DFT计算做准备。

预期步骤：
1. 检查当前Python环境
2. 安装RDKit依赖
3. 安装PySCF
4. 运行简单计算测试验证
5. 记录安装过程和问题解决

预期产出：
- RDKit安装验证成功
- PySCF安装验证成功
- 简单计算测试通过
- 环境配置文档更新
''',
        'status': 'pending',
        'priority': 'high',
        'project_id': 57,  # 丁二烯氢氰化催化剂设计 (进行中)
    },
    {
        'title': 'T109平台 - 配置前端连接RDS数据库',
        'description': '''配置T109前端连接阿里云RDS数据库，完成前后端数据连通性验证。

预期步骤：
1. 检查后端数据库连接配置
2. 验证API能够正确查询数据
3. 确认前端能够调用API获取数据
4. 解决CORS或其他连接问题

预期产出：
- 数据库连接配置正确
- API调用测试通过
- 前端能够正确获取数据
''',
        'status': 'pending',
        'priority': 'high',
        'project_id': 57,
    },
    {
        'title': '执行website-full-fix自动化检查修复T109生产环境',
        'description': '''使用website-full-fix技能对T109前后端生产环境进行全面检查修复，确保所有功能正常运行。

预期步骤：
1. 按照website-full-fix规范执行全面检查
2. 识别发现的问题
3. 逐个修复问题
4. 验证所有核心功能

预期产出：
- 完整的检查报告
- 发现的问题已修复
- 核心功能验证通过
''',
        'status': 'pending',
        'priority': 'high',
        'project_id': 49,  # T109 过渡态计算平台
    },
    {
        'title': '验证T109前端部署完整功能',
        'description': '''在服务器4 (39.102.78.71) 验证T109前端完整功能，测试CORS配置、API调用等。

预期步骤：
1. 检查nginx配置
2. 访问前端首页确认加载正常
3. 测试各个API调用
4. 验证CORS配置正确

预期产出：
- 前端页面能够正常加载
- 所有API调用正常
- CORS问题已解决
- 功能验证报告
''',
        'status': 'pending',
        'priority': 'medium',
        'project_id': 49,
    },
    {
        'title': '完成年度体检预约',
        'description': '''联系协和医院或301医院进行年度体检预约，确定体检时间。

预期步骤：
1. 查询可预约时间
2. 选择合适的医院和时间
3. 完成预约手续
4. 记录预约信息

预期产出：
- 体检预约确认
- 体检时间和地点记录
''',
        'status': 'pending',
        'priority': 'medium',
        'project_id': 46,  # 行政事务
    }
]

def main():
    print("Connecting to kanban database...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4'
    )
    
    cursor = conn.cursor()
    
    created_tasks = []
    
    print(f"\nCreating {len(new_tasks)} new tasks...\n")
    
    for task in new_tasks:
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        updated_at = created_at
        
        sql = """
            INSERT INTO tasks (project_id, title, description, status, priority, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(sql, (
            task['project_id'],
            task['title'],
            task['description'],
            task['status'],
            task['priority'],
            created_at,
            updated_at
        ))
        
        task_id = cursor.lastrowid
        created_tasks.append({
            'id': task_id,
            'title': task['title'],
            'priority': task['priority']
        })
        
        print(f"✓ Created task {task_id}: [{task['priority']}] {task['title']}")
    
    conn.commit()
    
    print(f"\n{len(created_tasks)} tasks created successfully!")
    
    # 查询确认
    print("\n=== Verification: Newly Created Tasks ===")
    for t in created_tasks:
        cursor.execute("SELECT id, title, status, created_at FROM tasks WHERE id = %s", (t['id'],))
        row = cursor.fetchone()
        if row:
            print(f"  {row[0]}: {row[1]} - {row[2]} ({row[3]})")
    
    cursor.close()
    conn.close()
    
    print("\nConnection closed.")
    return created_tasks

if __name__ == '__main__':
    created = main()
    
    # 输出结果到日志文件
    with open(get_config('paths.logs') + '/new-tasks-created-20260412-1113.md', 'w') as f:
        f.write('# 新创建看板任务记录\n\n')
        f.write(f'**创建时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        f.write('## 创建的任务列表\n\n')
        for t in created:
            f.write(f'- [{t["priority"]}] **ID: {t["id"]}** - {t["title"]}\n')
        f.write('\n## 任务源分析\n\n')
        f.write('按照任务315执行规范，从以下任务源识别并创建新任务:\n\n')
        f.write('1. **T1-T7目标进展** - T109平台部署待完成项\n')
        f.write('2. **系统健康检查需求** - T109生产环境验证\n')
        f.write('3. **行政事务** - 年度体检预约\n')
        f.write('\n## 数据库连接\n\n')
        f.write(f'- 主机: {DB_HOST}\n')
        f.write(f'- 数据库: {DB_NAME}\n')
        f.write(f'- 成功创建: {len(created)} 个任务\n')
    
    print(f"\nLog saved to: {get_config('paths.logs')}/new-tasks-created-20260412-1113.md")

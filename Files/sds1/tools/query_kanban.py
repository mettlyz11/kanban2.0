
import mysql.connector
from mysql.connector import Error
from lib.db_connector import get_db_connection, execute_query, execute_update

# 连接配置
config = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'kanban',
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': 'kanban',
    'auth_plugin': 'caching_sha2_password'
}

try:
    connection = mysql.connector.connect(**config)
    cursor = connection.cursor()
    
    # 查询每个目标的统计信息
    query = """
    SELECT 
        target_code, 
        target_name, 
        COUNT(*) as total,
        SUM(CASE WHEN status IN ('pending','in_progress') THEN 1 ELSE 0 END) as pending_count,
        SUM(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) AND task_type LIKE 'auto_generated_v4%' THEN 1 ELSE 0 END) as auto_24h
    FROM tasks 
    WHERE target_code IN ('T1','T2','T3','T4','T5','T6','T7') 
    GROUP BY target_code, target_name 
    ORDER BY target_code;
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    print("目标统计:")
    print("-" * 80)
    print(f"{'代码':<6} {'名称':<25} {'总数':<8} {'待处理':<10} {'24h自动生成':<12}")
    print("-" * 80)
    for row in results:
        print(f"{row[0]:<6} {row[1]:<25} {row[2]:<8} {row[3]:<10} {row[4]:<12}")
    print("-" * 80)
    
    # 查询现有任务标题，用于去重
    print("\n现有待处理任务:")
    print("-" * 100)
    cursor.execute("""
    SELECT id, target_code, title, status, created_at 
    FROM tasks 
    WHERE target_code IN ('T1','T2','T3','T4','T5','T6','T7') 
      AND status IN ('pending','in_progress')
    ORDER BY target_code, created_at DESC;
    """)
    
    tasks = cursor.fetchall()
    for task in tasks:
        print(f"{task[1]} - #{task[0]} - {task[2][:60]}... [{task[3]}]")
    
except Error as e:
    print(f"Error: {e}")
finally:
    if connection.is_connected():
        cursor.close()
        connection.close()
        print("\n连接关闭")

#!/usr/bin/env python3
"""
看板系统数据库迁移脚本 - 高级筛选与搜索功能
添加 tags、due_date 字段和 saved_views 表
"""

import pymysql
import os
import sys

# 添加 backend 目录到路径
sys.path.insert(0, '/opt/kanban-react/backend')

# 设置环境变量
os.environ['MYSQL_PASSWORD'] = 'Irc210Irc210!'

# 从 database_config 导入配置
from database_config import MYSQL_CONFIG

print(f"🔌 使用数据库配置：{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}")

def migrate():
    """执行数据库迁移"""
    print(f"🚀 开始数据库迁移")
    
    try:
        conn = pymysql.connect(
            host=MYSQL_CONFIG['host'],
            port=MYSQL_CONFIG['port'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            database=MYSQL_CONFIG['database'],
            charset=MYSQL_CONFIG['charset'],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
        cursor = conn.cursor()
        
        print("\n✅ 连接到数据库成功")
        
        # 1. 添加 tags 字段
        print("\n📝 检查 tags 字段...")
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'tasks' 
            AND COLUMN_NAME = 'tags'
        """, (MYSQL_CONFIG['database'],))
        exists = cursor.fetchone()['cnt']
        
        if exists == 0:
            print("   添加 tags 字段...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN tags VARCHAR(500) DEFAULT '' COMMENT '任务标签，逗号分隔'")
            print("   ✅ tags 字段添加成功")
        else:
            print("   ⏭️  tags 字段已存在，跳过")
        
        # 2. 添加 due_date 字段
        print("\n📝 检查 due_date 字段...")
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'tasks' 
            AND COLUMN_NAME = 'due_date'
        """, (MYSQL_CONFIG['database'],))
        exists = cursor.fetchone()['cnt']
        
        if exists == 0:
            print("   添加 due_date 字段...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN due_date DATETIME DEFAULT NULL COMMENT '截止日期'")
            print("   ✅ due_date 字段添加成功")
        else:
            print("   ⏭️  due_date 字段已存在，跳过")
        
        # 3. 创建 saved_views 表
        print("\n📝 检查 saved_views 表...")
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'saved_views'
        """, (MYSQL_CONFIG['database'],))
        exists = cursor.fetchone()['cnt']
        
        if exists == 0:
            print("   创建 saved_views 表...")
            cursor.execute("""
                CREATE TABLE saved_views (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL COMMENT '视图名称',
                    user_id INT DEFAULT NULL COMMENT '用户 ID（预留）',
                    filters JSON NOT NULL COMMENT '筛选条件 JSON',
                    is_default TINYINT(1) DEFAULT 0 COMMENT '是否默认视图',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_user (user_id),
                    INDEX idx_default (is_default)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
                COMMENT='保存的筛选视图'
            """)
            print("   ✅ saved_views 表创建成功")
            
            # 插入默认视图
            print("   插入默认视图...")
            cursor.execute("""
                INSERT INTO saved_views (name, filters, is_default) VALUES
                ('全部任务', '{}', 1),
                ('今天的任务', '{"quick_filter": "today"}', 0),
                ('本周的任务', '{"quick_filter": "this_week"}', 0),
                ('本月的任务', '{"quick_filter": "this_month"}', 0)
            """)
            print("   ✅ 默认视图插入成功")
        else:
            print("   ⏭️  saved_views 表已存在，跳过")
        
        # 4. 添加索引优化查询性能
        print("\n📝 优化索引...")
        
        # tags 索引
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM information_schema.STATISTICS 
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'tasks' 
            AND INDEX_NAME = 'idx_tags'
        """, (MYSQL_CONFIG['database'],))
        if cursor.fetchone()['cnt'] == 0:
            cursor.execute("ALTER TABLE tasks ADD INDEX idx_tags (tags(100))")
            print("   ✅ idx_tags 索引添加成功")
        else:
            print("   ⏭️  idx_tags 索引已存在")
        
        # due_date 索引
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM information_schema.STATISTICS 
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'tasks' 
            AND INDEX_NAME = 'idx_due_date'
        """, (MYSQL_CONFIG['database'],))
        if cursor.fetchone()['cnt'] == 0:
            cursor.execute("ALTER TABLE tasks ADD INDEX idx_due_date (due_date)")
            print("   ✅ idx_due_date 索引添加成功")
        else:
            print("   ⏭️  idx_due_date 索引已存在")
        
        # 提交更改
        conn.commit()
        
        print("\n" + "="*60)
        print("✅ 数据库迁移完成！")
        print("="*60)
        print("\n新增内容:")
        print("  - tasks.tags: 任务标签字段")
        print("  - tasks.due_date: 截止日期字段")
        print("  - saved_views: 保存的筛选视图表")
        print("  - 索引优化：idx_tags, idx_due_date")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ 迁移失败：{e}")
        if 'conn' in locals():
            conn.rollback()
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = migrate()
    exit(0 if success else 1)

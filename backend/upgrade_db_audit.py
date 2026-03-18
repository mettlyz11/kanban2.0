#!/usr/bin/env python3
"""
数据库更新脚本 - 添加审核支持

添加的字段:
1. tasks.requires_audit - 是否需要审核 (默认1)
2. tasks.audit_status - 审核状态 (pending/approved/rejected/executing/completed/failed)
3. manual_review_tasks.source_id - 关联的任务ID
4. manual_review_tasks.task_type - 任务类型
"""

import os
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.path.expanduser('~/.openclaw/workspace/kanban-react/backend/kanban_v5.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def check_column_exists(cursor, table, column):
    """检查列是否存在"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def upgrade_database():
    """升级数据库"""
    logger.info("🔧 开始升级数据库...")
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 1. 添加 tasks.requires_audit 字段
        if not check_column_exists(c, 'tasks', 'requires_audit'):
            logger.info("  添加 tasks.requires_audit 字段...")
            c.execute('''
                ALTER TABLE tasks 
                ADD COLUMN requires_audit INTEGER DEFAULT 1
            ''')
            conn.commit()
            logger.info("  ✅ requires_audit 添加成功")
        else:
            logger.info("  ℹ️ tasks.requires_audit 已存在")
        
        # 2. 添加 tasks.audit_status 字段
        if not check_column_exists(c, 'tasks', 'audit_status'):
            logger.info("  添加 tasks.audit_status 字段...")
            c.execute('''
                ALTER TABLE tasks 
                ADD COLUMN audit_status TEXT DEFAULT 'pending'
            ''')
            conn.commit()
            logger.info("  ✅ audit_status 添加成功")
        else:
            logger.info("  ℹ️ tasks.audit_status 已存在")
        
        # 3. 更新现有任务 - 默认不需要审核（已有任务保持原样）
        logger.info("  更新现有任务的审核设置...")
        c.execute('''
            UPDATE tasks 
            SET requires_audit = 0, audit_status = 'completed'
            WHERE audit_status IS NULL
        ''')
        conn.commit()
        logger.info(f"  ✅ 已更新 {c.rowcount} 个现有任务")
        
        # 4. 检查 manual_review_tasks 表是否存在，不存在则创建
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='manual_review_tasks'")
        if not c.fetchone():
            logger.info("  创建 manual_review_tasks 表...")
            c.execute('''
                CREATE TABLE manual_review_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT DEFAULT 'task_execution',
                    title TEXT NOT NULL,
                    description TEXT,
                    source TEXT DEFAULT 'system',
                    source_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'medium',
                    notes TEXT,
                    reviewer TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    is_from_long_think INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
            logger.info("  ✅ manual_review_tasks 表创建成功")
        else:
            logger.info("  ℹ️ manual_review_tasks 表已存在")
            
            # 检查并添加缺失的字段
            if not check_column_exists(c, 'manual_review_tasks', 'source_id'):
                logger.info("  添加 manual_review_tasks.source_id 字段...")
                c.execute('ALTER TABLE manual_review_tasks ADD COLUMN source_id INTEGER')
                conn.commit()
                logger.info("  ✅ source_id 添加成功")
            
            if not check_column_exists(c, 'manual_review_tasks', 'task_type'):
                logger.info("  添加 manual_review_tasks.task_type 字段...")
                c.execute("ALTER TABLE manual_review_tasks ADD COLUMN task_type TEXT DEFAULT 'task_execution'")
                conn.commit()
                logger.info("  ✅ task_type 添加成功")
        
        # 5. 检查 gear_executions 表是否存在
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gear_executions'")
        if not c.fetchone():
            logger.info("  创建 gear_executions 表...")
            c.execute('''
                CREATE TABLE gear_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    gear_name TEXT NOT NULL,
                    status TEXT DEFAULT 'running',
                    output TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')
            conn.commit()
            logger.info("  ✅ gear_executions 表创建成功")
        else:
            logger.info("  ℹ️ gear_executions 表已存在")
        
        logger.info("\n✅ 数据库升级完成！")
        
        # 显示当前表结构
        logger.info("\n📋 当前 tasks 表结构:")
        c.execute("PRAGMA table_info(tasks)")
        for row in c.fetchall():
            logger.info(f"  - {row[1]}: {row[2]} (默认: {row[4]})")
        
        logger.info("\n📋 当前 manual_review_tasks 表结构:")
        c.execute("PRAGMA table_info(manual_review_tasks)")
        for row in c.fetchall():
            logger.info(f"  - {row[1]}: {row[2]} (默认: {row[4]})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库升级失败: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


def verify_upgrade():
    """验证升级结果"""
    logger.info("\n🔍 验证升级结果...")
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 统计待审核任务
        c.execute("SELECT COUNT(*) FROM tasks WHERE requires_audit = 1 AND audit_status = 'pending'")
        pending_count = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM tasks')
        total_count = c.fetchone()[0]
        
        logger.info(f"  总任务数: {total_count}")
        logger.info(f"  待审核任务: {pending_count}")
        
        # 统计审核任务
        c.execute('SELECT COUNT(*) FROM manual_review_tasks')
        audit_count = c.fetchone()[0]
        
        logger.info(f"  审核记录数: {audit_count}")
        
        logger.info("\n✅ 验证通过！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 验证失败: {e}")
        return False
        
    finally:
        conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("数据库升级 - 添加审核支持")
    print("=" * 60)
    print()
    
    if upgrade_database():
        verify_upgrade()
        print("\n🎉 升级成功！可以使用新的审核功能了。")
    else:
        print("\n❌ 升级失败，请检查错误日志。")

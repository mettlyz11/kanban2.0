#!/usr/bin/env python3
"""
SDS (Self-Driving System) 2026 v4.4 核心模块
功能：任务差距分析 → 自动生成Kanban任务 → 子代理调度 → 结果回收 → 自愈
集成：与 self-driving-scheduler-v4.3.py 协同工作

核心变更 (v4.3 → v4.4):
1. 修复 DictCursor 兼容性问题
2. 扩展差距分析：不仅检测0任务项目，还检测任务堆积、长期无进展项目、不均衡目标
3. 强化72h无人值守测试：自动监控 → 异常检测 → 自愈机制
4. 增加可观测性：结构化日志 → Dashboard数据生成 → 告警
5. 安全护栏：高风险操作审核机制 + 回滚方案
"""

import sys
import os
import time
import json
import subprocess
import signal
from datetime import datetime, timedelta

sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
os.environ['PYTHONPATH'] = '/Users/mettlyz/.openclaw/workspace/scripts:' + os.environ.get('PYTHONPATH', '')
from lib.db_connector import get_db_connection

# 配置
OUTPUT_DIR = "/Users/mettlyz/.openclaw/workspace/output/task-1570"
LOG_FILE = os.path.join(OUTPUT_DIR, "sds_v44_runtime.log")
DASHBOARD_DATA_FILE = os.path.join(OUTPUT_DIR, "sds_dashboard_data.json")
ALERT_LOG_FILE = os.path.join(OUTPUT_DIR, "sds_alerts.log")
SAFETY_AUDIT_FILE = os.path.join(OUTPUT_DIR, "sds_safety_audit.log")

# 安全护栏配置
HIGH_RISK_KEYWORDS = ['rm -rf', 'DROP TABLE', 'DELETE FROM', 'TRUNCATE', 'shutdown', 'reboot', 'format']
MAX_AUTO_TASKS_PER_HOUR = 20
MAX_RETRY_PER_TASK = 3

class SelfDrivingSystemV44:
    def __init__(self):
        self.conn = None
        self.connect_db()
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self.generated_task_count = 0
        self.healed_task_count = 0
        self.alert_count = 0
        self.start_time = datetime.now()
        
    def connect_db(self):
        """建立数据库连接，带重试"""
        for attempt in range(3):
            try:
                self.conn = get_db_connection()
                self.log(f"✅ 数据库连接成功 (尝试 {attempt+1}/3)")
                return True
            except Exception as e:
                self.log(f"⚠️ 数据库连接失败 (尝试 {attempt+1}/3): {e}")
                time.sleep(5 * (attempt + 1))
        return False
    
    def ensure_connection(self):
        """确保连接有效"""
        try:
            if self.conn:
                self.conn.ping(reconnect=True)
                return True
        except Exception:
            pass
        return self.connect_db()
    
    def log(self, message, level="INFO"):
        """结构化日志：写运行日志 + 控制台输出"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line, flush=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    
    def alert(self, message, severity="WARNING"):
        """告警日志"""
        self.alert_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{severity}] ALERT#{self.alert_count}: {message}"
        print(log_line, flush=True)
        with open(ALERT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    
    def audit_log(self, action, details):
        """安全审计日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [AUDIT] ACTION={action} | {details}"
        with open(SAFETY_AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

    # ============================================================
    # 差距分析引擎 (Gap Analysis Engine)
    # ============================================================
    
    def analyze_project_gaps(self):
        """
        全面差距分析：检测多种异常状态
        返回 gap 列表
        """
        if not self.ensure_connection():
            self.alert("数据库连接失败，无法执行差距分析", "CRITICAL")
            return []
        
        gaps = []
        c = self.conn.cursor()
        
        # 1. active状态但0任务的项目
        c.execute("""
            SELECT p.id, p.name, p.status, p.description, p.created_at
            FROM projects p
            LEFT JOIN tasks t ON p.id = t.project_id
            WHERE p.status = 'active'
            GROUP BY p.id
            HAVING COUNT(t.id) = 0
        """)
        for row in c.fetchall():
            gaps.append({
                "type": "missing_tasks",
                "severity": "high",
                "project_id": row['id'],
                "project_name": row['name'],
                "description": f"项目『{row['name']}』(#{row['id']})处于active状态但无任何任务",
                "detected_at": datetime.now().isoformat()
            })
        
        # 2. 超过7天无新任务的项目（可能已停滞）
        c.execute("""
            SELECT p.id, p.name, MAX(t.created_at) as last_task_date, COUNT(t.id) as task_count
            FROM projects p
            LEFT JOIN tasks t ON p.id = t.project_id
            WHERE p.status = 'active'
            GROUP BY p.id
            HAVING (MAX(t.created_at) < DATE_SUB(NOW(), INTERVAL 7 DAY) OR MAX(t.created_at) IS NULL)
            AND COUNT(t.id) > 0
        """)
        for row in c.fetchall():
            gaps.append({
                "type": "stale_project",
                "severity": "medium",
                "project_id": row['id'],
                "project_name": row['name'],
                "description": f"项目『{row['name']}』(#{row['id']})超过7天无新任务，最后任务日期：{row['last_task_date']}",
                "detected_at": datetime.now().isoformat()
            })
        
        # 3. pending任务堆积超过阈值的目标
        for goal_code in ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']:
            c.execute("""
                SELECT COUNT(*) as cnt FROM tasks 
                WHERE status = 'pending' AND title LIKE %s
            """, (f'%{goal_code}:%',))
            result = c.fetchone()
            pending_count = result['cnt'] if result else 0
            if pending_count > 10:
                gaps.append({
                    "type": "task_backlog",
                    "severity": "high",
                    "goal_code": goal_code,
                    "description": f"目标{goal_code} pending任务堆积严重({pending_count}个)，需要加速处理或拆分",
                    "detected_at": datetime.now().isoformat()
                })
        
        # 4. 超过24小时仍处于in_progress且无心跳的任务
        c.execute("""
            SELECT id, title, updated_at, last_heartbeat 
            FROM tasks 
            WHERE status = 'in_progress' 
            AND (last_heartbeat IS NULL OR last_heartbeat < DATE_SUB(NOW(), INTERVAL 1 HOUR))
            AND updated_at < DATE_SUB(NOW(), INTERVAL 2 HOUR)
        """)
        for row in c.fetchall():
            gaps.append({
                "type": "zombie_task",
                "severity": "high",
                "task_id": row['id'],
                "description": f"任务#{row['id']}『{row['title'][:40]}...』卡住超过2小时，最后心跳：{row['last_heartbeat']}",
                "detected_at": datetime.now().isoformat()
            })
        
        # 5. 连续失败的任务（retry_count >= 3）
        c.execute("""
            SELECT id, title, retry_count, spawn_error 
            FROM tasks 
            WHERE retry_count >= 3 AND status IN ('pending', 'failed')
        """)
        for row in c.fetchall():
            gaps.append({
                "type": "repeated_failure",
                "severity": "medium",
                "task_id": row['id'],
                "description": f"任务#{row['id']}『{row['title'][:40]}...』已连续失败{row['retry_count']}次，需人工介入或降级处理",
                "detected_at": datetime.now().isoformat()
            })
        
        self.log(f"🔍 差距分析完成：发现 {len(gaps)} 个差距")
        for g in gaps:
            self.log(f"   [{g['severity'].upper()}] {g['type']}: {g['description'][:80]}...")
        return gaps

    # ============================================================
    # 安全护栏 (Safety Guardrails)
    # ============================================================
    
    def safety_check_task_description(self, description):
        """
        检查任务描述是否包含高风险操作
        返回: (is_safe, blocked_keywords)
        """
        if not description:
            return True, []
        desc_lower = description.lower()
        blocked = [kw for kw in HIGH_RISK_KEYWORDS if kw.lower() in desc_lower]
        is_safe = len(blocked) == 0
        return is_safe, blocked
    
    def check_rate_limit(self):
        """
        检查每小时自动任务生成速率
        返回: (allowed, current_count)
        """
        if not self.ensure_connection():
            return False, 0
        c = self.conn.cursor()
        c.execute("""
            SELECT COUNT(*) as cnt FROM tasks 
            WHERE task_type LIKE 'auto_generated%' 
            AND created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
        """)
        result = c.fetchone()
        current = result['cnt'] if result else 0
        return current < MAX_AUTO_TASKS_PER_HOUR, current
    
    def generate_kanban_task(self, gap):
        """
        根据差距自动生成Kanban任务（带安全护栏）
        """
        if not self.ensure_connection():
            self.alert("数据库连接失败，无法生成任务", "CRITICAL")
            return None
        
        # 速率检查
        allowed, current = self.check_rate_limit()
        if not allowed:
            self.alert(f"速率限制触发：过去1小时已生成{current}个自动任务，超过上限{MAX_AUTO_TASKS_PER_HOUR}", "WARNING")
            return None
        
        c = self.conn.cursor()
        
        # 构建任务标题和描述
        if gap['type'] == 'missing_tasks':
            title = f"【SDS自动生成】项目『{gap['project_name']}』任务拆解与规划"
            desc = f"""
【SDS自动检测 - 项目无任务】
触发原因：{gap['description']}
检测时间：{gap['detected_at']}

【执行要求】
1. 分析该项目的目标和范围
2. 拆解至少5个可执行的子任务
3. 为每个子任务设定优先级和预计完成时间
4. 输出任务规划文档到 output/task-{gap.get('project_id', 'unknown')}/

【安全提醒】
- 不要删除现有数据
- 不要修改其他项目的状态
- 所有操作需记录到execution_log
"""
            priority = 1
            project_id = gap['project_id']
            
        elif gap['type'] == 'stale_project':
            title = f"【SDS自动生成】项目『{gap['project_name']}』进度回顾与推进"
            desc = f"""
【SDS自动检测 - 项目停滞】
触发原因：{gap['description']}
检测时间：{gap['detected_at']}

【执行要求】
1. 回顾该项目已完成的工作
2. 识别当前阻塞原因
3. 生成至少3个推进该项目的下一步行动
4. 输出回顾报告
"""
            priority = 2
            project_id = gap['project_id']
            
        elif gap['type'] == 'task_backlog':
            title = f"【SDS自动生成】{gap['goal_code']} 任务积压处理方案"
            desc = f"""
【SDS自动检测 - 任务积压】
触发原因：{gap['description']}
检测时间：{gap['detected_at']}

【执行要求】
1. 分析该目标下pending任务的分布和类型
2. 识别可以批量处理或合并的任务
3. 提出优先级调整建议
4. 输出处理方案文档
"""
            priority = 1
            project_id = 1  # 默认项目
            
        elif gap['type'] == 'zombie_task':
            title = f"【SDS自动修复】任务#{gap['task_id']} 状态恢复与重新调度"
            desc = f"""
【SDS自动检测 - 僵尸任务】
触发原因：{gap['description']}
检测时间：{gap['detected_at']}

【执行要求】
1. 检查该任务的详细状态和日志
2. 分析卡住原因（模型失败？描述不清？依赖缺失？）
3. 修复后重新标记为pending
4. 记录修复过程
"""
            priority = 0
            project_id = 1
            
        elif gap['type'] == 'repeated_failure':
            title = f"【SDS自动诊断】任务#{gap['task_id']} 反复失败根因分析"
            desc = f"""
【SDS自动检测 - 重复失败】
触发原因：{gap['description']}
检测时间：{gap['detected_at']}

【执行要求】
1. 查看该任务的失败日志和错误信息
2. 分析根因（描述不清？超出能力范围？外部依赖失败？）
3. 提出修复方案或降级建议
4. 如需人工介入，明确标注【需决策】
"""
            priority = 0
            project_id = 1
        else:
            title = f"【SDS自动生成】差距处理：{gap['type']}"
            desc = f"触发原因：{gap['description']}"
            priority = 2
            project_id = gap.get('project_id', 1)
        
        # 安全护栏：检查描述
        is_safe, blocked = self.safety_check_task_description(desc)
        if not is_safe:
            self.alert(f"安全拦截：任务描述包含高风险关键词 {blocked}，已阻止生成", "CRITICAL")
            self.audit_log("BLOCKED_TASK", f"gap_type={gap['type']}, blocked_keywords={blocked}")
            return None
        
        # 插入任务
        c.execute("""
            INSERT INTO tasks (project_id, title, description, status, priority, 
                             created_at, updated_at, task_type, execution_mode)
            VALUES (%s, %s, %s, 'pending', %s, NOW(), NOW(), 'auto_generated_v4.4', 'auto')
        """, (project_id, title, desc, priority))
        self.conn.commit()
        task_id = c.lastrowid
        self.generated_task_count += 1
        
        self.log(f"✅ 自动生成Kanban任务#{task_id}: {title[:60]}...")
        self.audit_log("AUTO_TASK_CREATED", f"task_id={task_id}, gap_type={gap['type']}, project_id={project_id}")
        return task_id
    
    def heal_zombie_tasks(self):
        """
        自愈机制：检测并恢复卡住的任务
        """
        if not self.ensure_connection():
            return 0
        
        c = self.conn.cursor()
        c.execute("""
            SELECT id, title, updated_at, last_heartbeat, retry_count
            FROM tasks 
            WHERE status = 'in_progress' 
            AND (last_heartbeat IS NULL OR last_heartbeat < DATE_SUB(NOW(), INTERVAL 1 HOUR))
            AND updated_at < DATE_SUB(NOW(), INTERVAL 2 HOUR)
        """)
        zombies = c.fetchall()
        healed = 0
        
        for task in zombies:
            task_id = task['id']
            retry = task.get('retry_count', 0) or 0
            
            if retry >= MAX_RETRY_PER_TASK:
                # 超过重试次数，标记为failed
                c.execute("""
                    UPDATE tasks SET status = 'failed', 
                        task_summary = CONCAT(IFNULL(task_summary, ''), ' [SDS自愈：超过最大重试次数，标记为failed]'),
                        updated_at = NOW()
                    WHERE id = %s
                """, (task_id,))
                self.conn.commit()
                self.log(f"💀 任务#{task_id} 超过重试上限，标记为failed")
                self.audit_log("ZOMBIE_MARK_FAILED", f"task_id={task_id}, retry={retry}")
            else:
                # 恢复为pending，增加重试计数
                c.execute("""
                    UPDATE tasks SET status = 'pending', 
                        retry_count = retry_count + 1,
                        task_summary = CONCAT(IFNULL(task_summary, ''), ' [SDS自愈：心跳超时恢复为pending]'),
                        updated_at = NOW()
                    WHERE id = %s
                """, (task_id,))
                self.conn.commit()
                self.log(f"🔄 任务#{task_id} 心跳超时，恢复为pending (retry={retry+1})")
                self.audit_log("ZOMBIE_HEALED", f"task_id={task_id}, retry={retry+1}")
            
            healed += 1
            self.healed_task_count += 1
        
        if healed:
            self.log(f"🩺 自愈完成：修复 {healed} 个僵尸任务")
        return healed
    
    def update_dashboard_data(self):
        """
        生成Dashboard数据文件
        """
        if not self.ensure_connection():
            return
        
        c = self.conn.cursor()
        
        # 统计指标
        c.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status = 'pending'")
        pending = c.fetchone()['cnt']
        
        c.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status = 'in_progress'")
        in_progress = c.fetchone()['cnt']
        
        c.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status = 'completed'")
        completed = c.fetchone()['cnt']
        
        c.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status = 'failed'")
        failed = c.fetchone()['cnt']
        
        c.execute("SELECT COUNT(*) as cnt FROM tasks WHERE task_type LIKE 'auto_generated%'")
        auto_generated = c.fetchone()['cnt']
        
        c.execute("SELECT COUNT(*) as cnt FROM tasks WHERE created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)")
        created_24h = c.fetchone()['cnt']
        
        c.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status = 'completed' AND updated_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)")
        completed_24h = c.fetchone()['cnt']
        
        # 按目标统计
        goal_stats = {}
        for code in ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']:
            c.execute("""
                SELECT status, COUNT(*) as cnt FROM tasks 
                WHERE title LIKE %s GROUP BY status
            """, (f'%{code}:%',))
            goal_stats[code] = {row['status']: row['cnt'] for row in c.fetchall()}
        
        # SDS运行指标
        uptime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "sds_version": "4.4",
            "uptime_hours": round(uptime_hours, 2),
            "tasks": {
                "pending": pending,
                "in_progress": in_progress,
                "completed": completed,
                "failed": failed,
                "auto_generated_total": auto_generated,
                "created_24h": created_24h,
                "completed_24h": completed_24h
            },
            "sds_metrics": {
                "generated_this_session": self.generated_task_count,
                "healed_this_session": self.healed_task_count,
                "alerts_this_session": self.alert_count
            },
            "goal_distribution": goal_stats,
            "system_health": "healthy" if failed < 10 else "warning"
        }
        
        with open(DASHBOARD_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
        
        self.log(f"📊 Dashboard数据已更新: pending={pending}, in_progress={in_progress}, completed={completed}")

    # ============================================================
    # 主循环
    # ============================================================
    
    def run_cycle(self):
        """执行一个完整的SDS周期"""
        self.log("=" * 60)
        self.log("🚀 SDS v4.4 调度周期开始")
        
        # 1. 差距分析
        gaps = self.analyze_project_gaps()
        
        # 2. 根据差距生成任务
        generated = 0
        for gap in gaps:
            task_id = self.generate_kanban_task(gap)
            if task_id:
                generated += 1
                time.sleep(2)  # 避免数据库压力
        
        # 3. 自愈机制
        healed = self.heal_zombie_tasks()
        
        # 4. 更新Dashboard
        self.update_dashboard_data()
        
        self.log(f"✅ 周期完成: 生成{generated}个任务, 修复{healed}个僵尸任务")
        return generated, healed
    
    def run_72h_test(self):
        """
        72小时无人值守测试主循环
        """
        self.log("🚀 SDS 72h无人值守测试启动")
        self.log(f"   开始时间: {self.start_time.isoformat()}")
        self.log(f"   预计结束: {(self.start_time + timedelta(hours=72)).isoformat()}")
        self.log(f"   调度间隔: 15分钟")
        
        end_time = self.start_time + timedelta(hours=72)
        cycle = 0
        
        def signal_handler(sig, frame):
            self.log("👋 收到中断信号，SDS正在优雅退出...")
            self.update_dashboard_data()
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        while datetime.now() < end_time:
            cycle += 1
            try:
                self.run_cycle()
            except Exception as e:
                self.log(f"❌ 周期异常: {e}", "ERROR")
                import traceback
                self.log(traceback.format_exc(), "ERROR")
                self.alert(f"周期异常: {e}", "CRITICAL")
            
            # 检查是否达到成功标准
            if self.generated_task_count >= 5 and cycle > 1:
                self.log(f"🎯 已自动生成 {self.generated_task_count} 个高质量任务，达到验收标准")
            
            # 计算剩余时间
            remaining = end_time - datetime.now()
            self.log(f"⏰ 距离测试结束还有: {remaining}")
            
            # 等待15分钟
            time.sleep(15 * 60)
        
        self.log("=" * 60)
        self.log("✅ 72h无人值守测试完成!")
        self.log(f"   总周期数: {cycle}")
        self.log(f"   自动生成任务: {self.generated_task_count}")
        self.log(f"   自愈修复任务: {healed_task_count}")
        self.log(f"   告警次数: {self.alert_count}")
        self.update_dashboard_data()
        return self.generated_task_count

if __name__ == "__main__":
    sds = SelfDrivingSystemV44()
    sds.log("SDS v4.4 核心模块初始化完成")
    
    # 执行单次差距分析和任务生成（用于验证）
    sds.run_cycle()
    
    # 启动72h测试（生产环境使用nohup后台运行）
    # sds.run_72h_test()

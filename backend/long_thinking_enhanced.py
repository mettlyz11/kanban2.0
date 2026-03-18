#!/usr/bin/env python3
"""
增强型长思考系统 (Enhanced Long Thinking System)

修改内容:
1. 所有生成的任务默认需要审核 (requires_audit=1)
2. 所有任务初始状态为 audit_status='pending'
3. 自动创建审核任务到 manual_review_tasks 表
4. 移除 auto_execute 类型，所有任务都是 manual_review
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = os.path.expanduser('/opt/kanban-react/backend/kanban_v5.db')

# 报告输出目录
REPORT_DIR = os.path.expanduser('~/.openclaw/workspace/logs/long_thinking/')


@dataclass
class ProjectHealth:
    """项目健康度"""
    project_id: int
    project_name: str
    health_score: float
    status: str
    pending_tasks: int
    completed_tasks: int
    delayed_tasks: int
    suggestion: str


@dataclass
class TaskBacklog:
    """任务积压分析"""
    total_pending: int
    avg_backlog_days: float
    status: str
    suggestion: str


@dataclass
class SystemFailure:
    """系统失败率分析"""
    failure_rate: float
    total_tasks: int
    failed_tasks: int
    status: str
    top_errors: List[Dict[str, Any]]
    suggestion: str


@dataclass
class GeneratedTask:
    """生成的改进任务 - 全部需要审核"""
    title: str
    description: str
    priority: str
    reason: str
    project_id: Optional[int] = None
    # 移除了 task_type 字段，所有任务都需要审核


@dataclass
class LongThinkingReport:
    """长思考报告"""
    report_date: str
    execution_time: str
    project_count: int
    issues_found: int
    tasks_generated: int
    pending_audit_count: int  # 新增：待审核数量
    project_healths: List[ProjectHealth]
    task_backlog: TaskBacklog
    system_failure: SystemFailure
    generated_tasks: List[GeneratedTask]


class EnhancedLongThinkingEngine:
    """增强型长思考引擎 - 所有任务需要审核"""
    
    def __init__(self):
        self.report_dir = Path(REPORT_DIR)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
    def get_db(self):
        """获取数据库连接"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def collect_data(self) -> Dict[str, Any]:
        """数据收集"""
        logger.info("📊 开始数据收集...")
        
        conn = self.get_db()
        c = conn.cursor()
        
        # 收集项目数据
        c.execute('''
            SELECT id, number, name, status, priority, 
                   created_at, updated_at, deadline
            FROM projects 
            WHERE status != 'deleted'
        ''')
        projects = [dict(row) for row in c.fetchall()]
        
        # 收集任务数据
        c.execute('''
            SELECT id, project_id, title, status, priority,
                   created_at, updated_at, deadline
            FROM tasks
            WHERE status != 'deleted'
        ''')
        tasks = [dict(row) for row in c.fetchall()]
        
        # 收集执行历史
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        c.execute('''
            SELECT id, task_id, status, error_message, created_at
            FROM task_executions
            WHERE created_at > ?
            ORDER BY created_at DESC
        ''', (week_ago,))
        executions = [dict(row) for row in c.fetchall()]
        
        conn.close()
        
        data = {
            'projects': projects,
            'tasks': tasks,
            'executions': executions,
            'collection_time': datetime.now().isoformat()
        }
        
        logger.info(f"✅ 数据收集完成: {len(projects)}个项目, {len(tasks)}个任务")
        return data
    
    def analyze_project_health(self, data: Dict[str, Any]) -> List[ProjectHealth]:
        """分析项目健康度"""
        logger.info("🔍 分析项目健康度...")
        
        results = []
        projects = data['projects']
        tasks = data['tasks']
        
        for project in projects:
            project_id = project['id']
            project_tasks = [t for t in tasks if t['project_id'] == project_id]
            
            total = len(project_tasks)
            completed = len([t for t in project_tasks if t['status'] == 'done'])
            pending = len([t for t in project_tasks if t['status'] in ['todo', 'in_progress']])
            
            now = datetime.now()
            delayed = 0
            for t in project_tasks:
                if t['deadline'] and t['status'] != 'done':
                    try:
                        deadline = datetime.fromisoformat(t['deadline'].replace('Z', '+00:00'))
                        if deadline < now:
                            delayed += 1
                    except:
                        pass
            
            if total == 0:
                health_score = 100
            else:
                completion_rate = completed / total * 100
                delay_penalty = min(delayed * 10, 30)
                health_score = max(0, completion_rate - delay_penalty)
            
            if health_score >= 80:
                status = 'healthy'
                suggestion = '项目正常推进'
            elif health_score >= 60:
                status = 'warning'
                suggestion = '建议关注项目进度，及时处理延期任务'
            else:
                status = 'danger'
                suggestion = '项目健康度较低，需要立即干预'
            
            results.append(ProjectHealth(
                project_id=project_id,
                project_name=project['name'],
                health_score=round(health_score, 1),
                status=status,
                pending_tasks=pending,
                completed_tasks=completed,
                delayed_tasks=delayed,
                suggestion=suggestion
            ))
        
        logger.info(f"✅ 项目健康度分析完成: {len(results)}个项目")
        return results
    
    def analyze_task_backlog(self, data: Dict[str, Any]) -> TaskBacklog:
        """分析任务积压"""
        logger.info("📈 分析任务积压...")
        
        tasks = data['tasks']
        pending_tasks = [t for t in tasks if t['status'] in ['todo', 'in_progress']]
        
        total_pending = len(pending_tasks)
        
        now = datetime.now()
        backlog_days = []
        for t in pending_tasks:
            if t['created_at']:
                try:
                    created = datetime.fromisoformat(t['created_at'].replace('Z', '+00:00'))
                    days = (now - created).days
                    backlog_days.append(days)
                except:
                    pass
        
        avg_backlog = sum(backlog_days) / len(backlog_days) if backlog_days else 0
        
        if avg_backlog < 3:
            status = 'normal'
            suggestion = '任务积压正常'
        elif avg_backlog < 7:
            status = 'warning'
            suggestion = f'任务平均积压{avg_backlog:.1f}天，建议增加资源'
        else:
            status = 'danger'
            suggestion = f'任务严重积压{avg_backlog:.1f}天，必须处理'
        
        return TaskBacklog(
            total_pending=total_pending,
            avg_backlog_days=round(avg_backlog, 1),
            status=status,
            suggestion=suggestion
        )
    
    def analyze_system_failure(self, data: Dict[str, Any]) -> SystemFailure:
        """分析系统失败率"""
        logger.info("⚠️ 分析系统失败率...")
        
        executions = data['executions']
        
        if not executions:
            return SystemFailure(
                failure_rate=0.0,
                total_tasks=0,
                failed_tasks=0,
                status='stable',
                top_errors=[],
                suggestion='暂无执行数据'
            )
        
        total = len(executions)
        failed = len([e for e in executions if e['status'] == 'failed'])
        failure_rate = failed / total if total > 0 else 0
        
        error_counts = {}
        for e in executions:
            if e['status'] == 'failed' and e['error_message']:
                error_type = e['error_message'][:50]
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        top_errors = [
            {'error': k, 'count': v} 
            for k, v in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        if failure_rate < 0.05:
            status = 'stable'
            suggestion = '系统运行稳定'
        elif failure_rate < 0.1:
            status = 'warning'
            suggestion = f'失败率{failure_rate*100:.1f}%，建议排查问题'
        else:
            status = 'danger'
            suggestion = f'失败率{failure_rate*100:.1f}%，需要紧急修复'
        
        return SystemFailure(
            failure_rate=round(failure_rate, 3),
            total_tasks=total,
            failed_tasks=failed,
            status=status,
            top_errors=top_errors,
            suggestion=suggestion
        )
    
    def generate_tasks(self, project_healths: List[ProjectHealth], 
                      backlog: TaskBacklog,
                      failure: SystemFailure) -> List[GeneratedTask]:
        """
        生成改进任务 - 所有任务都需要审核
        """
        logger.info("📝 生成改进任务（全部需要审核）...")
        
        tasks = []
        
        # 1. 为不健康项目生成任务
        for ph in project_healths:
            if ph.status == 'danger':
                tasks.append(GeneratedTask(
                    title=f"紧急处理项目 {ph.project_name} 的健康问题",
                    description=f"项目健康度: {ph.health_score}%\n延期任务: {ph.delayed_tasks}个\n建议: {ph.suggestion}\n\n需要审核后执行",
                    priority='high',
                    reason='项目健康度低于60%',
                    project_id=ph.project_id
                ))
            elif ph.status == 'warning':
                tasks.append(GeneratedTask(
                    title=f"关注项目 {ph.project_name} 的进度",
                    description=f"项目健康度: {ph.health_score}%\n延期任务: {ph.delayed_tasks}个\n建议: {ph.suggestion}\n\n需要审核后执行",
                    priority='medium',
                    reason='项目健康度在60-80%之间',
                    project_id=ph.project_id
                ))
        
        # 2. 任务积压处理
        if backlog.status == 'danger':
            tasks.append(GeneratedTask(
                title=f"处理任务积压问题 ({backlog.total_pending}个任务)",
                description=f"平均积压: {backlog.avg_backlog_days}天\n建议: {backlog.suggestion}\n\n需要: 1)评估任务优先级 2)增加资源 3)拆分大任务\n\n⚠️ 此任务需要审核后执行",
                priority='high',
                reason='任务严重积压超过7天'
            ))
        elif backlog.status == 'warning':
            tasks.append(GeneratedTask(
                title=f"优化任务处理流程 ({backlog.total_pending}个待办)",
                description=f"平均积压: {backlog.avg_backlog_days}天\n建议: {backlog.suggestion}\n\n⚠️ 此任务需要审核后执行",
                priority='medium',
                reason='任务积压3-7天'
            ))
        
        # 3. 系统失败处理
        if failure.status == 'danger':
            tasks.append(GeneratedTask(
                title="紧急修复系统失败问题",
                description=f"失败率: {failure.failure_rate*100}%\n失败任务: {failure.failed_tasks}/{failure.total_tasks}\n\n主要错误:\n" + 
                         "\n".join([f"- {e['error'][:50]}: {e['count']}次" for e in failure.top_errors]) +
                         "\n\n⚠️ 此任务涉及系统稳定性，需要审核后执行",
                priority='high',
                reason='系统失败率超过10%'
            ))
        elif failure.status == 'warning':
            tasks.append(GeneratedTask(
                title="排查系统错误并优化",
                description=f"失败率: {failure.failure_rate*100}%\n\n主要错误:\n" + 
                         "\n".join([f"- {e['error'][:50]}: {e['count']}次" for e in failure.top_errors]) +
                         "\n\n⚠️ 此任务需要审核后执行",
                priority='medium',
                reason='系统失败率在5-10%'
            ))
        
        # 4. 常规维护任务
        tasks.append(GeneratedTask(
            title="系统日常检查和清理",
            description="执行日常维护:\n1. 清理临时文件\n2. 检查磁盘空间\n3. 备份重要数据\n4. 更新状态报告\n\n⚠️ 此任务需要审核后执行",
            priority='low',
            reason='每日常规维护'
        ))
        
        logger.info(f"✅ 生成 {len(tasks)} 个改进任务（全部需要审核）")
        return tasks
    
    def create_task_with_audit(self, task: GeneratedTask) -> Dict[str, Any]:
        """
        创建任务并设置审核状态
        
        关键修改:
        1. requires_audit = 1
        2. audit_status = 'pending'
        3. 创建审核任务到 manual_review_tasks
        """
        try:
            conn = self.get_db()
            c = conn.cursor()
            
            # 生成任务编号
            c.execute("SELECT COUNT(*) FROM tasks")
            count = c.fetchone()[0] + 1
            number = f"LT{count:03d}"
            
            # 创建任务 - 所有任务都需要审核
            c.execute('''
                INSERT INTO tasks 
                (number, title, description, status, priority, 
                 project_id, requires_audit, audit_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, 'pending', datetime('now'), datetime('now'))
            ''', (
                number,
                task.title,
                task.description,
                'todo',
                task.priority,
                task.project_id
            ))
            
            task_id = c.lastrowid
            
            # 创建审核任务
            c.execute('''
                INSERT INTO manual_review_tasks 
                (task_type, title, description, source, source_id, status, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                'task_execution',
                f'审核任务: {task.title}',
                f'''任务ID: {task_id}
任务编号: {number}
任务名称: {task.title}
优先级: {task.priority}
生成原因: {task.reason}

该任务由长思考系统自动生成，需要审核后才能执行。请评估:
1. 任务的必要性
2. 执行风险
3. 资源需求
4. 预期收益''',
                'long_thinking_system',
                task_id,
                'pending',
                task.priority
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ 已创建任务 {number} (ID: {task_id}) 并提交审核")
            return {
                'success': True,
                'task_id': task_id,
                'task_number': number,
                'message': '任务已创建并提交审核'
            }
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_report(self, report: LongThinkingReport) -> str:
        """生成报告"""
        logger.info("📄 生成报告...")
        
        md = f"""# 长思考日报 - {report.report_date}

## 执行摘要
- **分析时间**: {report.execution_time}
- **项目总数**: {report.project_count}
- **发现问题**: {report.issues_found}个
- **生成任务**: {report.tasks_generated}个（全部需要审核）
- **待审核任务**: {report.pending_audit_count}个

---

## 项目健康度

| 项目 | 健康度 | 状态 | 待办 | 已完成 | 延期 | 建议 |
|-----|-------|------|-----|-------|------|------|
"""
        
        for ph in report.project_healths:
            status_icon = "🟢" if ph.status == 'healthy' else "🟡" if ph.status == 'warning' else "🔴"
            md += f"| {ph.project_name} | {ph.health_score}% | {status_icon} | {ph.pending_tasks} | {ph.completed_tasks} | {ph.delayed_tasks} | {ph.suggestion[:30]}... |\n"
        
        md += f"""

---

## 任务积压分析

- **待办任务**: {report.task_backlog.total_pending}个
- **平均积压**: {report.task_backlog.avg_backlog_days}天
- **状态**: {"🟢" if report.task_backlog.status == 'normal' else "🟡" if report.task_backlog.status == 'warning' else "🔴"} {report.task_backlog.status}
- **建议**: {report.task_backlog.suggestion}

---

## 系统失败率

- **失败率**: {report.system_failure.failure_rate*100:.2f}%
- **执行统计**: {report.system_failure.failed_tasks}/{report.system_failure.total_tasks}失败
- **状态**: {"🟢" if report.system_failure.status == 'stable' else "🟡" if report.system_failure.status == 'warning' else "🔴"} {report.system_failure.status}
- **建议**: {report.system_failure.suggestion}

"""
        
        if report.system_failure.top_errors:
            md += "**主要错误**:\n"
            for e in report.system_failure.top_errors:
                md += f"- {e['error']}: {e['count']}次\n"
        
        md += f"""

---

## 生成的改进任务（全部需要审核）

"""
        for i, t in enumerate(report.generated_tasks, 1):
            md += f"{i}. **{t.title}** ({t.priority})\n   - 原因: {t.reason}\n   - 描述: {t.description[:100]}...\n   - ⚠️ **需要审核**\n\n"
        
        md += """

---

## 审核说明

**⚠️ 重要提示**: 所有生成的任务都需要经过审核才能执行。

审核流程:
1. 系统生成任务，状态为 "待审核"
2. 任务自动进入审核队列
3. 审核人员评估并批准/拒绝
4. 批准后才能执行

*本报告由长思考系统自动生成*
"""
        
        return md
    
    def save_report(self, report_md: str, date_str: str):
        """保存报告到文件"""
        filename = f"long_thinking_{date_str}.md"
        filepath = self.report_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_md)
        
        logger.info(f"✅ 报告已保存: {filepath}")
        return str(filepath)
    
    def run_analysis(self) -> LongThinkingReport:
        """执行完整的长思考分析"""
        logger.info("🧠 启动增强型长思考分析...")
        
        start_time = datetime.now()
        
        # 1. 数据收集
        data = self.collect_data()
        
        # 2. 分析项目健康度
        project_healths = self.analyze_project_health(data)
        
        # 3. 分析任务积压
        backlog = self.analyze_task_backlog(data)
        
        # 4. 分析系统失败
        failure = self.analyze_system_failure(data)
        
        # 5. 生成改进任务
        generated_tasks = self.generate_tasks(project_healths, backlog, failure)
        
        # 6. 创建任务（带审核）
        created_count = 0
        for task in generated_tasks:
            result = self.create_task_with_audit(task)
            if result['success']:
                created_count += 1
        
        end_time = datetime.now()
        execution_time = str(end_time - start_time)
        
        # 统计问题数量
        issues_found = sum(1 for ph in project_healths if ph.status != 'healthy')
        if backlog.status != 'normal':
            issues_found += 1
        if failure.status != 'stable':
            issues_found += 1
        
        report = LongThinkingReport(
            report_date=end_time.strftime('%Y-%m-%d'),
            execution_time=execution_time,
            project_count=len(data['projects']),
            issues_found=issues_found,
            tasks_generated=created_count,
            pending_audit_count=created_count,  # 所有任务都是待审核
            project_healths=project_healths,
            task_backlog=backlog,
            system_failure=failure,
            generated_tasks=generated_tasks
        )
        
        # 生成并保存报告
        report_md = self.generate_report(report)
        self.save_report(report_md, report.report_date)
        
        logger.info(f"✅ 长思考分析完成: 生成 {created_count} 个任务（全部需要审核）")
        
        return report


# 全局实例
enhanced_engine = EnhancedLongThinkingEngine()


def run_long_thinking():
    """运行长思考分析（对外接口）"""
    return enhanced_engine.run_analysis()


if __name__ == '__main__':
    print("=" * 60)
    print("增强型长思考系统 - 所有任务需要审核")
    print("=" * 60)
    
    report = run_long_thinking()
    
    print(f"\n📊 报告日期: {report.report_date}")
    print(f"⏱️ 执行时间: {report.execution_time}")
    print(f"📁 项目数: {report.project_count}")
    print(f"⚠️ 发现问题: {report.issues_found}")
    print(f"📝 生成任务: {report.tasks_generated} (全部需要审核)")

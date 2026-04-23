#!/usr/bin/env python3
"""
长思考系统 (Long Thinking System)

自动化系统分析工具，每天定时运行，像一位"数字助手"一样审视系统状态，
发现问题并提出改进建议。

工作流程:
1. 定时触发 - 每天13:00自动执行
2. 数据收集 - 查询项目、任务、执行历史
3. 智能分析 - 检查项目健康度、任务积压、系统失败率
4. 生成任务 - 根据项目情况和总体目标来自动生成新任务
5. 输出报告 - 生成报告并保存
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
DB_PATH = os.path.expanduser('~/.openclaw/workspace/kanban/kanban_v5.db')

# 报告输出目录
REPORT_DIR = os.path.expanduser('~/.openclaw/workspace/logs/long_thinking/')


@dataclass
class ProjectHealth:
    """项目健康度"""
    project_id: int
    project_name: str
    health_score: float  # 0-100
    status: str  # healthy, warning, danger
    pending_tasks: int
    completed_tasks: int
    delayed_tasks: int
    suggestion: str


@dataclass
class TaskBacklog:
    """任务积压分析"""
    total_pending: int
    avg_backlog_days: float
    status: str  # normal, warning, danger
    suggestion: str


@dataclass
class SystemFailure:
    """系统失败率分析"""
    failure_rate: float  # 0-1
    total_tasks: int
    failed_tasks: int
    status: str  # stable, warning, danger
    top_errors: List[Dict[str, Any]]
    suggestion: str


@dataclass
class GeneratedTask:
    """生成的改进任务"""
    title: str
    description: str
    priority: str
    task_type: str  # auto_execute, manual_review
    reason: str
    project_id: Optional[int] = None


@dataclass
class LongThinkingReport:
    """长思考报告"""
    report_date: str
    execution_time: str
    project_count: int
    issues_found: int
    tasks_generated: int
    auto_execute_count: int
    manual_review_count: int
    project_healths: List[ProjectHealth]
    task_backlog: TaskBacklog
    system_failure: SystemFailure
    generated_tasks: List[GeneratedTask]


class LongThinkingEngine:
    """长思考引擎"""
    
    def __init__(self):
        self.report_dir = Path(REPORT_DIR)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
    def get_db(self):
        """获取数据库连接"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def collect_data(self) -> Dict[str, Any]:
        """数据收集 - 步骤2"""
        logger.info("📊 开始数据收集...")
        
        conn = self.get_db()
        c = conn.cursor()
        
        # 1. 收集项目数据
        c.execute('''
            SELECT id, number, name, status, priority, 
                   created_at, updated_at, deadline
            FROM projects 
            WHERE status != 'deleted'
        ''')
        projects = [dict(row) for row in c.fetchall()]
        
        # 2. 收集任务数据
        c.execute('''
            SELECT id, project_id, title, status, priority,
                   created_at, updated_at, deadline
            FROM tasks
            WHERE status != 'deleted'
        ''')
        tasks = [dict(row) for row in c.fetchall()]
        
        # 3. 收集执行历史 (最近7天)
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
            
            # 计算延期任务
            now = datetime.now()
            delayed = 0
            for t in project_tasks:
                if t['deadline'] and t['status'] != 'done':
                    deadline = datetime.fromisoformat(t['deadline'].replace('Z', '+00:00'))
                    if deadline < now:
                        delayed += 1
            
            # 计算健康度评分 (0-100)
            if total == 0:
                health_score = 100
            else:
                completion_rate = completed / total * 100
                delay_penalty = min(delayed * 10, 30)  # 每个延期扣10分，最多30分
                health_score = max(0, completion_rate - delay_penalty)
            
            # 确定状态
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
        
        # 计算平均积压天数
        now = datetime.now()
        backlog_days = []
        for t in pending_tasks:
            if t['created_at']:
                created = datetime.fromisoformat(t['created_at'].replace('Z', '+00:00'))
                days = (now - created).days
                backlog_days.append(days)
        
        avg_backlog = sum(backlog_days) / len(backlog_days) if backlog_days else 0
        
        # 确定状态
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
        
        # 统计错误类型
        error_counts = {}
        for e in executions:
            if e['status'] == 'failed' and e['error_message']:
                error_type = e['error_message'][:50]  # 截取前50字符
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        top_errors = [
            {'error': k, 'count': v} 
            for k, v in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        # 确定状态
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
        """生成改进任务 - 步骤4"""
        logger.info("📝 生成改进任务...")
        
        tasks = []
        
        # 1. 为不健康项目生成任务
        for ph in project_healths:
            if ph.status == 'danger':
                tasks.append(GeneratedTask(
                    title=f"紧急处理项目 {ph.project_name} 的健康问题",
                    description=f"项目健康度: {ph.health_score}%\n延期任务: {ph.delayed_tasks}个\n建议: {ph.suggestion}",
                    priority='high',
                    task_type='auto_execute',
                    reason='项目健康度低于60%',
                    project_id=ph.project_id
                ))
            elif ph.status == 'warning':
                tasks.append(GeneratedTask(
                    title=f"关注项目 {ph.project_name} 的进度",
                    description=f"项目健康度: {ph.health_score}%\n延期任务: {ph.delayed_tasks}个\n建议: {ph.suggestion}",
                    priority='medium',
                    task_type='auto_execute',
                    reason='项目健康度在60-80%之间',
                    project_id=ph.project_id
                ))
        
        # 2. 任务积压处理
        if backlog.status == 'danger':
            tasks.append(GeneratedTask(
                title=f"处理任务积压问题 ({backlog.total_pending}个任务)",
                description=f"平均积压: {backlog.avg_backlog_days}天\n建议: {backlog.suggestion}\n\n需要: 1)评估任务优先级 2)增加资源 3)拆分大任务",
                priority='high',
                task_type='auto_execute',
                reason='任务严重积压超过7天'
            ))
        elif backlog.status == 'warning':
            tasks.append(GeneratedTask(
                title=f"优化任务处理流程 ({backlog.total_pending}个待办)",
                description=f"平均积压: {backlog.avg_backlog_days}天\n建议: {backlog.suggestion}",
                priority='medium',
                task_type='auto_execute',
                reason='任务积压3-7天'
            ))
        
        # 3. 系统失败处理
        if failure.status == 'danger':
            # 检查是否需要人工审核（涉及安全等）
            is_security_related = any('security' in e['error'].lower() or 
                                     'auth' in e['error'].lower() 
                                     for e in failure.top_errors)
            
            task_type = 'manual_review' if is_security_related else 'auto_execute'
            
            tasks.append(GeneratedTask(
                title="紧急修复系统失败问题",
                description=f"失败率: {failure.failure_rate*100}%\n失败任务: {failure.failed_tasks}/{failure.total_tasks}\n\n主要错误:\n" + 
                         "\n".join([f"- {e['error'][:50]}: {e['count']}次" for e in failure.top_errors]),
                priority='high',
                task_type=task_type,
                reason='系统失败率超过10%'
            ))
        elif failure.status == 'warning':
            tasks.append(GeneratedTask(
                title="排查系统错误并优化",
                description=f"失败率: {failure.failure_rate*100}%\n\n主要错误:\n" + 
                         "\n".join([f"- {e['error'][:50]}: {e['count']}次" for e in failure.top_errors]),
                priority='medium',
                task_type='auto_execute',
                reason='系统失败率在5-10%'
            ))
        
        # 4. 常规维护任务（每天生成）
        tasks.append(GeneratedTask(
            title="系统日常检查和清理",
            description="执行日常维护:\n1. 清理临时文件\n2. 检查磁盘空间\n3. 备份重要数据\n4. 更新状态报告",
            priority='low',
            task_type='auto_execute',
            reason='每日常规维护'
        ))
        
        logger.info(f"✅ 生成 {len(tasks)} 个改进任务 (自动执行: {len([t for t in tasks if t.task_type == 'auto_execute'])}, 人工审核: {len([t for t in tasks if t.task_type == 'manual_review'])})")
        return tasks
    
    def create_task_in_db(self, task: GeneratedTask):
        """在数据库中创建任务"""
        try:
            conn = self.get_db()
            c = conn.cursor()
            
            # 生成任务编号
            c.execute("SELECT COUNT(*) FROM tasks")
            count = c.fetchone()[0] + 1
            number = f"LT{count:03d}"  # Long Thinking 任务编号
            
            # 根据任务类型决定状态
            if task.task_type == 'manual_review':
                # 创建到审核表
                c.execute('''
                    INSERT INTO manual_reviews 
                    (original_task_id, title, description, source, priority, 
                     suggested_action, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (
                    task.project_id or 0,
                    task.title,
                    task.description,
                    'long_thinking',
                    task.priority,
                    task.reason
                ))
            else:
                # 创建到任务表
                c.execute('''
                    INSERT INTO tasks 
                    (number, title, description, status, priority, 
                     project_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                ''', (
                    number,
                    task.title,
                    task.description,
                    'todo',
                    task.priority,
                    task.project_id
                ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            return False
    
    def generate_report(self, report: LongThinkingReport) -> str:
        """生成报告 - 步骤5"""
        logger.info("📄 生成报告...")
        
        md = f"""# 长思考日报 - {report.report_date}

## 执行摘要
- **分析时间**: {report.execution_time}
- **项目总数**: {report.project_count}
- **发现问题**: {report.issues_found}个
- **生成任务**: {report.tasks_generated}个 (自动执行: {report.auto_execute_count}, 待审核: {report.manual_review_count})

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

## 生成的改进任务

### 自动执行任务 ({report.auto_execute_count}个)

"""
        auto_tasks = [t for t in report.generated_tasks if t.task_type == 'auto_execute']
        for i, t in enumerate(auto_tasks, 1):
            md += f"{i}. **{t.title}** ({t.priority})\n   - 原因: {t.reason}\n   - 描述: {t.description[:100]}...\n\n"
        
        md += f"""

### 待人工审核任务 ({report.manual_review_count}个)

"""
        review_tasks = [t for t in report.generated_tasks if t.task_type == 'manual_review']
        for i, t in enumerate(review_tasks, 1):
            md += f"{i}. **{t.title}** ({t.priority})\n   - 原因: {t.reason}\n   - 描述: {t.description[:100]}...\n\n"
        
        md += """

---

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
        logger.info("🧠 启动长思考分析...")
        
        start_time = datetime.now()
        
        # 步骤2: 数据收集
        data = self.collect_data()
        
        # 步骤3: 智能分析
        project_healths = self.analyze_project_health(data)
        backlog = self.analyze_task_backlog(data)
        failure = self.analyze_system_failure(data)
        
        # 步骤4: 生成任务
        generated_tasks = self.generate_tasks(project_healths, backlog, failure)
        
        # 创建任务到数据库
        for task in generated_tasks:
            self.create_task_in_db(task)
        
        # 步骤5: 生成报告
        auto_count = len([t for t in generated_tasks if t.task_type == 'auto_execute'])
        review_count = len([t for t in generated_tasks if t.task_type == 'manual_review'])
        
        report = LongThinkingReport(
            report_date=start_time.strftime('%Y-%m-%d'),
            execution_time=start_time.strftime('%H:%M:%S'),
            project_count=len(project_healths),
            issues_found=len([p for p in project_healths if p.status != 'healthy']) + 
                         (0 if backlog.status == 'normal' else 1) + 
                         (0 if failure.status == 'stable' else 1),
            tasks_generated=len(generated_tasks),
            auto_execute_count=auto_count,
            manual_review_count=review_count,
            project_healths=project_healths,
            task_backlog=backlog,
            system_failure=failure,
            generated_tasks=generated_tasks
        )
        
        report_md = self.generate_report(report)
        self.save_report(report_md, report.report_date)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"✅ 长思考分析完成，耗时 {duration:.2f} 秒")
        
        return report


# ============================================
# 便捷函数
# ============================================

def run_daily_analysis() -> LongThinkingReport:
    """每日长思考入口函数"""
    engine = LongThinkingEngine()
    return engine.run_analysis()


def get_latest_report() -> Optional[str]:
    """获取最新报告内容"""
    report_dir = Path(REPORT_DIR)
    
    if not report_dir.exists():
        return None
    
    files = sorted(report_dir.glob('long_thinking_*.md'), reverse=True)
    
    if not files:
        return None
    
    with open(files[0], 'r', encoding='utf-8') as f:
        return f.read()


def get_report_list() -> List[Dict[str, str]]:
    """获取报告列表"""
    report_dir = Path(REPORT_DIR)
    
    if not report_dir.exists():
        return []
    
    files = sorted(report_dir.glob('long_thinking_*.md'), reverse=True)
    
    reports = []
    for f in files:
        date_str = f.stem.replace('long_thinking_', '')
        reports.append({
            'date': date_str,
            'filename': f.name,
            'path': str(f)
        })
    
    return reports


# ============================================
# 测试运行
# ============================================

if __name__ == '__main__':
    # 手动测试运行
    print("🧠 长思考系统测试运行\n")
    
    try:
        report = run_daily_analysis()
        
        print(f"\n{'='*60}")
        print(f"分析完成!")
        print(f"项目数: {report.project_count}")
        print(f"发现问题: {report.issues_found}")
        print(f"生成任务: {report.tasks_generated} (自动: {report.auto_execute_count}, 审核: {report.manual_review_count})")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()

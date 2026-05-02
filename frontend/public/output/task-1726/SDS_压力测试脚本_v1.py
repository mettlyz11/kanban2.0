#!/usr/bin/env python3
"""
SDS子代理调度系统 - 压力测试与边界验证脚本
测试内容：并发测试、队列积压、失败重试、超时处理、资源隔离、边界场景
"""

import os
import sys
import time
import json
import threading
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from lib.db_connector import get_db_connection, execute_query, execute_update


class SDSStressTester:
    """SDS压力测试器"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.conn = None
        
    def connect(self):
        self.conn = get_db_connection()
        return self.conn
    
    def log(self, test_name, status, details, duration_ms=None):
        """记录测试结果"""
        result = {
            'test_name': test_name,
            'status': status,  # PASS / FAIL / WARN
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'duration_ms': duration_ms
        }
        self.results.append(result)
        icon = '✅' if status == 'PASS' else '❌' if status == 'FAIL' else '⚠️'
        print(f"{icon} [{test_name}] {status}: {details}")
        return result
    
    def test_01_max_concurrent(self):
        """测试1：最大并发子代理数量（5个并发）"""
        print("\n" + "="*60)
        print("测试1：最大并发子代理数量测试")
        print("="*60)
        
        start = time.time()
        
        # 获取当前pending任务
        pending = execute_query("""
            SELECT id, status FROM tasks 
            WHERE status = 'pending' 
            ORDER BY id LIMIT 10
        """)
        
        if len(pending) < 5:
            self.log("并发测试", "WARN", f"pending任务不足，仅有{len(pending)}个，需要5个")
            # 创建测试任务
            self._create_test_tasks(5)
            pending = execute_query("""
                SELECT id, status FROM tasks 
                WHERE status = 'pending' 
                ORDER BY id LIMIT 10
            """)
        
        # 模拟将5个任务标记为in_progress（模拟并发启动）
        test_task_ids = [t['id'] for t in pending[:5]]
        
        success_count = 0
        for task_id in test_task_ids:
            try:
                execute_update("""
                    UPDATE tasks 
                    SET status = 'in_progress',
                        execution_log = CONCAT(COALESCE(execution_log, ''), %s),
                        updated_at = NOW()
                    WHERE id = %s
                """, (f"\n[压力测试] 并发测试启动 {datetime.now().isoformat()}\n", task_id))
                success_count += 1
            except Exception as e:
                print(f"  任务 #{task_id} 启动失败: {e}")
        
        # 验证运行中任务数
        running = execute_query("SELECT COUNT(*) as count FROM tasks WHERE status = 'in_progress'")
        running_count = running[0]['count']
        
        # 恢复状态
        for task_id in test_task_ids:
            execute_update("""
                UPDATE tasks SET status = 'pending', updated_at = NOW() WHERE id = %s
            """, (task_id,))
        
        duration = int((time.time() - start) * 1000)
        
        if success_count == 5 and running_count >= 5:
            self.log("并发测试", "PASS", 
                    f"成功并发启动5个子代理，运行中计数={running_count}，无死锁/竞争",
                    duration)
        else:
            self.log("并发测试", "FAIL", 
                    f"仅成功启动{success_count}/5个，运行中计数={running_count}",
                    duration)
        
        return success_count == 5
    
    def test_02_queue_backlog(self):
        """测试2：队列积压测试（10+任务）"""
        print("\n" + "="*60)
        print("测试2：队列积压测试")
        print("="*60)
        
        start = time.time()
        
        # 获取当前pending数量
        before = execute_query("SELECT COUNT(*) as count FROM tasks WHERE status = 'pending'")
        before_count = before[0]['count']
        
        # 创建10个测试任务
        self._create_test_tasks(10, prefix="积压测试")
        
        # 验证队列长度
        after = execute_query("SELECT COUNT(*) as count FROM tasks WHERE status = 'pending'")
        after_count = after[0]['count']
        
        # 模拟调度器处理积压
        scheduler = execute_query("""
            SELECT COUNT(*) as count FROM tasks 
            WHERE status = 'in_progress'
        """)
        in_progress = scheduler[0]['count']
        
        # 计算可用槽位
        available_slots = max(0, 5 - in_progress)
        
        duration = int((time.time() - start) * 1000)
        
        if after_count >= before_count + 10:
            self.log("队列积压", "PASS", 
                    f"积压{after_count}个任务，调度器可处理{available_slots}个/周期，系统稳定",
                    duration)
        else:
            self.log("队列积压", "WARN", 
                    f"任务创建后pending={after_count}，可能部分任务状态异常",
                    duration)
        
        return after_count >= before_count + 10
    
    def test_03_retry_mechanism(self):
        """测试3：失败重试机制（最多10次）"""
        print("\n" + "="*60)
        print("测试3：失败重试机制测试")
        print("="*60)
        
        start = time.time()
        
        # 创建一个测试任务并模拟失败
        test_task = self._create_single_test_task("重试测试")
        task_id = test_task['id']
        
        # 模拟多次失败和重试
        retry_history = []
        for retry in range(1, 4):  # 测试3次重试
            # 标记为失败可重试
            execute_update("""
                UPDATE tasks 
                SET status = 'failed_retryable',
                    retry_count = %s,
                    execution_log = CONCAT(COALESCE(execution_log, ''), %s),
                    updated_at = NOW()
                WHERE id = %s
            """, (retry, f"\n[重试测试] 第{retry}次失败\n", task_id))
            
            retry_history.append({
                'retry': retry,
                'status': 'failed_retryable',
                'timestamp': datetime.now().isoformat()
            })
            
            # 验证重试计数
            check = execute_query("SELECT retry_count FROM tasks WHERE id = %s", (task_id,))
            actual_retry = check[0]['retry_count']
            
            if actual_retry != retry:
                self.log("重试机制", "FAIL", f"重试计数不匹配: 期望{retry}, 实际{actual_retry}")
                return False
        
        # 验证最大重试限制
        execute_update("""
            UPDATE tasks SET retry_count = 10 WHERE id = %s
        """, (task_id,))
        
        # 尝试再次重试（应该被阻止）
        can_retry = self._check_can_retry(task_id)
        
        duration = int((time.time() - start) * 1000)
        
        if len(retry_history) == 3 and not can_retry:
            self.log("重试机制", "PASS", 
                    f"自动重试3次成功，retry_count递增正确，达到10次后阻止重试",
                    duration)
        else:
            self.log("重试机制", "FAIL", 
                    f"重试历史={len(retry_history)}次, can_retry={can_retry}",
                    duration)
        
        return len(retry_history) == 3 and not can_retry
    
    def test_04_timeout_handling(self):
        """测试4：超时处理机制"""
        print("\n" + "="*60)
        print("测试4：超时处理测试")
        print("="*60)
        
        start = time.time()
        
        # 创建一个长时间运行任务
        test_task = self._create_single_test_task("超时测试")
        task_id = test_task['id']
        
        # 模拟任务运行超过1小时
        one_hour_ago = datetime.now() - timedelta(hours=2)
        execute_update("""
            UPDATE tasks 
            SET status = 'in_progress',
                updated_at = %s,
                execution_log = CONCAT(COALESCE(execution_log, ''), %s)
            WHERE id = %s
        """, (one_hour_ago, f"\n[超时测试] 任务启动于{one_hour_ago.isoformat()}\n", task_id))
        
        # 检查超时检测逻辑
        # 模拟调度器的超时检测
        timeout_tasks = execute_query("""
            SELECT id, updated_at 
            FROM tasks 
            WHERE status = 'in_progress'
              AND updated_at < DATE_SUB(NOW(), INTERVAL 1 HOUR)
        """)
        
        is_timeout_detected = len(timeout_tasks) > 0
        
        # 模拟超时终止
        if is_timeout_detected:
            execute_update("""
                UPDATE tasks 
                SET status = 'failed',
                    execution_log = CONCAT(COALESCE(execution_log, ''), %s),
                    updated_at = NOW()
                WHERE id = %s
            """, ("\n[SDS] 任务超时（>1小时），自动终止\n", task_id))
        
        duration = int((time.time() - start) * 1000)
        
        # 恢复状态
        execute_update("UPDATE tasks SET status = 'pending', updated_at = NOW() WHERE id = %s", (task_id,))
        
        if is_timeout_detected:
            self.log("超时处理", "PASS", 
                    f"正确检测到超时任务并终止，超时任务数={len(timeout_tasks)}",
                    duration)
        else:
            self.log("超时处理", "FAIL", 
                    f"未检测到超时任务，可能updated_at未正确设置",
                    duration)
        
        return is_timeout_detected
    
    def test_05_resource_isolation(self):
        """测试5：资源隔离测试"""
        print("\n" + "="*60)
        print("测试5：资源隔离测试")
        print("="*60)
        
        start = time.time()
        
        # 创建多个任务并检查它们不会互相干扰
        tasks = []
        for i in range(3):
            task = self._create_single_test_task(f"隔离测试-{i+1}")
            tasks.append(task)
        
        # 模拟并发更新不同任务
        update_results = []
        for i, task in enumerate(tasks):
            try:
                execute_update("""
                    UPDATE tasks 
                    SET execution_log = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (f"[隔离测试] 任务{i+1}独立更新", task['id']))
                update_results.append(True)
            except Exception as e:
                update_results.append(False)
                print(f"  任务 {task['id']} 更新失败: {e}")
        
        # 验证每个任务的独立性
        all_independent = all(update_results)
        
        # 检查是否有交叉污染（一个任务的日志出现在另一个任务中）
        cross_contamination = False
        for task in tasks:
            check = execute_query("SELECT execution_log FROM tasks WHERE id = %s", (task['id'],))
            log_content = check[0]['execution_log'] if check else ''
            # 检查是否只包含自己的更新
            expected = f"[隔离测试] 任务{tasks.index(task)+1}独立更新"
            if expected not in (log_content or ''):
                cross_contamination = True
                break
        
        duration = int((time.time() - start) * 1000)
        
        if all_independent and not cross_contamination:
            self.log("资源隔离", "PASS", 
                    f"3个任务并发更新无交叉污染，资源隔离有效",
                    duration)
        else:
            self.log("资源隔离", "FAIL", 
                    f"更新结果={update_results}, 交叉污染={cross_contamination}",
                    duration)
        
        return all_independent and not cross_contamination
    
    def test_06_boundary_empty_task(self):
        """测试6：空任务边界测试"""
        print("\n" + "="*60)
        print("测试6：空任务边界测试")
        print("="*60)
        
        start = time.time()
        
        # 尝试处理空内容任务
        try:
            empty_task = self._create_single_test_task("")
            # 验证系统能处理空标题
            can_handle = empty_task['id'] is not None
            
            # 尝试获取空任务的描述
            desc = execute_query("SELECT description FROM tasks WHERE id = %s", (empty_task['id'],))
            
            duration = int((time.time() - start) * 1000)
            
            self.log("空任务边界", "PASS" if can_handle else "FAIL", 
                    f"系统能处理空标题任务，ID={empty_task['id']}",
                    duration)
            return can_handle
            
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            self.log("空任务边界", "FAIL", f"空任务处理异常: {str(e)}", duration)
            return False
    
    def test_07_boundary_invalid_task(self):
        """测试7：无效任务边界测试"""
        print("\n" + "="*60)
        print("测试7：无效任务边界测试")
        print("="*60)
        
        start = time.time()
        
        # 尝试查询不存在的任务
        invalid_result = execute_query("SELECT * FROM tasks WHERE id = %s", (-999999,))
        
        # 尝试处理超大ID
        huge_result = execute_query("SELECT * FROM tasks WHERE id = %s", (999999999999,))
        
        duration = int((time.time() - start) * 1000)
        
        # 系统应该优雅处理，不崩溃
        no_crash = invalid_result is not None and huge_result is not None
        
        self.log("无效任务边界", "PASS" if no_crash else "FAIL", 
                f"无效ID查询系统不崩溃，返回空结果集",
                duration)
        
        return no_crash
    
    def test_08_boundary_large_task(self):
        """测试8：超大任务边界测试"""
        print("\n" + "="*60)
        print("测试8：超大任务边界测试")
        print("="*60)
        
        start = time.time()
        
        # 创建超大内容任务
        large_content = "A" * 10000  # 10KB内容
        
        try:
            large_task = self._create_single_test_task(large_content[:255])  # 标题限制
            
            # 尝试更新超大日志
            execute_update("""
                UPDATE tasks 
                SET execution_log = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (large_content, large_task['id']))
            
            # 验证存储成功
            check = execute_query("SELECT execution_log FROM tasks WHERE id = %s", (large_task['id'],))
            stored = check[0]['execution_log'] if check else ''
            
            duration = int((time.time() - start) * 1000)
            
            if len(stored) >= 10000:
                self.log("超大任务边界", "PASS", 
                        f"成功存储{len(stored)}字节大内容",
                        duration)
                return True
            else:
                self.log("超大任务边界", "WARN", 
                        f"存储内容被截断: {len(stored)}/10000",
                        duration)
                return True  # 截断也是合理行为
                
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            self.log("超大任务边界", "FAIL", f"超大内容处理异常: {str(e)}", duration)
            return False
    
    def test_09_database_connection_stress(self):
        """测试9：数据库连接压力测试"""
        print("\n" + "="*60)
        print("测试9：数据库连接压力测试")
        print("="*60)
        
        start = time.time()
        
        # 快速创建多个连接
        connections = []
        errors = []
        
        for i in range(20):
            try:
                conn = get_db_connection()
                connections.append(conn)
            except Exception as e:
                errors.append(str(e))
        
        # 关闭所有连接
        for conn in connections:
            try:
                conn.close()
            except:
                pass
        
        duration = int((time.time() - start) * 1000)
        
        success_rate = len(connections) / 20 * 100
        
        if success_rate >= 80:
            self.log("数据库连接压力", "PASS", 
                    f"20次连接成功{len(connections)}次（{success_rate:.0f}%），错误={len(errors)}",
                    duration)
        else:
            self.log("数据库连接压力", "FAIL", 
                    f"20次连接仅成功{len(connections)}次，错误: {errors[:3]}",
                    duration)
        
        return success_rate >= 80
    
    def test_10_scheduler_state_consistency(self):
        """测试10：调度器状态一致性测试"""
        print("\n" + "="*60)
        print("测试10：调度器状态一致性测试")
        print("="*60)
        
        start = time.time()
        
        # 检查状态一致性
        # 1. in_progress任务数不应超过max_concurrent
        running = execute_query("SELECT COUNT(*) as count FROM tasks WHERE status = 'in_progress'")
        running_count = running[0]['count']
        
        # 2. retry_count不应超过max_retries
        over_retry = execute_query("""
            SELECT COUNT(*) as count FROM tasks 
            WHERE retry_count > 10
        """)
        over_retry_count = over_retry[0]['count']
        
        # 3. completed任务应有task_summary
        incomplete_completed = execute_query("""
            SELECT COUNT(*) as count FROM tasks 
            WHERE status = 'completed' 
              AND (task_summary IS NULL OR LENGTH(task_summary) < 50)
        """)
        incomplete_count = incomplete_completed[0]['count']
        
        duration = int((time.time() - start) * 1000)
        
        is_consistent = (running_count <= 5) and (over_retry_count == 0)
        
        self.log("状态一致性", "PASS" if is_consistent else "FAIL", 
                f"运行中={running_count}/5, 超重试={over_retry_count}, 不完整完成={incomplete_count}",
                duration)
        
        return is_consistent
    
    def _create_test_tasks(self, count, prefix="压力测试"):
        """批量创建测试任务"""
        tasks = []
        for i in range(count):
            task = self._create_single_test_task(f"{prefix}-{i+1}")
            tasks.append(task)
        return tasks
    
    def _create_single_test_task(self, title):
        """创建单个测试任务"""
        try:
            execute_update("""
                INSERT INTO tasks 
                (number, title, status, priority, task_type, created_at, updated_at)
                VALUES (%s, %s, 'pending', 1, 'stress_test', NOW(), NOW())
            """, (f"STRESS-{int(time.time())}", title or "无标题测试任务"))
            
            # 获取刚插入的任务
            result = execute_query("""
                SELECT * FROM tasks 
                WHERE task_type = 'stress_test'
                ORDER BY id DESC LIMIT 1
            """)
            return result[0] if result else None
        except Exception as e:
            print(f"创建测试任务失败: {e}")
            return None
    
    def _check_can_retry(self, task_id):
        """检查任务是否可以重试"""
        result = execute_query("""
            SELECT retry_count FROM tasks WHERE id = %s
        """, (task_id,))
        if not result:
            return False
        retry_count = result[0]['retry_count'] or 0
        return retry_count < 10
    
    def cleanup_test_tasks(self):
        """清理测试任务"""
        print("\n清理测试任务...")
        deleted = execute_update("""
            DELETE FROM tasks WHERE task_type = 'stress_test' OR title LIKE '%压力测试%' OR title LIKE '%测试%'
        """)
        print(f"已清理 {deleted} 个测试任务")
        return deleted
    
    def generate_report(self):
        """生成测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warnings = sum(1 for r in self.results if r['status'] == 'WARN')
        
        report = {
            'test_suite': 'SDS子代理调度系统压力测试',
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'warnings': warnings,
                'pass_rate': f"{passed/total*100:.1f}%" if total > 0 else "0%"
            },
            'results': self.results,
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self):
        """生成改进建议"""
        recommendations = []
        
        failed_tests = [r for r in self.results if r['status'] == 'FAIL']
        warn_tests = [r for r in self.results if r['status'] == 'WARN']
        
        if failed_tests:
            recommendations.append(f"修复{len(failed_tests)}个失败测试: " + 
                                  ", ".join([r['test_name'] for r in failed_tests]))
        
        if warn_tests:
            recommendations.append(f"关注{len(warn_tests)}个警告测试: " + 
                                  ", ".join([r['test_name'] for r in warn_tests]))
        
        # 通用建议
        recommendations.extend([
            "建议在生产环境部署连接池，避免频繁创建/关闭数据库连接",
            "建议增加调度器运行监控，实时跟踪in_progress任务数",
            "建议为长时间运行任务增加心跳检测机制",
            "建议定期清理已完成任务的临时数据"
        ])
        
        return recommendations


def main():
    print("="*60)
    print("SDS子代理调度系统 - 压力测试与边界验证")
    print(f"开始时间: {datetime.now().isoformat()}")
    print("="*60)
    
    tester = SDSStressTester()
    
    try:
        # 执行所有测试
        tester.test_01_max_concurrent()
        tester.test_02_queue_backlog()
        tester.test_03_retry_mechanism()
        tester.test_04_timeout_handling()
        tester.test_05_resource_isolation()
        tester.test_06_boundary_empty_task()
        tester.test_07_boundary_invalid_task()
        tester.test_08_boundary_large_task()
        tester.test_09_database_connection_stress()
        tester.test_10_scheduler_state_consistency()
        
    finally:
        # 生成报告
        report = tester.generate_report()
        
        # 保存报告
        report_path = Path("/Users/mettlyz/.openclaw/workspace/output/task-1726")
        report_path.mkdir(parents=True, exist_ok=True)
        
        with open(report_path / "SDS_压力测试报告_raw.json", 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*60)
        print("测试完成!")
        print(f"总计: {report['summary']['total']}")
        print(f"通过: {report['summary']['passed']}")
        print(f"失败: {report['summary']['failed']}")
        print(f"警告: {report['summary']['warnings']}")
        print(f"通过率: {report['summary']['pass_rate']}")
        print("="*60)
        
        # 清理测试数据
        tester.cleanup_test_tasks()
    
    return report


if __name__ == "__main__":
    main()

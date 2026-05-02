#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS 查询分析与性能基准测试工具
用于识别慢查询、测量响应时间、生成优化建议
"""

import sys
import time
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lib.db_connector import get_db_connection, execute_query, execute_update


class QueryAnalyzer:
    """查询分析器 - 识别慢查询并测量性能"""
    
    def __init__(self):
        self.results = {}
        self.baseline_sqls = [
            # Q1: 待处理任务按优先级排序（调度器核心查询）
            {
                'name': 'Q1-待处理任务优先级排序',
                'sql': """
                    SELECT id, number, title, status, priority, project_id,
                           retry_count, updated_at
                    FROM tasks 
                    WHERE status IN ('pending', 'failed_retryable')
                    ORDER BY priority DESC, id ASC
                    LIMIT 10
                """,
                'type': '调度器',
            },
            # Q2: 项目-任务关联分析（分析器核心查询）
            {
                'name': 'Q2-项目任务关联统计',
                'sql': """
                    SELECT p.id, p.name, p.status, 
                           COUNT(t.id) as task_count
                    FROM projects p
                    LEFT JOIN tasks t ON p.id = t.project_id
                    WHERE p.status = 'active'
                    GROUP BY p.id, p.name, p.status
                    ORDER BY p.id
                """,
                'type': '分析器',
            },
            # Q3: 停滞任务检测（分析器核心查询）
            {
                'name': 'Q3-停滞任务检测',
                'sql': """
                    SELECT id, number, title, status, updated_at, 
                           TIMESTAMPDIFF(HOUR, updated_at, NOW()) as hours_since_update
                    FROM tasks
                    WHERE status IN ('pending', 'in_progress')
                    ORDER BY hours_since_update DESC
                    LIMIT 20
                """,
                'type': '分析器',
            },
            # Q4: 已完成任务汇总（仪表盘查询）
            {
                'name': 'Q4-已完成任务汇总',
                'sql': """
                    SELECT id, number, title, status, task_summary, execution_log,
                           result_summary, updated_at
                    FROM tasks
                    WHERE status = 'completed'
                    ORDER BY updated_at DESC
                    LIMIT 20
                """,
                'type': '仪表盘',
            },
            # Q5: 状态统计（仪表盘核心查询）
            {
                'name': 'Q5-状态统计聚合',
                'sql': """
                    SELECT status, COUNT(*) as count
                    FROM tasks
                    GROUP BY status
                """,
                'type': '仪表盘',
            },
            # Q6: 自动生成任务统计
            {
                'name': 'Q6-自动任务统计',
                'sql': """
                    SELECT DATE(created_date) as date, COUNT(*) as count
                    FROM tasks
                    WHERE task_type = 'auto_generated'
                    GROUP BY DATE(created_date)
                    ORDER BY date DESC
                    LIMIT 30
                """,
                'type': '仪表盘',
            },
            # Q7: 附件数量统计
            {
                'name': 'Q7-附件统计',
                'sql': """
                    SELECT entity_type, COUNT(*) as count
                    FROM attachments
                    GROUP BY entity_type
                """,
                'type': '仪表盘',
            },
            # Q8: 项目模糊搜索（任务生成器）
            {
                'name': 'Q8-项目模糊搜索',
                'sql': """
                    SELECT id, name, status, priority
                    FROM projects
                    WHERE name LIKE '%SDS%' OR name LIKE '%系统%'
                    LIMIT 10
                """,
                'type': '生成器',
            },
            # Q9: 已取消任务分析
            {
                'name': 'Q9-取消任务分析',
                'sql': """
                    SELECT id, number, title, task_type, 
                           DATE(created_date) as created
                    FROM tasks 
                    ORDER BY id DESC 
                    LIMIT 1000
                """,
                'type': '安全护栏',
            },
            # Q10: 子任务-项目关联
            {
                'name': 'Q10-子任务关联',
                'sql': """
                    SELECT st.project_id, p.name as project_name, 
                           COUNT(st.id) as sub_count, st.status
                    FROM sub_tasks st
                    LEFT JOIN projects p ON st.project_id = p.id
                    GROUP BY st.project_id, p.name, st.status
                """,
                'type': '分析器',
            },
        ]
    
    def benchmark(self, iterations: int = 3) -> Dict:
        """执行基准测试，计算每次查询的响应时间"""
        print("=" * 70)
        print(f"  SDS 查询性能基准测试")
        print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  每查询迭代次数: {iterations}")
        print("=" * 70)
        
        all_results = []
        total_slow = 0
        
        for q in self.baseline_sqls:
            times = []
            errors = 0
            
            for i in range(iterations):
                try:
                    start = time.time()
                    result = execute_query(q['sql'])
                    elapsed = (time.time() - start) * 1000  # ms
                    times.append(elapsed)
                    
                    if elapsed > 1000:
                        print(f"  ⚠️  [{q['name']}] 迭代{i+1}: {elapsed:.1f}ms (>1000ms SLOW!)")
                    else:
                        print(f"  ✓ [{q['name']}] 迭代{i+1}: {elapsed:.1f}ms")
                except Exception as e:
                    errors += 1
                    print(f"  ✗ [{q['name']}] 迭代{i+1}: 错误 - {e}")
            
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)
                
                if avg_time > 1000:
                    total_slow += 1
                
                q_result = {
                    'name': q['name'],
                    'type': q['type'],
                    'avg_ms': round(avg_time, 2),
                    'min_ms': round(min_time, 2),
                    'max_ms': round(max_time, 2),
                    'is_slow': avg_time > 1000,
                    'errors': errors,
                    'iterations': len(times),
                    'result_count': len(result) if not errors else 0,
                }
                all_results.append(q_result)
                
                status = "⚠️ 慢查询" if avg_time > 1000 else "✅ 正常"
                print(f"  {'─' * 50}")
                print(f"  [{status}] {q['name']}")
                print(f"  平均: {avg_time:.2f}ms | 最小: {min_time:.2f}ms | 最大: {max_time:.2f}ms")
                if errors:
                    print(f"  错误: {errors}/{iterations}")
            print()
        
        # 生成报告
        report = {
            'test_time': datetime.now().isoformat(),
            'total_queries': len(all_results),
            'slow_queries': total_slow,
            'overall_avg_ms': round(sum(r['avg_ms'] for r in all_results) / len(all_results), 2) if all_results else 0,
            'results': all_results,
        }
        
        print("=" * 70)
        print(f"  测试完成: {report['total_queries']}个查询")
        print(f"  慢查询: {report['slow_queries']}个 (>{1000}ms)")
        print(f"  总体平均响应: {report['overall_avg_ms']:.2f}ms")
        print("=" * 70)
        
        return report
    
    def analyze_index_usage(self) -> Dict:
        """分析当前索引使用情况"""
        print("\n" + "=" * 70)
        print("  索引使用分析")
        print("=" * 70)
        
        # 检查现有索引
        tables = ['tasks', 'projects', 'attachments', 'sub_tasks', 'task_history', 'task_metrics']
        analysis = {}
        
        for table in tables:
            try:
                indexes = execute_query(f"SHOW INDEX FROM {table}")
                if indexes:
                    current = {}
                    for idx in indexes:
                        name = idx['Key_name']
                        if name not in current:
                            current[name] = {
                                'columns': [],
                                'unique': idx['Non_unique'] == 0,
                            }
                        current[name]['columns'].append(idx['Column_name'])
                    analysis[table] = list(current.keys())
                    print(f"  📊 {table}: {list(current.keys())}")
                else:
                    analysis[table] = []
                    print(f"  📊 {table}: 无索引")
            except Exception as e:
                analysis[table] = f"错误: {e}"
                print(f"  ✗ {table}: 查询失败 - {e}")
        
        return analysis


def main():
    analyzer = QueryAnalyzer()
    
    # 阶段1: 分析现有索引
    print("\n" + "=" * 70)
    print("  阶段1: 数据库索引分析")
    print("=" * 70)
    index_analysis = analyzer.analyze_index_usage()
    
    # 阶段2: 执行基准测试
    print("\n" + "=" * 70)
    print("  阶段2: 查询性能基准测试")
    print("=" * 70)
    benchmark_result = analyzer.benchmark(iterations=3)
    
    # 保存结果
    output_path = Path(__file__).parent / "sds_benchmark_before.json"
    with open(output_path, 'w') as f:
        json.dump({
            'index_analysis': index_analysis,
            'benchmark': benchmark_result,
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 基准测试结果已保存: {output_path}")
    
    # 输出优化建议
    print("\n" + "=" * 70)
    print("  优化建议")
    print("=" * 70)
    if benchmark_result['slow_queries'] > 0:
        print(f"  发现 {benchmark_result['slow_queries']} 个慢查询，建议:")
        print(f"  1. 为 tasks 表添加 status+priority 复合索引")
        print(f"  2. 为 tasks 表添加 updated_at 索引")
        print(f"  3. 为 projects 表添加 status 和 name 索引")
        print(f"  4. 为 sub_tasks 表添加 project_id 和 status 索引")
        print(f"  5. 实现连接池减少连接开销")
    else:
        print("  未发现慢查询，系统性能良好")
    
    return benchmark_result


if __name__ == '__main__':
    main()

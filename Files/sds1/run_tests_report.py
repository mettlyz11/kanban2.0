#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速测试运行器 - 生成测试报告"""
import sys
from config_loader import get_config
import os
import unittest
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "core"))

from core.task_generation_guard_v46 import (
    IdempotencyLayer, RateLimitLayer, SemanticDedupLayer,
    TaskGenerationGuard, GuardDecision
)

def run_all_tests():
    """运行所有测试并生成报告"""
    results = {
        'timestamp': datetime.now().isoformat(),
        'version': 'V4.6',
        'tests': {},
        'summary': {'total': 0, 'passed': 0, 'failed': 0}
    }
    
    print("=" * 70)
    print("SDS任务生成三重保障系统 V4.6 - 测试执行")
    print("=" * 70)
    
    # 测试1: 幂等性层
    print("\n【Layer 1: 幂等性保障测试】")
    idem_tests = test_idempotency()
    results['tests']['idempotency'] = idem_tests
    
    # 测试2: 频率限制层
    print("\n【Layer 2: 频率限制测试】")
    rate_tests = test_rate_limit()
    results['tests']['rate_limit'] = rate_tests
    
    # 测试3: 语义去重层
    print("\n【Layer 3: 语义去重测试】")
    dedup_tests = test_semantic_dedup()
    results['tests']['semantic_dedup'] = dedup_tests
    
    # 测试4: 集成测试
    print("\n【集成测试: 三重保障协调器】")
    integration_tests = test_integration()
    results['tests']['integration'] = integration_tests
    
    # 汇总
    total = passed = failed = 0
    for category in results['tests'].values():
        for test in category:
            total += 1
            if test['status'] == 'PASS':
                passed += 1
            else:
                failed += 1
    
    results['summary'] = {
        'total': total,
        'passed': passed,
        'failed': failed,
        'pass_rate': f"{passed/total*100:.1f}%" if total > 0 else "0%"
    }
    
    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"通过率: {results['summary']['pass_rate']}")
    
    return results

def test_idempotency():
    """测试幂等性层"""
    tests = []
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'test.log')
    layer = IdempotencyLayer(log_file=log_file)
    
    # 测试1: 确定性键生成
    try:
        k1 = layer.generate_key("测试任务", 75, "描述")
        k2 = layer.generate_key("测试任务", 75, "描述")
        assert k1 == k2, "相同输入应生成相同键"
        assert len(k1) == 16, "键长度应为16"
        tests.append({'name': '确定性键生成', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '确定性键生成', 'status': 'FAIL', 'error': str(e)})
    
    # 测试2: 不同输入不同键
    try:
        k1 = layer.generate_key("任务A", 75)
        k2 = layer.generate_key("任务B", 75)
        assert k1 != k2, "不同标题应生成不同键"
        tests.append({'name': '不同输入不同键', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '不同输入不同键', 'status': 'FAIL', 'error': str(e)})
    
    # 测试3: 新键安全检查
    try:
        key = layer.generate_key("全新任务", 999)
        result = layer.check(key)
        assert result['is_safe'] == True, "新键应安全"
        tests.append({'name': '新键安全检查', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '新键安全检查', 'status': 'FAIL', 'error': str(e)})
    
    # 测试4: 已存在键拦截
    try:
        key = layer.generate_key("重复任务", 999)
        layer.record(key, 12345, "重复任务", 999)
        result = layer.check(key)
        assert result['is_safe'] == False, "已存在键应被拦截"
        assert result['local_task_id'] == 12345
        tests.append({'name': '已存在键拦截', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '已存在键拦截', 'status': 'FAIL', 'error': str(e)})
    
    # 测试5: 空标题处理
    try:
        k = layer.generate_key("")
        assert len(k) == 16, "空标题也能生成键"
        tests.append({'name': '空标题处理', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '空标题处理', 'status': 'FAIL', 'error': str(e)})
    
    # 测试6: Unicode支持
    try:
        k1 = layer.generate_key("日本語タスク", 1)
        k2 = layer.generate_key("日本語タスク", 1)
        assert k1 == k2, "Unicode标题键应一致"
        tests.append({'name': 'Unicode支持', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': 'Unicode支持', 'status': 'FAIL', 'error': str(e)})
    
    # 清理
    os.remove(log_file)
    os.rmdir(temp_dir)
    
    for t in tests:
        status = "✅" if t['status'] == 'PASS' else "❌"
        print(f"  {status} {t['name']}")
    
    return tests

def test_rate_limit():
    """测试频率限制层"""
    tests = []
    layer = RateLimitLayer(max_tasks=2, max_pending=3, window_hours=24)
    
    # 测试1: 默认配置
    try:
        default = RateLimitLayer()
        assert default.max_tasks == 2
        assert default.max_pending == 3
        assert default.window_hours == 24
        tests.append({'name': '默认配置验证', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '默认配置验证', 'status': 'FAIL', 'error': str(e)})
    
    # 测试2: 自定义配置
    try:
        custom = RateLimitLayer(max_tasks=5, max_pending=10, window_hours=12)
        assert custom.max_tasks == 5
        assert custom.max_pending == 10
        assert custom.window_hours == 12
        tests.append({'name': '自定义配置', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '自定义配置', 'status': 'FAIL', 'error': str(e)})
    
    # 测试3: 返回结构检查
    try:
        result = layer.check_rate_limit(999999)
        assert 'can_generate' in result
        assert 'current_count' in result
        assert 'max_allowed' in result
        tests.append({'name': '返回结构检查', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '返回结构检查', 'status': 'FAIL', 'error': str(e)})
    
    # 测试4: 零上限拦截
    try:
        zero_layer = RateLimitLayer(max_tasks=0)
        result = zero_layer.check_rate_limit(1)
        assert result['can_generate'] == False
        tests.append({'name': '零上限拦截', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '零上限拦截', 'status': 'FAIL', 'error': str(e)})
    
    # 测试5: 组合检查
    try:
        result = layer.check_all(999999)
        assert 'can_generate' in result
        assert 'rate_check' in result
        assert 'pending_check' in result
        tests.append({'name': '组合检查结构', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '组合检查结构', 'status': 'FAIL', 'error': str(e)})
    
    for t in tests:
        status = "✅" if t['status'] == 'PASS' else "❌"
        print(f"  {status} {t['name']}")
    
    return tests

def test_semantic_dedup():
    """测试语义去重层"""
    tests = []
    layer = SemanticDedupLayer(prefix_length=15, similarity_threshold=0.85)
    
    # 测试1: Levenshtein距离-相同字符串
    try:
        d = SemanticDedupLayer.levenshtein_distance("hello", "hello")
        assert d == 0, "相同字符串距离为0"
        tests.append({'name': 'Levenshtein相同字符串', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': 'Levenshtein相同字符串', 'status': 'FAIL', 'error': str(e)})
    
    # 测试2: Levenshtein距离-空字符串
    try:
        d = SemanticDedupLayer.levenshtein_distance("", "")
        assert d == 0, "空字符串距离为0"
        tests.append({'name': 'Levenshtein空字符串', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': 'Levenshtein空字符串', 'status': 'FAIL', 'error': str(e)})
    
    # 测试3: 相似度-相同字符串
    try:
        s = SemanticDedupLayer.string_similarity("test", "test")
        assert s == 1.0, "相同字符串相似度为1.0"
        tests.append({'name': '相似度相同字符串', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '相似度相同字符串', 'status': 'FAIL', 'error': str(e)})
    
    # 测试4: 相似度-阈值边界
    try:
        # 20字符中差2个: 1 - 2/20 = 0.90 > 0.85
        s1 = "ABCDEFGHIJ1234567890"
        s2 = "ABCDEFGHIJ12345678XX"
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        assert sim > 0.85, "应高于阈值"
        tests.append({'name': '相似度阈值边界(上)', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '相似度阈值边界(上)', 'status': 'FAIL', 'error': str(e)})
    
    # 测试5: 相似度-低于阈值
    try:
        # 25字符中差4个: 1 - 4/25 = 0.84 < 0.85
        s1 = "A" * 25
        s2 = "A" * 21 + "B" * 4
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        assert sim < 0.85, "应低于阈值"
        tests.append({'name': '相似度阈值边界(下)', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '相似度阈值边界(下)', 'status': 'FAIL', 'error': str(e)})
    
    # 测试6: 文本标准化
    try:
        result = SemanticDedupLayer.normalize_text("Hello, World!")
        assert result == "helloworld", "应去除标点并转小写"
        tests.append({'name': '文本标准化', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '文本标准化', 'status': 'FAIL', 'error': str(e)})
    
    # 测试7: 空标题不重复
    try:
        result = layer.check("")
        assert result['is_duplicate'] == False
        tests.append({'name': '空标题不重复', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '空标题不重复', 'status': 'FAIL', 'error': str(e)})
    
    # 测试8: 超长字符串相似度
    try:
        l1 = "A" * 1000
        l2 = "A" * 999 + "B"
        sim = SemanticDedupLayer.string_similarity(l1, l2)
        assert sim > 0.99, "超长字符串微小差异应高相似度"
        tests.append({'name': '超长字符串相似度', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '超长字符串相似度', 'status': 'FAIL', 'error': str(e)})
    
    for t in tests:
        status = "✅" if t['status'] == 'PASS' else "❌"
        print(f"  {status} {t['name']}")
    
    return tests

def test_integration():
    """测试集成"""
    tests = []
    
    # 测试1: 初始化
    try:
        guard = TaskGenerationGuard()
        assert guard.config['max_tasks_per_24h'] == 2
        assert guard.config['similarity_threshold'] == 0.85
        assert guard.config['prefix_length'] == 15
        tests.append({'name': '协调器初始化', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '协调器初始化', 'status': 'FAIL', 'error': str(e)})
    
    # 测试2: 新任务通过检查
    try:
        guard = TaskGenerationGuard()
        unique_title = f"唯一测试任务_{time.time()}"
        result = guard.check(unique_title, 999, "测试描述")
        assert result.can_generate == True
        assert result.decision == GuardDecision.ALLOWED
        tests.append({'name': '新任务通过检查', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '新任务通过检查', 'status': 'FAIL', 'error': str(e)})
    
    # 测试3: 重复任务拦截
    try:
        guard = TaskGenerationGuard()
        title = f"幂等测试_{time.time()}"
        r1 = guard.check(title, 999, "测试")
        assert r1.can_generate == True, "第一次应通过"
        
        # 记录幂等性
        if r1.idempotency_key:
            guard.idempotency.record(r1.idempotency_key, 99999, title, 999)
        
        r2 = guard.check(title, 999, "测试")
        assert r2.can_generate == False, "第二次应被拦截"
        assert r2.decision == GuardDecision.BLOCKED_IDEMPOTENT
        tests.append({'name': '重复任务拦截', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '重复任务拦截', 'status': 'FAIL', 'error': str(e)})
    
    # 测试4: 过滤空列表
    try:
        guard = TaskGenerationGuard()
        passed, blocked = guard.filter_recommendations([])
        assert passed == [] and blocked == []
        tests.append({'name': '过滤空列表', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '过滤空列表', 'status': 'FAIL', 'error': str(e)})
    
    # 测试5: 批次ID生成
    try:
        guard = TaskGenerationGuard()
        assert guard.batch_id.startswith('V46-')
        tests.append({'name': '批次ID格式', 'status': 'PASS'})
    except AssertionError as e:
        tests.append({'name': '批次ID格式', 'status': 'FAIL', 'error': str(e)})
    
    for t in tests:
        status = "✅" if t['status'] == 'PASS' else "❌"
        print(f"  {status} {t['name']}")
    
    return tests

if __name__ == "__main__":
    results = run_all_tests()
    
    # 保存结果
    output_file = Path(get_config("paths.output") + "/task-2119")
    output_file.mkdir(parents=True, exist_ok=True)
    
    with open(output_file / "test_results_2026-04-27.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n测试结果已保存: {output_file / 'test_results_2026-04-27.json'}")

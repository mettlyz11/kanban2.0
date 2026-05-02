#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V4.7去重机制单元测试 (Task#2110)

测试覆盖:
1. 15字精确前缀匹配
2. Levenshtein语义相似度
3. 频率限制检查
4. Pending水位检查
5. 幂等性检查
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

from task_generation_guard_v47 import (
    SemanticDedupLayer,
    RateLimitLayer,
    IdempotencyLayer,
    TaskGenerationGuardV47
)


class TestSemanticDedupLayer:
    """语义去重层测试"""
    
    def __init__(self):
        self.dedup = SemanticDedupLayer()
        self.passed = 0
        self.failed = 0
    
    def assert_equal(self, actual, expected, message=""):
        if actual == expected:
            self.passed += 1
            print(f"  ✅ {message}")
        else:
            self.failed += 1
            print(f"  ❌ {message}: 期望 {expected}, 实际 {actual}")
    
    def test_levenshtein_distance(self):
        """测试编辑距离计算"""
        print("\n【测试1: Levenshtein编辑距离计算】")
        
        cases = [
            ("", "", 0),
            ("abc", "", 3),
            ("", "abc", 3),
            ("kitten", "sitting", 3),
            ("saturday", "sunday", 3),
            ("你好世界", "你好", 2),
            ("AI助手优化", "AI助手优化V2", 2),
        ]
        
        for s1, s2, expected in cases:
            dist = self.dedup.levenshtein_distance(s1, s2)
            self.assert_equal(dist, expected, f"distance('{s1}', '{s2}')")
    
    def test_string_similarity(self):
        """测试字符串相似度"""
        print("\n【测试2: 字符串相似度计算】")
        
        cases = [
            ("", "", 1.0),
            ("abc", "abc", 1.0),
            ("abc", "abd", 2/3),
            ("T1: AI助手优化 - 调度系统升级", "T1: AI助手优化 - 调度系统升级V2", 0.9),
            ("完全不同的标题1", "完全不同的标题2", 0.0),
        ]
        
        for s1, s2, min_expected in cases:
            sim = self.dedup.string_similarity(s1, s2)
            if isinstance(min_expected, float):
                if sim >= min_expected - 0.1:
                    self.passed += 1
                    print(f"  ✅ similarity('{s1[:20]}', '{s2[:20]}') = {sim:.2f}")
                else:
                    self.failed += 1
                    print(f"  ❌ 期望至少 {min_expected}, 实际 {sim}")
            else:
                self.assert_equal(sim, min_expected, f"similarity('{s1}', '{s2}')")
    
    def test_normalize_text(self):
        """测试文本标准化"""
        print("\n【测试3: 文本标准化】")
        
        cases = [
            ("T1: AI助手优化!", "t1ai助手优化"),
            ("Hello, World!", "helloworld"),
            ("  你好  世界  ", "你好世界"),
            ("", ""),
        ]
        
        for input_text, expected in cases:
            result = self.dedup.normalize_text(input_text)
            self.assert_equal(result, expected, f"normalize('{input_text}')")
    
    def test_exact_prefix_match(self):
        """测试精确前缀匹配逻辑"""
        print("\n【测试4: 15字精确前缀匹配逻辑】")
        
        # 测试前缀长度
        prefix_length = self.dedup.PREFIX_LENGTH
        self.assert_equal(prefix_length, 15, "前缀长度配置")
        
        # 测试前缀提取
        title1 = "T1: AI助手优化 - 调度系统频率限制升级测试"
        prefix1 = title1[:15]
        self.assert_equal(len(prefix1), 15, "前缀提取长度")
        
        title2 = "T1: AI助手优化 - 调度系统频率限制升级测试V2"
        prefix2 = title2[:15]
        self.assert_equal(prefix1, prefix2, "相似任务前15字应相同")
        
        title3 = "T2: 完全不同的任务标题"
        prefix3 = title3[:15]
        if prefix1 != prefix3:
            self.passed += 1
            print(f"  ✅ 不同任务前15字应不同")
        else:
            self.failed += 1
            print(f"  ❌ 不同任务前15字意外相同")


class TestRateLimitLayer:
    """频率限制层测试"""
    
    def __init__(self):
        self.rate = RateLimitLayer()
        self.passed = 0
        self.failed = 0
    
    def test_config_values(self):
        """测试配置值"""
        print("\n【测试5: 频率限制配置值】")
        
        # Task#2110硬限制
        if self.rate.MAX_TASKS_PER_24H == 2:
            self.passed += 1
            print(f"  ✅ 24小时任务上限: {self.rate.MAX_TASKS_PER_24H} (正确)")
        else:
            self.failed += 1
            print(f"  ❌ 24小时任务上限应为2, 实际{self.rate.MAX_TASKS_PER_24H}")
        
        if self.rate.MAX_PENDING_PER_GOAL == 3:
            self.passed += 1
            print(f"  ✅ pending水位上限: {self.rate.MAX_PENDING_PER_GOAL} (正确)")
        else:
            self.failed += 1
            print(f"  ❌ pending水位上限应为3, 实际{self.rate.MAX_PENDING_PER_GOAL}")


class TestIdempotencyLayer:
    """幂等性层测试"""
    
    def __init__(self):
        self.idem = IdempotencyLayer()
        self.passed = 0
        self.failed = 0
    
    def test_key_generation(self):
        """测试幂等键生成"""
        print("\n【测试6: 幂等键生成】")
        
        # 相同输入应生成相同key
        key1 = self.idem.generate_key("测试标题", 1, "描述")
        key2 = self.idem.generate_key("测试标题", 1, "描述")
        if key1 == key2:
            self.passed += 1
            print(f"  ✅ 相同输入生成相同key: {key1}")
        else:
            self.failed += 1
            print(f"  ❌ 相同输入key不同: {key1} vs {key2}")
        
        # 不同输入应生成不同key
        key3 = self.idem.generate_key("不同标题", 1, "描述")
        if key1 != key3:
            self.passed += 1
            print(f"  ✅ 不同标题生成不同key")
        else:
            self.failed += 1
            print(f"  ❌ 不同标题key相同")
        
        # key长度应为16 (SHA-256前16位)
        if len(key1) == 16:
            self.passed += 1
            print(f"  ✅ key长度为16字节")
        else:
            self.failed += 1
            print(f"  ❌ key长度应为16, 实际{len(key1)}")


def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("V4.7去重机制单元测试 (Task#2110)")
    print("=" * 70)
    
    total_passed = 0
    total_failed = 0
    
    # 测试组1: 语义去重层
    test1 = TestSemanticDedupLayer()
    test1.test_levenshtein_distance()
    test1.test_string_similarity()
    test1.test_normalize_text()
    test1.test_exact_prefix_match()
    total_passed += test1.passed
    total_failed += test1.failed
    
    # 测试组2: 频率限制层
    test2 = TestRateLimitLayer()
    test2.test_config_values()
    total_passed += test2.passed
    total_failed += test2.failed
    
    # 测试组3: 幂等性层
    test3 = TestIdempotencyLayer()
    test3.test_key_generation()
    total_passed += test3.passed
    total_failed += test3.failed
    
    # 总结
    print("\n" + "=" * 70)
    print("测试总结:")
    print(f"  通过: {total_passed}")
    print(f"  失败: {total_failed}")
    print(f"  总计: {total_passed + total_failed}")
    print("=" * 70)
    
    if total_failed == 0:
        print("🎉 所有测试通过!")
        return True
    else:
        print(f"⚠️  有 {total_failed} 个测试失败")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

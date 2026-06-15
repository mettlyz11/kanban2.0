#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V4.3 任务重复检测与自动去重机制（系统脚本）
==============================================
任务: #1928 - AI助手架构优化
作者: AI助手 Dudu 🐕
日期: 2026-04-25

三种相似度计算方法:
1. Jaccard相似度 — 标题分词后交集/并集
2. TF-IDF余弦相似度 — 标题+描述 语义空间距离
3. 编辑距离相似度(Levenshtein) — 防止微小措辞变化
4. 前缀相似度 — 标题前N字匹配比例

增强: 自动剥离 "TX: xxx - " 前缀，防止T标签漂移导致漏判

使用方式:
    python3 T1_去重检测算法实现.py                    # 扫描全部重复
    python3 T1_去重检测算法实现.py --check "新任务标题" # 前置检查
    python3 T1_去重检测算法实现.py --cleanup --no-dry-run  # 执行清理
    python3 T1_去重检测算法实现.py --test            # 运行单元测试
"""

import sys
import re
import os
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from math import sqrt

# ─── 数据库连接 ───────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))
try:
    from lib.db_connector import get_db_connection, execute_query, execute_update
    HAS_DB = True
except ImportError:
    HAS_DB = False
    # print("⚠️ 无法加载db_connector，将以离线模式运行")


# ═══════════════════════════════════════════════════════════
# 第一部分: 文本预处理 + 相似度计算函数
# ═══════════════════════════════════════════════════════════

def strip_t_prefix(text: str) -> str:
    """
    剥离任务标题中的 T-prefix 和领域标题前缀。
    
    "T4: 财富增值与资产管理 - 黄金ETF建仓" → "黄金ETF建仓"
    "T6: 行业影响力与社会参与 - AI催化产业联盟" → "AI催化产业联盟"
    """
    if not text:
        return ""
    # 去掉 "TX: " 前缀
    text = re.sub(r'^T\d+[：:]\s*', '', text)
    # 去掉 "xxx - " 或 "xxx — " 的领域前缀（保留冒号后的内容）
    text = re.sub(r'^[\u4e00-\u9fff]+\s*[-—]\s*', '', text)
    # 也处理 "xxx - xxx - " 双前缀的情况
    text = re.sub(r'^.+?[-—]\s*.+?[-—]\s*', '', text, count=1)
    return text.strip()


def tokenize(text: str) -> set:
    """中文文本分词（基于字符bigram + 英文单词切分）"""
    if not text:
        return set()
    text = text.lower().strip()
    words = set()
    # 提取英文单词
    words.update(re.findall(r'[a-z0-9]+', text))
    # 中文: 双字组合 (bigram) 以捕获语义
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    for i in range(len(chinese_chars) - 1):
        words.add(chinese_chars[i] + chinese_chars[i+1])
    words.update(chinese_chars)
    return words


def jaccard_similarity(text_a: str, text_b: str, strip_prefix: bool = True) -> float:
    """
    Jaccard相似度: |A∩B| / |A∪B|
    适用: 短文本快速匹配，阈值建议 ≥0.6
    """
    if strip_prefix:
        text_a = strip_t_prefix(text_a)
        text_b = strip_t_prefix(text_b)
    set_a = tokenize(text_a)
    set_b = tokenize(text_b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def tfidf_similarity(text_a: str, text_b: str, 
                     global_corpus: Optional[List[str]] = None,
                     strip_prefix: bool = True) -> float:
    """
    TF-IDF 余弦相似度
    适用: 标题+描述的长文本语义匹配，阈值建议 ≥0.5
    """
    if strip_prefix:
        text_a = strip_t_prefix(text_a)
        text_b = strip_t_prefix(text_b)
    
    corpus = global_corpus or [text_a, text_b]
    docs = [list(tokenize(t)) for t in [text_a, text_b]]
    all_tokens = set()
    for d in docs:
        all_tokens.update(d)
    
    N = len(corpus)
    idf = {}
    for token in all_tokens:
        doc_count = sum(1 for t in [text_a, text_b] if token in tokenize(t))
        idf[token] = sqrt(N / (doc_count + 1)) if doc_count > 0 else 0
    
    vectors = []
    for d in docs:
        tf = defaultdict(int)
        for token in d:
            tf[token] += 1
        max_tf = max(tf.values()) if tf else 1
        vec = {}
        for token in all_tokens:
            tf_val = tf.get(token, 0) / max_tf
            vec[token] = tf_val * idf.get(token, 0)
        vectors.append(vec)
    
    vec_a, vec_b = vectors
    dot = sum(vec_a.get(t, 0) * vec_b.get(t, 0) for t in all_tokens)
    norm_a = sqrt(sum(v*v for v in vec_a.values()))
    norm_b = sqrt(sum(v*v for v in vec_b.values()))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def levenshtein_similarity(text_a: str, text_b: str, strip_prefix: bool = True) -> float:
    """
    编辑距离(Levenshtein)相似度: 1 - (编辑距离 / max_len)
    适用: 检测微小措辞变化，阈值建议 ≥0.7
    """
    if strip_prefix:
        a = strip_t_prefix(text_a)
        b = strip_t_prefix(text_b)
    else:
        a = text_a
        b = text_b
    
    a = a.lower().strip()[:50]
    b = b.lower().strip()[:50]
    
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    
    distance = dp[m][n]
    max_len = max(m, n)
    return 1.0 - (distance / max_len) if max_len > 0 else 0.0


def prefix_similarity(text_a: str, text_b: str, prefix_len: int = 20,
                      strip_prefix: bool = True) -> float:
    """
    前缀相似度: 比较前N个字符的匹配比例
    适用: 快速初筛，阈值建议 ≥0.75
    """
    if strip_prefix:
        a = strip_t_prefix(text_a)
        b = strip_t_prefix(text_b)
    else:
        a = text_a
        b = text_b
    
    a = a.strip()[:prefix_len]
    b = b.strip()[:prefix_len]
    
    if not a or not b:
        return 0.0
    match = sum(1 for i in range(min(len(a), len(b))) if a[i] == b[i])
    return match / max(len(a), len(b))


# ═══════════════════════════════════════════════════════════
# 第二部分: 综合去重检测器
# ═══════════════════════════════════════════════════════════

THRESHOLDS = {
    'jaccard': 0.60,
    'tfidf': 0.50,
    'levenshtein': 0.70,
    'prefix': 0.80,
}


class DupDetector:
    """任务重复检测器"""
    
    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = thresholds or THRESHOLDS.copy()
        self.tasks: List[Dict] = []
        self.dup_groups: List[List[Dict]] = []
    
    def load_tasks_from_db(self, status_filter: Optional[str] = None):
        """从数据库加载任务"""
        if not HAS_DB:
            # print("❌ 无数据库连接，请使用 load_tasks_from_list()")
            return
        
        sql = "SELECT id, title, description, status, goal_id, created_at FROM tasks"
        params = None
        if status_filter:
            sql += " WHERE status = %s"
            params = (status_filter,)
        sql += " ORDER BY created_at DESC"
        
        rows = execute_query(sql, params)
        self.tasks = []
        for r in rows:
            self.tasks.append({
                'id': r['id'],
                'title': r['title'] or '',
                'description': r['description'] or '',
                'status': r['status'],
                'goal_id': r['goal_id'],
                'created_at': str(r['created_at']),
            })
        # print(f"✅ 已加载 {len(self.tasks)} 条任务")
    
    def load_tasks_from_list(self, task_list: List[Dict]):
        """从列表加载任务（离线模式）"""
        self.tasks = task_list
    
    def check_dup(self, new_title: str, new_desc: str = "", new_goal: Optional[int] = None,
                  verbose: bool = True) -> Tuple[bool, Optional[Dict], Dict]:
        """
        前置检查: 检测新任务是否与现有任务重复
        
        Returns:
            (is_duplicate, matched_task, scores)
        """
        best_match = None
        best_scores = {}
        max_combined = 0.0
        
        # 剥离T前缀后的标题用于显示
        clean_title = strip_t_prefix(new_title)
        # print(f"\n🔍 前置检查: '{new_title[:60]}...'")
        # print(f"   剥离前缀后: '{clean_title[:60]}...'")
        # print(f"   对比 {len(self.tasks)} 条现有任务:\n")
        
        for task in self.tasks:
            scores = self._compute_similarity(new_title, new_desc, task)
            combined = self._combined_score(scores)
            
            if combined > max_combined:
                max_combined = combined
                best_match = task
                best_scores = scores
            
            if verbose:
                flag = "⚠️" if self._is_dup(scores) else "  "
                # print(f"  [{flag}] ID={task['id']:>4}: "
                      f"J={scores['jaccard']:.3f} "
                      f"T={scores['tfidf']:.3f} "
                      f"L={scores['levenshtein']:.3f} "
                      f"P={scores['prefix']:.3f} "
                      f"组合={combined:.3f} "
                      f"'{task['title'][:40]}...'")
        
        is_dup = self._is_dup(best_scores)
        if is_dup and verbose:
            # print(f"\n🔴 重复! 最高匹配 -> ID={best_match['id']}: "
                  f"'{best_match['title'][:50]}'")
        elif verbose:
            # print(f"\n✅ 不重复")
        
        return is_dup, best_match, best_scores
    
    def find_all_duplicates(self, only_pending: bool = False, min_group_size: int = 2) -> List[List[Dict]]:
        """
        扫描全部任务，找出所有重复组
        """
        candidates = self.tasks
        if only_pending:
            candidates = [t for t in self.tasks if t['status'] in ('pending', 'in_progress')]
        
        self.dup_groups = []
        processed = set()
        
        for i, task_a in enumerate(candidates):
            if task_a['id'] in processed:
                continue
            
            group = [task_a]
            for j, task_b in enumerate(candidates):
                if i >= j or task_b['id'] in processed:
                    continue
                scores = self._compute_similarity(
                    task_a['title'], task_a['description'], task_b
                )
                if self._is_dup(scores):
                    group.append(task_b)
            
            if len(group) >= min_group_size:
                ids = [t['id'] for t in group]
                self.dup_groups.append(group)
                processed.update(ids)
                # print(f"📋 重复组: {', '.join(str(x) for x in ids)} "
                      f"| {group[0]['title'][:50]}...")
        
        # print(f"\n✅ 共发现 {len(self.dup_groups)} 组重复任务 "
              f"(涉及 {len(processed)} 条任务)")
        return self.dup_groups
    
    def _compute_similarity(self, title: str, desc: str, task: Dict) -> Dict:
        full_a = f"{title} {desc}"
        full_b = f"{task['title']} {task['description']}"
        return {
            'jaccard': jaccard_similarity(full_a, full_b),
            'tfidf': tfidf_similarity(full_a, full_b),
            'levenshtein': levenshtein_similarity(title, task['title']),
            'prefix': prefix_similarity(title, task['title']),
        }
    
    def _is_dup(self, scores: Dict) -> bool:
        """
        综合判定是否重复（OR逻辑: 任意两项超过阈值即判定重复）
        增强: 比单OR更稳健，防止单一指标意外波动
        """
        if not scores:
            return False
        above = sum(1 for k, v in scores.items() if v >= self.thresholds.get(k, 0.5))
        return above >= 2
    
    def _combined_score(self, scores: Dict) -> float:
        """加权组合得分"""
        weights = {'jaccard': 0.25, 'tfidf': 0.35, 'levenshtein': 0.15, 'prefix': 0.25}
        return sum(scores.get(k, 0) * w for k, w in weights.items())


# ═══════════════════════════════════════════════════════════
# 第三部分: 清理执行
# ═══════════════════════════════════════════════════════════

def cleanup_redundant(dup_groups: List[List[Dict]], 
                       dry_run: bool = True) -> int:
    """清理重复任务"""
    if not HAS_DB:
        # print("❌ 无数据库连接，无法执行清理")
        return 0
    
    count = 0
    for group in dup_groups:
        if len(group) < 2:
            continue
        
        # 按创建时间排序，保留最早的
        sorted_group = sorted(group, key=lambda x: x['created_at'])
        keep = sorted_group[0]
        to_remove = sorted_group[1:]
        
        # print(f"\n保留: ID={keep['id']} [{keep['status']}] {keep['title'][:50]}")
        for t in to_remove:
            action = "(DRY RUN)" if dry_run else ""
            # print(f"  → 标记冗余: ID={t['id']} [{t['status']}] {t['title'][:50]} {action}")
            
            if not dry_run:
                execute_update(
                    "UPDATE tasks SET status = 'redundant', "
                    "notes = CONCAT(COALESCE(notes,''), "
                    "' 由去重检测(ID=1928)标记为冗余，保留任务ID=', %s), "
                    "updated_at = NOW() WHERE id = %s",
                    (str(keep['id']), t['id'])
                )
            count += 1
    
    if dry_run:
        # print(f"\n📋 模拟运行，共识别 {count} 条应清理任务")
        # print("   使用 --no-dry-run 执行实际清理")
    else:
        # print(f"\n✅ 实际清理完成，共处理 {count} 条任务")
    
    return count


# ═══════════════════════════════════════════════════════════
# 第四部分: 单元测试
# ═══════════════════════════════════════════════════════════

def run_tests():
    """验证算法有效性"""
    # print("=" * 60)
    # print("🔬 去重算法单元测试（含T前缀剥离）")
    # print("=" * 60)
    
    tests = [
        # (title_a, title_b, expected_is_dup, description)
        ("T4: 财富增值 - AI催化赛道一级市场投资标的系统性扫描与筛选",
         "T4: 财富增值 - AI催化赛道一级市场投资机会系统性扫描与筛选",
         True, "几乎相同标题（差"机会"二字）"),
        
        ("T4: 财富增值 - AI催化赛道一级市场投资标的系统性扫描与筛选",
         "T4: 财富增值 - AI催化赛道一级市场投资标的系统性扫描与筛选",
         True, "完全相同的标题"),
        
        ("T5: 子女教育 - 北京国际学校择校调研与2026-2027申请时间轴",
         "T5: 子女教育 - 北京国际学校2026-2027择校深度调研与申请时间轴",
         True, "仅措辞顺序不同"),
        
        ("T4: 财富增值与资产管理 - 黄金ETF建仓时机分析与执行计划",
         "T4: 资产配置与产业投资 - 黄金ETF Q2建仓时机量化分析",
         True, "同一主题不同T前缀（黄金ETF建仓）"),
        
        ("T1: AI助手优化 - 任务自动生成引擎V4.4版本迭代与优化",
         "T3: 学术影响力 - NSFC 2026面上项目AI催化领域精准选题与申报时间表",
         False, "完全不同领域的任务"),
        
        ("T6: 行业影响力 - 2026年AI催化领域顶级会议投稿与speaker申请",
         "T6: 行业影响力与社会参与 - AI催化产业联盟发起与2026行业峰会策划",
         False, "不同主题（会议投稿 vs 产业联盟）"),
        
        ("T7: 健康管理 - 2026年度全面体检方案与健康指标跟踪体系",
         "T7: 健康管理 - 2026年度全面体检方案与健康指标跟踪体系",
         True, "完全相同标题"),
        
        ("T2: 和光智成融资 - AI催化剂赛道2026年Pre-A轮估值模型与投资人对接清单",
         "T3: 学术影响力 - Periodic Labs技术路线深度拆解与差异化竞争分析",
         False, "完全不同的T领域和主题"),
        
        ("T6: 行业影响力与社会参与 - AI催化产业联盟发起与2026行业峰会策划",
         "T6: 行业影响力与社会参与 - AI催化产业联盟发起与2026行业峰会策划",
         True, "完全相同（pending重复）"),
        
        ("T7: 健康管理 - 2026年度全面体检方案与健康指标跟踪体系",
         "T6: 身心健康与生活质量 - 2026年春季健康管理计划制定",
         False, "不同T领域但都有健康相关"),
    ]
    
    passed = 0
    failed = 0
    
    for title_a, title_b, expected, desc in tests:
        jac = jaccard_similarity(title_a, title_b)
        tfidf = tfidf_similarity(title_a, title_b)
        lev = levenshtein_similarity(title_a, title_b)
        pre = prefix_similarity(title_a, title_b)
        
        # OR逻辑: 2项以上超过阈值 = 重复
        th = THRESHOLDS
        above = sum([jac >= th['jaccard'], tfidf >= th['tfidf'], 
                     lev >= th['levenshtein'], pre >= th['prefix']])
        is_dup = above >= 2
        
        status = "✅" if is_dup == expected else "❌"
        if is_dup == expected:
            passed += 1
        else:
            failed += 1
        
        clean_a = strip_t_prefix(title_a)[:30]
        clean_b = strip_t_prefix(title_b)[:30]
        # print(f"\n{status} {desc}")
        # print(f"   剥离后: '{clean_a}' vs '{clean_b}'")
        # print(f"   J={jac:.3f} T={tfidf:.3f} L={lev:.3f} P={pre:.3f} | "
              f"超阈值={above}/4 → {'重复' if is_dup else '不重复'} "
              f"(期望: {'重复' if expected else '不重复'})")
    
    # print(f"\n{'='*60}")
    # print(f"📊 结果: {passed}/{passed+failed} 通过", end="")
    if failed > 0:
        # print(f" ❌ {failed} 失败")
    else:
        # print(" ✅ 全部通过！")
    # print(f"{'='*60}")


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="V4.3 任务重复检测与自动去重")
    parser.add_argument("--check", type=str, help="前置检查: 检测新标题是否重复")
    parser.add_argument("--find-all", action="store_true", help="扫描全部任务找出重复组")
    parser.add_argument("--only-pending", action="store_true", 
                        help="只扫描pending/in_progress任务")
    parser.add_argument("--cleanup", action="store_true", help="执行清理")
    parser.add_argument("--no-dry-run", action="store_true", help="实际执行清理")
    parser.add_argument("--test", action="store_true", help="运行单元测试")
    
    args = parser.parse_args()
    
    if args.test:
        run_tests()
        return
    
    if not HAS_DB:
        # print("❌ 无数据库连接，请确保 scripts/lib/db_connector.py 可用")
        run_tests()
        return
    
    detector = DupDetector()
    detector.load_tasks_from_db()
    
    if args.check:
        detector.check_dup(args.check)
        return
    
    if args.find_all:
        groups = detector.find_all_duplicates(only_pending=args.only_pending)
        if args.cleanup:
            cleanup_redundant(groups, dry_run=not args.no_dry_run)
        return
    
    # 默认: 扫描全部
    # print("\n🔍 执行全部任务重复扫描...")
    groups = detector.find_all_duplicates()
    # print("\n💡 前置检查: --check '标题' | 清理: --find-all --cleanup --no-dry-run")


if __name__ == "__main__":
    main()

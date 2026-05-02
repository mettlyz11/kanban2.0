"""
self_improvement_loop.py
Self-Improving AI Agent 反馈驱动学习闭环架构
基于2026年多Agent协作评估框架实现

Author: Dudu (AI Assistant)
Date: 2026-04-25
"""

import json
import re
import time
import hashlib
from datetime import datetime
from typing import Optional
from lib.db_connector import get_db_connection, execute_query, execute_update


# ─────────────────────────────────────────────
# 1. 执行质量自动评估模块
# ─────────────────────────────────────────────

class ExecutionQualityEvaluator:
    """
    对已完成任务的 execution_log / result_summary 进行质量评分。
    评分维度：
      - 长度达标（execution_log ≥ 200字，result_summary ≥ 50字）
      - 关键词覆盖（工具使用、问题/解决、产出描述）
      - 结构完整性（段落数量、是否有编号/条目）
    返回 0-100 分。
    """

    KEYWORD_SETS = {
        "tools":    ["python", "sql", "api", "脚本", "模块", "工具", "函数", "代码"],
        "process":  ["执行", "实现", "构建", "生成", "分析", "测试", "验证", "完成"],
        "problems": ["问题", "错误", "异常", "失败", "修复", "优化", "调整"],
        "output":   ["产出", "文件", "报告", "结果", "数据", "保存", "上传"],
    }

    def score_execution_log(self, text: str) -> dict:
        if not text:
            return {"score": 0, "details": "空日志"}

        length = len(text)
        score = 0
        details = []

        # 长度分 (40分)
        if length >= 200:
            score += 40
            details.append(f"✅ 长度达标({length}字)")
        elif length >= 100:
            score += 20
            details.append(f"⚠️ 长度不足200字({length}字)")
        else:
            details.append(f"❌ 长度严重不足({length}字)")

        # 关键词覆盖 (40分，每组10分)
        for category, keywords in self.KEYWORD_SETS.items():
            if any(kw in text for kw in keywords):
                score += 10
                details.append(f"✅ 关键词[{category}]覆盖")
            else:
                details.append(f"❌ 缺少[{category}]关键词")

        # 结构完整性 (20分)
        paragraphs = [p for p in text.split('\n') if p.strip()]
        if len(paragraphs) >= 3:
            score += 10
            details.append(f"✅ 段落数达标({len(paragraphs)}段)")
        has_structure = bool(re.search(r'(\d+[\.、]|[-*])\s', text))
        if has_structure:
            score += 10
            details.append("✅ 有结构化列表")

        return {"score": score, "length": length, "details": details}

    def score_result_summary(self, text: str) -> dict:
        if not text:
            return {"score": 0, "details": "空摘要"}

        length = len(text)
        score = 0
        details = []

        if length >= 50:
            score += 60
            details.append(f"✅ 长度达标({length}字)")
        else:
            score += int(length / 50 * 60)
            details.append(f"❌ 长度不足50字({length}字)")

        # 内容质量 (40分)
        quality_words = ["实现", "完成", "产出", "构建", "生成", "优化", "成果", "关键"]
        matched = [w for w in quality_words if w in text]
        score += min(40, len(matched) * 10)
        details.append(f"质量词命中{len(matched)}个")

        return {"score": score, "length": length, "details": details}

    def evaluate_task(self, task_id: int) -> dict:
        rows = execute_query(
            "SELECT execution_log, result_summary, status FROM tasks WHERE id = %s",
            (task_id,)
        )
        if not rows:
            return {"error": f"Task {task_id} not found"}

        row = rows[0]
        log_eval = self.score_execution_log(row.get("execution_log") or "")
        sum_eval = self.score_result_summary(row.get("result_summary") or "")
        overall = (log_eval["score"] + sum_eval["score"]) // 2

        return {
            "task_id": task_id,
            "status": row.get("status"),
            "execution_log_score": log_eval,
            "result_summary_score": sum_eval,
            "overall_score": overall,
            "pass": overall >= 60 and log_eval["length"] >= 200 and sum_eval["length"] >= 50,
        }


# ─────────────────────────────────────────────
# 2. 错误分类器 & 自动修正机制
# ─────────────────────────────────────────────

class ErrorClassifier:
    """
    识别重复/低质量任务并建议修正动作。
    错误类型：
      - DUPLICATE: 标题/描述高度相似
      - LOW_QUALITY: execution_log/result_summary 质量分低于阈值
      - STALE: 长时间 in_progress 未完成
      - EMPTY_OUTPUT: 无产出文件/附件
    """

    QUALITY_THRESHOLD = 60
    STALE_HOURS = 48

    def classify(self, task_id: int, quality_eval: dict) -> list[dict]:
        errors = []

        # 低质量检测
        if not quality_eval.get("pass"):
            log_score = quality_eval["execution_log_score"]["score"]
            sum_score = quality_eval["result_summary_score"]["score"]
            errors.append({
                "type": "LOW_QUALITY",
                "severity": "HIGH",
                "task_id": task_id,
                "log_score": log_score,
                "summary_score": sum_score,
                "suggestion": "重新执行任务，补充详细的 execution_log（≥200字）和 result_summary（≥50字）",
            })

        # 附件缺失检测
        attachments = execute_query(
            "SELECT COUNT(*) as cnt FROM attachments WHERE entity_type='task' AND entity_id=%s",
            (task_id,)
        )
        if attachments and attachments[0].get("cnt", 0) == 0:
            errors.append({
                "type": "EMPTY_OUTPUT",
                "severity": "MEDIUM",
                "task_id": task_id,
                "suggestion": "任务有产出但未上传附件，需执行附件INSERT",
            })

        return errors

    def detect_duplicates(self, limit: int = 50) -> list[dict]:
        """基于标题相似度检测重复任务"""
        rows = execute_query(
            "SELECT id, title FROM tasks ORDER BY created_at DESC LIMIT %s",
            (limit,)
        )
        if not rows:
            return []

        duplicates = []
        seen: dict[str, int] = {}
        for row in rows:
            title = (row.get("title") or "").strip()
            key = re.sub(r'\s+', ' ', title[:50].lower())
            if key in seen:
                duplicates.append({
                    "type": "DUPLICATE",
                    "task_id": row["id"],
                    "duplicate_of": seen[key],
                    "title": title,
                    "suggestion": "合并或删除重复任务",
                })
            else:
                seen[key] = row["id"]

        return duplicates

    def auto_correct(self, task_id: int, errors: list[dict]) -> dict:
        """对低质量任务自动重置为 pending 以触发重新执行"""
        high_severity = [e for e in errors if e.get("severity") == "HIGH"]
        if high_severity:
            execute_update(
                "UPDATE tasks SET status = 'pending', updated_at = NOW() WHERE id = %s AND status = 'completed'",
                (task_id,)
            )
            return {"action": "reset_to_pending", "task_id": task_id, "reason": "LOW_QUALITY"}
        return {"action": "no_action", "task_id": task_id}


# ─────────────────────────────────────────────
# 3. 最佳实践提取器
# ─────────────────────────────────────────────

class BestPracticeExtractor:
    """
    从已完成高质量任务中提取最佳实践，
    生成可复用的任务模板和提示词片段。
    """

    HIGH_QUALITY_THRESHOLD = 80

    def extract_from_completed_tasks(self, top_n: int = 10) -> list[dict]:
        rows = execute_query(
            """SELECT id, title, task_type, execution_log, result_summary, task_summary
               FROM tasks
               WHERE status = 'completed'
                 AND execution_log IS NOT NULL
                 AND result_summary IS NOT NULL
               ORDER BY updated_at DESC
               LIMIT %s""",
            (top_n,)
        )

        evaluator = ExecutionQualityEvaluator()
        best_practices = []

        for row in rows:
            log_eval = evaluator.score_execution_log(row.get("execution_log") or "")
            sum_eval = evaluator.score_result_summary(row.get("result_summary") or "")
            overall = (log_eval["score"] + sum_eval["score"]) // 2

            if overall >= self.HIGH_QUALITY_THRESHOLD:
                # 提取关键模式
                practice = {
                    "source_task_id": row["id"],
                    "title": row.get("title"),
                    "task_type": row.get("task_type"),
                    "quality_score": overall,
                    "execution_pattern": self._extract_pattern(row.get("execution_log") or ""),
                    "summary_pattern": self._extract_pattern(row.get("result_summary") or ""),
                    "fingerprint": hashlib.md5((row.get("title") or "").encode()).hexdigest()[:8],
                }
                best_practices.append(practice)

        return best_practices

    def _extract_pattern(self, text: str) -> str:
        """提取文本的结构化模式（前3句 + 关键动词短语）"""
        sentences = [s.strip() for s in re.split(r'[。\n]', text) if len(s.strip()) > 10]
        return "；".join(sentences[:3])

    def generate_task_template(self, task_type: str, practices: list[dict]) -> str:
        """根据最佳实践生成新任务的execution_log模板"""
        matching = [p for p in practices if p.get("task_type") == task_type]
        if not matching:
            matching = practices[:3]

        template_parts = [
            f"【任务类型: {task_type}】",
            "【执行步骤（基于最佳实践）】",
        ]
        for i, p in enumerate(matching[:3], 1):
            template_parts.append(f"{i}. 参考任务#{p['source_task_id']}: {p['execution_pattern']}")

        return "\n".join(template_parts)

    def save_practices_to_file(self, practices: list[dict], output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(practices, f, ensure_ascii=False, indent=2)
        print(f"✅ 最佳实践已保存: {output_path} ({len(practices)} 条)")


# ─────────────────────────────────────────────
# 4. Self-Improvement 主循环
# ─────────────────────────────────────────────

class SelfImprovementLoop:
    """
    Self-Improving AI Agent 主控制器。
    工作流：
      1. 扫描最近完成任务 → 质量评估
      2. 错误分类 → 自动修正低质量任务
      3. 提取最佳实践 → 缓存到本地
      4. 生成改进报告
    """

    def __init__(self, scan_limit: int = 20):
        self.evaluator = ExecutionQualityEvaluator()
        self.classifier = ErrorClassifier()
        self.extractor = BestPracticeExtractor()
        self.scan_limit = scan_limit

    def run(self, output_dir: str = "/Users/mettlyz/.openclaw/workspace/output/task-1911") -> dict:
        print("🔄 Self-Improvement Loop 启动...")
        report = {
            "run_at": datetime.now().isoformat(),
            "evaluated": [],
            "errors_found": [],
            "corrections": [],
            "best_practices": [],
            "duplicates": [],
        }

        # Step 1: 获取最近完成任务
        tasks = execute_query(
            """SELECT id FROM tasks
               WHERE status IN ('completed', 'in_progress')
               ORDER BY updated_at DESC
               LIMIT %s""",
            (self.scan_limit,)
        )
        print(f"📋 扫描 {len(tasks)} 个任务...")

        # Step 2: 质量评估 + 错误分类
        for task in tasks:
            tid = task["id"]
            eval_result = self.evaluator.evaluate_task(tid)
            report["evaluated"].append(eval_result)

            errors = self.classifier.classify(tid, eval_result)
            if errors:
                report["errors_found"].extend(errors)
                correction = self.classifier.auto_correct(tid, errors)
                if correction["action"] != "no_action":
                    report["corrections"].append(correction)
                    print(f"  🔧 Task #{tid}: {correction['action']}")

        # Step 3: 重复检测
        duplicates = self.classifier.detect_duplicates(50)
        report["duplicates"] = duplicates
        if duplicates:
            print(f"⚠️ 发现 {len(duplicates)} 个重复任务")

        # Step 4: 提取最佳实践
        practices = self.extractor.extract_from_completed_tasks(top_n=20)
        report["best_practices"] = practices
        if practices:
            practices_path = f"{output_dir}/best_practices.json"
            self.extractor.save_practices_to_file(practices, practices_path)
            print(f"⭐ 提取到 {len(practices)} 条最佳实践")

        # Step 5: 保存报告
        report_path = f"{output_dir}/improvement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"📄 改进报告已保存: {report_path}")

        # 统计摘要
        passed = sum(1 for e in report["evaluated"] if e.get("pass"))
        failed = len(report["evaluated"]) - passed
        print(f"\n✅ 评估完成: {passed} 个达标 / {failed} 个不达标")
        print(f"🔧 自动修正: {len(report['corrections'])} 个任务")
        print(f"⭐ 最佳实践: {len(practices)} 条")

        return report


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    output_dir = "/Users/mettlyz/.openclaw/workspace/output/task-1911"

    loop = SelfImprovementLoop(scan_limit=30)
    report = loop.run(output_dir=output_dir)

    print("\n" + "="*50)
    print("Self-Improvement Loop 执行完成")
    print(f"评估任务数: {len(report['evaluated'])}")
    print(f"发现错误数: {len(report['errors_found'])}")
    print(f"自动修正数: {len(report['corrections'])}")
    print(f"最佳实践数: {len(report['best_practices'])}")
    print(f"重复任务数: {len(report['duplicates'])}")

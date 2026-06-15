#!/usr/bin/env python3
"""
SDS v4.4 安全护栏模块
功能：高风险操作拦截、审计日志、回滚方案、人工审核触发
"""

import sys
import os
import json
import re
from datetime import datetime

sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

# 高风险操作关键词库
HIGH_RISK_PATTERNS = {
    'destructive': [
        r'\brm\s+-rf\b', r'\bDROP\s+TABLE\b', r'\bDELETE\s+FROM\b',
        r'\bTRUNCATE\b', r'\bFORMAT\b', r'\bmkfs\b',
    ],
    'system_control': [
        r'\bshutdown\b', r'\breboot\b', r'\binit\s+0\b',
        r'\bsystemctl\s+(stop|restart)\s+\w+\b',
    ],
    'data_exfiltration': [
        r'\bcurl\s+.*\b(http|ftp)',
        r'\bwget\s+.*\b(http|ftp)',
        r'\bscp\s+.*@',
    ],
    'privilege_escalation': [
        r'\bsudo\s+.*\b(rm|dd|mkfs|shutdown)',
        r'\bchmod\s+777\b',
    ]
}

# 风险等级映射
RISK_LEVELS = {
    'destructive': 'CRITICAL',
    'system_control': 'HIGH',
    'data_exfiltration': 'MEDIUM',
    'privilege_escalation': 'HIGH'
}

class SafetyGuardrails:
    def __init__(self):
        self.output_dir = "/Users/mettlyz/.openclaw/workspace/output/task-1570"
        self.audit_file = os.path.join(self.output_dir, "sds_safety_audit.log")
        self.blocked_file = os.path.join(self.output_dir, "sds_blocked_actions.log")
        self.rollback_manifest = os.path.join(self.output_dir, "sds_rollback_manifest.json")
        os.makedirs(self.output_dir, exist_ok=True)
        
    def log_audit(self, action, details, risk_level="INFO"):
        """记录安全审计日志"""
        ts = datetime.now().isoformat()
        line = f"[{ts}] [{risk_level}] ACTION={action} | {details}\n"
        with open(self.audit_file, "a", encoding="utf-8") as f:
            f.write(line)
        # print(line.strip())
    
    def log_blocked(self, action, reason, context=""):
        """记录被拦截的操作"""
        ts = datetime.now().isoformat()
        entry = {
            "timestamp": ts,
            "action": action,
            "reason": reason,
            "context": context
        }
        with open(self.blocked_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def scan_task_description(self, description):
        """
        扫描任务描述中的风险操作
        返回: (is_safe, findings)
        findings: [{category, pattern, risk_level, matched_text}]
        """
        if not description:
            return True, []
        
        findings = []
        for category, patterns in HIGH_RISK_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, description, re.IGNORECASE)
                for match in matches:
                    findings.append({
                        "category": category,
                        "pattern": pattern,
                        "risk_level": RISK_LEVELS.get(category, "HIGH"),
                        "matched_text": match.group(0)
                    })
        
        is_safe = len(findings) == 0
        return is_safe, findings
    
    def validate_sql_in_task(self, sql_text):
        """
        验证任务中的SQL语句安全性
        拦截：DELETE without WHERE, DROP, TRUNCATE
        """
        if not sql_text:
            return True, []
        
        dangerous = []
        sql_upper = sql_text.upper()
        
        # 检测DELETE无WHERE
        if 'DELETE' in sql_upper and 'WHERE' not in sql_upper:
            dangerous.append({"type": "DELETE_WITHOUT_WHERE", "risk": "CRITICAL"})
        
        # 检测DROP
        if 'DROP TABLE' in sql_upper or 'DROP DATABASE' in sql_upper:
            dangerous.append({"type": "DROP_COMMAND", "risk": "CRITICAL"})
        
        # 检测TRUNCATE
        if 'TRUNCATE' in sql_upper:
            dangerous.append({"type": "TRUNCATE_COMMAND", "risk": "CRITICAL"})
        
        return len(dangerous) == 0, dangerous
    
    def require_audit_approval(self, task_id, task_title, risk_findings):
        """
        对高风险任务要求人工审核
        修改任务状态为 review_needed
        """
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            audit_note = f"【SDS安全护栏拦截】任务包含高风险操作，需人工审核后才能执行。\n"
            audit_note += f"检测到的风险：\n"
            for f in risk_findings:
                audit_note += f"  - [{f['risk_level']}] {f['category']}: {f['matched_text']}\n"
            
            c.execute("""
                UPDATE tasks 
                SET status = 'pending',
                    execution_mode = 'review_needed',
                    notes = CONCAT(IFNULL(notes, ''), %s),
                    updated_at = NOW()
                WHERE id = %s
            """, (audit_note, task_id))
            conn.commit()
            conn.close()
            
            self.log_audit("AUDIT_REQUIRED", 
                f"task_id={task_id}, title={task_title}, findings={len(risk_findings)}", 
                "HIGH")
            return True
        except Exception as e:
            self.log_audit("AUDIT_ERROR", f"task_id={task_id}, error={e}", "CRITICAL")
            return False
    
    def create_rollback_point(self, task_id, operation_type, before_state):
        """
        创建回滚点，保存操作前的状态
        """
        rollback_entry = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "operation": operation_type,
            "before_state": before_state
        }
        
        manifest = []
        if os.path.exists(self.rollback_manifest):
            with open(self.rollback_manifest, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        
        manifest.append(rollback_entry)
        
        with open(self.rollback_manifest, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        
        self.log_audit("ROLLBACK_POINT_CREATED", 
            f"task_id={task_id}, operation={operation_type}")
    
    def execute_safety_check(self, task_id, task_title, task_description):
        """
        执行完整的安全检查流程
        返回: (allowed, reason)
        """
        self.log_audit("SAFETY_CHECK_START", f"task_id={task_id}, title={task_title[:50]}")
        
        # 1. 扫描任务描述
        is_safe, findings = self.scan_task_description(task_description)
        if not is_safe:
            critical_findings = [f for f in findings if f['risk_level'] == 'CRITICAL']
            if critical_findings:
                self.log_blocked(task_title, f"发现{critical_findings}个CRITICAL风险", task_description[:200])
                self.require_audit_approval(task_id, task_title, findings)
                return False, f"检测到CRITICAL风险操作: {[f['matched_text'] for f in critical_findings]}"
            else:
                # HIGH/MEDIUM级别记录审计日志，但允许执行（加监控）
                self.log_audit("HIGH_RISK_EXECUTION", 
                    f"task_id={task_id}, findings={findings}", "HIGH")
        
        # 2. 检查SQL安全性
        # 提取任务描述中的SQL代码块
        sql_blocks = re.findall(r'```sql\s*(.*?)\s*```', task_description, re.DOTALL | re.IGNORECASE)
        sql_blocks += re.findall(r'```\s*(.*?)\s*```', task_description, re.DOTALL)
        
        for sql in sql_blocks:
            sql_safe, sql_risks = self.validate_sql_in_task(sql)
            if not sql_safe:
                self.log_blocked(task_title, f"SQL安全风险: {sql_risks}", sql[:200])
                self.require_audit_approval(task_id, task_title, 
                    [{"category": "sql_injection", "risk_level": r["risk"], "matched_text": r["type"]} for r in sql_risks])
                return False, f"检测到SQL安全风险: {[r['type'] for r in sql_risks]}"
        
        self.log_audit("SAFETY_CHECK_PASS", f"task_id={task_id}")
        return True, "安全检查通过"

if __name__ == "__main__":
    guard = SafetyGuardrails()
    # print("🛡️ SDS v4.4 安全护栏模块测试")
    
    # 测试用例1: 安全任务
    safe, reason = guard.execute_safety_check(9999, "测试安全任务", "这是一个正常的研究任务，不涉及任何危险操作")
    # print(f"安全任务检测结果: {safe}, {reason}")
    
    # 测试用例2: 包含rm -rf的危险任务
    safe, reason = guard.execute_safety_check(9998, "危险任务", "请执行 rm -rf / 清理磁盘")
    # print(f"危险任务检测结果: {safe}, {reason}")
    
    # 测试用例3: 包含DROP TABLE的SQL
    safe, reason = guard.execute_safety_check(9997, "SQL任务", "```sql\nDROP TABLE users;\n```")
    # print(f"SQL任务检测结果: {safe}, {reason}")

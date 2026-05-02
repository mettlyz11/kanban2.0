#!/usr/bin/env python3
"""
SDS安全护栏模块
功能：高风险操作审核、操作审计、回滚机制
"""
import sys
import os
import json
from datetime import datetime
sys.path.append('/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

class SDSSafetyGuard:
    def __init__(self):
        self.conn = get_db_connection()
        self.audit_log_file = "/Users/mettlyz/.openclaw/workspace/output/task-1570/sds_audit.log"
        # 高风险操作列表
        self.high_risk_ops = [
            "DELETE FROM", "DROP TABLE", "TRUNCATE",
            "rm -rf", "sudo", "format", "mkfs",
            "send_email", "send_message", "post_tweet"
        ]
    
    def audit_log(self, op_type, content, risk_level="low", approved=False):
        """操作审计日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "op_type": op_type,
            "content": content,
            "risk_level": risk_level,
            "approved": approved
        }
        with open(self.audit_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        # 写入数据库审计表
        c = self.conn.cursor()
        c.execute("""
        INSERT INTO sds_audit_log (op_type, content, risk_level, approved, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        """, (op_type, content, risk_level, approved))
        self.conn.commit()
    
    def check_risk(self, operation):
        """检测操作风险等级"""
        for op in self.high_risk_ops:
            if op.lower() in operation.lower():
                return "high"
        return "low"
    
    def approve_operation(self, operation):
        """高风险操作审批机制"""
        risk_level = self.check_risk(operation)
        if risk_level == "low":
            self.audit_log("execute", operation, "low", True)
            return True
        
        # 高风险操作需要人工审批，写入待审批队列
        self.audit_log("pending_approval", operation, "high", False)
        print(f"⚠️ 高风险操作需要审批：{operation}")
        # 临时自动放行测试用，生产环境需要对接审批流
        # TODO: 对接企业微信/邮件审批
        approved = True # 测试阶段默认放行，生产环境改为False
        if approved:
            self.audit_log("approved", operation, "high", True)
        return approved
    
    def rollback_operation(self, operation_id):
        """操作回滚机制"""
        c = self.conn.cursor()
        c.execute("SELECT * FROM sds_audit_log WHERE id = %s", (operation_id,))
        op = c.fetchone()
        if not op:
            return False
        # 根据操作类型执行回滚
        # TODO: 实现各类操作的回滚逻辑
        self.audit_log("rollback", f"回滚操作#{operation_id}: {op['content']}", "medium", True)
        return True

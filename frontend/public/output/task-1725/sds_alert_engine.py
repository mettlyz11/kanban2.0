#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS告警引擎 - 告警规则定义与评估
任务 #1725: SDS告警推送系统与微信集成
"""

import time
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('sds_alert')


# ─────────────────────────────────────────
# 数据结构
# ─────────────────────────────────────────

@dataclass
class Alert:
    rule_id: str
    severity: str          # info / warning / critical
    title: str
    message: str
    resource_id: str = ""
    labels: dict = field(default_factory=dict)
    fired_at: datetime = field(default_factory=datetime.now)
    alert_id: str = ""

    def __post_init__(self):
        if not self.alert_id:
            ts = self.fired_at.strftime('%Y%m%d%H%M%S')
            self.alert_id = f"ALT-{ts}-{self.rule_id[:8].upper()}"

    def fingerprint(self) -> str:
        raw = f"{self.rule_id}:{self.resource_id}:{self.severity}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]


# ─────────────────────────────────────────
# 告警规则定义（12条规则，覆盖3个级别）
# ─────────────────────────────────────────

ALERT_RULES = [
    # ── INFO ──
    {
        "id": "api_slow",
        "severity": "info",
        "title": "SDS API响应偏慢",
        "condition": lambda m: m.get("api_avg_rt_ms", 0) > 500,
        "message_tpl": "[INFO] SDS-API响应偏慢：当前 {api_avg_rt_ms}ms，建议关注",
    },
    {
        "id": "db_pool_warn",
        "severity": "info",
        "title": "数据库连接池使用率高",
        "condition": lambda m: m.get("db_pool_pct", 0) > 70,
        "message_tpl": "[INFO] 数据库连接池使用率 {db_pool_pct}%，请关注趋势",
    },
    {
        "id": "disk_warn",
        "severity": "info",
        "title": "磁盘使用率预警",
        "condition": lambda m: m.get("disk_pct", 0) > 75,
        "message_tpl": "[INFO] 磁盘空间使用率 {disk_pct}%，请及时清理历史数据",
    },
    # ── WARNING ──
    {
        "id": "push_fail",
        "severity": "warning",
        "title": "告警推送失败",
        "condition": lambda m: m.get("push_fail_count", 0) >= 3,
        "message_tpl": "[WARNING] 告警推送服务异常，连续失败 {push_fail_count} 次",
    },
    {
        "id": "task_timeout",
        "severity": "warning",
        "title": "SDS任务执行超时",
        "condition": lambda m: m.get("task_elapsed_ratio", 0) >= 2.0,
        "message_tpl": "[WARNING] 任务 #{task_id} 执行超时，已耗时 {task_elapsed}s",
    },
    {
        "id": "mem_high",
        "severity": "warning",
        "title": "内存使用率过高",
        "condition": lambda m: m.get("mem_pct", 0) > 85,
        "message_tpl": "[WARNING] SDS内存使用率 {mem_pct}%，可能影响性能",
    },
    {
        "id": "import_error_rate",
        "severity": "warning",
        "title": "数据导入失败率超阈值",
        "condition": lambda m: m.get("import_fail_rate", 0) > 5,
        "message_tpl": "[WARNING] 数据导入失败率 {import_fail_rate:.1f}%，请检查数据质量",
    },
    # ── CRITICAL ──
    {
        "id": "sds_down",
        "severity": "critical",
        "title": "SDS服务宕机",
        "condition": lambda m: m.get("health_fail_count", 0) >= 3,
        "message_tpl": "🚨 [CRITICAL] SDS服务宕机！已离线 {health_fail_count} 次健康检查，请立即处理！",
    },
    {
        "id": "db_connection_fail",
        "severity": "critical",
        "title": "数据库连接失败",
        "condition": lambda m: m.get("db_conn_fail", False),
        "message_tpl": "🚨 [CRITICAL] 数据库连接失败！SDS系统无法正常工作！",
    },
    {
        "id": "api_error_spike",
        "severity": "critical",
        "title": "API错误率暴涨",
        "condition": lambda m: m.get("api_5xx_rate", 0) > 20,
        "message_tpl": "🚨 [CRITICAL] API 5xx错误率 {api_5xx_rate:.1f}%，系统异常！请立即排查！",
    },
    {
        "id": "core_task_fail",
        "severity": "critical",
        "title": "核心任务连续失败",
        "condition": lambda m: m.get("core_task_fail_count", 0) >= 3,
        "message_tpl": "🚨 [CRITICAL] 核心任务连续失败 {core_task_fail_count} 次，系统异常！",
    },
    {
        "id": "disk_critical",
        "severity": "critical",
        "title": "磁盘空间耗尽",
        "condition": lambda m: m.get("disk_pct", 0) > 95,
        "message_tpl": "🚨 [CRITICAL] 磁盘空间严重不足，使用率 {disk_pct}%，系统即将停止运行！",
    },
]


# ─────────────────────────────────────────
# 告警聚合器（去重 & 抑制）
# ─────────────────────────────────────────

class AlertAggregator:
    SUPPRESSION_WINDOW = {
        'critical': 900,   # 15分钟抑制重复
        'warning': 3600,   # 1小时
        'info': 3600,
    }

    def __init__(self):
        self._cache: dict[str, float] = {}  # fingerprint → last_push_ts

    def should_send(self, alert: Alert) -> bool:
        fp = alert.fingerprint()
        now = time.time()
        window = self.SUPPRESSION_WINDOW.get(alert.severity, 3600)
        last = self._cache.get(fp, 0)
        if now - last > window:
            self._cache[fp] = now
            return True
        logger.debug(f"告警抑制 [{alert.rule_id}] 距上次推送 {int(now-last)}s，窗口 {window}s")
        return False


# ─────────────────────────────────────────
# 静默管理器
# ─────────────────────────────────────────

class SilenceManager:
    def __init__(self):
        self.silences = []

    def add_time_silence(self, start_hour: int, end_hour: int, suppress_levels: list):
        self.silences.append({
            "type": "time_range",
            "start_hour": start_hour,
            "end_hour": end_hour,
            "suppress_levels": suppress_levels,
        })

    def add_rule_silence(self, rule_id: str, duration_seconds: int):
        expires = time.time() + duration_seconds
        self.silences.append({"type": "rule", "rule_id": rule_id, "expires": expires})

    def is_silenced(self, alert: Alert) -> bool:
        now_hour = datetime.now().hour
        for s in self.silences:
            if s["type"] == "time_range":
                in_window = s["start_hour"] <= now_hour < s["end_hour"]
                if in_window and alert.severity in s.get("suppress_levels", []):
                    return True
            elif s["type"] == "rule":
                if s["rule_id"] == alert.rule_id and time.time() < s["expires"]:
                    return True
        return False


# ─────────────────────────────────────────
# 通知器（微信/Hermes桥集成）
# ─────────────────────────────────────────

class AlertNotifier:
    def __init__(self, hermes_endpoint: Optional[str] = None):
        self.hermes_endpoint = hermes_endpoint
        self.push_fail_count = 0

    def format_message(self, alert: Alert) -> str:
        level_emoji = {"info": "🔵", "warning": "🟡", "critical": "🔴"}.get(alert.severity, "⚪")
        ts = alert.fired_at.strftime('%Y-%m-%d %H:%M:%S')
        return (
            f"📊 SDS告警通知\n"
            f"━━━━━━━━━━━━━━\n"
            f"级别：{level_emoji} {alert.severity.upper()}\n"
            f"规则：{alert.title}\n"
            f"时间：{ts}\n"
            f"描述：{alert.message}\n"
            f"\n📌 告警ID：{alert.alert_id}\n"
            f"━━━━━━━━━━━━━━\n"
            f"回复「确认 {alert.alert_id}」标记已知悉"
        )

    def send(self, alert: Alert) -> bool:
        msg = self.format_message(alert)
        logger.info(f"[PUSH] {alert.severity.upper()} 告警推送: {alert.alert_id}")
        logger.info(f"消息内容:\n{msg}")
        # 实际集成时：调用 hermes-bridge 或 QQBot API
        # import subprocess
        # subprocess.run(['hermes-bridge', 'send', msg])
        return True


# ─────────────────────────────────────────
# 升级调度器
# ─────────────────────────────────────────

class EscalationScheduler:
    ESCALATION_TIMEOUT = 900  # 15分钟

    def __init__(self, notifier: AlertNotifier):
        self.notifier = notifier
        self.pending: dict[str, float] = {}  # alert_id → fired_ts

    def register(self, alert: Alert):
        if alert.severity == 'critical':
            self.pending[alert.alert_id] = time.time()

    def acknowledge(self, alert_id: str):
        self.pending.pop(alert_id, None)

    def check_escalations(self):
        now = time.time()
        for alert_id, fired_ts in list(self.pending.items()):
            if now - fired_ts > self.ESCALATION_TIMEOUT:
                logger.warning(f"⚠️ 升级通知：告警 {alert_id} 超过15分钟未确认！")
                # 发送升级通知
                escalation = Alert(
                    rule_id="escalation",
                    severity="critical",
                    title="未处理告警升级提醒",
                    message=f"告警 {alert_id} 已超过15分钟未确认，请立即处理！",
                )
                self.notifier.send(escalation)
                self.pending.pop(alert_id)


# ─────────────────────────────────────────
# 主告警引擎
# ─────────────────────────────────────────

class SDSAlertEngine:
    def __init__(self):
        self.aggregator = AlertAggregator()
        self.silence_mgr = SilenceManager()
        self.notifier = AlertNotifier()
        self.escalation = EscalationScheduler(self.notifier)
        self.history: list[dict] = []

        # 默认静默规则：凌晨2-4点只静默INFO/WARNING
        self.silence_mgr.add_time_silence(2, 4, ["info", "warning"])

    def evaluate(self, metrics: dict) -> list[Alert]:
        """评估所有规则，返回触发的告警列表"""
        triggered = []
        for rule in ALERT_RULES:
            try:
                if rule["condition"](metrics):
                    msg = rule["message_tpl"].format(**metrics)
                    alert = Alert(
                        rule_id=rule["id"],
                        severity=rule["severity"],
                        title=rule["title"],
                        message=msg,
                        resource_id=metrics.get("resource_id", "sds-main"),
                    )
                    triggered.append(alert)
            except Exception as e:
                logger.debug(f"规则 {rule['id']} 评估跳过: {e}")
        return triggered

    def process(self, metrics: dict):
        """处理一批指标数据"""
        alerts = self.evaluate(metrics)
        for alert in alerts:
            # 静默检查
            if self.silence_mgr.is_silenced(alert):
                logger.info(f"[SILENCED] {alert.rule_id}")
                self._record(alert, "silenced")
                continue
            # 聚合去重
            if not self.aggregator.should_send(alert):
                self._record(alert, "suppressed")
                continue
            # 推送
            ok = self.notifier.send(alert)
            self._record(alert, "fired" if ok else "push_failed")
            # CRITICAL注册升级
            if alert.severity == "critical":
                self.escalation.register(alert)
        # 检查升级
        self.escalation.check_escalations()

    def _record(self, alert: Alert, status: str):
        self.history.append({
            "alert_id": alert.alert_id,
            "rule_id": alert.rule_id,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "status": status,
            "fired_at": alert.fired_at.isoformat(),
        })

    def query_history(self, days: int = 7, severity: Optional[str] = None) -> list:
        cutoff = datetime.now() - timedelta(days=days)
        results = [
            h for h in self.history
            if datetime.fromisoformat(h["fired_at"]) >= cutoff
            and (severity is None or h["severity"] == severity)
        ]
        return results


# ─────────────────────────────────────────
# 端到端测试
# ─────────────────────────────────────────

if __name__ == "__main__":
    engine = SDSAlertEngine()
    print("=" * 50)
    print("SDS告警引擎 端到端测试")
    print("=" * 50)

    # 测试场景1：INFO - 磁盘预警
    print("\n[测试1] INFO级别 - 磁盘预警")
    engine.process({"disk_pct": 78, "resource_id": "sds-main"})

    # 测试场景2：WARNING - 数据导入失败率
    print("\n[测试2] WARNING级别 - 数据导入失败率")
    engine.process({"import_fail_rate": 7.3, "resource_id": "sds-main"})
    print("  [二次触发-应被抑制]")
    engine.process({"import_fail_rate": 7.3, "resource_id": "sds-main"})

    # 测试场景3：CRITICAL - SDS服务宕机
    print("\n[测试3] CRITICAL级别 - SDS服务宕机")
    engine.process({"health_fail_count": 3, "resource_id": "sds-main"})

    # 查询历史
    print("\n[历史记录查询]")
    history = engine.query_history(days=7)
    print(json.dumps(history, ensure_ascii=False, indent=2))
    print(f"\n✅ 测试完成，共记录 {len(history)} 条告警历史")

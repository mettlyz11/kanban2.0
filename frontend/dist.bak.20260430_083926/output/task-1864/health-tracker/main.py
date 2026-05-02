#!/usr/bin/env python3
"""
Health Tracker 主程序入口
支持：每日同步、健康评分、数据存储、报告生成、微信推送
"""

import sys
import yaml
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from health_exporter import HealthDataExporter
from health_score import HealthScoreCalculator
from influxdb_store import HealthInfluxDB
from wechat_notifier import WeChatNotifier

class HealthTracker:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.exporter = HealthDataExporter(config_path)
        self.calculator = HealthScoreCalculator(config_path)
        self.db = None
        self.notifier = WeChatNotifier(config_path)
    
    def init_db(self):
        """初始化数据库连接"""
        try:
            self.db = HealthInfluxDB(self.config_path)
            return True
        except Exception as e:
            print(f"⚠️ InfluxDB 连接失败: {e}")
            return False
    
    def daily_sync(self, date=None):
        """每日数据同步"""
        print(f"🔄 开始每日健康数据同步 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
        
        # 1. 获取数据
        metrics = self.exporter.get_daily_summary(date)
        print(f"📥 数据获取完成: {metrics['date']}")
        
        # 2. 计算评分
        scores = self.calculator.calculate_daily_score(metrics)
        print(f"📊 健康评分: {scores['total']} ({scores['grade']})")
        
        # 3. 获取历史趋势（最近14天）
        historical = []
        if self.db:
            try:
                recent_data = self.db.query_recent(days=14)
                # 简化为只取分数
                historical = [{'total': r.get('total', 75)} for r in recent_data]
            except Exception as e:
                print(f"⚠️ 历史数据查询失败: {e}")
        
        # 4. 计算趋势
        trend = self.calculator.calculate_trend(historical) if len(historical) >= 7 else None
        
        # 5. 保存到数据库
        if self.db:
            try:
                self.db.save_daily_metrics(metrics, scores)
                print("💾 数据已保存到 InfluxDB")
            except Exception as e:
                print(f"⚠️ 数据保存失败: {e}")
        
        # 6. 生成报告
        report = self.calculator.generate_daily_report(metrics, scores, trend)
        
        # 7. 推送通知
        self.notifier.send_daily_report(report)
        
        # 8. 发送异常预警
        for alert in scores.get('alerts', []):
            self.notifier.send_alert(alert)
        
        # 保存报告到文件
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        report_file = reports_dir / f"daily_{metrics['date']}.md"
        report_file.write_text(report, encoding='utf-8')
        
        print(f"✅ 每日同步完成，报告保存至: {report_file}")
        return metrics, scores, report
    
    def weekly_report(self):
        """生成周报"""
        print("📅 生成周健康报告...")
        
        if not self.db:
            print("❌ 需要 InfluxDB 连接才能生成周报")
            return None
        
        data = self.db.query_recent(days=7)
        if not data:
            print("⚠️ 无足够数据")
            return None
        
        # 计算周均值
        avg_steps = sum(d.get('steps', 0) for d in data) / len(data)
        avg_sleep = sum(d.get('sleep_hours', 0) for d in data) / len(data)
        avg_score = sum(d.get('total', 0) for d in data) / len(data)
        avg_rhr = sum(d.get('resting_heart_rate', 0) for d in data) / len(data)
        
        report_lines = [
            f"📅 周健康报告 ({(datetime.now() - timedelta(days=7)).strftime('%m/%d')} - {datetime.now().strftime('%m/%d')})",
            f"",
            f"🏆 周均评分: {avg_score:.1f}",
            f"",
            f"📈 本周均值:",
            f"  • 日均步数: {avg_steps:,.0f}",
            f"  • 平均睡眠: {avg_sleep:.1f} 小时",
            f"  • 平均静息心率: {avg_rhr:.0f} bpm",
            f"",
            f"📊 与目标对比:",
            f"  • 步数达成率: {avg_steps / self.calculator.targets['steps'] * 100:.0f}%",
            f"  • 睡眠充足率: {'✅' if avg_sleep >= self.calculator.targets['sleep_hours'] else '⚠️'} ({avg_sleep:.1f}/{self.calculator.targets['sleep_hours']}h)",
        ]
        
        report = "\n".join(report_lines)
        
        # 保存
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        week_start = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        week_end = datetime.now().strftime('%Y%m%d')
        report_file = reports_dir / f"weekly_{week_start}_{week_end}.md"
        report_file.write_text(report, encoding='utf-8')
        
        print(f"✅ 周报已生成: {report_file}")
        return report
    
    def monthly_report(self):
        """生成月报"""
        print("📆 生成月度健康报告...")
        
        if not self.db:
            print("❌ 需要 InfluxDB 连接才能生成月报")
            return None
        
        data = self.db.query_recent(days=30)
        if not data:
            print("⚠️ 无足够数据")
            return None
        
        # 月度统计
        avg_score = sum(d.get('total', 0) for d in data) / len(data)
        avg_steps = sum(d.get('steps', 0) for d in data) / len(data)
        avg_sleep = sum(d.get('sleep_hours', 0) for d in data) / len(data)
        avg_rhr = sum(d.get('resting_heart_rate', 0) for d in data) / len(data)
        
        # 最佳/最差日
        best_day = max(data, key=lambda x: x.get('total', 0))
        worst_day = min(data, key=lambda x: x.get('total', 0))
        
        report_lines = [
            f"📆 月度健康报告 ({datetime.now().strftime('%Y年%m月')})",
            f"",
            f"🏆 月度综合评分: {avg_score:.1f}",
            f"",
            f"📊 核心指标月均:",
            f"  • 日均步数: {avg_steps:,.0f}",
            f"  • 平均睡眠: {avg_sleep:.1f} 小时",
            f"  • 平均静息心率: {avg_rhr:.0f} bpm",
            f"",
            f"⭐ 最佳表现日: {best_day.get('_time', 'N/A')[:10] if isinstance(best_day.get('_time'), str) else 'N/A'} (评分: {best_day.get('total', 0)})",
            f"💤 需改善日: {worst_day.get('_time', 'N/A')[:10] if isinstance(worst_day.get('_time'), str) else 'N/A'} (评分: {worst_day.get('total', 0)})",
            f"",
            f"📈 健康建议:",
        ]
        
        # 个性化建议
        if avg_sleep < 7:
            report_lines.append(f"  • 睡眠时长不足，建议提前30分钟入睡，目标 7.5 小时")
        if avg_steps < 8000:
            report_lines.append(f"  • 运动量偏低，建议每日增加 2000 步")
        if avg_rhr > 75:
            report_lines.append(f"  • 静息心率偏高，建议增加有氧运动")
        
        if len(report_lines) == 9:  # 没有添加建议
            report_lines.append(f"  • 各项指标良好，继续保持！")
        
        report = "\n".join(report_lines)
        
        # 保存
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        month_str = datetime.now().strftime('%Y%m')
        report_file = reports_dir / f"monthly_{month_str}.md"
        report_file.write_text(report, encoding='utf-8')
        
        print(f"✅ 月报已生成: {report_file}")
        return report
    
    def close(self):
        if self.db:
            self.db.close()


def main():
    parser = argparse.ArgumentParser(description='Health Tracker - 量化自我健康监测系统')
    parser.add_argument('command', choices=['sync', 'weekly', 'monthly', 'all'],
                        help='执行命令: sync=每日同步, weekly=周报, monthly=月报, all=全部执行')
    parser.add_argument('--config', default='config.yaml', help='配置文件路径')
    parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)，仅 sync 有效')
    
    args = parser.parse_args()
    
    tracker = HealthTracker(args.config)
    tracker.init_db()
    
    try:
        if args.command == 'sync':
            date = datetime.strptime(args.date, '%Y-%m-%d').date() if args.date else None
            tracker.daily_sync(date)
        elif args.command == 'weekly':
            tracker.weekly_report()
        elif args.command == 'monthly':
            tracker.monthly_report()
        elif args.command == 'all':
            tracker.daily_sync()
            tracker.weekly_report()
            tracker.monthly_report()
    finally:
        tracker.close()


if __name__ == "__main__":
    main()

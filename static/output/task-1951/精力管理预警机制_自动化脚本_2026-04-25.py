#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创业者高压期精力管理预警系统 v1.0
功能：数据采集 → 分析计算 → 预警判断 → 推送通知 → 记录存档
创建日期：2026-04-25
"""

import os
import json
import datetime
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Tuple

# ==================== 配置区域 ====================

CONFIG = {
    # 个人基线数据（首次使用需校准）
    'baseline': {
        'sleep_hours': 7.0,           # 目标睡眠时长
        'deep_sleep_min': 90,         # 目标深度睡眠（分钟）
        'hrv_baseline': 45.0,         # 个人HRV基线（ms）
        'resting_hr_baseline': 65,    # 个人静息心率基线（bpm）
        'sleep_score_target': 80,     # 目标睡眠评分
    },
    
    # 预警阈值
    'thresholds': {
        'yellow': {
            'sleep_hours': 6.5,       # 连续2天<6.5h → 黄警
            'resting_hr': 75,         # 静息心率>75 → 黄警
            'hrv_drop_pct': 20,       # HRV下降>20% → 黄警
            'consecutive_days': 2,    # 连续天数触发黄警
        },
        'orange': {
            'sleep_hours': 6.0,       # 连续3天<6h → 橙警
            'resting_hr': 85,         # 静息心率>85 → 橙警
            'hrv_drop_pct': 30,       # HRV下降>30% → 橙警
            'consecutive_days': 3,    # 连续天数触发橙警
        },
        'red': {
            'sleep_hours': 6.0,       # 连续4天<6h → 红警
            'resting_hr': 90,         # 静息心率>90 → 红警
            'energy_score': 50,       # 综合评分<50 → 红警
            'consecutive_days': 4,    # 连续天数触发红警
        }
    },
    
    # 恢复建议
    'recovery_actions': {
        'yellow': [
            '当日增加30分钟恢复时间',
            '减少1次非必要会议',
            '午间增加15分钟小憩',
        ],
        'orange': [
            '强制执行半天恢复',
            '当日工作时长不超过6小时',
            '下午进行30分钟轻度运动',
        ],
        'red': [
            '⚠️ 强制全天休息！',
            '停止所有深度工作',
            '执行24小时全面恢复计划',
            '联系医生咨询（如持续异常）',
        ]
    },
    
    # 数据存储路径
    'data_dir': '~/.openclaw/energy_management',
    'log_file': 'energy_log.json',
    'alert_log': 'alert_history.json',
}

# ==================== 核心类 ====================

class EnergyManagementSystem:
    """精力管理系统核心类"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.base_path = Path(os.path.expanduser(config['data_dir']))
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.log_path = self.base_path / config['log_file']
        self.alert_path = self.base_path / config['alert_log']
        
        self.daily_data = self._load_json(self.log_path, default=[])
        self.alert_history = self._load_json(self.alert_path, default=[])
    
    def _load_json(self, path: Path, default: List) -> List:
        """加载JSON文件"""
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    
    def _save_json(self, path: Path, data: List):
        """保存JSON文件"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_daily_data(self, 
                       sleep_hours: float,
                       sleep_score: int,
                       deep_sleep_min: int,
                       morning_hrv: float,
                       resting_hr: int,
                       steps: int,
                       exercise_min: int,
                       deep_work_hours: float,
                       subjective_rating: int) -> Dict:
        """
        添加每日精力数据
        返回：计算得到的综合分析结果
        """
        today = datetime.date.today().isoformat()
        
        # 计算各项得分
        sleep_score_norm = min(100, (sleep_hours / 8.0) * 100)
        hrv_score = self._calculate_hrv_score(morning_hrv)
        hr_score = self._calculate_hr_score(resting_hr)
        exercise_score = min(100, (exercise_min / 60.0) * 100)
        
        # 综合精力评分（加权）
        energy_score = (
            sleep_score_norm * 0.35 +
            hrv_score * 0.25 +
            hr_score * 0.15 +
            exercise_score * 0.15 +
            subjective_rating * 0.10
        )
        
        daily_record = {
            'date': today,
            'sleep_hours': sleep_hours,
            'sleep_score': sleep_score,
            'deep_sleep_min': deep_sleep_min,
            'morning_hrv': morning_hrv,
            'resting_hr': resting_hr,
            'steps': steps,
            'exercise_min': exercise_min,
            'deep_work_hours': deep_work_hours,
            'subjective_rating': subjective_rating,
            'energy_score': round(energy_score, 1),
            'component_scores': {
                'sleep': round(sleep_score_norm, 1),
                'hrv': round(hrv_score, 1),
                'heart_rate': round(hr_score, 1),
                'exercise': round(exercise_score, 1)
            }
        }
        
        # 移除旧的同日数据（如果有）
        self.daily_data = [d for d in self.daily_data if d['date'] != today]
        self.daily_data.append(daily_record)
        self.daily_data.sort(key=lambda x: x['date'])
        self._save_json(self.log_path, self.daily_data)
        
        return daily_record
    
    def _calculate_hrv_score(self, hrv: float) -> float:
        """计算HRV得分"""
        baseline = self.config['baseline']['hrv_baseline']
        diff_pct = (hrv - baseline) / baseline * 100
        
        if diff_pct >= 10:
            return 100
        elif diff_pct >= 0:
            return 85 + (diff_pct / 10) * 15
        elif diff_pct >= -10:
            return 70 + ((diff_pct + 10) / 10) * 15
        elif diff_pct >= -20:
            return 50 + ((diff_pct + 20) / 10) * 20
        else:
            return max(0, 30 + ((diff_pct + 30) / 10) * 20)
    
    def _calculate_hr_score(self, hr: int) -> float:
        """计算心率得分"""
        baseline = self.config['baseline']['resting_hr_baseline']
        
        if hr <= baseline:
            return 100
        elif hr <= baseline + 5:
            return 90
        elif hr <= baseline + 10:
            return 75
        elif hr <= baseline + 15:
            return 60
        elif hr <= baseline + 20:
            return 45
        else:
            return 30
    
    def check_alerts(self) -> Tuple[str, List[str], Dict]:
        """
        检查预警状态
        返回：(预警等级, 恢复建议列表, 详细诊断)
        """
        if len(self.daily_data) < 3:
            return 'green', ['数据不足，继续采集'], {}
        
        recent = sorted(self.daily_data, key=lambda x: x['date'], reverse=True)[:7]
        baseline = self.config['baseline']
        thresholds = self.config['thresholds']
        
        diagnosis = {
            'sleep_consecutive_low': 0,
            'hr_elevated': False,
            'hrv_trend': 'stable',
            'energy_trend': 'stable'
        }
        
        # 检查连续睡眠不足
        for d in recent:
            if d['sleep_hours'] < thresholds['red']['sleep_hours']:
                diagnosis['sleep_consecutive_low'] += 1
            else:
                break
        
        # 检查今日静息心率
        today_hr = recent[0]['resting_hr']
        diagnosis['hr_elevated'] = today_hr
        
        # HRV趋势分析
        if len(recent) >= 3:
            hrv_values = [d['morning_hrv'] for d in recent[:3]]
            if hrv_values[0] < hrv_values[1] < hrv_values[2]:
                diagnosis['hrv_trend'] = 'rising'
            elif hrv_values[0] > hrv_values[1] > hrv_values[2]:
                diagnosis['hrv_trend'] = 'falling'
        
        # 综合精力趋势
        if len(recent) >= 3:
            energy_values = [d['energy_score'] for d in recent[:3]]
            if sum(energy_values[:2]) / 2 < sum(energy_values[1:]) / 2:
                diagnosis['energy_trend'] = 'improving'
            elif sum(energy_values[:2]) / 2 > sum(energy_values[1:]) / 2:
                diagnosis['energy_trend'] = 'declining'
        
        # 判断预警等级
        if (diagnosis['sleep_consecutive_low'] >= thresholds['red']['consecutive_days'] or
            today_hr >= thresholds['red']['resting_hr'] or
            recent[0]['energy_score'] < thresholds['red']['energy_score']):
            alert_level = 'red'
        elif (diagnosis['sleep_consecutive_low'] >= thresholds['orange']['consecutive_days'] or
              today_hr >= thresholds['orange']['resting_hr']):
            alert_level = 'orange'
        elif (diagnosis['sleep_consecutive_low'] >= thresholds['yellow']['consecutive_days'] or
              today_hr >= thresholds['yellow']['resting_hr'] or
              diagnosis['hrv_trend'] == 'falling'):
            alert_level = 'yellow'
        else:
            alert_level = 'green'
        
        # 获取恢复建议
        recovery_actions = self.config['recovery_actions'].get(alert_level, [])
        
        # 记录预警历史
        if alert_level != 'green':
            self.alert_history.append({
                'date': datetime.date.today().isoformat(),
                'level': alert_level,
                'diagnosis': diagnosis,
                'actions': recovery_actions,
                'energy_score': recent[0]['energy_score']
            })
            self._save_json(self.alert_path, self.alert_history)
        
        return alert_level, recovery_actions, diagnosis
    
    def generate_daily_report(self) -> str:
        """生成每日报告"""
        if not self.daily_data:
            return "暂无数据"
        
        today_data = sorted(self.daily_data, key=lambda x: x['date'])[-1]
        alert_level, actions, diagnosis = self.check_alerts()
        
        emoji_map = {'green': '🟢', 'yellow': '🟡', 'orange': '🟠', 'red': '🔴'}
        
        report = f"""
{'='*50}
📊 每日精力管理报告 - {today_data['date']}
{'='*50}

【综合状态】 {emoji_map.get(alert_level, '⚪')} {alert_level.upper()}
综合精力评分: {today_data['energy_score']}/100

【分项得分】
• 🛌 睡眠: {today_data['component_scores']['sleep']} 
  - {today_data['sleep_hours']:.1f}小时, 评分{today_data['sleep_score']}分
• 💓 HRV: {today_data['component_scores']['hrv']}
  - 晨间HRV: {today_data['morning_hrv']}ms
• ❤️ 心率: {today_data['component_scores']['heart_rate']}
  - 静息心率: {today_data['resting_hr']}bpm
• 🏃 运动: {today_data['component_scores']['exercise']}
  - {today_data['exercise_min']}分钟, {today_data['steps']:,}步

【工作效率】
• 深度工作: {today_data['deep_work_hours']:.1f}小时
• 自我状态评分: {today_data['subjective_rating']}/100

【趋势分析】
• HRV趋势: {diagnosis.get('hrv_trend', '未知')}
• 精力趋势: {diagnosis.get('energy_trend', '未知')}
• 连续睡眠不足: {diagnosis.get('sleep_consecutive_low', 0)}天
"""
        
        if alert_level != 'green':
            report += f"\n【⚠️ 恢复建议】\n"
            for i, action in enumerate(actions, 1):
                report += f"  {i}. {action}\n"
        
        report += f"\n{'='*50}\n"
        
        return report
    
    def get_weekly_summary(self) -> str:
        """生成周度总结"""
        if len(self.daily_data) < 7:
            return "数据不足7天，无法生成周度总结"
        
        week_data = sorted(self.daily_data, key=lambda x: x['date'])[-7:]
        
        avg_sleep = sum(d['sleep_hours'] for d in week_data) / 7
        avg_energy = sum(d['energy_score'] for d in week_data) / 7
        avg_hr = sum(d['resting_hr'] for d in week_data) / 7
        avg_hrv = sum(d['morning_hrv'] for d in week_data) / 7
        total_exercise = sum(d['exercise_min'] for d in week_data)
        
        alert_count = sum(1 for a in self.alert_history 
                         if a['date'] in [d['date'] for d in week_data])
        
        summary = f"""
📈 周度精力总结 - {week_data[0]['date']} 至 {week_data[-1]['date']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【核心指标周平均】
• 平均睡眠: {avg_sleep:.1f}小时/天
• 平均精力评分: {avg_energy:.1f}/100
• 平均静息心率: {avg_hr:.1f} bpm
• 平均晨间HRV: {avg_hrv:.1f} ms
• 周总运动: {total_exercise}分钟

【预警统计】
• 本周预警次数: {alert_count}次

【状态评估】
"""
        if avg_energy >= 80:
            summary += "• ✅ 整体状态优秀，继续保持！\n"
        elif avg_energy >= 65:
            summary += "• ⚡ 状态良好，还有提升空间\n"
        else:
            summary += "• ⚠️ 需要关注精力恢复\n"
        
        if avg_sleep >= 7:
            summary += "• ✅ 睡眠达标\n"
        else:
            summary += "• ⚠️ 睡眠不足，建议调整作息\n"
        
        if total_exercise >= 150:
            summary += "• ✅ 运动量达标（WHO标准）\n"
        else:
            summary += f"• ⚠️ 运动不足，还差{150-total_exercise}分钟达标\n"
        
        return summary


# ==================== 使用示例 ====================

def main():
    """主函数演示"""
    # print("🚀 创业者精力管理系统 v1.0")
    # print("-" * 40)
    
    ems = EnergyManagementSystem(CONFIG)
    
    # 演示：添加模拟数据
    # print("\n📝 添加今日精力数据...")
    result = ems.add_daily_data(
        sleep_hours=7.2,
        sleep_score=82,
        deep_sleep_min=95,
        morning_hrv=48.0,
        resting_hr=63,
        steps=8500,
        exercise_min=35,
        deep_work_hours=4.5,
        subjective_rating=85
    )
    # print(f"✅ 今日精力评分: {result['energy_score']}/100")
    
    # 检查预警
    # print("\n🔍 检查预警状态...")
    level, actions, diagnosis = ems.check_alerts()
    # print(f"   预警等级: {level}")
    if actions:
        # print("   建议措施:")
        for action in actions:
            # print(f"    • {action}")
    
    # 生成报告
    # print("\n" + ems.generate_daily_report())
    
    # print("\n💡 提示：将此脚本与iOS快捷指令集成，可实现全自动运行！")


if __name__ == '__main__':
    main()

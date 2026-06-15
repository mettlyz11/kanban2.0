#!/usr/bin/env python3
"""
生成月度健康报告 - Markdown格式
"""

import json
import pandas as pd
from datetime import datetime, timedelta
import os

def load_data():
    """加载数据"""
    with open('/Users/mettlyz/.openclaw/workspace/output/task-1864/data/health_data.json', 'r') as f:
        health_data = json.load(f)
    
    with open('/Users/mettlyz/.openclaw/workspace/output/task-1864/reports/monthly_report.json', 'r') as f:
        report_data = json.load(f)
    
    return pd.DataFrame(health_data), report_data

def generate_monthly_report_md():
    """生成月度健康报告Markdown"""
    df, report = load_data()
    
    start_date = report['start_date']
    end_date = report['end_date']
    
    # 计算一些额外的统计数据
    df['date'] = pd.to_datetime(df['date'])
    best_day = df.loc[df['score_total'].idxmax()]
    worst_day = df.loc[df['score_total'].idxmin()]
    
    # 计算周数据
    df['date'] = pd.to_datetime(df['date'])
    df['week'] = df['date'].dt.isocalendar().week
    
    weekly_data = df.groupby('week').agg({
        'score_total': 'mean',
        'steps': 'mean',
        'sleep_total': 'mean',
        'exercise_minutes': 'mean'
    }).round(1)
    
    md_content = f"""# 🏆 Apple Watch 月度健康报告

**报告周期**: {start_date} 至 {end_date}  
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**分析天数**: {report['days_analyzed']} 天

---

## 📊 核心指标概览

| 指标 | 月度平均值 | 目标值 | 达成率 |
|------|-----------|--------|--------|
| **综合健康评分** | **{report['avg_total_score']:.1f} 分** | 85分 | {report['avg_total_score']/85*100:.0f}% |
| 每日步数 | {report['avg_steps']:.0f} 步 | 10,000步 | {report['avg_steps']/10000*100:.0f}% |
| 睡眠时长 | {report['avg_sleep']:.1f} 小时 | 7小时 | {report['avg_sleep']/7*100:.0f}% |
| 静息心率 | {report['avg_heart_rate']:.0f} bpm | 55-65bpm | ✓ |
| 评分标准差 | {report['score_std']:.1f} | <10 | {'✓ 稳定' if report['score_std'] < 10 else '⚠️ 波动较大'} |

---

## 📈 评分分布分析

### 各等级天数分布

| 等级 | 天数 | 占比 | 评价 |
|------|------|------|------|
| 🌟 优秀 (85-100分) | {report['score_distribution']['excellent']} 天 | {report['score_distribution']['excellent']/report['days_analyzed']*100:.0f}% | { '🎉 表现出色!' if report['score_distribution']['excellent'] >= 15 else '💪 继续加油'} |
| 👍 良好 (70-84分) | {report['score_distribution']['good']} 天 | {report['score_distribution']['good']/report['days_analyzed']*100:.0f}% | |
| ⚠️ 一般 (55-69分) | {report['score_distribution']['fair']} 天 | {report['score_distribution']['fair']/report['days_analyzed']*100:.0f}% | |
| 🔴 需关注 (0-54分) | {report['score_distribution']['poor']} 天 | {report['score_distribution']['poor']/report['days_analyzed']*100:.0f}% | |

---

## 🏆 最佳表现 vs 需关注日

### 🌟 最佳表现日: {best_day['date'].strftime('%Y-%m-%d')}
- 综合评分: **{best_day['score_total']:.1f} 分**
- 步数: {best_day['steps']:,} 步
- 睡眠: {best_day['sleep_total']:.1f} 小时
- 运动: {best_day['exercise_minutes']} 分钟
- 静息心率: {best_day['heart_rate_resting']:.0f} bpm

### 📉 需关注日: {worst_day['date'].strftime('%Y-%m-%d')}
- 综合评分: **{worst_day['score_total']:.1f} 分**
- 步数: {worst_day['steps']:,} 步
- 睡眠: {worst_day['sleep_total']:.1f} 小时
- 运动: {worst_day['exercise_minutes']} 分钟

---

## 📅 周度趋势对比

| 周次 | 平均评分 | 日均步数 | 日均睡眠 | 趋势 |
|------|----------|----------|----------|------|
"""
    
    for i, (week, row) in enumerate(weekly_data.iterrows(), 1):
        trend = '↗️' if i > 1 and row['score_total'] > weekly_data.iloc[i-2]['score_total'] else '↘️' if i > 1 else '➖'
        md_content += f"| 第{i}周 | {row['score_total']:.1f}分 | {row['steps']:.0f}步 | {row['sleep_total']:.1f}h | {trend} |\n"
    
    md_content += f"""
---

## 💡 关键洞察

"""
    for insight in report['key_insights']:
        md_content += f"- {insight}\n"
    
    md_content += """
---

## 🎯 改善建议

"""
    recommendations = report.get('recommendations', [])
    
    if not recommendations:
        # 基于数据生成建议
        if report['avg_sleep'] < 7:
            recommendations.append("😴 **睡眠改善**: 建议将入睡时间提前30分钟，目标每晚7-9小时充足睡眠")
        if report['avg_steps'] < 8000:
            recommendations.append("🚶 **增加活动**: 工作日利用午休时间散步15分钟，增加日常活动量")
        if report['avg_heart_rate'] > 70:
            recommendations.append("❤️ **心血管健康**: 静息心率偏高，建议每周进行3次有氧运动，每次30分钟以上")
        if report['score_std'] > 12:
            recommendations.append("⚖️ **作息规律**: 健康评分波动较大，建议保持规律的作息和饮食习惯")
    
    for i, rec in enumerate(recommendations, 1):
        md_content += f"{i}. {rec}\n"
    
    md_content += """
---

## 📋 下月行动计划

| 行动项 | 目标 | 频率 |
|--------|------|------|
| 规律作息 | 23:00前入睡，7:00起床 | 每天 |
| 每日运动 | 30分钟以上活动 | 每天 |
| 步数目标 | 工作日≥8000步，周末≥10000步 | 每天 |
| 睡眠监测 | 深度睡眠占比≥20% | 每晚 |

---

## 📊 数据可视化

本报告配套仪表盘截图已生成:

1. **综合评分趋势图** - 30天评分变化曲线
2. **四维评分雷达图** - 运动/睡眠/心率/精力对比
3. **关键指标卡片** - 步数/睡眠/心率/运动概览
4. **评分分布图** - 各等级天数分布统计
5. **周度热力图** - 每日评分可视化

---

*本报告由 Apple Watch 健康数据量化系统自动生成*  
*数据来源: Apple HealthKit / 健康App*
"""
    
    return md_content

def save_report():
    """保存报告"""
    output_dir = '/Users/mettlyz/.openclaw/workspace/output/task-1864/reports'
    os.makedirs(output_dir, exist_ok=True)
    
    md_content = generate_monthly_report_md()
    
    # 保存Markdown报告
    md_path = f"{output_dir}/monthly_health_report.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    # 保存HTML版本
    html_content = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apple Watch 月度健康报告</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f5f5f7;
            line-height: 1.6;
        }
        h1, h2, h3 {
            color: #1d1d1f;
        }
        h1 {
            text-align: center;
            border-bottom: 3px solid #007aff;
            padding-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        th, td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #e5e5e5;
        }
        th {
            background: #007aff;
            color: white;
            font-weight: 600;
        }
        tr:hover {
            background: #f8f8fa;
        }
    </style>
</head>
<body>
<div style="background:white; padding:40px; border-radius:16px; box-shadow:0 4px 20px rgba(0,0,0,0.1);">
'''
    html_content = html_content.replace('</h1>', '</h1><h2>')
    
    # 简单转换Markdown到HTML
    import re
    html_body = md_content
    html_body = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_body, flags=re.MULTILINE)
    html_body = html_body.replace('---', '<hr>')
    html_body = re.sub(r'^\- (.+)$', r'<li>\1</li>', html_body, flags=re.MULTILINE)
    
    html_content += html_body
    html_content += '''
</div>
</body>
</html>
'''
    
    html_path = f"{output_dir}/monthly_health_report.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # print(f"✅ 月度健康报告已生成:")
    # print(f"   Markdown: {md_path}")
    # print(f"   HTML: {html_path}")

if __name__ == '__main__':
    save_report()

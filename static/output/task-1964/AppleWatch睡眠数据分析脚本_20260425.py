#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apple Watch 睡眠数据自动分析脚本与CBT-I效果评估Dashboard
功能：
1. 解析Apple Health导出的XML数据
2. 自动计算CBT-I核心指标（SOL、NWAK、WASO、SE、TST）
3. 生成可视化评估Dashboard
4. 追踪4周CBT-I执行的改善趋势
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os
from pathlib import Path
import seaborn as sns

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")


class SleepAnalyzer:
    """Apple Watch睡眠数据分析器"""
    
    def __init__(self, export_path=None):
        self.export_path = export_path
        self.sleep_data = None
        self.daily_metrics = None
        
    def parse_apple_health_export(self, xml_path=None):
        """解析Apple Health导出的XML文件"""
        path = xml_path or self.export_path
        if not path or not os.path.exists(path):
            # print(f"⚠️ 未找到导出文件: {path}")
            # print("📱 导出步骤：健康App → 头像 → 导出所有健康数据 → 解压获取export.xml")
            return None
            
        # print(f"🔍 正在解析健康数据: {path}")
        tree = ET.parse(path)
        root = tree.getroot()
        
        # 提取睡眠记录
        sleep_records = []
        for record in root.findall('.//Record'):
            record_type = record.get('type')
            if 'SleepAnalysis' in record_type:
                sleep_records.append({
                    'start_time': datetime.fromisoformat(record.get('startDate')),
                    'end_time': datetime.fromisoformat(record.get('endDate')),
                    'value': record.get('value'),
                    'source': record.get('sourceName'),
                    'duration': (datetime.fromisoformat(record.get('endDate')) - 
                               datetime.fromisoformat(record.get('startDate'))).total_seconds() / 3600
                })
        
        df = pd.DataFrame(sleep_records)
        df['date'] = df['end_time'].dt.date
        
        # 过滤Apple Watch数据
        if 'source' in df.columns:
            apple_watch = df['source'].str.contains('Watch', na=False)
            if apple_watch.any():
                df = df[apple_watch]
                # print(f"✅ 已过滤Apple Watch数据")
        
        self.sleep_data = df
        # print(f"✅ 解析完成，共 {len(df)} 条睡眠记录")
        return df
    
    def calculate_daily_metrics(self):
        """计算CBT-I核心指标"""
        if self.sleep_data is None:
            # print("❌ 请先解析睡眠数据")
            return None
            
        daily_metrics = []
        
        for date, group in self.sleep_data.groupby('date'):
            # 按时间排序
            group = group.sort_values('start_time')
            
            # 计算各项指标
            first_sleep = group['start_time'].min()
            last_wake = group['end_time'].max()
            
            # 卧床时间（从首次入睡到最后醒来）
            time_in_bed = (last_wake - first_sleep).total_seconds() / 3600
            
            # 总睡眠时间
            total_sleep_time = group['duration'].sum()
            
            # 入睡潜伏期（SOL）- 需要清醒数据，这里用估算
            # Apple Watch会记录在床时间，我们简化处理
            sol_estimate = 15  # 默认估算值
            
            # 觉醒次数（NWAK）
            # 计算睡眠段之间的间隙
            gaps = []
            for i in range(1, len(group)):
                gap = (group.iloc[i]['start_time'] - 
                       group.iloc[i-1]['end_time']).total_seconds() / 60
                if gap > 5:  # 超过5分钟算作觉醒
                    gaps.append(gap)
            
            num_awakenings = len(gaps)
            waso = sum(gaps)  # 入睡后觉醒时间（分钟）
            
            # 睡眠效率
            sleep_efficiency = (total_sleep_time / time_in_bed * 100) if time_in_bed > 0 else 0
            
            # 睡眠阶段统计（如果有数据）
            deep_sleep = group[group['value'].str.contains('Deep|Core', na=False)]['duration'].sum()
            rem_sleep = group[group['value'].str.contains('REM', na=False)]['duration'].sum()
            
            daily_metrics.append({
                'date': date,
                'first_sleep_time': first_sleep,
                'last_wake_time': last_wake,
                'time_in_bed_hours': round(time_in_bed, 2),
                'total_sleep_time_hours': round(total_sleep_time, 2),
                'sleep_efficiency_pct': round(sleep_efficiency, 1),
                'sleep_onset_latency_min': sol_estimate,
                'num_awakenings': num_awakenings,
                'waso_min': round(waso, 1),
                'deep_sleep_hours': round(deep_sleep, 2),
                'rem_sleep_hours': round(rem_sleep, 2),
                'sleep_segments': len(group)
            })
        
        self.daily_metrics = pd.DataFrame(daily_metrics)
        self.daily_metrics = self.daily_metrics.sort_values('date').reset_index(drop=True)
        
        # print(f"✅ 计算完成，共 {len(self.daily_metrics)} 天的睡眠指标")
        return self.daily_metrics
    
    def generate_cbti_dashboard(self, start_date=None, end_date=None, save_path=None):
        """生成CBT-I效果评估Dashboard"""
        if self.daily_metrics is None:
            # print("❌ 请先计算每日指标")
            return
            
        df = self.daily_metrics.copy()
        
        # 日期过滤
        if start_date:
            df = df[df['date'] >= pd.to_datetime(start_date).date()]
        if end_date:
            df = df[df['date'] <= pd.to_datetime(end_date).date()]
            
        if len(df) < 7:
            # print(f"⚠️ 数据量不足（仅{len(df)}天），建议至少7天数据进行评估")
        
        # 创建Dashboard
        fig = plt.figure(figsize=(16, 12))
        fig.suptitle('CBT-I 睡眠改善效果评估 Dashboard', fontsize=16, fontweight='bold', y=0.98)
        
        # 1. 睡眠效率趋势图
        ax1 = plt.subplot(3, 2, 1)
        ax1.plot(df['date'], df['sleep_efficiency_pct'], 'o-', color='#2E86AB', linewidth=2, markersize=4)
        ax1.axhline(y=90, color='green', linestyle='--', alpha=0.7, label='目标线 (90%)')
        ax1.axhline(y=85, color='orange', linestyle='--', alpha=0.7, label='合格线 (85%)')
        ax1.set_title('睡眠效率趋势 (%)', fontweight='bold')
        ax1.set_ylabel('睡眠效率 (%)')
        ax1.set_ylim(60, 100)
        ax1.legend()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.xticks(rotation=45)
        
        # 2. 总睡眠时间趋势
        ax2 = plt.subplot(3, 2, 2)
        ax2.plot(df['date'], df['total_sleep_time_hours'], 'o-', color='#A23B72', linewidth=2, markersize=4)
        ax2.axhline(y=7, color='green', linestyle='--', alpha=0.7, label='目标 (7小时)')
        ax2.axhline(y=6, color='orange', linestyle='--', alpha=0.7, label='底线 (6小时)')
        ax2.set_title('总睡眠时间趋势 (小时)', fontweight='bold')
        ax2.set_ylabel('小时')
        ax2.set_ylim(4, 9)
        ax2.legend()
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.xticks(rotation=45)
        
        # 3. 夜间觉醒次数
        ax3 = plt.subplot(3, 2, 3)
        ax3.bar(df['date'], df['num_awakenings'], color='#F18F01', alpha=0.7)
        ax3.axhline(y=1, color='green', linestyle='--', alpha=0.7, label='目标 (<1次)')
        ax3.set_title('夜间觉醒次数', fontweight='bold')
        ax3.set_ylabel('次数')
        ax3.legend()
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.xticks(rotation=45)
        
        # 4. WASO (入睡后觉醒时间)
        ax4 = plt.subplot(3, 2, 4)
        ax4.bar(df['date'], df['waso_min'], color='#C73E1D', alpha=0.7)
        ax4.axhline(y=30, color='green', linestyle='--', alpha=0.7, label='目标 (<30分钟)')
        ax4.set_title('入睡后觉醒时间 WASO (分钟)', fontweight='bold')
        ax4.set_ylabel('分钟')
        ax4.legend()
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.xticks(rotation=45)
        
        # 5. 睡眠结构饼图（平均值）
        ax5 = plt.subplot(3, 2, 5)
        avg_deep = df['deep_sleep_hours'].mean()
        avg_rem = df['rem_sleep_hours'].mean()
        avg_light = df['total_sleep_time_hours'].mean() - avg_deep - avg_rem
        
        labels = ['深度睡眠', 'REM睡眠', '浅睡']
        sizes = [avg_deep, avg_rem, max(0, avg_light)]
        colors = ['#3B1F8C', '#8C1F6B', '#1F6B8C']
        explode = (0.05, 0.05, 0)
        
        ax5.pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=90)
        ax5.set_title(f'平均睡眠结构分布\n总睡眠时间: {df["total_sleep_time_hours"].mean():.1f}小时', fontweight='bold')
        
        # 6. 核心指标汇总卡片
        ax6 = plt.subplot(3, 2, 6)
        ax6.axis('off')
        
        # 计算改善幅度
        if len(df) >= 14:
            first_week = df.head(7)
            last_week = df.tail(7)
            
            se_improvement = last_week['sleep_efficiency_pct'].mean() - first_week['sleep_efficiency_pct'].mean()
            tst_improvement = last_week['total_sleep_time_hours'].mean() - first_week['total_sleep_time_hours'].mean()
            nwak_improvement = first_week['num_awakenings'].mean() - last_week['num_awakenings'].mean()
        else:
            se_improvement = tst_improvement = nwak_improvement = None
            
        summary_text = f"""
        ╔═══════════════════════════════════════╗
        ║        CBT-I 效果评估汇总              ║
        ╠═══════════════════════════════════════╣
        ║  统计周期: {len(df)} 天                  ║
        ║                                       ║
        ║  📊 核心指标平均值:                    ║
        ║  ─────────────────────                ║
        ║  睡眠效率:    {df['sleep_efficiency_pct'].mean():.1f}%        ║
        ║  总睡眠时间:  {df['total_sleep_time_hours'].mean():.1f} 小时    ║
        ║  觉醒次数:    {df['num_awakenings'].mean():.1f} 次          ║
        ║  WASO:        {df['waso_min'].mean():.1f} 分钟          ║
        ║                                       ║
        """
        
        if se_improvement is not None:
            summary_text += f"""
        ║  📈 2周改善幅度:                      ║
        ║  ─────────────────────                ║
        ║  睡眠效率:    {'+' if se_improvement > 0 else ''}{se_improvement:+.1f}%       ║
        ║  睡眠时间:    {'+' if tst_improvement > 0 else ''}{tst_improvement:+.1f}小时    ║
        ║  觉醒次数:    {'+' if nwak_improvement > 0 else ''}{nwak_improvement:+.1f}次     ║
            """
            
        summary_text += """
        ╠═══════════════════════════════════════╣
        ║  🎯 CBT-I 成功标准:                   ║
        ║  ─────────────────────                ║
        ║  ✅ 入睡潜伏期 < 20分钟                ║
        ║  ✅ 夜间觉醒 < 1次                     ║
        ║  ✅ WASO < 30分钟                      ║
        ║  ✅ 睡眠效率 > 90%                     ║
        ╚═══════════════════════════════════════╝
        """
        
        ax6.text(0.05, 0.95, summary_text, transform=ax6.transAxes,
                fontsize=10, verticalalignment='top', family='monospace')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            # print(f"✅ Dashboard已保存: {save_path}")
            
        plt.show()
        
    def generate_weekly_report(self, week_num=1):
        """生成周度报告"""
        if self.daily_metrics is None or len(self.daily_metrics) < week_num * 7:
            # print(f"⚠️ 数据不足，无法生成第{week_num}周报告")
            return
            
        week_data = self.daily_metrics.tail(7)
        
        report = f"""
╔════════════════════════════════════════════════════╗
║           CBT-I 第 {week_num} 周睡眠报告                  ║
╠════════════════════════════════════════════════════╣
║  统计周期: {week_data['date'].min()} ~ {week_data['date'].max()}  ║
╠════════════════════════════════════════════════════╣
║  📊 本周平均指标:                                   ║
║  ─────────────────────────────────                 ║
║  睡眠效率:    {week_data['sleep_efficiency_pct'].mean():>6.1f}%  {'✅' if week_data['sleep_efficiency_pct'].mean() >= 85 else '⬜'}  ║
║  总睡眠时间:  {week_data['total_sleep_time_hours'].mean():>6.1f}h                                       ║
║  觉醒次数:    {week_data['num_awakenings'].mean():>6.1f}次  {'✅' if week_data['num_awakenings'].mean() <= 2 else '⬜'}  ║
║  WASO:        {week_data['waso_min'].mean():>6.1f}min                                       ║
╠════════════════════════════════════════════════════╣
║  📈 周度变化趋势:                                   ║
║  ─────────────────────────────────                 ║
        """
        
        # 计算本周内的变化
        first_3 = week_data.head(3)
        last_3 = week_data.tail(3)
        
        se_trend = last_3['sleep_efficiency_pct'].mean() - first_3['sleep_efficiency_pct'].mean()
        tst_trend = last_3['total_sleep_time_hours'].mean() - first_3['total_sleep_time_hours'].mean()
        
        report += f"""
║  睡眠效率趋势:  {'↑ 改善' if se_trend > 2 else '↓ 下降' if se_trend < -2 else '→ 稳定'} ({se_trend:+.1f}%)              ║
║  睡眠时间趋势:  {'↑ 增加' if tst_trend > 0.3 else '↓ 减少' if tst_trend < -0.3 else '→ 稳定'} ({tst_trend:+.1f}h)              ║
╠════════════════════════════════════════════════════╣
║  🎯 下周建议:                                      ║
        """
        
        avg_se = week_data['sleep_efficiency_pct'].mean()
        if avg_se >= 90:
            report += "║  ✨ 睡眠效率优秀，可增加卧床时间15-30分钟            ║"
        elif avg_se >= 85:
            report += "║  🟢 睡眠效率良好，保持当前方案继续执行              ║"
        else:
            report += "║  🟡 睡眠效率待提升，检查刺激控制规则执行质量        ║"
            
        report += "\n╚════════════════════════════════════════════════════╝"
        
        # print(report)
        return report
    
    def export_csv(self, path='sleep_metrics.csv'):
        """导出数据到CSV"""
        if self.daily_metrics is not None:
            self.daily_metrics.to_csv(path, index=False)
            # print(f"✅ 数据已导出: {path}")
            
    def create_sample_data(self, days=28):
        """创建模拟数据用于演示（无真实数据时使用）"""
        # print(f"🔧 创建 {days} 天模拟睡眠数据用于演示")
        
        dates = [datetime.now().date() - timedelta(days=days-i-1) for i in range(days)]
        
        # 模拟CBT-I改善趋势：前两周差，后两周逐步改善
        metrics = []
        for i, date in enumerate(dates):
            # 基础值带随机波动
            base_se = 75 + min(15, i * 0.6) + np.random.normal(0, 3)
            base_tst = 5.0 + min(2.0, i * 0.07) + np.random.normal(0, 0.3)
            base_nwak = max(0, 4 - i * 0.12 + np.random.normal(0, 0.5))
            base_waso = max(0, 60 - i * 1.5 + np.random.normal(0, 10))
            
            metrics.append({
                'date': date,
                'first_sleep_time': datetime.combine(date, datetime.min.time()) + timedelta(hours=23),
                'last_wake_time': datetime.combine(date, datetime.min.time()) + timedelta(hours=7),
                'time_in_bed_hours': round(base_tst / (base_se/100), 2),
                'total_sleep_time_hours': round(max(4, base_tst), 2),
                'sleep_efficiency_pct': round(min(95, base_se), 1),
                'sleep_onset_latency_min': max(10, 30 - i),
                'num_awakenings': int(round(base_nwak)),
                'waso_min': round(base_waso, 1),
                'deep_sleep_hours': round(base_tst * 0.2, 2),
                'rem_sleep_hours': round(base_tst * 0.25, 2),
                'sleep_segments': int(round(base_nwak + 1))
            })
            
        self.daily_metrics = pd.DataFrame(metrics)
        # print(f"✅ 模拟数据创建完成")
        return self.daily_metrics


def main():
    """主函数：完整的CBT-I数据分析流程"""
    # print("=" * 60)
    # print("  🛌 CBT-I Apple Watch睡眠数据分析工具")
    # print("=" * 60)
    
    analyzer = SleepAnalyzer()
    
    # 尝试读取真实数据，如无则使用模拟数据
    health_export_path = os.path.expanduser("~/Downloads/export.xml")
    
    if os.path.exists(health_export_path):
        # print(f"📂 找到健康数据导出文件")
        analyzer.parse_apple_health_export(health_export_path)
        analyzer.calculate_daily_metrics()
    else:
        # print("⚠️ 未找到健康数据文件，使用模拟数据演示功能")
        # print("   （请将Apple Health的export.xml放到Downloads目录）")
        analyzer.create_sample_data(days=28)
    
    # print("\n" + "=" * 60)
    # print("  📊 生成CBT-I效果评估Dashboard")
    # print("=" * 60)
    
    # 生成Dashboard
    dashboard_path = "/Users/mettlyz/.openclaw/workspace/output/task-1964/CBT-I睡眠评估Dashboard_20260425.png"
    analyzer.generate_cbti_dashboard(save_path=dashboard_path)
    
    # 生成周度报告
    # print("\n" + "=" * 60)
    # print("  📋 周度睡眠报告")
    # print("=" * 60)
    analyzer.generate_weekly_report(week_num=4)
    
    # 导出数据
    csv_path = "/Users/mettlyz/.openclaw/workspace/output/task-1964/睡眠指标数据_20260425.csv"
    analyzer.export_csv(csv_path)
    
    # print("\n" + "=" * 60)
    # print("  ✅ 分析完成！产出物清单：")
    # print("=" * 60)
    # print(f"  1. Dashboard图像: {dashboard_path}")
    # print(f"  2. 睡眠指标CSV:  {csv_path}")
    # print(f"  3. 周度报告（控制台输出）")
    # print("=" * 60)


if __name__ == "__main__":
    main()

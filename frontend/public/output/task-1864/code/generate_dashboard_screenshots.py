#!/usr/bin/env python3
"""
生成仪表盘截图 - 使用matplotlib创建可视化图表
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import numpy as np
from datetime import datetime, timedelta
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('dark_background')

def load_health_data():
    """加载健康数据"""
    with open('/Users/mettlyz/.openclaw/workspace/output/task-1864/data/health_data.json', 'r') as f:
        data = json.load(f)
    return pd.DataFrame(data)

def create_score_overview(df):
    """创建综合评分概览图"""
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # 转换日期
    df['date'] = pd.to_datetime(df['date'])
    
    # 绘制评分趋势
    line = ax.plot(df['date'], df['score_total'], color='#73D676', linewidth=3, marker='o', markersize=6)
    ax.fill_between(df['date'], df['score_total'], alpha=0.3, color='#73D676')
    
    # 添加参考线
    ax.axhline(y=85, color='#EAB839', linestyle='--', alpha=0.7, label='优秀线 (85)')
    ax.axhline(y=70, color='#FF9800', linestyle='--', alpha=0.7, label='良好线 (70)')
    ax.axhline(y=55, color='#F44336', linestyle='--', alpha=0.7, label='警戒线 (55)')
    
    # 标注最新值
    latest_score = df['score_total'].iloc[-1]
    latest_date = df['date'].iloc[-1]
    ax.annotate(f'最新: {latest_score:.1f}分', 
                xy=(latest_date, latest_score), 
                xytext=(10, 30), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='#73D676', ec='none', alpha=0.9),
                fontsize=14, fontweight='bold', color='#1a1a1a')
    
    ax.set_title('综合健康评分趋势', fontsize=20, fontweight='bold', pad=20, color='white')
    ax.set_xlabel('日期', fontsize=14, color='white')
    ax.set_ylabel('评分 (0-100)', fontsize=14, color='white')
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.2)
    ax.legend(loc='upper left', fontsize=12)
    
    # 格式化x轴日期
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.tick_params(colors='white')
    
    plt.tight_layout()
    return fig

def create_dimensions_radar(df):
    """创建四维评分雷达图"""
    latest = df.iloc[-1]
    
    categories = ['运动', '睡眠', '心率', '精力']
    scores = [
        latest['score_exercise'],
        latest['score_sleep'],
        latest['score_heart'],
        latest['score_energy']
    ]
    
    # 闭合雷达图
    scores += scores[:1]
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    # 绘制背景区域
    ax.fill(angles, [85]*5, color='#4CAF50', alpha=0.2, label='优秀')
    ax.fill(angles, [70]*5, color='#FF9800', alpha=0.2, label='良好')
    ax.fill(angles, [55]*5, color='#F44336', alpha=0.2, label='需关注')
    
    # 绘制当前评分
    ax.plot(angles, scores, 'o-', linewidth=3, color='#73D676', markersize=10)
    ax.fill(angles, scores, alpha=0.4, color='#73D676')
    
    # 设置标签
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=16, color='white')
    ax.set_ylim(0, 100)
    ax.set_title('各维度健康评分', fontsize=20, fontweight='bold', pad=30, color='white')
    ax.grid(True, alpha=0.3)
    ax.tick_params(colors='white')
    
    # 添加数值标注
    for i, (angle, score) in enumerate(zip(angles[:-1], scores[:-1])):
        ax.annotate(f'{score:.1f}分', xy=(angle, score + 5), 
                   ha='center', va='center', fontsize=14, fontweight='bold', color='white')
    
    plt.tight_layout()
    return fig

def create_metrics_cards(df):
    """创建指标卡"""
    latest = df.iloc[-1]
    avg = df.mean()
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('关键健康指标', fontsize=24, fontweight='bold', color='white', y=0.98)
    
    metrics = [
        ('今日步数', latest['steps'], '步', '#2196F3', 10000),
        ('睡眠时长', latest['sleep_total'], '小时', '#9C27B0', 7),
        ('静息心率', latest['heart_rate_resting'], 'bpm', '#F44336', 65),
        ('运动时长', latest['exercise_minutes'], '分钟', '#4CAF50', 30),
    ]
    
    for ax, (title, value, unit, color, target) in zip(axes.flat, metrics):
        # 计算完成率
        progress = min(value / target * 100, 120)
        
        # 背景色
        ax.set_facecolor('#2d2d2d')
        
        # 进度环
        circle = plt.Circle((0.5, 0.5), 0.35, color='#444444', fill=False, linewidth=15, transform=ax.transAxes)
        ax.add_artist(circle)
        
        progress_color = '#4CAF50' if progress >= 80 else '#FF9800' if progress >= 60 else '#F44336'
        theta = np.linspace(0, 2 * np.pi * progress / 100, 100)
        x = 0.5 + 0.35 * np.cos(theta)
        y = 0.5 + 0.35 * np.sin(theta)
        ax.plot(x, y, color=progress_color, linewidth=15, transform=ax.transAxes)
        
        # 数值
        ax.text(0.5, 0.55, f'{value:.0f}', fontsize=36, fontweight='bold', 
                ha='center', va='center', color='white', transform=ax.transAxes)
        ax.text(0.5, 0.35, unit, fontsize=18, ha='center', va='center', 
                color='#aaaaaa', transform=ax.transAxes)
        ax.text(0.5, 0.85, title, fontsize=20, fontweight='bold', ha='center', 
                va='center', color='white', transform=ax.transAxes)
        ax.text(0.5, 0.15, f'目标: {target}{unit}', fontsize=12, ha='center', 
                va='center', color='#888888', transform=ax.transAxes)
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
    
    plt.tight_layout()
    return fig

def create_score_distribution(df):
    """创建评分分布图"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    
    # 评分分布柱状图
    bins = [0, 55, 70, 85, 100]
    labels = ['需关注\n(0-55)', '一般\n(55-70)', '良好\n(70-85)', '优秀\n(85-100)']
    colors = ['#F44336', '#FF9800', '#FFEB3B', '#4CAF50']
    
    hist, _ = np.histogram(df['score_total'], bins=bins)
    bars = ax1.bar(labels, hist, color=colors, alpha=0.8, edgecolor='white', linewidth=2)
    
    ax1.set_title('健康评分分布', fontsize=18, fontweight='bold', pad=20, color='white')
    ax1.set_ylabel('天数', fontsize=14, color='white')
    ax1.tick_params(colors='white')
    ax1.grid(True, alpha=0.2, axis='y')
    
    # 添加数值标签
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.3,
                f'{int(height)}天', ha='center', va='bottom', fontsize=14, fontweight='bold', color='white')
    
    # 各维度评分对比
    dimensions = ['综合', '运动', '睡眠', '心率', '精力']
    avg_scores = [
        df['score_total'].mean(),
        df['score_exercise'].mean(),
        df['score_sleep'].mean(),
        df['score_heart'].mean(),
        df['score_energy'].mean()
    ]
    
    bars2 = ax2.barh(dimensions, avg_scores, color=['#2196F3', '#4CAF50', '#9C27B0', '#F44336', '#FF9800'], alpha=0.8)
    ax2.set_xlim(0, 100)
    ax2.set_title('各维度平均得分', fontsize=18, fontweight='bold', pad=20, color='white')
    ax2.set_xlabel('平均得分', fontsize=14, color='white')
    ax2.tick_params(colors='white')
    ax2.grid(True, alpha=0.2, axis='x')
    
    # 添加数值标签
    for bar in bars2:
        width = bar.get_width()
        ax2.text(width + 1, bar.get_y() + bar.get_height()/2.,
                f'{width:.1f}分', ha='left', va='center', fontsize=12, fontweight='bold', color='white')
    
    plt.tight_layout()
    return fig

def create_weekly_trend(df):
    """创建周度趋势热力图"""
    df['date'] = pd.to_datetime(df['date'])
    df['week'] = df['date'].dt.isocalendar().week
    df['weekday'] = df['date'].dt.weekday
    
    # 创建热力图数据矩阵
    weeks = sorted(df['week'].unique())
    weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    
    heatmap_data = np.zeros((len(weeks), 7))
    
    for i, week in enumerate(weeks):
        for j in range(7):
            mask = (df['week'] == week) & (df['weekday'] == j)
            if mask.any():
                heatmap_data[i, j] = df[mask]['score_total'].values[0]
            else:
                heatmap_data[i, j] = np.nan
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    im = ax.imshow(heatmap_data, cmap='RdYlGn', vmin=50, vmax=100, aspect='auto')
    
    # 设置标签
    ax.set_xticks(np.arange(7))
    ax.set_xticklabels(weekdays, fontsize=12, color='white')
    ax.set_yticks(np.arange(len(weeks)))
    ax.set_yticklabels([f'第{w}周' for w in weeks], fontsize=12, color='white')
    
    # 在每个单元格中添加数值
    for i in range(len(weeks)):
        for j in range(7):
            if not np.isnan(heatmap_data[i, j]):
                text_color = 'white' if heatmap_data[i, j] < 70 else 'black'
                ax.text(j, i, f'{heatmap_data[i, j]:.0f}',
                       ha="center", va="center", color=text_color, fontsize=11, fontweight='bold')
    
    ax.set_title('每日健康评分热力图', fontsize=20, fontweight='bold', pad=20, color='white')
    cbar = plt.colorbar(im, ax=ax)
    cbar.ax.yaxis.label.set_color('white')
    cbar.ax.tick_params(colors='white')
    cbar.set_label('健康评分', color='white')
    
    plt.tight_layout()
    return fig

def generate_all_screenshots():
    """生成所有仪表盘截图"""
    output_dir = '/Users/mettlyz/.openclaw/workspace/output/task-1864/screenshots'
    os.makedirs(output_dir, exist_ok=True)
    
    print("加载健康数据...")
    df = load_health_data()
    
    print("生成综合评分趋势图...")
    fig1 = create_score_overview(df)
    fig1.savefig(f'{output_dir}/01_score_trend.png', dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
    plt.close(fig1)
    
    print("生成雷达图...")
    fig2 = create_dimensions_radar(df)
    fig2.savefig(f'{output_dir}/02_dimensions_radar.png', dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
    plt.close(fig2)
    
    print("生成指标卡...")
    fig3 = create_metrics_cards(df)
    fig3.savefig(f'{output_dir}/03_metrics_cards.png', dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
    plt.close(fig3)
    
    print("生成评分分布图...")
    fig4 = create_score_distribution(df)
    fig4.savefig(f'{output_dir}/04_score_distribution.png', dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
    plt.close(fig4)
    
    print("生成热力图...")
    fig5 = create_weekly_trend(df)
    fig5.savefig(f'{output_dir}/05_weekly_heatmap.png', dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
    plt.close(fig5)
    
    print(f"\n✅ 所有仪表盘截图已生成: {output_dir}")
    print(f"   共生成 {len(os.listdir(output_dir))} 张图表")

if __name__ == '__main__':
    generate_all_screenshots()

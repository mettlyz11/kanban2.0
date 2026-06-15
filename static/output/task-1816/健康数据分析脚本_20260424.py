#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康数据分析脚本
基于可穿戴设备数据的运动健康分析模型
日期：2026年4月24日
版本：v1.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt
import seaborn as sns

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


class SleepQualityScorer:
    """睡眠质量评分模型"""
    
    def __init__(self):
        self.weights = {
            'duration': 0.25,      # 总睡眠时长
            'efficiency': 0.20,    # 睡眠效率
            'deep_ratio': 0.20,    # 深睡比例
            'rem_ratio': 0.15,     # REM比例
            'latency': 0.10,       # 入睡潜伏期
            'awakenings': 0.10     # 夜间觉醒
        }
    
    def calculate_score(self, sleep_data):
        """
        计算睡眠质量综合评分
        
        Args:
            sleep_data: dict, 包含以下字段
                - total_duration: 总睡眠时长(分钟)
                - bed_time: 在床上时间(分钟)
                - deep_duration: 深睡时长(分钟)
                - rem_duration: REM时长(分钟)
                - sleep_latency: 入睡潜伏期(分钟)
                - awakenings_count: 醒来次数
        
        Returns:
            dict: 包含各维度得分和综合评分
        """
        scores = {}
        
        # 1. 总睡眠时长评分 (满分25分)
        optimal_duration = 480  # 8小时
        duration_diff = abs(sleep_data['total_duration'] - optimal_duration)
        scores['duration'] = max(0, 25 - (duration_diff / 60) * 2)
        
        # 2. 睡眠效率评分 (满分20分)
        efficiency = (sleep_data['total_duration'] / sleep_data['bed_time']) * 100
        sleep_data['efficiency'] = efficiency
        if efficiency >= 90:
            scores['efficiency'] = 20
        else:
            scores['efficiency'] = 20 * (efficiency / 90)
        
        # 3. 深睡比例评分 (满分20分)
        deep_ratio = sleep_data['deep_duration'] / sleep_data['total_duration']
        optimal_deep = 0.20
        deep_diff = abs(deep_ratio - optimal_deep)
        scores['deep_ratio'] = max(0, 20 - deep_diff * 100)
        
        # 4. REM比例评分 (满分15分)
        rem_ratio = sleep_data['rem_duration'] / sleep_data['total_duration']
        optimal_rem = 0.22
        rem_diff = abs(rem_ratio - optimal_rem)
        scores['rem_ratio'] = max(0, 15 - rem_diff * 80)
        
        # 5. 入睡潜伏期评分 (满分10分)
        latency = sleep_data['sleep_latency']
        if latency <= 15:
            scores['latency'] = 10
        elif latency <= 30:
            scores['latency'] = 8
        elif latency <= 45:
            scores['latency'] = 5
        else:
            scores['latency'] = max(0, 10 - (latency - 45) / 5)
        
        # 6. 夜间觉醒评分 (满分10分)
        awakenings = sleep_data['awakenings_count']
        if awakenings <= 1:
            scores['awakenings'] = 10
        else:
            scores['awakenings'] = max(0, 10 - (awakenings - 1) * 1.5)
        
        # 计算综合评分
        total_score = sum(scores.values())
        
        # 计算评分等级
        if total_score >= 90:
            grade = 'A'
            evaluation = '睡眠质量极佳'
        elif total_score >= 80:
            grade = 'B'
            evaluation = '睡眠质量良好'
        elif total_score >= 70:
            grade = 'C'
            evaluation = '睡眠质量一般'
        elif total_score >= 60:
            grade = 'D'
            evaluation = '睡眠质量较差'
        else:
            grade = 'F'
            evaluation = '睡眠质量很差'
        
        return {
            'dimension_scores': scores,
            'total_score': round(total_score, 1),
            'grade': grade,
            'evaluation': evaluation
        }


class ExerciseEvaluator:
    """运动效果评估模型"""
    
    def __init__(self, user_profile):
        """
        Args:
            user_profile: dict, 用户基础信息
                - age: 年龄
                - gender: 性别
                - weight: 体重(kg)
                - height: 身高(cm)
                - resting_hr: 静息心率
        """
        self.user = user_profile
        self.max_hr = 220 - user_profile['age']
        
    def calculate_hr_zones(self):
        """计算心率区间"""
        zones = {
            'zone1': (int(self.max_hr * 0.5), int(self.max_hr * 0.6)),
            'zone2': (int(self.max_hr * 0.6), int(self.max_hr * 0.7)),
            'zone3': (int(self.max_hr * 0.7), int(self.max_hr * 0.8)),
            'zone4': (int(self.max_hr * 0.8), int(self.max_hr * 0.9)),
            'zone5': (int(self.max_hr * 0.9), self.max_hr)
        }
        return zones
    
    def calculate_training_load(self, activity_data):
        """
        计算训练负荷
        
        Args:
            activity_data: dict
                - duration: 运动时长(分钟)
                - avg_hr: 平均心率
                - activity_type: 运动类型
        
        Returns:
            float: 训练负荷分数
        """
        # 根据平均心率确定强度系数
        hr_ratio = activity_data['avg_hr'] / self.max_hr
        if hr_ratio < 0.5:
            intensity = 1.0
        elif hr_ratio < 0.6:
            intensity = 1.5
        elif hr_ratio < 0.75:
            intensity = 2.0
        elif hr_ratio < 0.9:
            intensity = 3.0
        else:
            intensity = 4.0
        
        acute_load = activity_data['duration'] * intensity
        return acute_load
    
    def evaluate_exercise_effect(self, activity_data):
        """
        综合评估运动效果
        
        Returns:
            dict: 多维度运动效果评分
        """
        scores = {}
        
        # 1. 有氧效果评分 (满分30分)
        hr_zones = self.calculate_hr_zones()
        avg_hr = activity_data['avg_hr']
        
        if avg_hr >= hr_zones['zone3'][0]:
            aerobic_score = 30  # 达到有氧区间
        elif avg_hr >= hr_zones['zone2'][0]:
            aerobic_score = 25  # 燃脂区间
        else:
            aerobic_score = 15  # 低强度
        scores['aerobic'] = aerobic_score
        
        # 2. 卡路里消耗评分 (满分15分)
        target_calories = activity_data['duration'] * 8  # 目标8卡/分钟
        cal_ratio = min(1.0, activity_data['calories'] / target_calories)
        scores['calories'] = cal_ratio * 15
        
        # 3. 持续时间评分 (满分15分)
        optimal_duration = 45  # 45分钟最佳
        duration = activity_data['duration']
        if duration >= optimal_duration:
            scores['duration'] = 15
        else:
            scores['duration'] = (duration / optimal_duration) * 15
        
        # 4. 强度表现评分 (满分25分)
        max_hr_ratio = activity_data.get('max_hr', self.max_hr * 0.8) / self.max_hr
        scores['intensity'] = max_hr_ratio * 25
        
        # 5. 恢复评分 (满分15分)
        # 基于运动后1小时心率恢复情况
        recovery_hr = activity_data.get('recovery_hr', self.user['resting_hr'] + 20)
        recovery_rate = (activity_data['max_hr'] - recovery_hr) / (activity_data['max_hr'] - self.user['resting_hr'])
        scores['recovery'] = min(15, recovery_rate * 15)
        
        total_score = sum(scores.values())
        
        # 评级
        if total_score >= 85:
            grade = '优秀'
        elif total_score >= 70:
            grade = '良好'
        elif total_score >= 55:
            grade = '一般'
        else:
            grade = '需改进'
        
        return {
            'dimension_scores': scores,
            'total_score': round(total_score, 1),
            'grade': grade
        }


class HealthAnalyzer:
    """健康数据分析主类"""
    
    def __init__(self, user_profile):
        self.user = user_profile
        self.sleep_scorer = SleepQualityScorer()
        self.exercise_evaluator = ExerciseEvaluator(user_profile)
        
    def calculate_bmr(self):
        """计算基础代谢率"""
        if self.user['gender'] == 'male':
            bmr = 88.362 + (13.397 * self.user['weight']) + \
                  (4.799 * self.user['height']) - (5.677 * self.user['age'])
        else:
            bmr = 447.593 + (9.247 * self.user['weight']) + \
                  (3.098 * self.user['height']) - (4.330 * self.user['age'])
        return round(bmr, 1)
    
    def calculate_daily_activity_score(self, activity_data):
        """
        计算日常活动评分
        
        Args:
            activity_data: dict
                - steps: 步数
                - active_minutes: 活动分钟数
                - calories: 卡路里消耗
        """
        score = 0
        
        # 步数控分 (40分)
        steps = activity_data['steps']
        if steps >= 10000:
            score += 40
        elif steps >= 8000:
            score += 35
        elif steps >= 6000:
            score += 28
        elif steps >= 4000:
            score += 20
        else:
            score += steps / 10000 * 40
        
        # 活动分钟 (35分)
        active_minutes = activity_data['active_minutes']
        if active_minutes >= 60:
            score += 35
        elif active_minutes >= 30:
            score += 28
        elif active_minutes >= 15:
            score += 20
        else:
            score += active_minutes / 60 * 35
        
        # 卡路里消耗 (25分)
        bmr = self.calculate_bmr()
        target_calories = bmr * 0.3
        cal_ratio = min(1.0, activity_data['calories'] / target_calories)
        score += cal_ratio * 25
        
        return round(score, 1)
    
    def calculate_h_score(self, sleep_score, activity_score, recovery_score=75):
        """
        计算H-Score综合健康评分
        
        H-Score = 睡眠评分 × 0.35 + 活动评分 × 0.30 + 
                  心血管评分 × 0.20 + 恢复评分 × 0.15
        """
        # 简化版心血管评分 (基于静息心率)
        resting_hr = self.user['resting_hr']
        if resting_hr <= 60:
            cardio_score = 95
        elif resting_hr <= 70:
            cardio_score = 85
        elif resting_hr <= 80:
            cardio_score = 75
        else:
            cardio_score = 60
        
        h_score = (sleep_score * 0.35 + 
                   activity_score * 0.30 + 
                   cardio_score * 0.20 + 
                   recovery_score * 0.15)
        
        # 健康等级
        if h_score >= 90:
            level = '优秀'
            color = '🟢'
        elif h_score >= 80:
            level = '良好'
            color = '🟢'
        elif h_score >= 70:
            level = '一般'
            color = '🟡'
        elif h_score >= 60:
            level = '需关注'
            color = '🟠'
        else:
            level = '需改善'
            color = '🔴'
        
        return {
            'h_score': round(h_score, 1),
            'level': level,
            'color': color,
            'breakdown': {
                'sleep_contribution': round(sleep_score * 0.35, 1),
                'activity_contribution': round(activity_score * 0.30, 1),
                'cardio_contribution': round(cardio_score * 0.20, 1),
                'recovery_contribution': round(recovery_score * 0.15, 1)
            }
        }


def generate_sample_data():
    """生成示例数据用于演示"""
    
    # 用户基础信息
    user_profile = {
        'age': 35,
        'gender': 'male',
        'weight': 75,
        'height': 175,
        'resting_hr': 62
    }
    
    # 睡眠数据 (过去7天)
    sleep_data_7days = [
        {
            'date': f'2026-04-{18+i}',
            'bed_time': 495,
            'total_duration': 455 - i*5,
            'deep_duration': 90 - i*3,
            'rem_duration': 100 - i*2,
            'sleep_latency': 15 + i*2,
            'awakenings_count': 1 + i//2
        }
        for i in range(7)
    ]
    
    # 活动数据 (过去7天)
    activity_data_7days = [
        {
            'date': f'2026-04-{18+i}',
            'steps': 8500 + np.random.randint(-2000, 3000),
            'active_minutes': 45 + np.random.randint(-15, 30),
            'calories': 350 + np.random.randint(-100, 150)
        }
        for i in range(7)
    ]
    
    # 单次运动数据
    exercise_session = {
        'type': '跑步',
        'duration': 45,
        'avg_hr': 148,
        'max_hr': 172,
        'calories': 420,
        'distance': 5.2,
        'recovery_hr': 85  # 运动后1小时心率
    }
    
    return user_profile, sleep_data_7days, activity_data_7days, exercise_session


def generate_health_report(output_path='health_analysis_report.md'):
    """生成健康分析报告"""
    
    # print("=" * 60)
    # print("健康数据分析模型 - 报告生成中...")
    # print("=" * 60)
    
    # 生成示例数据
    user_profile, sleep_data_7days, activity_data_7days, exercise_session = generate_sample_data()
    
    # 初始化分析器
    analyzer = HealthAnalyzer(user_profile)
    
    # 分析睡眠
    # print("\n【睡眠质量分析】")
    sleep_results = []
    for sleep_day in sleep_data_7days:
        result = analyzer.sleep_scorer.calculate_score(sleep_day)
        sleep_results.append({
            'date': sleep_day['date'],
            'score': result['total_score'],
            'grade': result['grade'],
            'duration': sleep_day['total_duration']
        })
        # print(f"  {sleep_day['date']}: 评分 {result['total_score']}分 ({result['grade']})")
    
    avg_sleep_score = np.mean([r['score'] for r in sleep_results])
    # print(f"  7天平均睡眠评分: {avg_sleep_score:.1f}分")
    
    # 分析日常活动
    # print("\n【日常活动分析】")
    activity_scores = []
    for activity_day in activity_data_7days:
        score = analyzer.calculate_daily_activity_score(activity_day)
        activity_scores.append(score)
        # print(f"  {activity_day['date']}: {activity_day['steps']}步, 评分 {score}分")
    
    avg_activity_score = np.mean(activity_scores)
    # print(f"  7天平均活动评分: {avg_activity_score:.1f}分")
    
    # 分析运动效果
    # print("\n【运动效果评估】")
    exercise_result = analyzer.exercise_evaluator.evaluate_exercise_effect(exercise_session)
    # print(f"  运动类型: {exercise_session['type']}")
    # print(f"  运动时长: {exercise_session['duration']}分钟")
    # print(f"  综合评分: {exercise_result['total_score']}分 ({exercise_result['grade']})")
    # print(f"  各维度得分: {exercise_result['dimension_scores']}")
    
    # 计算综合H-Score
    # print("\n【综合健康评分】")
    h_result = analyzer.calculate_h_score(avg_sleep_score, avg_activity_score)
    # print(f"  H-Score综合评分: {h_result['h_score']}分")
    # print(f"  健康等级: {h_result['color']} {h_result['level']}")
    # print(f"  得分构成: {h_result['breakdown']}")
    
    # 计算基础代谢
    bmr = analyzer.calculate_bmr()
    # print(f"\n【身体基础指标】")
    # print(f"  BMI: {user_profile['weight'] / ((user_profile['height']/100)**2):.1f}")
    # print(f"  基础代谢率(BMR): {bmr} 大卡/天")
    # print(f"  静息心率: {user_profile['resting_hr']} bpm")
    
    # print("\n" + "=" * 60)
    # print("分析完成！")
    # print("=" * 60)
    
    return {
        'user_profile': user_profile,
        'sleep_results': sleep_results,
        'avg_sleep_score': avg_sleep_score,
        'activity_scores': activity_scores,
        'avg_activity_score': avg_activity_score,
        'exercise_result': exercise_result,
        'h_score_result': h_result,
        'bmr': bmr
    }


if __name__ == '__main__':
    # 执行健康分析
    analysis_results = generate_health_report()
    
    # 保存结果为JSON
    with open('/Users/mettlyz/.openclaw/workspace/output/task-1816/分析结果数据_20260424.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, ensure_ascii=False, indent=2)
    
    # print("\n✅ 分析结果已保存到 output/task-1816/")

#!/usr/bin/env python3
"""
微信推送健康简报模块
支持企业微信应用消息和Server酱推送
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class WeChatNotifier:
    """微信通知器"""
    
    def __init__(self, push_method: str = "serverchan"):
        self.push_method = push_method
        self.serverchan_key = os.getenv("SERVERCHAN_KEY", "")
        self.qyapi_corpid = os.getenv("QYAPI_CORPID", "")
        self.qyapi_corpsecret = os.getenv("QYAPI_CORPSECRET", "")
        self.qyapi_agentid = os.getenv("QYAPI_AGENTID", "")
        self.access_token = None
        self.token_expires = 0
    
    def _get_access_token(self) -> str:
        """获取企业微信access_token"""
        if self.access_token and datetime.now().timestamp() < self.token_expires:
            return self.access_token
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.qyapi_corpid}&corpsecret={self.qyapi_corpsecret}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('errcode') == 0:
            self.access_token = data.get('access_token')
            self.token_expires = datetime.now().timestamp() + data.get('expires_in', 7200) - 300
            return self.access_token
        else:
            logger.error(f"Failed to get access token: {data}")
            return ""
    
    def send_via_qyapi(self, title: str, content: str) -> bool:
        """通过企业微信应用推送"""
        if not all([self.qyapi_corpid, self.qyapi_corpsecret, self.qyapi_agentid]):
            logger.warning("企业微信配置不完整，跳过推送")
            return False
        
        access_token = self._get_access_token()
        if not access_token:
            return False
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        
        # 转换为Markdown格式（企业微信支持的格式）
        markdown_content = f"""## {title}

{content}

---
*推送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        payload = {
            "touser": "@all",
            "msgtype": "markdown",
            "agentid": int(self.qyapi_agentid),
            "markdown": {
                "content": markdown_content
            },
            "safe": 0
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            if result.get('errcode') == 0:
                logger.info("企业微信推送成功")
                return True
            else:
                logger.error(f"企业微信推送失败: {result}")
                return False
        except Exception as e:
            logger.error(f"企业微信推送异常: {e}")
            return False
    
    def send_via_serverchan(self, title: str, content: str) -> bool:
        """通过Server酱推送"""
        if not self.serverchan_key:
            logger.warning("Server酱密钥未配置，跳过推送")
            return False
        
        url = f"https://sctapi.ftqq.com/{self.serverchan_key}.send"
        
        payload = {
            "title": title,
            "desp": content
        }
        
        try:
            response = requests.post(url, data=payload, timeout=10)
            result = response.json()
            if result.get('code') == 0:
                logger.info("Server酱推送成功")
                return True
            else:
                logger.error(f"Server酱推送失败: {result}")
                return False
        except Exception as e:
            logger.error(f"Server酱推送异常: {e}")
            return False
    
    def send_daily_report(self, daily_data: Dict, anomalies: List[Dict] = None) -> bool:
        """发送每日健康简报"""
        date = daily_data.get('date', datetime.now().strftime('%Y-%m-%d'))
        score = daily_data.get('score_total', 0)
        
        # 评分等级
        if score >= 85:
            grade = "🌟 优秀"
        elif score >= 70:
            grade = "👍 良好"
        elif score >= 55:
            grade = "⚠️ 一般"
        else:
            grade = "🔴 需关注"
        
        title = f"【健康日报】{date} - 综合评分{score}分 - {grade}"
        
        content = f"""
📊 **今日健康概览**

| 维度 | 得分 | 数据 |
|------|------|------|
| 🏃 运动 | {daily_data.get('score_exercise', 0)}分 | {daily_data.get('exercise_minutes', 0)}分钟 |
| 😴 睡眠 | {daily_data.get('score_sleep', 0)}分 | {daily_data.get('sleep_total', 0):.1f}小时 |
| ❤️ 心率 | {daily_data.get('score_heart', 0)}分 | 静息{daily_data.get('heart_rate_resting', 0):.0f}bpm |
| ⚡ 精力 | {daily_data.get('score_energy', 0)}分 | {daily_data.get('steps', 0)}步 |

---

📈 **详细数据**
- 今日步数: **{daily_data.get('steps', 0):,}** 步
- 活动能量: **{daily_data.get('active_energy', 0):.0f}** kcal
- 深度睡眠: **{daily_data.get('sleep_deep', 0):.1f}** 小时

---
"""
        
        # 添加异常预警
        if anomalies:
            content += "\n⚠️ **异常预警**\n\n"
            for anomaly in anomalies:
                content += f"- **{anomaly['message']}**\n"
                content += f"  💡 建议: {anomaly['recommendation']}\n\n"
        
        # 添加建议
        content += """
💡 **健康小贴士**
- 每小时起身活动5分钟，避免久坐
- 睡前1小时避免使用电子设备
- 保持规律作息，周末也不要熬夜
"""
        
        # 发送
        if self.push_method == "qyapi":
            return self.send_via_qyapi(title, content)
        else:
            return self.send_via_serverchan(title, content)
    
    def send_weekly_summary(self, report: Dict) -> bool:
        """发送周度总结"""
        title = f"【健康周报】{report['start_date']} ~ {report['end_date']}"
        
        content = f"""
📊 **本周健康总结**

- 📈 平均健康评分: **{report['avg_total_score']:.1f}** 分
- 👣 日均步数: **{report['avg_steps']:.0f}** 步
- 😴 日均睡眠: **{report['avg_sleep']:.1f}** 小时
- ❤️ 平均静息心率: **{report['avg_heart_rate']:.0f}** bpm

---

🏆 最佳表现日: **{report['best_day']}**
📉 需关注日: **{report['worst_day']}**
📈 整体趋势: **{'↗️ 改善中' if report['trend'] == 'improving' else '↘️ 需关注' if report['trend'] == 'declining' else '➡️ 稳定'}**

---

💡 **关键洞察**
"""
        for insight in report.get('key_insights', []):
            content += f"- {insight}\n"
        
        return self.send_via_serverchan(title, content)

def test_notification():
    """测试通知功能"""
    notifier = WeChatNotifier()
    
    # 模拟数据
    test_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'score_total': 78.5,
        'score_exercise': 85,
        'score_sleep': 72,
        'score_heart': 78,
        'score_energy': 75,
        'steps': 9200,
        'exercise_minutes': 42,
        'active_energy': 380,
        'heart_rate_resting': 62,
        'sleep_total': 6.8,
        'sleep_deep': 1.6
    }
    
    # print("测试微信通知功能...")
    # print("注: 需要配置 SERVERCHAN_KEY 环境变量才能实际发送")
    
    # 生成预览
    notifier.send_daily_report(test_data)
    # print("✅ 通知预览已生成（如需实际发送请配置环境变量）")

if __name__ == '__main__':
    test_notification()

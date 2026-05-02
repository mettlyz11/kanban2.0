#!/usr/bin/env python3
"""
企业微信机器人推送模块
用于每日健康简报推送
"""

import requests
import yaml
import json

class WeChatNotifier:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.enabled = self.config.get('wechat', {}).get('enabled', False)
        self.webhook_url = self.config.get('wechat', {}).get('webhook_url', '')
    
    def send_message(self, content, msg_type='text'):
        """发送文本消息"""
        if not self.enabled or not self.webhook_url:
            print("⚠️ 微信推送未启用，消息内容：")
            print(content)
            return False
        
        if msg_type == 'text':
            data = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
        elif msg_type == 'markdown':
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }
        else:
            raise ValueError(f"Unsupported message type: {msg_type}")
        
        try:
            response = requests.post(
                self.webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            result = response.json()
            if result.get('errcode') == 0:
                print("✅ 微信消息发送成功")
                return True
            else:
                print(f"❌ 发送失败: {result}")
                return False
        except Exception as e:
            print(f"❌ 发送异常: {e}")
            return False
    
    def send_daily_report(self, report_text):
        """发送每日健康报告（Markdown格式）"""
        markdown = report_text.replace('📊', '**📊**')\
                              .replace('🏆', '**🏆**')\
                              .replace('📈', '**📈**')\
                              .replace('📋', '**📋**')\
                              .replace('📉', '**📉**')\
                              .replace('⚠️', '**⚠️**')
        
        return self.send_message(markdown, msg_type='markdown')
    
    def send_alert(self, alert):
        """发送异常预警"""
        severity_icons = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
        icon = severity_icons.get(alert['severity'], '⚠️')
        
        content = f"{icon} 健康异常预警\n\n{alert['message']}\n\n请及时关注身体状况。"
        return self.send_message(content)


if __name__ == "__main__":
    notifier = WeChatNotifier()
    
    # 测试发送
    test_report = """📊 每日健康报告 (2026-04-25)

🏆 综合评分: 87.5 分 (A)

📈 各维度得分:
  • 运动 (30%): 92
  • 睡眠 (30%): 85
  • 心率 (20%): 82
  • 精力 (20%): 90"""
    
    notifier.send_daily_report(test_report)

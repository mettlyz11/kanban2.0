#!/usr/bin/env python3
"""
微信内容智能分析 - T1.3.2
全面分析微信内容，提取关键信息
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
import html

# ============================================================================
# 配置
# ============================================================================

INPUT_BASE_DIR = "/Users/mettlyz/.openclaw/workspace/Files/微信_backup"
OUTPUT_DIR = "/Users/mettlyz/.openclaw/workspace/output/task-1251"

# 话题关键词库
TOPIC_KEYWORDS = {
    "AI/机器学习": ["AI", "机器学习", "深度学习", "模型", "预测", "训练", "神经网络", "算法", "大模型", "GPT", "Claude"],
    "化学/材料": ["化学", "材料", "分子", "反应", "催化剂", "合成", "实验", "DFT", "计算", "晶体", "纳米"],
    "业务/合作": ["合作", "项目", "业务", "合同", "协议", "商务", "客户", "订单", "签约", "落地"],
    "融资/投资": ["融资", "投资", "BP", "估值", "股权", "VC", "PE", "天使", "路演", "基金"],
    "学术/科研": ["论文", "科研", "学术", "期刊", "发表", "研究", "高校", "教授", "课题", "基金"],
    "产品/技术": ["产品", "技术", "开发", "研发", "平台", "系统", "软件", "工具", "架构"],
    "管理/运营": ["管理", "运营", "团队", "招聘", "人事", "财务", "行政", "会议", "汇报"],
    "质量体系": ["ISO", "质量", "认证", "审核", "标准", "体系", "合规", "审计"],
    "法律/诉讼": ["官司", "诉讼", "律师", "法院", "起诉", "判决", "法务", "合同纠纷", "包头", "九原"],
}

# 待办/承诺关键词
TODO_KEYWORDS = ["需要", "应该", "必须", "记得", "别忘了", "安排", "计划", "下周", "明天", "后天", "下周一", "周五", "周三", "周四", "周二", "周六", "周日", "约", "约定", "承诺", "答应", "我会", "我将", "要做", "处理", "跟进", "确认", "回复"]

# 情感关键词
SENTIMENT_POSITIVE = ["好的", "没问题", "可以", "同意", "支持", "很棒", "不错", "感谢", "谢谢", "太好了", "完美", "优秀", "厉害", "祝贺", "恭喜"]
SENTIMENT_NEGATIVE = ["不行", "不能", "不同意", "反对", "问题", "麻烦", "困难", "担心", "担忧", "不好", "糟糕", "生气", "郁闷", "焦虑"]

# ============================================================================
# 核心分析类
# ============================================================================

class WeChatAnalyzer:
    def __init__(self):
        self.all_messages = []
        self.contacts = defaultdict(lambda: {
            "message_count": 0,
            "topics": defaultdict(int),
            "last_contact": None,
            "first_contact": None,
            "todos": [],
            "sentiment": {"positive": 0, "negative": 0, "neutral": 0},
            "sessions": set()
        })
        self.todos = []
        self.business_opportunities = []
        self.relationship_scores = {}
        self.group_chats = defaultdict(lambda: {"messages": 0, "members": set(), "topics": defaultdict(int)})
        
    def parse_message(self, content, sender, timestamp, session_name, is_group=False):
        """解析单条消息"""
        msg_data = {
            "content": content,
            "sender": sender,
            "timestamp": timestamp,
            "session": session_name,
            "is_group": is_group
        }
        self.all_messages.append(msg_data)
        
        # 更新联系人统计
        if sender and sender not in ["我", "本人", "刘宇宙", ""]:
            contact = self.contacts[sender]
            contact["message_count"] += 1
            contact["sessions"].add(session_name)
            
            if timestamp:
                if not contact["first_contact"] or timestamp < contact["first_contact"]:
                    contact["first_contact"] = timestamp
                if not contact["last_contact"] or timestamp > contact["last_contact"]:
                    contact["last_contact"] = timestamp
            
            # 话题分析
            for topic, keywords in TOPIC_KEYWORDS.items():
                for kw in keywords:
                    if kw in content:
                        contact["topics"][topic] += 1
                        break
            
            # 情感分析
            pos_count = sum(1 for kw in SENTIMENT_POSITIVE if kw in content)
            neg_count = sum(1 for kw in SENTIMENT_NEGATIVE if kw in content)
            if pos_count > neg_count:
                contact["sentiment"]["positive"] += 1
            elif neg_count > pos_count:
                contact["sentiment"]["negative"] += 1
            else:
                contact["sentiment"]["neutral"] += 1
        
        # 待办/承诺提取
        self._extract_todos(content, sender, timestamp, session_name)
        
        # 商业机会识别
        self._extract_business_opportunities(content, sender, timestamp, session_name)
        
        # 群聊统计
        if is_group:
            self.group_chats[session_name]["messages"] += 1
            self.group_chats[session_name]["members"].add(sender)
            for topic, keywords in TOPIC_KEYWORDS.items():
                for kw in keywords:
                    if kw in content:
                        self.group_chats[session_name]["topics"][topic] += 1
                        break
    
    def _extract_todos(self, content, sender, timestamp, session_name):
        """提取待办事项和承诺"""
        for kw in TODO_KEYWORDS:
            if kw in content and len(content) > 10:
                # 简单的待办提取
                self.todos.append({
                    "content": content,
                    "sender": sender,
                    "timestamp": timestamp,
                    "session": session_name,
                    "keyword": kw
                })
                break
    
    def _extract_business_opportunities(self, content, sender, timestamp, session_name):
        """识别商业机会"""
        business_keywords = ["合作", "投资", "项目", "融资", "订单", "需求", "机会", "介绍", "推荐", "一起"]
        for kw in business_keywords:
            if kw in content and len(content) > 15:
                self.business_opportunities.append({
                    "content": content,
                    "sender": sender,
                    "timestamp": timestamp,
                    "session": session_name,
                    "type": kw
                })
                break
    
    def calculate_relationship_strength(self):
        """计算关系强度评分"""
        for name, data in self.contacts.items():
            if data["message_count"] < 5:
                continue  # 跳过联系太少的
            
            # 评分维度：
            # 1. 消息数量 (40%)
            # 2. 最近联系时间 (30%) - 越近越好
            # 3. 话题多样性 (20%)
            # 4. 积极情感占比 (10%)
            
            score = 0
            
            # 消息数量评分
            msg_score = min(data["message_count"] / 100, 1.0) * 40
            score += msg_score
            
            # 最近联系评分
            if data["last_contact"]:
                try:
                    last_date = datetime.strptime(data["last_contact"], "%Y-%m-%d %H:%M:%S")
                    days_ago = (datetime.now() - last_date).days
                    recency_score = max(0, 30 - days_ago * 0.5)
                    score += recency_score
                except:
                    pass
            
            # 话题多样性
            topic_count = len(data["topics"])
            topic_score = min(topic_count * 5, 20)
            score += topic_score
            
            # 积极情感
            total_sentiment = sum(data["sentiment"].values())
            if total_sentiment > 0:
                pos_ratio = data["sentiment"]["positive"] / total_sentiment
                sentiment_score = pos_ratio * 10
                score += sentiment_score
            
            self.relationship_scores[name] = {
                "score": round(score, 1),
                "level": "强关系" if score >= 60 else "中关系" if score >= 30 else "弱关系",
                "message_count": data["message_count"],
                "last_contact": data["last_contact"],
                "topics": dict(data["topics"])
            }
    
    def generate_report(self):
        """生成分析报告"""
        report = []
        
        # 总体统计
        total_contacts = len([c for c in self.contacts.values() if c["message_count"] > 0])
        report.append("# 微信内容智能分析报告")
        report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\n## 总体统计")
        report.append(f"- 总消息数: {len(self.all_messages)}")
        report.append(f"- 有效联系人: {total_contacts}")
        report.append(f"- 群聊数量: {len(self.group_chats)}")
        report.append(f"- 待办事项: {len(self.todos)}")
        report.append(f"- 商业机会线索: {len(self.business_opportunities)}")
        
        # 关系强度评估
        report.append(f"\n## 关系强度评估 TOP 20")
        sorted_relationships = sorted(
            [(k, v) for k, v in self.relationship_scores.items()],
            key=lambda x: x[1]["score"],
            reverse=True
        )[:20]
        
        for name, data in sorted_relationships:
            report.append(f"\n### {name}")
            report.append(f"- 关系强度: {data['score']}分 ({data['level']})")
            report.append(f"- 消息数量: {data['message_count']}")
            report.append(f"- 最近联系: {data['last_contact']}")
            if data['topics']:
                report.append(f"- 主要话题: {', '.join([f'{k}({v})' for k, v in data['topics'].items()])}")
        
        # 关键待办事项
        report.append(f"\n## 关键待办事项与承诺 (TOP 30)")
        for todo in self.todos[:30]:
            report.append(f"\n- [{todo['timestamp']}] {todo['sender']} @ {todo['session']}:")
            report.append(f"  {todo['content'][:200]}...")
        
        # 商业机会
        report.append(f"\n## 商业机会线索 (TOP 20)")
        for opp in self.business_opportunities[:20]:
            report.append(f"\n- [{opp['timestamp']}] {opp['sender']} @ {opp['session']} ({opp['type']}):")
            report.append(f"  {opp['content'][:200]}...")
        
        # 活跃群聊分析
        report.append(f"\n## 活跃群聊分析 (TOP 15)")
        sorted_groups = sorted(
            self.group_chats.items(),
            key=lambda x: x[1]["messages"],
            reverse=True
        )[:15]
        
        for name, data in sorted_groups:
            report.append(f"\n### {name}")
            report.append(f"- 消息数量: {data['messages']}")
            report.append(f"- 参与人数: {len(data['members'])}")
            if data['topics']:
                report.append(f"- 主要话题: {', '.join([f'{k}({v})' for k, v in sorted(data['topics'].items(), key=lambda x: x[1], reverse=True)[:5]])}")
        
        # 话题分布
        report.append(f"\n## 整体话题分布")
        all_topics = defaultdict(int)
        for contact in self.contacts.values():
            for topic, count in contact["topics"].items():
                all_topics[topic] += count
        
        for topic, count in sorted(all_topics.items(), key=lambda x: x[1], reverse=True):
            report.append(f"- {topic}: {count} 次提及")
        
        # 关系维护建议
        report.append(f"\n## 关系维护建议")
        
        report.append(f"\n### 需要尽快联系 (超过30天未联系的重要关系)")
        for name, data in sorted_relationships[:50]:
            if data["score"] >= 40:  # 中强关系
                if data["last_contact"]:
                    try:
                        last_date = datetime.strptime(data["last_contact"], "%Y-%m-%d %H:%M:%S")
                        days_ago = (datetime.now() - last_date).days
                        if days_ago > 30:
                            report.append(f"- {name}: 已 {days_ago} 天未联系 (关系强度 {data['score']}分)")
                    except:
                        pass
        
        report.append(f"\n### 推荐沟通话题")
        hot_topics = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)[:5]
        for topic, count in hot_topics:
            report.append(f"- {topic}: 近期高频话题，适合作为沟通切入点")
        
        report.append(f"\n## 风险提示")
        report.append(f"- 共识别 {len(self.todos)} 个待办事项，请及时跟进")
        report.append(f"- 有 {len([r for r in self.relationship_scores.values() if r['level'] == '强关系'])} 个强关系需要维护")
        report.append(f"- 法律/诉讼话题出现 {all_topics.get('法律/诉讼', 0)} 次，需重点关注")
        
        return "\n".join(report)


# ============================================================================
# 主程序
# ============================================================================

def main():
    analyzer = WeChatAnalyzer()
    
    # print("开始扫描微信备份目录...")
    
    # 遍历所有备份目录
    backup_dirs = [d for d in os.listdir(INPUT_BASE_DIR) if os.path.isdir(os.path.join(INPUT_BASE_DIR, d))]
    
    total_sessions = 0
    total_messages = 0
    
    for backup_dir in backup_dirs:
        backup_path = os.path.join(INPUT_BASE_DIR, backup_dir)
        # print(f"处理备份: {backup_dir}")
        
        # 遍历所有会话目录
        try:
            session_dirs = [d for d in os.listdir(backup_path) if os.path.isdir(os.path.join(backup_path, d))]
        except:
            continue
        
        for session_dir in session_dirs:
            session_path = os.path.join(backup_path, session_dir)
            
            # 查找消息文件
            msg_file = os.path.join(session_path, "message_0.html")
            if not os.path.exists(msg_file):
                continue
            
            total_sessions += 1
            
            # 判断是否群聊
            is_group = "群" in session_dir or len(session_dir) > 10
            
            try:
                with open(msg_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 简单解析HTML消息
                # 查找消息块
                msg_pattern = r'class="message(?:-system)?".*?<div class="name">([^<]*)</div>.*?<div class="text">([^<]*)</div>'
                time_pattern = r'class="time">([^<]*)</div>'
                
                messages = re.findall(msg_pattern, content, re.DOTALL)
                times = re.findall(time_pattern, content)
                
                for i, (sender, msg_content) in enumerate(messages):
                    msg_content = html.unescape(msg_content.strip())
                    timestamp = times[i] if i < len(times) else ""
                    
                    if msg_content and len(msg_content) > 1:
                        analyzer.parse_message(
                            msg_content,
                            sender.strip(),
                            timestamp,
                            session_dir,
                            is_group
                        )
                        total_messages += 1
                
            except Exception as e:
                # print(f"  错误处理 {session_dir}: {e}")
                continue
    
    # print(f"\n扫描完成:")
    # print(f"- 备份目录: {len(backup_dirs)}")
    # print(f"- 会话数量: {total_sessions}")
    # print(f"- 消息数量: {total_messages}")
    
    # 计算关系强度
    # print("\n计算关系强度...")
    analyzer.calculate_relationship_strength()
    
    # 生成报告
    # print("生成分析报告...")
    report = analyzer.generate_report()
    
    report_path = os.path.join(OUTPUT_DIR, "微信内容智能分析报告_20260422.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # print(f"\n报告已保存: {report_path}")
    
    # 保存详细数据
    data_path = os.path.join(OUTPUT_DIR, "analysis_data.json")
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump({
            "relationship_scores": analyzer.relationship_scores,
            "todos": analyzer.todos,
            "business_opportunities": analyzer.business_opportunities,
            "contacts": {k: dict(v, topics=dict(v["topics"]), sessions=list(v["sessions"])) for k, v in analyzer.contacts.items()}
        }, f, ensure_ascii=False, indent=2)
    
    # print(f"详细数据已保存: {data_path}")
    
    return report_path, total_messages, len(analyzer.todos), len(analyzer.business_opportunities)


if __name__ == "__main__":
    main()

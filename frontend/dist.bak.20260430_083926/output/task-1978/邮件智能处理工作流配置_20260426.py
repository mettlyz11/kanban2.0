#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件智能处理工作流 v1.0
功能: 新邮件 → 智能分类 → 优先级排序 → 回复草稿生成 → 人工审核 → 发送
日期: 2026-04-26
⚠️ 安全声明: 本脚本仅提供辅助功能，所有邮件发送前必须经过人工审核
"""

import os
import sys
import json
import time
import logging
import imaplib
import smtplib
import email
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 第三方库
try:
    from anthropic import Anthropic
except ImportError:
    print("请安装依赖: pip install anthropic python-dotenv")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/.openclaw/logs/email_automation.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ 安全配置 ============
SECURITY_CONFIG = {
    # ⚠️ 关键安全设置 - 请勿随意修改
    "auto_send_enabled": False,  # 永远设置为False，禁止自动发送
    "max_draft_per_hour": 20,    # 每小时最多生成20封草稿
    "sensitive_keywords": ["机密", "保密", "密码", "工资", "薪酬", "secret", "confidential", "password"],
    "review_required": True,      # 所有邮件必须人工审核
    "log_all_emails": True,       # 记录所有邮件处理日志
}

# ============ 工作流配置 ============
WORKFLOW_CONFIG = {
    # IMAP 收件服务器配置
    "imap_server": "imap.qq.com",
    "imap_port": 993,
    
    # SMTP 发件服务器配置 (仅用于保存到草稿箱)
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    
    # 邮箱账号 (从环境变量读取，不要硬编码)
    "email_account": os.getenv('EMAIL_ACCOUNT', ''),
    "email_password": os.getenv('EMAIL_PASSWORD', ''),
    
    # 检查间隔 (分钟)
    "check_interval": 15,
    
    # 要处理的文件夹
    "folders_to_check": ["INBOX"],
    
    # 输出文件夹
    "output_folder": os.path.expanduser("~/Documents/邮件处理/"),
    
    # Claude 配置
    "claude_model": "claude-3-5-sonnet-20241022",
    "claude_max_tokens": 2048,
    
    # 联系人优先级配置
    "vip_contacts": [
        # "boss@company.com",
        # "important@partner.com"
    ],
}

# ============ 邮件分类体系 ============
CLASSIFICATION_SYSTEM = {
    "重要程度": ["高", "中", "低"],
    "邮件类型": ["工作请求", "信息咨询", "会议邀请", "合作洽谈", "行政通知", "垃圾邮件", "其他"],
    "紧急程度": ["24小时内", "3天内", "1周内", "无明确时限"],
    "领域标签": ["科研", "行政", "财务", "个人", "其他"],
}

# ============ 优先级算法 ============
PRIORITY_WEIGHTS = {
    "重要程度": {"高": 6, "中": 4, "低": 2},
    "紧急程度": {"24小时内": 9, "3天内": 6, "1周内": 3, "无明确时限": 0},
    "发件人权重": {"vip": 6, "同事": 4, "陌生人": 2},
}

def calculate_priority(classification: Dict, sender: str) -> int:
    """计算邮件优先级分数"""
    score = 0
    
    # 重要程度
    score += PRIORITY_WEIGHTS["重要程度"].get(classification.get("重要程度", "中"), 4)
    
    # 紧急程度
    score += PRIORITY_WEIGHTS["紧急程度"].get(classification.get("紧急程度", "无明确时限"), 0)
    
    # 发件人权重
    if sender in WORKFLOW_CONFIG["vip_contacts"]:
        score += PRIORITY_WEIGHTS["发件人权重"]["vip"]
    elif "edu.cn" in sender or "company.com" in sender:
        score += PRIORITY_WEIGHTS["发件人权重"]["同事"]
    else:
        score += PRIORITY_WEIGHTS["发件人权重"]["陌生人"]
    
    return score

# ============ 初始化客户端 ============
def init_clients() -> Dict:
    """初始化API客户端"""
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/.openclaw/.env"))
    
    clients = {}
    
    # 更新邮箱配置
    WORKFLOW_CONFIG["email_account"] = os.getenv('EMAIL_ACCOUNT', '')
    WORKFLOW_CONFIG["email_password"] = os.getenv('EMAIL_PASSWORD', '')
    
    # Anthropic (Claude)
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_api_key:
        clients['anthropic'] = Anthropic(api_key=anthropic_api_key)
        logger.info("Anthropic客户端初始化成功")
    else:
        logger.warning("未找到ANTHROPIC_API_KEY")
    
    return clients

# ============ 邮件读取 ============
def connect_imap() -> Optional[imaplib.IMAP4_SSL]:
    """连接IMAP服务器"""
    if not WORKFLOW_CONFIG["email_account"] or not WORKFLOW_CONFIG["email_password"]:
        logger.error("邮箱账号或密码未配置")
        return None
    
    try:
        imap = imaplib.IMAP4_SSL(
            WORKFLOW_CONFIG["imap_server"],
            WORKFLOW_CONFIG["imap_port"]
        )
        imap.login(WORKFLOW_CONFIG["email_account"], WORKFLOW_CONFIG["email_password"])
        logger.info("IMAP连接成功")
        return imap
    except Exception as e:
        logger.error(f"IMAP连接失败: {str(e)}")
        return None

def decode_email_header(header: str) -> str:
    """解码邮件标题"""
    if not header:
        return ""
    
    decoded_parts = decode_header(header)
    result = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            if encoding:
                try:
                    result += part.decode(encoding)
                except:
                    result += part.decode('utf-8', errors='ignore')
            else:
                result += part.decode('utf-8', errors='ignore')
        else:
            result += str(part)
    return result

def get_email_body(msg: email.message.Message) -> str:
    """获取邮件正文"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    body += payload.decode(charset, errors='ignore')
                except:
                    pass
            elif content_type == "text/html" and "attachment" not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    html_content = payload.decode(charset, errors='ignore')
                    # 简单提取纯文本
                    from html import unescape
                    import re
                    clean = re.compile('<.*?>')
                    body += unescape(re.sub(clean, '', html_content))
                except:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            body = payload.decode(charset, errors='ignore')
        except:
            body = str(msg.get_payload())
    
    return body[:5000]  # 限制长度

def fetch_unread_emails(imap: imaplib.IMAP4_SSL, folder: str = "INBOX") -> List[Dict]:
    """获取未读邮件"""
    emails = []
    
    try:
        imap.select(folder)
        
        # 搜索未读邮件
        status, messages = imap.search(None, 'UNSEEN')
        if status != 'OK':
            return emails
        
        email_ids = messages[0].split()
        logger.info(f"找到 {len(email_ids)} 封未读邮件")
        
        # 只处理最近的20封
        for email_id in email_ids[-20:]:
            status, msg_data = imap.fetch(email_id, '(RFC822)')
            if status != 'OK':
                continue
            
            msg = email.message_from_bytes(msg_data[0][1])
            
            email_data = {
                "id": email_id.decode(),
                "subject": decode_email_header(msg["Subject"]),
                "from": decode_email_header(msg["From"]),
                "to": decode_email_header(msg["To"]),
                "date": msg["Date"],
                "body": get_email_body(msg),
                "message_id": msg["Message-ID"],
            }
            
            # 提取发件人邮箱
            import re
            sender_match = re.search(r'[\w\.-]+@[\w\.-]+', email_data["from"])
            if sender_match:
                email_data["sender_email"] = sender_match.group()
            else:
                email_data["sender_email"] = email_data["from"]
            
            emails.append(email_data)
            
            # 标记为未读（因为我们只是扫描，不是真正处理）
            imap.store(email_id, '-FLAGS', '\\Seen')
            
    except Exception as e:
        logger.error(f"获取邮件失败: {str(e)}")
    
    return emails

# ============ 阶段1: 邮件智能分类 ============
def classify_email(clients: Dict, email_data: Dict) -> Optional[Dict]:
    """使用Claude对邮件进行智能分类"""
    if 'anthropic' not in clients:
        logger.error("Anthropic客户端未初始化")
        return None
    
    logger.info(f"正在分类邮件: {email_data.get('subject', '无主题')}")
    
    prompt = f"""
请对以下邮件进行智能分类和分析。

【邮件信息】
发件人: {email_data.get('from', '未知')}
发件人邮箱: {email_data.get('sender_email', '未知')}
主题: {email_data.get('subject', '无主题')}
日期: {email_data.get('date', '未知')}

【邮件正文】
{email_data.get('body', '')[:8000]}

请严格按照以下JSON格式输出分类结果（确保是合法JSON）：

{{
  "重要程度": "高/中/低",
  "邮件类型": "工作请求/信息咨询/会议邀请/合作洽谈/行政通知/垃圾邮件/其他",
  "紧急程度": "24小时内/3天内/1周内/无明确时限",
  "领域标签": "科研/行政/财务/个人/其他",
  "核心诉求": "用一句话总结邮件的核心目的或诉求",
  "建议处理方式": "立即回复/稍后处理/无需回复/转交给他人",
  "建议转交人": "姓名或部门（如适用）",
  "敏感内容标记": true/false,
  "敏感内容说明": "如果标记为true，说明是什么敏感内容",
  "回复要点": ["要点1", "要点2", "要点3"]
}}

分类标准：
- 重要程度高: VIP邮件、紧急事项、影响重大的决策
- 重要程度中: 日常工作、常规沟通
- 重要程度低: 通知、广告、不重要的信息
- 敏感内容: 涉及保密信息、个人隐私、财务数据等
"""
    
    try:
        response = clients['anthropic'].messages.create(
            model=WORKFLOW_CONFIG["claude_model"],
            max_tokens=WORKFLOW_CONFIG["claude_max_tokens"],
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text
        
        # 提取JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            classification = json.loads(json_match.group())
            
            # 计算优先级分数
            priority_score = calculate_priority(
                classification, 
                email_data.get("sender_email", "")
            )
            classification["priority_score"] = priority_score
            
            logger.info(f"分类完成，优先级分数: {priority_score}")
            return classification
        else:
            logger.error("无法从Claude响应中提取JSON")
            return None
            
    except Exception as e:
        logger.error(f"邮件分类失败: {str(e)}")
        return None

# ============ 阶段2: 生成回复草稿 ============
def generate_reply_draft(clients: Dict, email_data: Dict, classification: Dict) -> Optional[str]:
    """生成回复草稿"""
    if classification.get("敏感内容标记", False):
        logger.warning("邮件包含敏感内容，跳过自动回复生成")
        return None
    
    if classification.get("建议处理方式") == "无需回复":
        logger.info("邮件无需回复")
        return None
    
    mail_type = classification.get("邮件类型", "其他")
    
    # 根据邮件类型选择不同的Prompt
    prompt = f"""
请帮我撰写一封邮件回复草稿。

【原邮件信息】
发件人: {email_data.get('from', '未知')}
主题: {email_data.get('subject', '无主题')}
邮件类型: {mail_type}
核心诉求: {classification.get('核心诉求', '')}
回复要点: {json.dumps(classification.get('回复要点', []), ensure_ascii=False)}

【原邮件正文】
{email_data.get('body', '')[:6000]}

请撰写一封合适的中文回复：
- 语气要专业、礼貌
- 针对邮件类型调整语气（正式/半正式/友好）
- 回复要点要清晰、有条理
- 如果是会议邀请，明确是否参加
- 如果是工作请求，给出时间节点
- 如果是信息咨询，清晰解答问题

请输出完整的邮件正文，不要包含邮件头。
"""
    
    try:
        response = clients['anthropic'].messages.create(
            model=WORKFLOW_CONFIG["claude_model"],
            max_tokens=WORKFLOW_CONFIG["claude_max_tokens"],
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        
        reply_body = response.content[0].text
        logger.info("回复草稿生成成功")
        
        return reply_body
        
    except Exception as e:
        logger.error(f"生成回复草稿失败: {str(e)}")
        return None

# ============ 阶段3: 保存草稿到待审核文件夹 ============
def save_to_review_queue(email_data: Dict, classification: Dict, reply_draft: str) -> str:
    """保存到待审核队列"""
    os.makedirs(WORKFLOW_CONFIG["output_folder"], exist_ok=True)
    review_folder = os.path.join(WORKFLOW_CONFIG["output_folder"], "待审核")
    os.makedirs(review_folder, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_subject = "".join(c for c in email_data.get('subject', '无主题') if c.isalnum() or c in (' ', '-', '_'))[:50]
    filename = f"{timestamp}_{safe_subject}.md"
    file_path = os.path.join(review_folder, filename)
    
    content = f"""# 邮件回复审核

## 原邮件信息

- **发件人**: {email_data.get('from', '未知')}
- **主题**: {email_data.get('subject', '无主题')}
- **日期**: {email_data.get('date', '未知')}
- **邮件ID**: {email_data.get('message_id', '未知')}

## 智能分类结果

| 项目 | 结果 |
|------|------|
| 重要程度 | {classification.get('重要程度', '未知')} |
| 邮件类型 | {classification.get('邮件类型', '未知')} |
| 紧急程度 | {classification.get('紧急程度', '未知')} |
| 领域标签 | {classification.get('领域标签', '未知')} |
| 优先级分数 | {classification.get('priority_score', 0)} |
| 建议处理方式 | {classification.get('建议处理方式', '未知')} |

## 核心诉求
{classification.get('核心诉求', '')}

## 原邮件正文

---
{email_data.get('body', '')[:2000]}
---

## AI生成的回复草稿

---
{reply_draft}
---

## 审核操作

请审核后执行以下操作之一：

1. ✅ 批准发送: 将文件移动到"已批准"文件夹
2. 修改后发送: 编辑下方回复内容，然后移动到"已批准"文件夹
3. ❌ 拒绝发送: 将文件移动到"已拒绝"文件夹

---

## 人工编辑区（在此处修改回复）

{reply_draft}

---

*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*⚠️ 警告: 此草稿由AI生成，发送前必须人工审核！*
"""
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    logger.info(f"草稿已保存到待审核队列: {file_path}")
    return file_path

# ============ 阶段4: 处理已批准的邮件 ============
def process_approved_emails() -> int:
    """处理已批准的邮件（实际发送）"""
    if SECURITY_CONFIG["auto_send_enabled"]:
        logger.warning("⚠️ 自动发送已启用！这可能存在安全风险")
    else:
        logger.info("自动发送已禁用，仅记录已批准的邮件")
    
    approved_folder = os.path.join(WORKFLOW_CONFIG["output_folder"], "已批准")
    os.makedirs(approved_folder, exist_ok=True)
    
    sent_folder = os.path.join(WORKFLOW_CONFIG["output_folder"], "已发送")
    os.makedirs(sent_folder, exist_ok=True)
    
    count = 0
    for filename in os.listdir(approved_folder):
        if not filename.endswith(".md"):
            continue
        
        file_path = os.path.join(approved_folder, filename)
        
        # TODO: 在这里实现实际的邮件发送逻辑
        # 注意: 必须确保人工审核后才能发送
        
        # 移动到已发送文件夹
        dest_path = os.path.join(sent_folder, filename)
        os.rename(file_path, dest_path)
        logger.info(f"已处理批准的邮件: {filename}")
        count += 1
    
    return count

# ============ 单封邮件处理 ============
def process_single_email(clients: Dict, email_data: Dict) -> bool:
    """处理单封邮件的完整流程"""
    logger.info(f"-" * 60)
    logger.info(f"处理邮件: {email_data.get('subject', '无主题')}")
    logger.info(f"发件人: {email_data.get('from', '未知')}")
    
    # 阶段1: 智能分类
    classification = classify_email(clients, email_data)
    if not classification:
        return False
    
    # 如果是垃圾邮件，跳过
    if classification.get("邮件类型") == "垃圾邮件":
        logger.info("检测为垃圾邮件，跳过处理")
        return True
    
    # 阶段2: 生成回复草稿（如果需要回复）
    if classification.get("建议处理方式") not in ["无需回复", "转交给他人"]:
        reply_draft = generate_reply_draft(clients, email_data, classification)
        if reply_draft:
            # 阶段3: 保存到待审核队列
            save_to_review_queue(email_data, classification, reply_draft)
    
    # 记录处理日志
    if SECURITY_CONFIG["log_all_emails"]:
        log_folder = os.path.join(WORKFLOW_CONFIG["output_folder"], "处理日志")
        os.makedirs(log_folder, exist_ok=True)
        log_file = os.path.join(log_folder, f"{datetime.now().strftime('%Y-%m-%d')}.jsonl")
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "email_subject": email_data.get("subject"),
            "sender": email_data.get("sender_email"),
            "classification": classification,
        }
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    return True

# ============ 批量处理 ============
def process_email_batch(clients: Dict) -> int:
    """批量处理未读邮件"""
    imap = connect_imap()
    if not imap:
        return 0
    
    total_processed = 0
    
    for folder in WORKFLOW_CONFIG["folders_to_check"]:
        emails = fetch_unread_emails(imap, folder)
        
        # 按优先级排序
        emails_with_classification = []
        for email_data in emails:
            classification = classify_email(clients, email_data)
            if classification:
                emails_with_classification.append((email_data, classification))
        
        # 按优先级分数降序排列
        emails_with_classification.sort(
            key=lambda x: x[1].get("priority_score", 0),
            reverse=True
        )
        
        # 按优先级顺序处理
        for email_data, classification in emails_with_classification:
            if process_single_email(clients, email_data):
                total_processed += 1
    
    imap.logout()
    
    # 处理已批准的邮件
    process_approved_emails()
    
    return total_processed

# ============ 定时任务模式 ============
def run_scheduled_mode(clients: Dict):
    """定时运行模式"""
    logger.info("=" * 60)
    logger.info("🚀 邮件智能处理工作流启动（定时模式）")
    logger.info(f"检查间隔: {WORKFLOW_CONFIG['check_interval']} 分钟")
    logger.info(f"自动发送: {'已启用' if SECURITY_CONFIG['auto_send_enabled'] else '已禁用'}")
    logger.info("=" * 60)
    
    while True:
        try:
            logger.info(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始检查邮件...")
            processed = process_email_batch(clients)
            logger.info(f"本轮处理完成，共处理 {processed} 封邮件")
            
            # 等待下一次检查
            time.sleep(WORKFLOW_CONFIG["check_interval"] * 60)
            
        except KeyboardInterrupt:
            logger.info("\n收到停止信号，退出...")
            break
        except Exception as e:
            logger.error(f"运行出错: {str(e)}")
            time.sleep(60)  # 出错后等待1分钟再重试

# ============ 单次运行模式 ============
def run_single_mode(clients: Dict):
    """单次运行模式"""
    logger.info("邮件智能处理工作流（单次模式）")
    processed = process_email_batch(clients)
    logger.info(f"处理完成，共处理 {processed} 封邮件")

# ============ 主函数 ============
def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='邮件智能处理工作流')
    parser.add_argument('--scheduled', action='store_true', help='启动定时运行模式')
    parser.add_argument('--process-approved', action='store_true', help='处理已批准的邮件')
    
    args = parser.parse_args()
    
    clients = init_clients()
    
    if args.process_approved:
        process_approved_emails()
    elif args.scheduled:
        run_scheduled_mode(clients)
    else:
        run_single_mode(clients)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会议纪要自动化工作流 v1.0
功能: 录音文件 → Whisper转写 → Claude结构化 → 看板同步 → 通知分发
日期: 2026-04-26
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 第三方库
try:
    from openai import OpenAI
    from anthropic import Anthropic
except ImportError:
    # print("请安装依赖: pip install openai anthropic python-dotenv watchdog")
    sys.exit(1)

# 本地库 - 数据库连接
sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace/scripts"))
try:
    from lib.db_connector import get_db_connection
except ImportError:
    # print("警告: 无法导入数据库连接模块，数据库功能将被禁用")
    get_db_connection = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/.openclaw/logs/meeting_automation.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ 配置区 ============
CONFIG = {
    # 监听文件夹
    "watch_folder": os.path.expanduser("~/Dropbox/Recordings/"),
    
    # 输出文件夹
    "output_folder": os.path.expanduser("~/Documents/会议纪要/"),
    
    # 支持的音频格式
    "audio_formats": ['.m4a', '.mp3', '.wav', '.aac'],
    
    # Whisper 模型配置
    "whisper_model": "whisper-1",
    "whisper_language": "zh",  # "en" for English, "zh" for Chinese
    
    # Claude 模型配置
    "claude_model": "claude-3-5-sonnet-20241022",
    "claude_max_tokens": 4096,
    
    # 是否启用数据库同步
    "enable_db_sync": True,
    
    # 是否启用通知
    "enable_notification": True,
    
    # 处理完成后是否移动原文件
    "move_processed": True,
    "processed_folder": os.path.expanduser("~/Dropbox/Recordings/已处理/"),
}

# ============ 初始化客户端 ============
def init_clients():
    """初始化API客户端"""
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/.openclaw/.env"))
    
    clients = {}
    
    # OpenAI (Whisper)
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        clients['openai'] = OpenAI(api_key=openai_api_key)
        logger.info("OpenAI客户端初始化成功")
    else:
        logger.warning("未找到OPENAI_API_KEY，Whisper功能将不可用")
    
    # Anthropic (Claude)
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_api_key:
        clients['anthropic'] = Anthropic(api_key=anthropic_api_key)
        logger.info("Anthropic客户端初始化成功")
    else:
        logger.warning("未找到ANTHROPIC_API_KEY，Claude功能将不可用")
    
    return clients

# ============ 阶段1: Whisper转写 ============
def transcribe_audio(clients: Dict, audio_path: str) -> Optional[str]:
    """使用Whisper进行语音转写"""
    if 'openai' not in clients:
        logger.error("OpenAI客户端未初始化，无法转写")
        return None
    
    logger.info(f"开始转写: {audio_path}")
    
    try:
        with open(audio_path, "rb") as audio_file:
            transcript = clients['openai'].audio.transcriptions.create(
                model=CONFIG["whisper_model"],
                file=audio_file,
                response_format="verbose_json",
                language=CONFIG["whisper_language"],
                timestamp_granularities=["word"]
            )
        
        # 保存原始转写稿
        base_name = Path(audio_path).stem
        output_dir = os.path.join(CONFIG["output_folder"], base_name)
        os.makedirs(output_dir, exist_ok=True)
        
        transcript_path = os.path.join(output_dir, f"{base_name}_转写稿.txt")
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript.text)
        
        logger.info(f"转写完成，已保存至: {transcript_path}")
        return transcript.text
        
    except Exception as e:
        logger.error(f"转写失败: {str(e)}")
        return None

# ============ 阶段2: Claude结构化处理 ============
def process_with_claude(clients: Dict, transcript: str, filename: str) -> Optional[Dict]:
    """使用Claude进行结构化处理"""
    if 'anthropic' not in clients:
        logger.error("Anthropic客户端未初始化，无法结构化处理")
        return None
    
    logger.info("开始结构化处理会议内容")
    
    # 从文件名提取日期时间
    meeting_datetime = ""
    try:
        # 假设文件名格式: YYYY-MM-DD_HHMM_会议主题.m4a
        name_parts = Path(filename).stem.split('_')
        if len(name_parts) >= 2:
            meeting_datetime = f"{name_parts[0]} {name_parts[1][:2]}:{name_parts[1][2:]}"
    except:
        pass
    
    prompt = f"""
请将以下会议录音转写稿整理成结构化会议纪要。

文件名信息: {filename}
推断会议时间: {meeting_datetime}

【原始转写稿】
{transcript[:150000]}  # 限制长度，避免超限

请严格按照以下JSON格式输出（确保是合法JSON，不要添加markdown标记）：

{{
  "会议主题": "从内容中推断会议主题，如果无法确定则使用文件名",
  "会议时间": "YYYY-MM-DD HH:MM格式，如果无法确定则从文件名推断",
  "参会人员": ["姓名1", "姓名2", "..."],
  "讨论要点": [
    {{
      "议题": "议题名称",
      "要点": ["要点1", "要点2", "要点3"],
      "结论": "本议题的结论或决定，如果没有明确结论则写"待跟进""
    }}
  ],
  "行动项": [
    {{
      "任务内容": "具体任务描述，要具体可执行",
      "负责人": "负责人姓名（如未明确则为"待确认"）",
      "截止日期": "YYYY-MM-DD格式（如未明确则为"待定"）",
      "优先级": "高/中/低"
    }}
  ],
  "下次会议安排": {{
    "时间": "时间或待定",
    "议题": ["议题1", "议题2"]
  }},
  "会议总结": "200字以内的会议整体总结"
}}

注意事项：
1. 确保JSON格式完全合法，使用双引号
2. 行动项要具体，不要太笼统
3. 负责人要从对话中识别，不要编造
4. 如果转写内容中有英文，保留英文
"""
    
    try:
        response = clients['anthropic'].messages.create(
            model=CONFIG["claude_model"],
            max_tokens=CONFIG["claude_max_tokens"],
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text
        
        # 提取JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            result = json.loads(json_match.group())
            logger.info(f"结构化处理完成: {result.get('会议主题', '未知主题')}")
            logger.info(f"提取到 {len(result.get('行动项', []))} 个行动项")
            return result
        else:
            logger.error("无法从Claude响应中提取JSON")
            logger.error(f"Claude响应: {result_text}")
            return None
            
    except Exception as e:
        logger.error(f"结构化处理失败: {str(e)}")
        return None

# ============ 阶段3: 保存会议纪要 ============
def save_meeting_minutes(meeting_data: Dict, filename: str) -> Optional[str]:
    """保存会议纪要为Markdown文件"""
    base_name = Path(filename).stem
    output_dir = os.path.join(CONFIG["output_folder"], base_name)
    os.makedirs(output_dir, exist_ok=True)
    
    md_path = os.path.join(output_dir, f"{base_name}_会议纪要.md")
    
    md_content = f"""# {meeting_data.get('会议主题', '会议纪要')}

**时间**: {meeting_data.get('会议时间', '待定')}  
**参会人员**: {', '.join(meeting_data.get('参会人员', ['待确认']))}  
**记录人**: AI自动生成  

---

## 会议总结

{meeting_data.get('会议总结', '')}

---

## 讨论要点

"""
    
    for point in meeting_data.get('讨论要点', []):
        md_content += f"### {point.get('议题', '议题')}\n\n"
        for item in point.get('要点', []):
            md_content += f"- {item}\n"
        md_content += f"\n**结论**: {point.get('结论', '')}\n\n---\n\n"
    
    # 行动项表格
    md_content += "## 行动项 (Action Items)\n\n"
    md_content += "| 序号 | 任务内容 | 负责人 | 截止日期 | 优先级 | 状态 |\n"
    md_content += "|------|---------|--------|---------|--------|------|\n"
    
    for i, item in enumerate(meeting_data.get('行动项', []), 1):
        md_content += f"| {i} | {item.get('任务内容', '')} | {item.get('负责人', '待确认')} | {item.get('截止日期', '待定')} | {item.get('优先级', '中')} | 待办 |\n"
    
    # 下次会议安排
    next_meeting = meeting_data.get('下次会议安排', {})
    if next_meeting:
        md_content += f"\n## 下次会议安排\n\n"
        md_content += f"- **时间**: {next_meeting.get('时间', '待定')}\n"
        md_content += f"- **议题**: {', '.join(next_meeting.get('议题', ['待定']))}\n"
    
    md_content += f"\n---\n\n*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        logger.info(f"会议纪要已保存: {md_path}")
        
        # 同时保存JSON原始数据
        json_path = os.path.join(output_dir, f"{base_name}_原始数据.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meeting_data, f, ensure_ascii=False, indent=2)
        
        return md_path
        
    except Exception as e:
        logger.error(f"保存会议纪要失败: {str(e)}")
        return None

# ============ 阶段4: 同步到看板数据库 ============
def sync_to_kanban(meeting_data: Dict, meeting_id: str) -> bool:
    """将行动项同步到看板系统"""
    if not CONFIG["enable_db_sync"] or get_db_connection is None:
        logger.info("数据库同步已禁用")
        return False
    
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("数据库连接失败")
            return False
        
        cursor = conn.cursor()
        
        # 1. 插入会议记录
        cursor.execute("""
            INSERT INTO meetings 
            (title, meeting_time, attendees, summary, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (
            meeting_data.get('会议主题', '未知会议'),
            meeting_data.get('会议时间', None),
            ','.join(meeting_data.get('参会人员', [])),
            meeting_data.get('会议总结', '')
        ))
        
        meeting_db_id = cursor.lastrowid
        
        # 2. 插入行动项
        action_items = meeting_data.get('行动项', [])
        for item in action_items:
            # 解析截止日期
            due_date = item.get('截止日期', '待定')
            if due_date == '待定':
                due_date = None
            
            # 转换优先级
            priority_map = {'高': 1, '中': 2, '低': 3}
            priority = priority_map.get(item.get('优先级', '中'), 2)
            
            cursor.execute("""
                INSERT INTO tasks 
                (title, description, assignee, due_date, priority, 
                 status, source, source_id, created_at)
                VALUES (%s, %s, %s, %s, %s, '待办', '会议纪要', %s, NOW())
            """, (
                item.get('任务内容', '')[:100],
                item.get('任务内容', ''),
                item.get('负责人', '待确认'),
                due_date,
                priority,
                meeting_db_id
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"已同步 {len(action_items)} 个行动项到看板")
        return True
        
    except Exception as e:
        logger.error(f"同步到看板失败: {str(e)}")
        return False

# ============ 阶段5: 发送通知 ============
def send_notifications(meeting_data: Dict, minutes_path: str) -> bool:
    """发送通知给相关人员"""
    if not CONFIG["enable_notification"]:
        logger.info("通知功能已禁用")
        return False
    
    # TODO: 实现企业微信/钉钉/邮件通知
    # 这里是示例框架，具体实现需要根据实际API调整
    
    action_items = meeting_data.get('行动项', [])
    
    # 按负责人分组
    from collections import defaultdict
    items_by_assignee = defaultdict(list)
    for item in action_items:
        assignee = item.get('负责人', '待确认')
        items_by_assignee[assignee].append(item)
    
    logger.info(f"通知摘要: {len(action_items)} 个行动项分配给 {len(items_by_assignee)} 位负责人")
    
    # 这里可以添加具体的通知实现
    # 例如: 企业微信机器人、邮件、钉钉等
    
    return True

# ============ 主处理流程 ============
def process_recording(audio_path: str, clients: Dict) -> bool:
    """处理单个录音文件的完整流程"""
    logger.info(f"=" * 60)
    logger.info(f"开始处理录音文件: {audio_path}")
    logger.info(f"=" * 60)
    
    filename = os.path.basename(audio_path)
    
    # 阶段1: 语音转写
    transcript = transcribe_audio(clients, audio_path)
    if not transcript:
        return False
    
    # 阶段2: 结构化处理
    meeting_data = process_with_claude(clients, transcript, filename)
    if not meeting_data:
        return False
    
    # 阶段3: 保存会议纪要
    minutes_path = save_meeting_minutes(meeting_data, filename)
    if not minutes_path:
        return False
    
    # 阶段4: 同步到看板
    meeting_id = Path(filename).stem
    sync_to_kanban(meeting_data, meeting_id)
    
    # 阶段5: 发送通知
    send_notifications(meeting_data, minutes_path)
    
    # 移动已处理文件
    if CONFIG["move_processed"]:
        os.makedirs(CONFIG["processed_folder"], exist_ok=True)
        dest_path = os.path.join(CONFIG["processed_folder"], filename)
        os.rename(audio_path, dest_path)
        logger.info(f"已移动原文件到: {dest_path}")
    
    logger.info(f"✅ 会议纪要处理完成！")
    logger.info(f"会议主题: {meeting_data.get('会议主题')}")
    logger.info(f"行动项数量: {len(meeting_data.get('行动项', []))}")
    logger.info(f"纪要文件: {minutes_path}")
    
    return True

# ============ 文件夹监听模式 ============
def start_watch_mode(clients: Dict):
    """启动文件夹监听模式"""
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    
    class RecordingHandler(FileSystemEventHandler):
        def __init__(self, clients):
            self.clients = clients
            self.processing_files = set()
        
        def on_created(self, event):
            if event.is_directory:
                return
            
            file_path = event.src_path
            ext = Path(file_path).suffix.lower()
            
            if ext in CONFIG["audio_formats"]:
                if file_path in self.processing_files:
                    return
                
                self.processing_files.add(file_path)
                
                # 等待文件写入完成
                time.sleep(5)
                
                try:
                    process_recording(file_path, self.clients)
                finally:
                    self.processing_files.discard(file_path)
    
    observer = Observer()
    handler = RecordingHandler(clients)
    observer.schedule(handler, CONFIG["watch_folder"], recursive=False)
    
    observer.start()
    logger.info(f"👀 开始监听文件夹: {CONFIG['watch_folder']}")
    logger.info("按 Ctrl+C 停止监听...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

# ============ 单次处理模式 ============
def process_single_file(audio_path: str):
    """单次处理单个文件"""
    clients = init_clients()
    process_recording(audio_path, clients)

# ============ 主函数 ============
def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='会议纪要自动化工作流')
    parser.add_argument('--watch', action='store_true', help='启动文件夹监听模式')
    parser.add_argument('--file', type=str, help='处理单个音频文件')
    
    args = parser.parse_args()
    
    # 确保输出目录存在
    os.makedirs(CONFIG["output_folder"], exist_ok=True)
    os.makedirs(CONFIG["watch_folder"], exist_ok=True)
    
    clients = init_clients()
    
    if args.watch:
        start_watch_mode(clients)
    elif args.file:
        process_recording(args.file, clients)
    else:
        # 默认模式: 处理监听文件夹中的所有新文件
        logger.info("单次处理模式: 扫描文件夹中的音频文件")
        for filename in os.listdir(CONFIG["watch_folder"]):
            ext = Path(filename).suffix.lower()
            if ext in CONFIG["audio_formats"]:
                file_path = os.path.join(CONFIG["watch_folder"], filename)
                process_recording(file_path, clients)

if __name__ == "__main__":
    main()

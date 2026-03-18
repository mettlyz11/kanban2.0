#!/usr/bin/env python3
"""
MUTT Email Skill
集成MUTT邮件客户端到OpenClaw系统
支持：发送邮件、查收邮件、通讯录管理
"""

import subprocess
import os
import re
import json
from datetime import datetime
from typing import List, Dict, Optional

class MuttSkill:
    """MUTT邮件处理Skill"""
    
    def __init__(self, account: str = "foxmail"):
        self.account = account
        self.mutt_rc = os.path.expanduser("~/.muttrc")
        self.configured = self._check_config()
        
    def _check_config(self) -> bool:
        """检查MUTT配置"""
        return os.path.exists(self.mutt_rc)
    
    def send_email(self, to: str, subject: str, body: str, 
                   cc: Optional[str] = None,
                   attachments: Optional[List[str]] = None) -> Dict:
        """
        发送邮件
        
        Args:
            to: 收件人邮箱
            subject: 主题
            body: 邮件正文
            cc: 抄送
            attachments: 附件列表
            
        Returns:
            发送结果
        """
        if not self.configured:
            return {"success": False, "error": "MUTT未配置"}
        
        # 创建临时邮件文件
        temp_file = f"/tmp/mutt_email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(f"To: {to}\n")
            if cc:
                f.write(f"Cc: {cc}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"\n{body}\n")
        
        try:
            # 使用mutt发送邮件
            cmd = ["mutt", "-s", subject, to]
            
            if cc:
                cmd.extend(["-c", cc])
            
            if attachments:
                for att in attachments:
                    cmd.extend(["-a", att])
            
            with open(temp_file, 'r') as f:
                result = subprocess.run(
                    cmd,
                    stdin=f,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            
            os.remove(temp_file)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "邮件发送成功",
                    "to": to,
                    "subject": subject,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "to": to,
                    "subject": subject
                }
                
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return {
                "success": False,
                "error": str(e),
                "to": to,
                "subject": subject
            }
    
    def check_inbox(self, limit: int = 10) -> List[Dict]:
        """
        检查收件箱
        
        Args:
            limit: 返回邮件数量限制
            
        Returns:
            邮件列表
        """
        if not self.configured:
            return [{"error": "MUTT未配置"}]
        
        try:
            # 使用mutt的标记功能导出邮件列表
            mail_dir = os.path.expanduser(f"~/Mail/{self.account}/Inbox")
            
            if not os.path.exists(mail_dir):
                return []
            
            # 获取邮件列表
            result = subprocess.run(
                ["ls", "-lt", mail_dir],
                capture_output=True,
                text=True
            )
            
            emails = []
            lines = result.stdout.strip().split('\n')[1:limit+1]  # 跳过标题行
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 8:
                    emails.append({
                        "date": " ".join(parts[5:8]),
                        "size": parts[4],
                        "filename": parts[-1]
                    })
            
            return emails
            
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_status(self) -> Dict:
        """获取MUTT配置状态"""
        return {
            "configured": self.configured,
            "account": self.account,
            "config_file": self.mutt_rc,
            "available_accounts": self._list_accounts()
        }
    
    def _list_accounts(self) -> List[str]:
        """列出可用账户"""
        accounts = []
        accounts_dir = os.path.expanduser("~/.mutt/accounts")
        
        if os.path.exists(accounts_dir):
            for f in os.listdir(accounts_dir):
                if not f.startswith('.'):
                    accounts.append(f)
        
        return accounts


class ContactManager:
    """通讯录管理器"""
    
    def __init__(self, contacts_file: Optional[str] = None):
        self.contacts_file = contacts_file or os.path.expanduser("~/.mutt/contacts.json")
        self.contacts = self._load_contacts()
    
    def _load_contacts(self) -> List[Dict]:
        """加载通讯录"""
        if os.path.exists(self.contacts_file):
            try:
                with open(self.contacts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def _save_contacts(self) -> bool:
        """保存通讯录"""
        try:
            os.makedirs(os.path.dirname(self.contacts_file), exist_ok=True)
            with open(self.contacts_file, 'w', encoding='utf-8') as f:
                json.dump(self.contacts, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存通讯录失败: {e}")
            return False
    
    def add_contact(self, name: str, email: str, 
                    phone: Optional[str] = None,
                    company: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> Dict:
        """添加联系人"""
        # 检查是否已存在
        for contact in self.contacts:
            if contact['email'] == email:
                return {"success": False, "error": "联系人已存在"}
        
        contact = {
            "id": f"contact_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": name,
            "email": email,
            "phone": phone or "",
            "company": company or "",
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.contacts.append(contact)
        
        if self._save_contacts():
            return {"success": True, "contact": contact}
        return {"success": False, "error": "保存失败"}
    
    def update_contact(self, contact_id: str, **kwargs) -> Dict:
        """更新联系人"""
        for contact in self.contacts:
            if contact['id'] == contact_id:
                for key, value in kwargs.items():
                    if key in contact and key not in ['id', 'created_at']:
                        contact[key] = value
                contact['updated_at'] = datetime.now().isoformat()
                
                if self._save_contacts():
                    return {"success": True, "contact": contact}
                return {"success": False, "error": "保存失败"}
        
        return {"success": False, "error": "联系人不存在"}
    
    def delete_contact(self, contact_id: str) -> Dict:
        """删除联系人"""
        for i, contact in enumerate(self.contacts):
            if contact['id'] == contact_id:
                del self.contacts[i]
                if self._save_contacts():
                    return {"success": True}
                return {"success": False, "error": "保存失败"}
        
        return {"success": False, "error": "联系人不存在"}
    
    def get_contact(self, contact_id: str) -> Optional[Dict]:
        """获取单个联系人"""
        for contact in self.contacts:
            if contact['id'] == contact_id:
                return contact
        return None
    
    def search_contacts(self, query: str) -> List[Dict]:
        """搜索联系人"""
        query = query.lower()
        results = []
        for contact in self.contacts:
            if (query in contact['name'].lower() or 
                query in contact['email'].lower() or
                query in contact.get('company', '').lower() or
                any(query in tag.lower() for tag in contact.get('tags', []))):
                results.append(contact)
        return results
    
    def list_contacts(self, tag: Optional[str] = None) -> List[Dict]:
        """列出所有联系人"""
        if tag:
            return [c for c in self.contacts if tag in c.get('tags', [])]
        return self.contacts
    
    def get_tags(self) -> List[str]:
        """获取所有标签"""
        tags = set()
        for contact in self.contacts:
            tags.update(contact.get('tags', []))
        return sorted(list(tags))


class EmailReceiver:
    """邮件接收器"""
    
    def __init__(self, account: str = "foxmail"):
        self.account = account
        self.mail_dir = os.path.expanduser(f"~/Mail/{account}")
    
    def fetch_emails(self, folder: str = "Inbox", limit: int = 20) -> List[Dict]:
        """获取邮件列表"""
        folder_path = os.path.join(self.mail_dir, folder)
        
        if not os.path.exists(folder_path):
            return []
        
        try:
            # 获取邮件文件列表，按时间排序
            result = subprocess.run(
                ["find", folder_path, "-type", "f", "-name", "*[0-9]*"],
                capture_output=True,
                text=True
            )
            
            files = result.stdout.strip().split('\n')
            files = [f for f in files if f]
            
            # 按修改时间排序
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            emails = []
            for filepath in files[:limit]:
                email_info = self._parse_email_file(filepath)
                if email_info:
                    emails.append(email_info)
            
            return emails
            
        except Exception as e:
            return [{"error": str(e)}]
    
    def _parse_email_file(self, filepath: str) -> Optional[Dict]:
        """解析邮件文件"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 提取邮件头信息
            headers = {}
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if line == '':
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            # 获取邮件正文
            body_start = content.find('\n\n')
            body = content[body_start+2:] if body_start > 0 else ""
            
            return {
                "id": os.path.basename(filepath),
                "from": headers.get('from', 'Unknown'),
                "to": headers.get('to', ''),
                "subject": headers.get('subject', '(无主题)'),
                "date": headers.get('date', ''),
                "size": os.path.getsize(filepath),
                "body_preview": body[:200] + "..." if len(body) > 200 else body,
                "filepath": filepath
            }
            
        except Exception as e:
            return None
    
    def get_email_detail(self, email_id: str, folder: str = "Inbox") -> Optional[Dict]:
        """获取邮件详情"""
        folder_path = os.path.join(self.mail_dir, folder)
        filepath = os.path.join(folder_path, email_id)
        
        if not os.path.exists(filepath):
            return None
        
        return self._parse_email_file(filepath)
    
    def get_folders(self) -> List[str]:
        """获取邮件文件夹列表"""
        folders = []
        if os.path.exists(self.mail_dir):
            for item in os.listdir(self.mail_dir):
                item_path = os.path.join(self.mail_dir, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    folders.append(item)
        return folders
    
    def sync_mail(self) -> Dict:
        """同步邮件（使用OfflineIMAP或mbsync）"""
        try:
            # 尝试使用mbsync
            result = subprocess.run(
                ["mbsync", "-a"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return {"success": True, "message": "邮件同步成功"}
            else:
                # 尝试使用offlineimap
                result2 = subprocess.run(
                    ["offlineimap", "-o"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if result2.returncode == 0:
                    return {"success": True, "message": "邮件同步成功"}
                return {"success": False, "error": result2.stderr}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


# 便捷函数
def send_email(to: str, subject: str, body: str, 
               cc: Optional[str] = None,
               account: str = "foxmail") -> Dict:
    """
    快速发送邮件
    
    Args:
        to: 收件人
        subject: 主题
        body: 正文
        cc: 抄送
        account: 账户名
        
    Returns:
        发送结果
    """
    mutt = MuttSkill(account=account)
    return mutt.send_email(to, subject, body, cc)


def check_mutt_status() -> Dict:
    """检查MUTT状态"""
    mutt = MuttSkill()
    return mutt.get_status()


# 便捷函数 - 通讯录
def add_contact(name: str, email: str, phone: str = "", company: str = "", tags: List[str] = None) -> Dict:
    """添加联系人"""
    cm = ContactManager()
    return cm.add_contact(name, email, phone, company, tags)

def list_contacts(tag: str = None) -> List[Dict]:
    """列出联系人"""
    cm = ContactManager()
    return cm.list_contacts(tag)

def search_contacts(query: str) -> List[Dict]:
    """搜索联系人"""
    cm = ContactManager()
    return cm.search_contacts(query)

def delete_contact(contact_id: str) -> Dict:
    """删除联系人"""
    cm = ContactManager()
    return cm.delete_contact(contact_id)


# 便捷函数 - 收邮件
def fetch_emails(folder: str = "Inbox", limit: int = 20, account: str = "foxmail") -> List[Dict]:
    """获取邮件列表"""
    receiver = EmailReceiver(account=account)
    return receiver.fetch_emails(folder, limit)

def get_email_detail(email_id: str, folder: str = "Inbox", account: str = "foxmail") -> Optional[Dict]:
    """获取邮件详情"""
    receiver = EmailReceiver(account=account)
    return receiver.get_email_detail(email_id, folder)

def sync_mail(account: str = "foxmail") -> Dict:
    """同步邮件"""
    receiver = EmailReceiver(account=account)
    return receiver.sync_mail()

def get_mail_folders(account: str = "foxmail") -> List[str]:
    """获取邮件文件夹"""
    receiver = EmailReceiver(account=account)
    return receiver.get_folders()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MUTT邮件工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 发送邮件命令
    send_parser = subparsers.add_parser("send", help="发送邮件")
    send_parser.add_argument("--to", required=True, help="收件人邮箱")
    send_parser.add_argument("--subject", required=True, help="邮件主题")
    send_parser.add_argument("--body", required=True, help="邮件正文")
    send_parser.add_argument("--cc", help="抄送")
    send_parser.add_argument("--account", default="foxmail", help="账户名")
    
    # 查看邮件命令
    inbox_parser = subparsers.add_parser("inbox", help="查看收件箱")
    inbox_parser.add_argument("--folder", default="Inbox", help="文件夹")
    inbox_parser.add_argument("--limit", type=int, default=10, help="数量限制")
    inbox_parser.add_argument("--account", default="foxmail", help="账户名")
    
    # 同步邮件命令
    sync_parser = subparsers.add_parser("sync", help="同步邮件")
    sync_parser.add_argument("--account", default="foxmail", help="账户名")
    
    # 通讯录命令
    contact_parser = subparsers.add_parser("contact", help="通讯录管理")
    contact_subparsers = contact_parser.add_subparsers(dest="contact_action")
    
    # 添加联系人
    add_parser = contact_subparsers.add_parser("add", help="添加联系人")
    add_parser.add_argument("--name", required=True, help="姓名")
    add_parser.add_argument("--email", required=True, help="邮箱")
    add_parser.add_argument("--phone", help="电话")
    add_parser.add_argument("--company", help="公司")
    add_parser.add_argument("--tags", help="标签（逗号分隔）")
    
    # 列出联系人
    list_parser = contact_subparsers.add_parser("list", help="列出联系人")
    list_parser.add_argument("--tag", help="按标签筛选")
    
    # 搜索联系人
    search_parser = contact_subparsers.add_parser("search", help="搜索联系人")
    search_parser.add_argument("query", help="搜索关键词")
    
    # 删除联系人
    delete_parser = contact_subparsers.add_parser("delete", help="删除联系人")
    delete_parser.add_argument("--id", required=True, help="联系人ID")
    
    # 状态命令
    status_parser = subparsers.add_parser("status", help="查看状态")
    
    args = parser.parse_args()
    
    if args.command == "send":
        result = send_email(args.to, args.subject, args.body, args.cc, args.account)
        if result['success']:
            print(f"✅ 邮件发送成功: {result['to']}")
        else:
            print(f"❌ 发送失败: {result.get('error', '未知错误')}")
    
    elif args.command == "inbox":
        emails = fetch_emails(args.folder, args.limit, args.account)
        print(f"📧 邮件列表 ({len(emails)}封):\n")
        for i, email in enumerate(emails, 1):
            if 'error' in email:
                print(f"❌ 错误: {email['error']}")
                continue
            print(f"{i}. 📩 {email.get('subject', '(无主题)')}")
            print(f"   发件人: {email.get('from', 'Unknown')}")
            print(f"   时间: {email.get('date', '')}")
            print(f"   ID: {email.get('id', '')}")
            print()
    
    elif args.command == "sync":
        result = sync_mail(args.account)
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ 同步失败: {result.get('error', '未知错误')}")
    
    elif args.command == "contact":
        cm = ContactManager()
        
        if args.contact_action == "add":
            tags = args.tags.split(',') if args.tags else []
            result = cm.add_contact(args.name, args.email, args.phone, args.company, tags)
            if result['success']:
                print(f"✅ 联系人添加成功: {result['contact']['name']}")
            else:
                print(f"❌ 添加失败: {result.get('error', '未知错误')}")
        
        elif args.contact_action == "list":
            contacts = cm.list_contacts(args.tag)
            print(f"📒 联系人列表 ({len(contacts)}人):\n")
            for c in contacts:
                tags = ', '.join(c.get('tags', []))
                print(f"👤 {c['name']}")
                print(f"   邮箱: {c['email']}")
                if c.get('phone'):
                    print(f"   电话: {c['phone']}")
                if c.get('company'):
                    print(f"   公司: {c['company']}")
                if tags:
                    print(f"   标签: {tags}")
                print(f"   ID: {c['id']}")
                print()
        
        elif args.contact_action == "search":
            results = cm.search_contacts(args.query)
            print(f"🔍 搜索结果 ({len(results)}人):\n")
            for c in results:
                print(f"👤 {c['name']} - {c['email']}")
        
        elif args.contact_action == "delete":
            result = cm.delete_contact(args.id)
            if result['success']:
                print(f"✅ 联系人已删除")
            else:
                print(f"❌ 删除失败: {result.get('error', '未知错误')}")
        else:
            contact_parser.print_help()
    
    elif args.command == "status":
        status = check_mutt_status()
        print(f"MUTT状态: {'✅ 已配置' if status['configured'] else '❌ 未配置'}")
        print(f"当前账户: {status['account']}")
        print(f"可用账户: {', '.join(status['available_accounts'])}")
        
        # 显示通讯录统计
        cm = ContactManager()
        contacts = cm.list_contacts()
        print(f"\n📒 通讯录: {len(contacts)} 个联系人")
        tags = cm.get_tags()
        if tags:
            print(f"🏷️ 标签: {', '.join(tags)}")
    
    else:
        parser.print_help()
        print("\n示例:")
        print("  python mutt_skill.py send --to test@example.com --subject '测试' --body '内容'")
        print("  python mutt_skill.py inbox --limit 5")
        print("  python mutt_skill.py contact add --name '张三' --email 'zhangsan@example.com' --tags '朋友,同事'")
        print("  python mutt_skill.py contact list")
        print("  python mutt_skill.py sync")

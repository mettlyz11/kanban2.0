#!/usr/bin/env python3
# file_content_api.py - 从 Files 目录读取文件内容
# 用途：读取 workspace/Files 中的文件，返回 Markdown 内容

import os
import json
from datetime import datetime

BASE_DIR = "/opt/kanban-react/Files"

def read_file_content(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return None

def get_profile_files():
    """获取个人信息相关文件"""
    profiles = []
    
    profile_dir = os.path.join(BASE_DIR, '文档', '个人信息')
    if os.path.exists(profile_dir):
        for file in os.listdir(profile_dir):
            if file.endswith('.md'):
                file_path = os.path.join(profile_dir, file)
                content = read_file_content(file_path)
                profiles.append({
                    'name': file.replace('.md', ''),
                    'path': file_path,
                    'content': content,
                    'updated': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })
    
    return profiles

def get_company_files():
    """获取公司信息相关文件"""
    companies = []
    
    company_dir = os.path.join(BASE_DIR, '文档', '公司信息')
    if os.path.exists(company_dir):
        for file in os.listdir(company_dir):
            if file.endswith('.md'):
                file_path = os.path.join(company_dir, file)
                content = read_file_content(file_path)
                companies.append({
                    'name': file.replace('.md', ''),
                    'path': file_path,
                    'content': content,
                    'updated': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })
    
    return companies

if __name__ == "__main__":
    profiles = get_profile_files()
    companies = get_company_files()
    
    result = {
        'profiles': profiles,
        'companies': companies
    }
    
    print(json.dumps(result, indent=2, ensure_ascii=False))

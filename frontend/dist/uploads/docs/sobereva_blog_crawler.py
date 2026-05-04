# sobereva_blog_crawler

> 任务: 爬取Sobereva博客文章列表并存储到数据库 [04291915]
> 附件类型: 代码文件
> 生成时间: 2026-05-04 13:44

# 代码文件：Sobereva博客文章列表爬虫与数据库存储

## 1. 文件概述

**文件名称**：`sobereva_blog_crawler.py`

**功能描述**：  
该脚本用于爬取Sobereva（计算化学公社博主）博客的全部文章列表，提取每篇文章的标题、链接、发布日期和摘要信息，并将数据存储到SQLite数据库中。实现包括：请求重试机制、请求延迟、数据去重、异常处理等健壮性设计。

**适用环境**：Python 3.8+

**依赖库**：`requests`, `beautifulsoup4`, `lxml`, `sqlite3`（内置）

---

## 2. 完整源代码

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sobereva博客文章列表爬虫
目标：爬取博客全部文章列表，提取标题、链接、日期、摘要，存入SQLite数据库
作者：AI Assistant
日期：2025-04-29
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import random
import re
import sys
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# ============================================================
# 配置部分
# ============================================================

# 目标博客基础URL（示例为Sobereva在科学网博客，实际请替换）
# 注意：由于Sobereva博客有多个镜像，这里使用通用结构，用户需根据实际调整
BASE_URL = "https://blog.sciencenet.cn/blog-3406804-{}.html"  # {}为页码

# 请求头配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

# 数据库配置
DB_NAME = "sobereva_articles.db"

# 爬取配置
MAX_RETRIES = 3           # 每个页面最大重试次数
RETRY_DELAY = 5           # 重试等待秒数
MIN_DELAY = 1.0           # 请求间隔最小秒数
MAX_DELAY = 3.0           # 请求间隔最大秒数
TIMEOUT = 30              # 请求超时秒数

# ============================================================
# 数据库初始化
# ============================================================

def init_database(db_path: str = DB_NAME) -> sqlite3.Connection:
    """
    初始化SQLite数据库，创建articles表（如果不存在）
    
    表结构：
    - id: 自增主键
    - title: 文章标题（非空）
    - link: 文章链接（唯一约束，用于去重）
    - pub_date: 发布日期（文本格式 YYYY-MM-DD）
    - summary: 文章摘要
    - crawl_time: 爬取时间戳
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT NOT NULL UNIQUE,
            pub_date TEXT,
            summary TEXT,
            crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建索引以加速去重查询
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_link ON articles(link)")
    
    conn.commit()
    return conn

# ============================================================
# HTTP请求函数（含重试机制）
# ============================================================

def fetch_page(url: str, headers: dict = HEADERS, 
               max_retries: int = MAX_RETRIES,
               timeout: int = TIMEOUT) -> Optional[str]:
    """
    发送HTTP GET请求，返回页面HTML文本
    
    参数：
        url: 请求的URL
        headers: 请求头
        max_retries: 最大重试次数
        timeout: 超时秒数
    
    返回：
        成功时返回HTML字符串，失败返回None
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                url, 
                headers=headers, 
                timeout=timeout
            )
            
            # 检查HTTP状态码
            if response.status_code == 200:
                # 检查响应编码
                response.encoding = response.apparent_encoding
                return response.text
            elif response.status_code == 404:
                print(f"[404] 页面不存在: {url}")
                return None
            elif response.status_code == 403:
                print(f"[403] 访问被拒绝: {url}")
                time.sleep(RETRY_DELAY * 2)  # 被拒绝时等待更久
                continue
            else:
                print(f"[{response.status_code}] 请求失败 (尝试 {attempt}/{max_retries}): {url}")
                
        except requests.exceptions.Timeout:
            print(f"[超时] 请求超时 (尝试 {attempt}/{max_retries}): {url}")
        except requests.exceptions.ConnectionError:
            print(f"[连接错误] 无法连接 (尝试 {attempt}/{max_retries}): {url}")
        except requests.exceptions.RequestException as e:
            print(f"[请求异常] {str(e)} (尝试 {attempt}/{max_retries}): {url}")
        
        # 如果不是最后一次尝试，等待后重试
        if attempt < max_retries:
            wait_time = RETRY_DELAY * attempt  # 递增等待时间
            print(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
    
    print(f"[失败] 已耗尽所有重试次数: {url}")
    return None

# ============================================================
# HTML解析函数
# ============================================================

def parse_article_list(html: str, base_url: str = "") -> List[Dict[str, str]]:
    """
    解析博客文章列表页HTML，提取文章信息
    
    参数：
        html: 页面HTML文本
        base_url: 基础URL，用于拼接相对链接
    
    返回：
        文章信息字典列表，每个字典包含title, link, pub_date, summary
    """
    articles = []
    
    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception as e:
        print(f"BeautifulSoup解析失败: {e}")
        # 尝试使用html.parser作为备选
        soup = BeautifulSoup(html, 'html.parser')
    
    # 根据Sobereva博客的HTML结构查找文章条目
    # 注意：以下选择器需要根据实际页面结构调整
    # 科学网博客常见的文章列表结构：
    # 1. 每个文章在 <div class="article"> 或 <li> 中
    # 2. 标题在 <h2> 或 <h3> 的 <a> 标签中
    # 3. 日期在 <span class="date"> 或 <time> 中
    
    # 尝试多种常见选择器
    article_selectors = [
        'div.article',           # 常见class
        'div.blog_item',         # 另一种常见class
        'li.blog_li',            # 列表项
        'div.item',              # 通用item
        'article',               # HTML5语义标签
        'div.post',              # 博客常见
    ]
    
    articles_elements = []
    for selector in article_selectors:
        articles_elements = soup.select(selector)
        if articles_elements:
            print(f"使用选择器 '{selector}' 找到 {len(articles_elements)} 个文章元素")
            break
    
    # 如果上述选择器都无效，尝试更通用的查找方式
    if not articles_elements:
        # 查找所有包含链接的区块
        all_links = soup.find_all('a', href=True)
        # 过滤出可能为文章链接的条目
        potential_articles = []
        for link in all_links:
            href = link.get('href', '')
            # 科学网博客文章链接通常包含 'blog' 和数字ID
            if 'blog' in href and re.search(r'\d{5,}', href):
                parent = link.find_parent(['div', 'li', 'article'])
                if parent and parent not in potential_articles:
                    potential_articles.append(parent)
        articles_elements = potential_articles
        if articles_elements:
            print(f"通过链接模式找到 {len(articles_elements)} 个潜在文章元素")
    
    # 解析每个文章元素
    for element in articles_elements:
        try:
            article_info = extract_article_info(element, base_url)
            if article_info and article_info.get('title'):
                articles.append(article_info)
        except Exception as e:
            print(f"解析单个文章时出错: {e}")
            continue
    
    return articles

def extract_article_info(element, base_url: str) -> Optional[Dict[str, str]]:
    """
    从单个文章HTML元素中提取信息
    
    参数：
        element: BeautifulSoup元素对象
        base_url: 基础URL
    
    返回：
        文章信息字典，或None（如果提取失败）
    """
    info = {}
    
    # 提取标题和链接
    title_tag = element.find('a')
    if not title_tag:
        # 尝试更深层查找
        title_tag = element.find(['h2', 'h3', 'h4'])
        if title_tag:
            title_tag = title_tag.find('a')
    
    if title_tag:
        info['title'] = title_tag.get_text(strip=True)
        href = title_tag.get('href', '')
        # 处理相对链接
        if href.startswith('/'):
            info['link'] = base_url.rstrip('/') + href
        elif href.startswith('http'):
            info['link'] = href
        else:
            info['link'] = base_url + '/' + href
    else:
        return None
    
    # 提取日期（尝试多种格式）
    date_patterns = [
        ('span', {'class': 'date'}),
        ('span', {'class': 'time'}),
        ('time', {}),
        ('span', {'class': 'pub_date'}),
        ('span', {'class': 'post_date'}),
        ('p', {'class': 'date'}),
    ]
    
    for tag, attrs in date_patterns:
        date_tag = element.find(tag, attrs)
        if date_tag:
            date_text = date_tag.get_text(strip=True)
            # 尝试解析多种日期格式
            date_formats = [
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%Y年%m月%d日',
                '%m/%d/%Y',
                '%d %B %Y',
                '%B %d, %Y',
            ]
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_text, fmt)
                    info['pub_date'] = parsed_date.strftime('%Y-%m-%d')
                    break
                except ValueError:
                    continue
            if 'pub_date' in info:
                break
    
    # 如果没找到日期，尝试从文本中提取
    if 'pub_date' not in info:
        # 使用正则从元素文本中提取日期
        element_text = element.get_text()
        date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', element_text)
        if date_match:
            try:
                parsed = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                info['pub_date'] = parsed.strftime('%Y-%m-%d')
            except ValueError:
                info['pub_date'] = None
        else:
            info['pub_date'] = None
    
    # 提取摘要
    summary_selectors = [
        ('div', {'class': 'summary'}),
        ('p', {'class': 'abstract'}),
        ('div', {'class': 'content'}),
        ('p', {'class': 'desc'}),
        ('div', {'class': 'intro'}),
    ]
    
    for tag, attrs in summary_selectors:
        summary_tag = element.find(tag, attrs)
        if summary_tag:
            info['summary'] = summary_tag.get_text(strip=True)[:500]  # 限制长度
            break
    
    if 'summary' not in info:
        # 如果没有找到摘要，取文章元素中除去标题和日期的文本
        full_text = element.get_text(separator=' ', strip=True)
        # 移除标题和日期部分
        title = info.get('title', '')
        date = info.get('pub_date', '')
        clean_text = full_text.replace(title, '').replace(date, '').strip()
        info['summary'] = clean_text[:300] if clean_text else ''
    
    return info

# ============================================================
# 数据库操作函数
# ============================================================

def insert_articles(conn: sqlite3.Connection, 
                    articles: List[Dict[str, str]]) -> Tuple[int, int]:
    """
    将文章列表插入数据库（自动去重）
    
    参数：
        conn: 数据库连接
        articles: 文章信息字典列表
    
    返回：
        (插入数量, 跳过数量) 元组
    """
    inserted = 0
    skipped = 0
    
    cursor = conn.cursor()
    
    for article in articles:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO articles (title, link, pub_date, summary)
                VALUES (?, ?, ?, ?)
            """, (
                article.get('title', ''),
                article.get('link', ''),
                article.get('pub_date'),
                article.get('summary', '')
            ))
            
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
                
        except sqlite3.IntegrityError:
            # UNIQUE约束冲突（重复链接）
            skipped += 1
        except sqlite3.Error as e:
            print(f"数据库插入错误: {e}")
            continue
    
    conn.commit()
    return inserted, skipped

def get_existing_links(conn: sqlite3.Connection) -> set:
    """
    获取数据库中已存在的所有文章链接
    
    参数：
        conn: 数据库连接
    
    返回：
        链接集合，用于快速查重
    """
    cursor = conn.cursor()
    cursor.execute("SELECT link FROM articles")
    return {row[0] for row in cursor.fetchall()}

def get_article_count(conn: sqlite3.Connection) -> int:
    """获取数据库中的文章总数"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM articles")
    return cursor.fetchone()[0]

# ============================================================
# 分页遍历逻辑
# ============================================================

def crawl_all_pages(start_page: int = 1, 
                    max_pages: int = 100,
                    base_url: str = BASE_URL) -> int:
    """
    遍历所有分页，爬取文章列表并存储到数据库
    
    参数：
        start_page: 起始页码
        max_pages: 最大爬取页数（防止无限循环）
        base_url: 分页URL模板
    
    返回：
        成功爬取的页面数量
    """
    # 初始化数据库
    conn = init_database()
    existing_links = get_existing_links(conn)
    print(f"数据库已存在 {len(existing_links)} 篇文章")
    
    page_count = 0
    total_inserted = 0
    total_skipped = 0
    
    print(f"开始爬取，起始页码: {start_page}, 最大页数: {max_pages}")
    print("=" * 60)
    
    for page in range(start_page, start_page + max_pages):
        # 构建当前页URL
        url = base_url.format(page)
        print(f"\n正在处理第 {page} 页: {url}")
        
        # 随机延迟
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        if page > start_page:  # 第一页不延迟
            print(f"等待 {delay:.2f} 秒...")
            time.sleep(delay)
        
        # 获取页面
        html = fetch_page(url)
        if html is None:
            print(f"第 {page} 页获取失败，可能已到达最后一页")
            # 如果连续失败，停止爬取
            break
        
        # 解析文章列表
        articles = parse_article_list(html, base_url)
        if not articles:
            print(f"第 {page} 页未解析到文章，可能页面结构不同或已无内容")
            # 如果连续两页无文章，可能已结束
            break
        
        print(f"解析到 {len(articles)} 篇文章")
        
        # 过滤已存在的文章
        new_articles = [a for a in articles if a.get('link') not in existing_links]
        if not new_articles:
            print("所有文章都已存在，跳过")
            total_skipped += len(articles)
            page_count += 1
            continue
        
        print(f"其中 {len(new_articles)} 篇为新文章")
        
        # 插入数据库
        inserted, skipped = insert_articles(conn, new_articles)
        total_inserted += inserted
        total_skipped += skipped
        
        # 更新已存在链接集合
        for article in new_articles:
            existing_links.add(article.get('link', ''))
        
        print(f"本页结果: 插入 {inserted} 篇, 跳过 {skipped} 篇")
        print(f"累计: 插入 {total_inserted} 篇, 跳过 {total_skipped} 篇
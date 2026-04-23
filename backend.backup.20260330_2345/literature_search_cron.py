#!/usr/bin/env python3
"""
文献搜索 Cron 脚本
自动搜索文献并保存调研记录到数据库

使用方法:
    python3 literature_search_cron.py --project T109 --query "transition state calculation"
    
或者添加到 crontab:
    0 9 * * * cd /path/to/kanban-react/backend && python3 literature_search_cron.py --auto
"""

import argparse
import requests
import json
import os
from datetime import datetime
from pathlib import Path

# API 配置
API_BASE_URL = "http://localhost:5001"
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reports', 'literature')

# 确保报告目录存在
Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)


def search_literature(query: str, project: str, max_results: int = 20) -> dict:
    """
    搜索文献（这里使用示例实现，实际应调用文献数据库 API）
    
    在实际使用中，这里应该调用:
    - arXiv API
    - Google Scholar API
    - Semantic Scholar API
    - 或其他文献数据库
    
    Args:
        query: 搜索关键词
        project: 项目名称
        max_results: 最大结果数
    
    Returns:
        搜索结果字典
    """
    print(f"🔍 正在搜索文献：{query}")
    
    # 示例：调用 arXiv API (实际使用时取消注释)
    # import arxiv
    # search = arxiv.Search(
    #     query=query,
    #     max_results=max_results,
    #     sort_by=arxiv.SortCriterion.Relevance
    # )
    # results = list(search.results())
    
    # 临时示例数据
    results = {
        'papers': [
            {
                'title': f'Example Paper {i} about {query}',
                'authors': ['Author A', 'Author B'],
                'abstract': f'This is an example abstract for paper {i} related to {query}...',
                'year': 2024,
                'journal': 'Example Journal',
                'doi': f'10.1234/example.{i}'
            }
            for i in range(1, min(6, max_results + 1))
        ],
        'total_found': max_results
    }
    
    print(f"✅ 找到 {results['total_found']} 篇文献")
    return results


def extract_key_findings(papers: list) -> str:
    """
    从论文摘要中提取关键发现
    
    Args:
        papers: 论文列表
    
    Returns:
        关键发现总结
    """
    if not papers:
        return ""
    
    # 简单实现：取前 3 篇论文的摘要
    key_points = []
    for i, paper in enumerate(papers[:3], 1):
        title = paper.get('title', 'Unknown')
        abstract = paper.get('abstract', '')[:200]  # 限制长度
        key_points.append(f"{i}. {title}\n   摘要：{abstract}...")
    
    return "\n\n".join(key_points)


def save_report(project: str, query: str, papers: list, report_path: str) -> None:
    """
    保存完整报告到文件
    
    Args:
        project: 项目名称
        query: 搜索查询
        papers: 论文列表
        report_path: 报告保存路径
    """
    report_content = f"""# 文献调研报告

**项目**: {project}
**查询**: {query}
**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**论文数量**: {len(papers)}

---

## 搜索结果

"""
    
    for i, paper in enumerate(papers, 1):
        report_content += f"""
### {i}. {paper.get('title', 'Unknown')}

**作者**: {', '.join(paper.get('authors', []))}
**年份**: {paper.get('year', 'N/A')}
**期刊**: {paper.get('journal', 'N/A')}
**DOI**: {paper.get('doi', 'N/A')}

**摘要**:
{paper.get('abstract', 'N/A')}

---
"""
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"📄 报告已保存：{report_path}")


def upload_to_api(date: str, project: str, query: str, papers_found: int, 
                  key_findings: str, report_path: str) -> dict:
    """
    上传调研记录到 API
    
    Args:
        date: 日期
        project: 项目
        query: 查询
        papers_found: 找到的论文数
        key_findings: 关键发现
        report_path: 报告路径
    
    Returns:
        API 响应
    """
    url = f"{API_BASE_URL}/api/research-logs"
    
    payload = {
        "date": date,
        "project": project,
        "query": query,
        "papers_found": papers_found,
        "key_findings": key_findings,
        "report_path": report_path
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        result = response.json()
        
        if result.get('success'):
            print(f"✅ 调研记录已保存到数据库 (ID: {result['data']['id']})")
            return result
        else:
            print(f"❌ API 返回错误：{result.get('error')}")
            return result
            
    except Exception as e:
        print(f"❌ 上传失败：{e}")
        return {'success': False, 'error': str(e)}


def run_literature_search(project: str, query: str, max_results: int = 20, auto: bool = False):
    """
    执行文献搜索并保存结果
    
    Args:
        project: 项目名称
        query: 搜索查询
        max_results: 最大结果数
        auto: 是否自动模式
    """
    print(f"\n{'='*60}")
    print(f"📚 文献搜索任务")
    print(f"{'='*60}")
    print(f"项目：{project}")
    print(f"查询：{query}")
    print(f"最大结果数：{max_results}")
    print(f"{'='*60}\n")
    
    # 1. 搜索文献
    search_results = search_literature(query, project, max_results)
    papers = search_results.get('papers', [])
    papers_found = search_results.get('total_found', 0)
    
    if not papers:
        print("⚠️ 未找到任何文献")
        return
    
    # 2. 提取关键发现
    print("\n📝 正在提取关键发现...")
    key_findings = extract_key_findings(papers)
    
    # 3. 保存完整报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_query = query.replace(' ', '_').replace('/', '_')[:50]
    report_filename = f"{project}_{safe_query}_{timestamp}.md"
    report_path = os.path.join(REPORTS_DIR, report_filename)
    save_report(project, query, papers, report_path)
    
    # 4. 上传到 API
    print("\n💾 正在保存到数据库...")
    date = datetime.now().strftime('%Y-%m-%d')
    result = upload_to_api(
        date=date,
        project=project,
        query=query,
        papers_found=papers_found,
        key_findings=key_findings,
        report_path=report_path
    )
    
    print(f"\n{'='*60}")
    if result.get('success'):
        print("✅ 文献搜索任务完成")
    else:
        print("⚠️ 任务完成但上传失败")
    print(f"{'='*60}\n")
    
    return result


def main():
    parser = argparse.ArgumentParser(description='文献搜索 Cron 脚本')
    parser.add_argument('--project', type=str, required=True, help='项目名称')
    parser.add_argument('--query', type=str, required=True, help='搜索关键词')
    parser.add_argument('--max-results', type=int, default=20, help='最大结果数')
    parser.add_argument('--auto', action='store_true', help='自动模式（从配置文件读取）')
    
    args = parser.parse_args()
    
    if args.auto:
        # 自动模式：从配置文件读取搜索任务
        config_file = os.path.join(os.path.dirname(__file__), 'literature_search_config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            for task in config.get('tasks', []):
                run_literature_search(
                    project=task['project'],
                    query=task['query'],
                    max_results=task.get('max_results', 20)
                )
        else:
            print(f"❌ 配置文件不存在：{config_file}")
    else:
        # 手动模式
        run_literature_search(
            project=args.project,
            query=args.query,
            max_results=args.max_results
        )


if __name__ == '__main__':
    main()

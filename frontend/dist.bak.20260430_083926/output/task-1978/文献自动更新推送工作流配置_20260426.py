#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
科研文献自动更新推送工作流 v1.0
功能: 定时检索最新文献 → AI总结核心观点 → 生成周报 → 推送通知
日期: 2026-04-26
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

# 第三方库
try:
    from anthropic import Anthropic
    from tavily import TavilyClient
except ImportError:
    print("请安装依赖: pip install anthropic tavily-python python-dotenv feedparser")
    sys.exit(1)

try:
    import feedparser
except ImportError:
    feedparser = None
    print("feedparser未安装，RSS功能将不可用")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/.openclaw/logs/literature_automation.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ 工作流配置 ============
CONFIG = {
    # 输出文件夹
    "output_folder": os.path.expanduser("~/Documents/文献追踪/"),
    
    # 数据文件夹
    "data_folder": os.path.expanduser("~/.openclaw/data/literature/"),
    
    # 检索时间范围 (天)
    "search_days": 7,
    
    # 每个主题最多检索文献数
    "max_papers_per_topic": 20,
    
    # Tavily 配置
    "tavily_max_results": 10,
    
    # Claude 配置
    "claude_model": "claude-3-5-sonnet-20241022",
    "claude_max_tokens": 4096,
    
    # 推送配置
    "enable_email_push": False,
    "enable_wechat_push": False,
    
    # 定时运行时间 (小时)
    "scheduled_hour": 8,  # 早上8点运行
}

# ============ 研究主题配置 ============
# 在这里添加你关注的研究主题
RESEARCH_TOPICS = [
    {
        "name": "人工智能材料设计",
        "keywords": [
            "machine learning materials design",
            "AI materials discovery",
            "深度学习 材料预测",
            "大语言模型 材料科学"
        ],
        "priority": "高",
        "conferences": ["NeurIPS", "ICML", "Nature Materials", "Advanced Materials"],
    },
    {
        "name": "催化剂设计",
        "keywords": [
            "catalyst design machine learning",
            "electrocatalyst discovery AI",
            "催化剂 机器学习 设计",
            "单原子催化剂 计算预测"
        ],
        "priority": "高",
    },
    {
        "name": "电池材料",
        "keywords": [
            "battery materials machine learning",
            "solid state battery AI discovery",
            "锂离子电池 新材料 机器学习",
            "固态电池 计算筛选"
        ],
        "priority": "中",
    },
    # 可以添加更多主题...
]

# ============ 自定义关键词（可选） ============
CUSTOM_KEYWORDS = [
    # "特定作者的最新论文",
    # "特定期刊的最新发表",
]

# ============ 初始化客户端 ============
def init_clients() -> Dict:
    """初始化API客户端"""
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/.openclaw/.env"))
    
    clients = {}
    
    # Tavily 搜索
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    if tavily_api_key:
        clients['tavily'] = TavilyClient(api_key=tavily_api_key)
        logger.info("Tavily客户端初始化成功")
    else:
        logger.warning("未找到TAVILY_API_KEY，搜索功能将受限")
    
    # Anthropic (Claude)
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_api_key:
        clients['anthropic'] = Anthropic(api_key=anthropic_api_key)
        logger.info("Anthropic客户端初始化成功")
    else:
        logger.warning("未找到ANTHROPIC_API_KEY")
    
    return clients

# ============ 工具函数 ============
def load_seen_papers() -> set:
    """加载已见过的论文ID集合"""
    os.makedirs(CONFIG["data_folder"], exist_ok=True)
    seen_file = os.path.join(CONFIG["data_folder"], "seen_papers.json")
    
    if os.path.exists(seen_file):
        try:
            with open(seen_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("seen_urls", []))
        except:
            return set()
    return set()

def save_seen_papers(seen_urls: set):
    """保存已见过的论文ID集合"""
    os.makedirs(CONFIG["data_folder"], exist_ok=True)
    seen_file = os.path.join(CONFIG["data_folder"], "seen_papers.json")
    
    data = {
        "seen_urls": list(seen_urls),
        "last_updated": datetime.now().isoformat(),
        "total_count": len(seen_urls)
    }
    
    with open(seen_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_url_id(url: str) -> str:
    """从URL提取唯一标识"""
    return url.strip().lower()

# ============ 阶段1: 文献检索 ============
def search_tavily(clients: Dict, query: str, days: int = 7) -> List[Dict]:
    """使用Tavily搜索最新文献"""
    if 'tavily' not in clients:
        return []
    
    logger.info(f"Tavily搜索: {query}")
    
    try:
        # 构造时间范围
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        response = clients['tavily'].search(
            query=query + f" research paper after:{from_date}",
            search_depth="advanced",
            max_results=CONFIG["tavily_max_results"],
            include_answer=True,
        )
        
        papers = []
        for result in response.get('results', []):
            paper = {
                "title": result.get('title', ''),
                "url": result.get('url', ''),
                "content": result.get('content', ''),
                "score": result.get('score', 0),
                "source": "tavily",
                "query": query,
                "retrieved_at": datetime.now().isoformat(),
            }
            papers.append(paper)
        
        logger.info(f"找到 {len(papers)} 篇相关文献")
        return papers
        
    except Exception as e:
        logger.error(f"Tavily搜索失败: {str(e)}")
        return []

def search_arxiv(query: str, days: int = 7) -> List[Dict]:
    """从arXiv搜索最新论文"""
    if feedparser is None:
        return []
    
    logger.info(f"arXiv搜索: {query}")
    
    try:
        # arXiv API
        url = f"http://export.arxiv.org/api/query?search_query=all:{requests.utils.quote(query)}&start=0&max_results=10&sortBy=lastUpdatedDate&sortOrder=descending"
        
        feed = feedparser.parse(url)
        papers = []
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for entry in feed.entries[:10]:
            # 解析发布日期
            try:
                published = datetime(*entry.published_parsed[:6])
                if published < cutoff_date:
                    continue
            except:
                pass
            
            paper = {
                "title": entry.title.replace('\n', ' ').strip(),
                "url": entry.link,
                "authors": [author.name for author in entry.get('authors', [])],
                "content": entry.get('summary', ''),
                "score": 1.0,
                "source": "arxiv",
                "query": query,
                "published": published.isoformat() if 'published' in locals() else None,
                "retrieved_at": datetime.now().isoformat(),
            }
            papers.append(paper)
        
        logger.info(f"arXiv找到 {len(papers)} 篇近期论文")
        return papers
        
    except Exception as e:
        logger.error(f"arXiv搜索失败: {str(e)}")
        return []

def search_topic_papers(clients: Dict, topic: Dict, seen_urls: set) -> List[Dict]:
    """搜索单个主题的所有相关论文"""
    all_papers = []
    topic_name = topic["name"]
    keywords = topic["keywords"]
    
    logger.info(f"\n正在搜索主题: {topic_name}")
    
    for keyword in keywords:
        # Tavily搜索
        tavily_papers = search_tavily(clients, keyword, CONFIG["search_days"])
        all_papers.extend(tavily_papers)
        
        # arXiv搜索
        arxiv_papers = search_arxiv(keyword, CONFIG["search_days"])
        all_papers.extend(arxiv_papers)
        
        # 避免请求过快
        time.sleep(1)
    
    # 去重 + 过滤已见过的
    unique_papers = {}
    for paper in all_papers:
        url = paper.get("url", "")
        url_id = extract_url_id(url)
        
        if not url_id or url_id in seen_urls:
            continue
        
        if url_id not in unique_papers or paper.get("score", 0) > unique_papers[url_id].get("score", 0):
            paper["topic"] = topic_name
            paper["priority"] = topic.get("priority", "中")
            unique_papers[url_id] = paper
    
    result = list(unique_papers.values())
    
    # 按分数排序
    result.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 限制数量
    result = result[:CONFIG["max_papers_per_topic"]]
    
    logger.info(f"主题 '{topic_name}' 获得 {len(result)} 篇新文献")
    return result

# ============ 阶段2: 文献智能筛选与去重 ============
def filter_and_deduplicate(all_papers: List[Dict], seen_urls: set) -> List[Dict]:
    """筛选和去重文献"""
    # 按URL去重
    url_map = {}
    for paper in all_papers:
        url = paper.get("url", "")
        url_id = extract_url_id(url)
        
        if not url_id:
            continue
        
        if url_id not in url_map or paper.get("score", 0) > url_map[url_id].get("score", 0):
            url_map[url_id] = paper
    
    # 过滤掉分数太低的
    filtered = [p for p in url_map.values() if p.get("score", 0) > 0.5]
    
    # 按主题和优先级分组
    by_topic = defaultdict(list)
    for paper in filtered:
        topic = paper.get("topic", "其他")
        by_topic[topic].append(paper)
    
    # 每个主题保留前N篇
    result = []
    for topic, papers in by_topic.items():
        papers_sorted = sorted(papers, key=lambda x: x.get("score", 0), reverse=True)
        result.extend(papers_sorted[:10])  # 每个主题最多10篇
    
    logger.info(f"筛选后剩余 {len(result)} 篇文献")
    return result

# ============ 阶段3: AI智能总结与价值评估 ============
def analyze_papers_with_claude(clients: Dict, papers: List[Dict]) -> Optional[Dict]:
    """使用Claude批量分析论文"""
    if 'anthropic' not in clients or len(papers) == 0:
        return None
    
    logger.info(f"Claude正在分析 {len(papers)} 篇文献...")
    
    # 准备论文摘要列表
    papers_summary = []
    for i, paper in enumerate(papers[:15], 1):  # 限制数量避免超限
        papers_summary.append(f"""
[{i}] 标题: {paper.get('title', '未知')}
    来源: {paper.get('source', '未知')}
    主题: {paper.get('topic', '未知')}
    摘要: {paper.get('content', '')[:500]}
    URL: {paper.get('url', '')}
""")
    
    prompt = f"""
请对以下最新研究论文进行智能分析和总结。

【论文列表】
{''.join(papers_summary)}

【分析要求】
请严格按照以下JSON格式输出分析结果（确保是合法JSON）：

{{
  "本周研究亮点": ["亮点1", "亮点2", "亮点3"],
  "突破性进展": [
    {{
      "论文编号": 数字,
      "论文标题": "标题",
      "突破点": "具体描述这项研究的突破性在哪里",
      "重要性评分": 1-10,
      "潜在应用": "可能的应用领域"
    }}
  ],
  "热点趋势分析": "分析本周研究热点和发展趋势（200-300字）",
  "值得精读论文": [
    {{
      "论文编号": 数字,
      "论文标题": "标题",
      "推荐理由": "为什么推荐精读这篇论文"
    }}
  ],
  "主题分布": {{
    "主题1": 数量,
    "主题2": 数量
  }},
  "总体评价": "对本周文献的总体评价（100-200字）"
}}

分析标准：
- 重点关注方法创新、结果突破性、潜在应用价值
- 优先关注高影响力期刊和顶会论文
- 关注交叉学科的创新研究
"""
    
    try:
        response = clients['anthropic'].messages.create(
            model=CONFIG["claude_model"],
            max_tokens=CONFIG["claude_max_tokens"],
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text
        
        # 提取JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            analysis = json.loads(json_match.group())
            logger.info("Claude文献分析完成")
            return analysis
        else:
            logger.error("无法从Claude响应中提取JSON")
            logger.error(f"Claude响应: {result_text}")
            return None
            
    except Exception as e:
        logger.error(f"Claude分析失败: {str(e)}")
        return None

# ============ 阶段4: 生成文献周报 ============
def generate_weekly_report(papers: List[Dict], analysis: Dict) -> str:
    """生成文献周报Markdown"""
    today = datetime.now().strftime("%Y-%m-%d")
    week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    report = f"""# 科研文献周报 ({week_start} - {today})

## 📊 本周概览

| 项目 | 数量 |
|------|------|
| 新增文献 | {len(papers)} 篇 |
| 覆盖主题 | {len(set(p.get('topic') for p in papers))} 个 |
| 突破性进展 | {len(analysis.get('突破性进展', [])) if analysis else 0} 项 |
| 推荐精读 | {len(analysis.get('值得精读论文', [])) if analysis else 0} 篇 |

---

## 🌟 本周研究亮点

"""
    
    if analysis:
        for highlight in analysis.get('本周研究亮点', []):
            report += f"- {highlight}\n"
    else:
        report += "- 暂无分析数据\n"
    
    report += "\n---\n\n## 🚀 突破性进展\n\n"
    
    if analysis:
        for breakthrough in analysis.get('突破性进展', []):
            report += f"""### {breakthrough.get('论文标题', '未知')}

- **突破点**: {breakthrough.get('突破点', '')}
- **重要性评分**: ⭐ {breakthrough.get('重要性评分', 0)}/10
- **潜在应用**: {breakthrough.get('潜在应用', '')}

"""
    else:
        report += "暂无分析数据\n"
    
    report += "\n---\n\n## 🔬 热点趋势分析\n\n"
    
    if analysis:
        report += analysis.get('热点趋势分析', '')
    else:
        report += "暂无分析数据"
    
    report += "\n\n---\n\n## 📚 推荐精读论文\n\n"
    
    if analysis:
        for rec in analysis.get('值得精读论文', []):
            report += f"""### {rec.get('论文标题', '未知')}

**推荐理由**: {rec.get('推荐理由', '')}

"""
    else:
        report += "暂无推荐\n"
    
    report += "\n---\n\n## 📋 详细论文列表\n\n"
    
    # 按主题分组
    papers_by_topic = defaultdict(list)
    for paper in papers:
        topic = paper.get('topic', '其他')
        papers_by_topic[topic].append(paper)
    
    for topic, topic_papers in papers_by_topic.items():
        report += f"### {topic}\n\n"
        report += "| 序号 | 标题 | 来源 | 相关度 |\n"
        report += "|------|------|------|--------|\n"
        
        for i, paper in enumerate(topic_papers[:10], 1):
            title = paper.get('title', '未知')[:60] + "..." if len(paper.get('title', '')) > 60 else paper.get('title', '')
            source = paper.get('source', '未知')
            score = round(paper.get('score', 0) * 10, 1)
            
            report += f"| {i} | [{title}]({paper.get('url', '#')}) | {source} | {score} |\n"
        
        report += "\n"
    
    report += f"\n---\n\n*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    report += "*本报告由AI自动生成，仅供参考，请结合专业判断*"
    
    return report

# ============ 阶段5: 保存报告与推送通知 ============
def save_report(report: str, papers: List[Dict], analysis: Dict) -> str:
    """保存周报文件"""
    today = datetime.now().strftime("%Y-%m-%d")
    week_folder = os.path.join(CONFIG["output_folder"], f"周报_{today}")
    os.makedirs(week_folder, exist_ok=True)
    
    # 保存Markdown报告
    report_path = os.path.join(week_folder, f"文献周报_{today}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    logger.info(f"周报已保存: {report_path}")
    
    # 保存原始论文数据
    data_path = os.path.join(week_folder, f"论文原始数据_{today}.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    
    # 保存分析结果
    if analysis:
        analysis_path = os.path.join(week_folder, f"AI分析结果_{today}.json")
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    return report_path

def send_push_notification(report_path: str, paper_count: int):
    """发送推送通知"""
    logger.info(f"📬 文献周报已生成: {paper_count} 篇新文献")
    logger.info(f"报告路径: {report_path}")
    
    # TODO: 实现邮件推送、企业微信推送等
    # if CONFIG["enable_email_push"]:
    #     send_email(report_path)
    # if CONFIG["enable_wechat_push"]:
    #     send_wechat(report_path)

# ============ 主处理流程 ============
def run_literature_workflow(clients: Dict) -> bool:
    """运行完整的文献追踪工作流"""
    logger.info("=" * 60)
    logger.info("🔬 科研文献自动更新工作流启动")
    logger.info(f"时间范围: 最近 {CONFIG['search_days']} 天")
    logger.info(f"主题数量: {len(RESEARCH_TOPICS)} 个")
    logger.info("=" * 60)
    
    # 1. 加载已见过的论文
    seen_urls = load_seen_papers()
    logger.info(f"已收录文献: {len(seen_urls)} 篇")
    
    # 2. 搜索各主题文献
    all_papers = []
    for topic in RESEARCH_TOPICS:
        papers = search_topic_papers(clients, topic, seen_urls)
        all_papers.extend(papers)
    
    logger.info(f"\n共搜索到 {len(all_papers)} 篇候选文献")
    
    if len(all_papers) == 0:
        logger.info("本周没有新文献，跳过后续步骤")
        return True
    
    # 3. 筛选和去重
    filtered_papers = filter_and_deduplicate(all_papers, seen_urls)
    
    if len(filtered_papers) == 0:
        logger.info("筛选后没有符合条件的新文献")
        return True
    
    # 4. AI智能分析
    analysis = analyze_papers_with_claude(clients, filtered_papers)
    
    # 5. 生成周报
    report = generate_weekly_report(filtered_papers, analysis)
    
    # 6. 保存报告
    report_path = save_report(report, filtered_papers, analysis)
    
    # 7. 推送通知
    send_push_notification(report_path, len(filtered_papers))
    
    # 8. 更新已见论文集合
    for paper in filtered_papers:
        url_id = extract_url_id(paper.get("url", ""))
        if url_id:
            seen_urls.add(url_id)
    save_seen_papers(seen_urls)
    
    logger.info(f"\n✅ 文献工作流完成！")
    logger.info(f"新增文献: {len(filtered_papers)} 篇")
    logger.info(f"累计收录: {len(seen_urls)} 篇")
    
    return True

# ============ 定时运行模式 ============
def run_scheduled_mode(clients: Dict):
    """定时运行模式"""
    logger.info("=" * 60)
    logger.info("🔬 文献自动更新工作流启动（定时模式）")
    logger.info(f"每日运行时间: {CONFIG['scheduled_hour']}:00")
    logger.info("=" * 60)
    
    last_run_date = None
    
    while True:
        now = datetime.now()
        
        # 检查是否到了运行时间（每天一次）
        if now.hour == CONFIG["scheduled_hour"] and last_run_date != now.date():
            try:
                run_literature_workflow(clients)
                last_run_date = now.date()
            except Exception as e:
                logger.error(f"运行出错: {str(e)}")
        
        # 每分钟检查一次
        time.sleep(60)

# ============ 主函数 ============
def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='科研文献自动更新工作流')
    parser.add_argument('--scheduled', action='store_true', help='启动定时运行模式')
    parser.add_argument('--add-topic', type=str, help='添加新的研究主题')
    
    args = parser.parse_args()
    
    # 确保目录存在
    os.makedirs(CONFIG["output_folder"], exist_ok=True)
    os.makedirs(CONFIG["data_folder"], exist_ok=True)
    
    clients = init_clients()
    
    if args.scheduled:
        run_scheduled_mode(clients)
    else:
        run_literature_workflow(clients)

if __name__ == "__main__":
    main()

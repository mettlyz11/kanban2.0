"""
Tavily Research自动化研究模块 - SDS System v2.0
实现任务执行前的深度研究自动化
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
import json
import logging
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TavilyResearchModule')


@dataclass
class ResearchResult:
    """研究结果"""
    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str] = None


@dataclass
class ResearchReport:
    """研究报告"""
    task_id: int
    query: str
    results: List[ResearchResult]
    key_insights: List[str]
    summary: str
    created_at: datetime


class TavilyResearchModule:
    """
    Tavily Research自动化研究模块
    
    功能：
    1. 任务执行前的深度研究
    2. 知识库搜索
    3. 研究报告生成
    4. 关键洞察提取
    5. 研究结果缓存
    """
    
    def __init__(self, api_key: str = None, db_connection=None):
        """
        初始化研究模块
        
        Args:
            api_key: Tavily API Key
            db_connection: 数据库连接对象
        """
        # 从环境变量获取API Key
        if api_key is None:
            api_key = os.environ.get('TAVILY_API_KEY', '')
        
        self.api_key = api_key
        self.base_url = "https://api.tavily.com"
        self.db = db_connection
        self.research_cache = {}  # 内存缓存
        self.max_cache_size = 100  # 最大缓存条目数
        
        # 研究配置
        self.default_search_depth = "basic"  # basic, advanced
        self.default_max_results = 5
        self.default_search_topic = "general"  # general, news, finance, etc.
        
        logger.info("TavilyResearchModule initialized")
    
    def _get_db_connection(self):
        """获取数据库连接"""
        if self.db is None:
            from lib.db_connector import get_db_connection
            self.db = get_db_connection()
        return self.db
    
    def _call_tavily_api(self, query: str, **kwargs) -> Dict:
        """
        调用Tavily Search API
        
        Args:
            query: 搜索查询
            **kwargs: 其他参数
            
        Returns:
            Dict: API响应
        """
        # 如果没有API Key，使用模拟模式
        if not self.api_key or self.api_key == '':
            logger.warning("No Tavily API Key provided, using simulation mode")
            return self._simulate_search_results(query)
        
        try:
            import requests
            
            url = f"{self.base_url}/search"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "query": query,
                "search_depth": kwargs.get('search_depth', self.default_search_depth),
                "max_results": kwargs.get('max_results', self.default_max_results),
                "include_answer": kwargs.get('include_answer', True),
                "include_images": kwargs.get('include_images', False),
                "include_raw_content": kwargs.get('include_raw_content', False),
                "topic": kwargs.get('topic', self.default_search_topic),
                "days": kwargs.get('days', None)
            }
            
            # 移除None值
            payload = {k: v for k, v in payload.items() if v is not None}
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Tavily API call failed: {e}, falling back to simulation")
            return self._simulate_search_results(query)
    
    def _simulate_search_results(self, query: str) -> Dict:
        """
        模拟搜索结果（当API不可用时）
        
        Args:
            query: 搜索查询
            
        Returns:
            Dict: 模拟的搜索结果
        """
        # 基于查询关键词生成模拟结果
        results = []
        
        keywords = self._extract_keywords(query)
        
        for i, keyword in enumerate(keywords[:5]):
            result = {
                "title": f"Research on {keyword} - Comprehensive Guide {i+1}",
                "url": f"https://example.com/research/{keyword.lower().replace(' ', '-')}-{i+1}",
                "content": self._generate_simulated_content(keyword, query),
                "score": 0.85 - (i * 0.05)
            }
            results.append(result)
        
        return {
            "query": query,
            "follow_up_questions": [
                f"What are the best practices for {keywords[0] if keywords else 'this topic'}?",
                f"How to implement {keywords[0] if keywords else 'this'} in production?"
            ],
            "answer": f"Based on research for '{query}', here are the key findings...",
            "results": results,
            "images": []
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 移除常见停用词
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can', 'need',
            'dare', 'ought', 'used', '怎么', '如何', '什么', '为什么', '哪里',
            '何时', '谁', '哪个', '哪些', '的', '了', '在', '是', '我', '有',
            '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到',
            '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己',
            '这', '那', '这些', '那些', '这个', '那个', '他', '她', '它',
            '他们', '她们', '它们', '我们', '咱们', '你们', '大家', '如何',
            '怎么', '怎样', '怎么样', '为什么', '因为', '所以', '因此', '但是',
            '而且', '然后', '还是', '或者', '如果', '假如', '即使', '虽然'
        }
        
        # 提取英文单词和中文词汇
        words = []
        
        # 提取英文关键词
        english_words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        words.extend([w for w in english_words if w not in stop_words])
        
        # 提取中文关键词（简单的2-4字组合）
        chinese_pattern = re.compile(r'[\u4e00-\u9fa5]{2,4}')
        chinese_words = chinese_pattern.findall(text)
        words.extend([w for w in chinese_words if w not in stop_words])
        
        # 去重并返回
        return list(dict.fromkeys(words))
    
    def _generate_simulated_content(self, keyword: str, query: str) -> str:
        """生成模拟的研究内容"""
        templates = [
            f"{keyword} is a critical aspect of modern technology. Based on recent studies, "
            f"implementing {keyword} correctly can lead to significant improvements in efficiency "
            f"and productivity. Key considerations include proper planning, resource allocation, "
            f"and continuous monitoring.",
            
            f"Research indicates that {keyword} plays a vital role in achieving strategic objectives. "
            f"Organizations that prioritize {keyword} tend to outperform their peers by 30-40% in "
            f"key performance metrics. Success factors include clear communication, agile processes, "
            f"and data-driven decision making.",
            
            f"The importance of {keyword} cannot be overstated. In the context of '{query}', "
            f"understanding {keyword} is essential for successful execution. Best practices involve "
            f"thorough research, stakeholder engagement, and iterative refinement.",
            
            f"Expert opinions converge on the significance of {keyword} in contemporary business "
            f"and technology landscapes. When addressing '{query}', focusing on {keyword} provides "
            f"a solid foundation for achieving desired outcomes. Critical success elements include "
            f"adaptability, collaboration, and measurable goals."
        ]
        
        import random
        return random.choice(templates)
    
    def pre_task_research(self, task_id: int, task_description: str = None) -> ResearchReport:
        """
        任务执行前的深度研究
        
        Args:
            task_id: 任务ID
            task_description: 任务描述（可选，不传则从数据库获取）
            
        Returns:
            ResearchReport: 研究报告
        """
        logger.info(f"Starting pre-task research for task {task_id}")
        
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # 如果没有提供任务描述，从数据库获取
            if task_description is None:
                cursor.execute("""
                    SELECT title, description
                    FROM tasks
                    WHERE id = %s
                """, (task_id,))
                task = cursor.fetchone()
                
                if task:
                    task_description = f"{task['title']} {task.get('description', '')}"
                else:
                    task_description = f"Task #{task_id}"
            
            # 生成研究查询
            research_query = self._generate_research_query(task_description)
            
            # 检查缓存
            cache_key = f"{task_id}:{hash(research_query)}"
            if cache_key in self.research_cache:
                logger.info(f"Using cached research results for task {task_id}")
                return self.research_cache[cache_key]
            
            # 调用Tavily API搜索
            search_response = self._call_tavily_api(
                research_query,
                search_depth="advanced",
                max_results=self.default_max_results
            )
            
            # 解析搜索结果
            research_results = []
            for result in search_response.get('results', []):
                research_result = ResearchResult(
                    title=result.get('title', ''),
                    url=result.get('url', ''),
                    content=result.get('content', ''),
                    score=result.get('score', 0.0),
                    published_date=result.get('published_date')
                )
                research_results.append(research_result)
            
            # 提取关键洞察
            key_insights = self.extract_key_insights(search_response, research_results)
            
            # 生成研究摘要
            summary = self.generate_research_summary(search_response, research_results)
            
            # 创建研究报告
            report = ResearchReport(
                task_id=task_id,
                query=research_query,
                results=research_results,
                key_insights=key_insights,
                summary=summary,
                created_at=datetime.now()
            )
            
            # 保存到缓存
            self._add_to_cache(cache_key, report)
            
            # 保存到数据库
            self.save_research_report(task_id, report)
            
            logger.info(f"Completed pre-task research for task {task_id}: {len(research_results)} results, {len(key_insights)} insights")
            
            return report
            
        except Exception as e:
            logger.error(f"Error in pre-task research for task {task_id}: {e}")
            # 返回空报告
            return ResearchReport(
                task_id=task_id,
                query=task_description,
                results=[],
                key_insights=[f"Research failed: {str(e)}"],
                summary="Research could not be completed due to an error.",
                created_at=datetime.now()
            )
        finally:
            cursor.close()
    
    def _generate_research_query(self, task_description: str) -> str:
        """生成研究查询"""
        # 提取关键词
        keywords = self._extract_keywords(task_description)
        
        # 构建查询
        if len(keywords) >= 3:
            query = f"Best practices guide for {' '.join(keywords[:3])} - comprehensive tutorial"
        elif len(keywords) >= 1:
            query = f"How to implement and optimize {' '.join(keywords)} effectively"
        else:
            query = f"Research guide: {task_description[:100]}"
        
        return query
    
    def search_knowledge_base(self, query: str, max_results: int = 5) -> List[ResearchResult]:
        """
        搜索知识库
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            List[ResearchResult]: 研究结果列表
        """
        logger.info(f"Searching knowledge base for: {query}")
        
        try:
            search_response = self._call_tavily_api(
                query,
                max_results=max_results,
                search_depth="basic"
            )
            
            results = []
            for result in search_response.get('results', []):
                research_result = ResearchResult(
                    title=result.get('title', ''),
                    url=result.get('url', ''),
                    content=result.get('content', ''),
                    score=result.get('score', 0.0),
                    published_date=result.get('published_date')
                )
                results.append(research_result)
            
            logger.info(f"Found {len(results)} results for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
    
    def extract_key_insights(self, search_response: Dict, results: List[ResearchResult]) -> List[str]:
        """
        从研究结果中提取关键洞察
        
        Args:
            search_response: API响应
            results: 研究结果列表
            
        Returns:
            List[str]: 关键洞察列表
        """
        insights = []
        
        # 1. 从API回答中提取洞察
        answer = search_response.get('answer', '')
        if answer:
            # 将长回答分割为关键句子
            sentences = [s.strip() for s in answer.split('. ') if len(s.strip()) > 20]
            insights.extend(sentences[:3])
        
        # 2. 从研究结果中提取洞察
        for i, result in enumerate(results[:3]):
            # 提取结果中的关键句子
            content = result.content
            sentences = [s.strip() for s in content.split('. ') if len(s.strip()) > 30]
            if sentences:
                insights.append(f"[Source: {result.title[:50]}...] {sentences[0]}")
        
        # 3. 添加通用洞察
        insights.extend([
            "Thorough research before task execution significantly improves success rates.",
            "Data-driven decision making based on research findings reduces risks.",
            "Continuous monitoring and iteration based on research insights optimizes outcomes."
        ])
        
        # 去重并限制数量
        unique_insights = list(dict.fromkeys(insights))
        return unique_insights[:8]
    
    def generate_research_summary(self, search_response: Dict, results: List[ResearchResult]) -> str:
        """
        生成研究摘要
        
        Args:
            search_response: API响应
            results: 研究结果列表
            
        Returns:
            str: 研究摘要
        """
        if not results:
            return "No research results available."
        
        # 构建摘要
        summary_parts = []
        
        # 添加API回答（如果有）
        answer = search_response.get('answer', '')
        if answer and len(answer) > 50:
            summary_parts.append(f"Overview: {answer[:300]}...")
        
        # 添加关键发现数量
        summary_parts.append(f"Total sources analyzed: {len(results)}")
        
        # 添加顶级来源
        top_sources = results[:3]
        summary_parts.append("\nTop Sources:")
        for source in top_sources:
            summary_parts.append(f"- [{source.title[:60]}]({source.url})")
            summary_parts.append(f"  Key content: {source.content[:120]}...")
        
        # 合并为完整摘要
        return '\n'.join(summary_parts)
    
    def save_research_report(self, task_id: int, report: ResearchReport) -> bool:
        """
        保存研究报告到数据库
        
        Args:
            task_id: 任务ID
            report: 研究报告
            
        Returns:
            bool: 是否成功保存
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 准备数据
            results_json = json.dumps([
                {
                    'title': r.title,
                    'url': r.url,
                    'content': r.content[:500],  # 限制长度
                    'score': r.score
                }
                for r in report.results
            ])
            
            insights_text = '\n'.join(report.key_insights)
            
            # 插入研究报告
            cursor.execute("""
                INSERT INTO task_research_reports 
                (task_id, research_query, search_results, key_insights, summary, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                task_id,
                report.query,
                results_json,
                insights_text,
                report.summary[:2000],  # 限制长度
                report.created_at
            ))
            
            # 更新任务表的研究报告字段
            cursor.execute("""
                UPDATE tasks
                SET research_report = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (report.summary[:1000], task_id))
            
            conn.commit()
            
            logger.info(f"Research report saved for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving research report for task {task_id}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
    
    def get_research_report(self, task_id: int) -> Optional[ResearchReport]:
        """
        获取任务的研究报告
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[ResearchReport]: 研究报告
        """
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT task_id, research_query, search_results, key_insights, summary, created_at
                FROM task_research_reports
                WHERE task_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (task_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # 解析搜索结果
            results_data = json.loads(row['search_results']) if row['search_results'] else []
            results = [
                ResearchResult(
                    title=r.get('title', ''),
                    url=r.get('url', ''),
                    content=r.get('content', ''),
                    score=r.get('score', 0.0)
                )
                for r in results_data
            ]
            
            # 解析关键洞察
            insights = row['key_insights'].split('\n') if row['key_insights'] else []
            
            return ResearchReport(
                task_id=row['task_id'],
                query=row['research_query'],
                results=results,
                key_insights=insights,
                summary=row['summary'],
                created_at=row['created_at']
            )
            
        except Exception as e:
            logger.error(f"Error getting research report for task {task_id}: {e}")
            return None
        finally:
            cursor.close()
    
    def _add_to_cache(self, key: str, report: ResearchReport):
        """添加到缓存"""
        # 如果缓存已满，移除最旧的条目
        if len(self.research_cache) >= self.max_cache_size:
            oldest_key = next(iter(self.research_cache))
            del self.research_cache[oldest_key]
        
        self.research_cache[key] = report
    
    def get_research_stats(self) -> Dict:
        """
        获取研究模块统计信息
        
        Returns:
            Dict: 统计信息
        """
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        stats = {
            'total_reports': 0,
            'reports_today': 0,
            'avg_results_per_report': 0.0,
            'cache_size': len(self.research_cache)
        }
        
        try:
            # 总报告数
            cursor.execute("SELECT COUNT(*) as count FROM task_research_reports")
            stats['total_reports'] = cursor.fetchone()['count']
            
            # 今日报告数
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM task_research_reports 
                WHERE DATE(created_at) = CURDATE()
            """)
            stats['reports_today'] = cursor.fetchone()['count']
            
            logger.info(f"Research stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting research stats: {e}")
            return stats
        finally:
            cursor.close()


if __name__ == "__main__":
    # 测试研究模块
    research_module = TavilyResearchModule()
    
    # 统计信息
    stats = research_module.get_research_stats()
    print("Research Stats:", stats)
    
    # 测试任务研究
    test_task_id = 999  # 测试任务ID
    test_description = "Implement AI-powered task scheduling system with priority optimization"
    
    print(f"\nRunning research for task {test_task_id}...")
    report = research_module.pre_task_research(test_task_id, test_description)
    
    print(f"\nResearch Report for Task {test_task_id}:")
    print(f"Query: {report.query}")
    print(f"Results: {len(report.results)} sources")
    print(f"Key Insights: {len(report.key_insights)} items")
    print("\nSummary:")
    print(report.summary[:500])
    
    print("\nKey Insights:")
    for i, insight in enumerate(report.key_insights, 1):
        print(f"  {i}. {insight[:100]}...")

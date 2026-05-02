#!/usr/bin/env python3
"""
Reports 去重引擎
功能：
1. 扫描 reports/ 目录已有报告
2. 提取报告主题、关键词
3. 生成任务前检查是否已有类似报告
4. 避免重复生成"融资策略"、"市场调研"等任务

作者: SDS v4.6
创建: 2026-04-30
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger('ReportsDedup')

# 常量
REPORTS_DIR = Path.home() / '.openclaw' / 'workspace' / 'reports'
OUTPUT_DIR = Path.home() / '.openclaw' / 'workspace' / 'data' / 'reports-index'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 常见重复主题映射
DEDUP_TOPIC_MAP = {
    '融资': ['融资', '估值', 'BP', '投资人', 'FA', '轮次', 'fundraising', 'valuation', 'investor'],
    '市场调研': ['市场调研', '竞品', '市场分析', '行业研究', 'market', 'competitor', 'research'],
    '战略规划': ['战略', '规划', '路线图', 'roadmap', 'strategy', 'planning'],
    '法律': ['法律', '诉讼', '合同', '协议', '法务', 'legal', 'contract', 'lawsuit'],
    '健康': ['健康', '体检', '睡眠', '运动', '心血管', 'health', 'sleep', 'exercise'],
    '教育': ['教育', '选课', '学校', 'GPA', '升学', 'education', 'course'],
    '财务': ['财务', '资产', '投资', '股票', '基金', 'finance', 'asset', 'investment'],
    '学术': ['学术', '论文', '引用', '影响因子', '期刊', 'academic', 'paper', 'citation'],
    '专利': ['专利', '知识产权', 'patent', 'IP', 'intellectual'],
    '产品': ['产品', '开发', '上线', '迭代', 'product', 'development'],
}


class ReportInfo:
    """报告信息"""
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filename = filepath.name
        self.title = self._extract_title()
        self.topics = self._extract_topics()
        self.date = self._extract_date()
        self.summary = self._extract_summary()
    
    def _extract_title(self) -> str:
        """从文件名提取标题"""
        # 去掉日期前缀和扩展名
        name = self.filename
        name = re.sub(r'\.md$', '', name)
        name = re.sub(r'\d{8}[-_]?', '', name)
        name = re.sub(r'^task[-_]', '', name)
        name = name.replace('_', ' ').replace('-', ' ')
        return name.strip()
    
    def _extract_topics(self) -> List[str]:
        """提取报告主题"""
        text = self.title.lower()
        topics = []
        for topic, keywords in DEDUP_TOPIC_MAP.items():
            if any(kw in text for kw in keywords):
                topics.append(topic)
        return topics
    
    def _extract_date(self) -> Optional[str]:
        """从文件名提取日期"""
        match = re.search(r'(\d{4})(\d{2})(\d{2})', self.filename)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        return None
    
    def _extract_summary(self) -> str:
        """提取报告内容摘要（前300字）"""
        if self.filepath.suffix == '.md':
            try:
                with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1000)
                    return content[:300]
            except Exception:
                pass
        return ''
    
    def to_dict(self) -> Dict:
        return {
            'filename': self.filename,
            'title': self.title,
            'topics': self.topics,
            'date': self.date,
            'summary': self.summary,
        }


class ReportsDedupEngine:
    """报告去重引擎"""
    
    def __init__(self):
        self.reports: List[ReportInfo] = []
        self.topic_index: Dict[str, List[str]] = {}  # topic -> [filenames]
        self._load_reports()
    
    def _load_reports(self):
        """加载所有报告"""
        if not REPORTS_DIR.exists():
            return
        
        for item in REPORTS_DIR.iterdir():
            if item.is_file() and item.suffix in ['.md', '.txt', '.pdf']:
                try:
                    report = ReportInfo(item)
                    self.reports.append(report)
                    
                    # 建立主题索引
                    for topic in report.topics:
                        if topic not in self.topic_index:
                            self.topic_index[topic] = []
                        self.topic_index[topic].append(report.filename)
                
                except Exception as e:
                    logger.warning(f"加载报告失败 {item}: {e}")
        
        logger.info(f"加载报告: {len(self.reports)} 个")
    
    def check_duplicate(self, task_title: str, task_description: str = '') -> Optional[Dict]:
        """检查任务是否已有类似报告
        
        Returns:
            如果找到相似报告，返回报告信息；否则返回 None
        """
        text = (task_title + ' ' + task_description).lower()
        
        # 提取任务主题
        task_topics = []
        for topic, keywords in DEDUP_TOPIC_MAP.items():
            if any(kw in text for kw in keywords):
                task_topics.append(topic)
        
        if not task_topics:
            return None
        
        # 查找匹配的报告
        matched_reports = []
        for topic in task_topics:
            for filename in self.topic_index.get(topic, []):
                for report in self.reports:
                    if report.filename == filename:
                        matched_reports.append(report)
                        break
        
        if not matched_reports:
            return None
        
        # 返回最新的匹配报告
        matched_reports.sort(key=lambda r: r.date or '0000-00-00', reverse=True)
        latest = matched_reports[0]
        
        return {
            'is_duplicate': True,
            'matched_topic': task_topics[0],
            'existing_report': latest.to_dict(),
            'suggestion': f"已存在相关报告《{latest.title}》（{latest.date or '日期未知'}），建议查看现有报告后再决定是否需要更新。",
        }
    
    def get_recent_reports_by_topic(self, topic: str, days: int = 30) -> List[Dict]:
        """获取指定主题最近N天的报告"""
        results = []
        cutoff = datetime.now().timestamp() - days * 86400
        
        for report in self.reports:
            if topic in report.topics:
                # 检查文件修改时间
                try:
                    mtime = report.filepath.stat().st_mtime
                    if mtime >= cutoff:
                        results.append(report.to_dict())
                except Exception:
                    pass
        
        return results
    
    def save_index(self):
        """保存去重索引"""
        data = {
            'total_reports': len(self.reports),
            'topic_distribution': {k: len(v) for k, v in self.topic_index.items()},
            'reports': [r.to_dict() for r in self.reports],
        }
        
        index_file = OUTPUT_DIR / 'reports_index.json'
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"去重索引已保存: {index_file}")
    
    def generate_dedup_prompt(self, task_title: str, task_description: str = '') -> str:
        """生成去重提示（供任务生成器使用）"""
        result = self.check_duplicate(task_title, task_description)
        
        if result:
            return f"""
⚠️ **重复任务警告**

检测到已存在相关报告：
- 报告名称: {result['existing_report']['title']}
- 报告日期: {result['existing_report']['date'] or '未知'}
- 匹配主题: {result['matched_topic']}

建议:
1. 先查看现有报告内容
2. 如果需要更新，生成"更新/修订"类任务而非全新任务
3. 如果已有报告完全满足需求，跳过此任务

现有报告摘要:
{result['existing_report']['summary'][:150]}...
"""
        return ""


# 全局实例
_dedup_instance = None

def get_dedup_engine() -> ReportsDedupEngine:
    """获取去重引擎单例"""
    global _dedup_instance
    if _dedup_instance is None:
        _dedup_instance = ReportsDedupEngine()
    return _dedup_instance


def check_task_duplicate(task_title: str, task_description: str = '') -> Optional[Dict]:
    """全局接口：检查任务是否重复"""
    engine = get_dedup_engine()
    return engine.check_duplicate(task_title, task_description)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    engine = ReportsDedupEngine()
    engine.save_index()
    
    # 测试
    print("\n=== 测试: 融资任务 ===")
    result = engine.check_duplicate("和光智成Pre-A轮融资策略制定")
    if result:
        print(f"  ⚠️ 发现重复: {result['existing_report']['title']}")
    else:
        print("  ✅ 无重复")

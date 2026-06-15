#!/usr/bin/env python3
"""
Memory 学习循环模块
功能：
1. 读取 memory/ 目录下的历史日志
2. 提取关键决策、修复记录、教训
3. 生成知识条目写入 knowledge-index
4. SDS 生成任务时参考历史教训避免重复错误

作者: SDS v4.6
创建: 2026-04-30
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('MemoryLearner')

# 常量
MEMORY_DIR = Path.home() / '.openclaw' / 'workspace' / 'memory'
KNOWLEDGE_INDEX_DIR = Path.home() / '.openclaw' / 'workspace' / 'data' / 'knowledge-index'
LEARNED_LESSONS_FILE = Path.home() / '.openclaw' / 'workspace' / 'data' / 'learned_lessons.json'

# 关键模式（用于提取教训）
LESSON_PATTERNS = [
    r'(?:修复|解决|处理).{0,30}(?:问题|错误|bug|故障)',
    r'(?:根因|原因).{0,50}(?:是|为|由于)',
    r'(?:教训|经验|总结).{0,30}(?:：|:)',
    r'(?:注意|警告|⚠️|❌).{0,50}',
    r'(?:关键|核心).{0,20}(?:发现|决策|改变)',
    r'(?:建议|推荐).{0,30}(?:：|:)',
    r'(?:成功|失败).{0,20}(?:原因|因素)',
    r'(?:避免|防止).{0,30}(?:问题|错误)',
    r'(?:优化|改进|提升).{0,30}(?:方案|措施)',
]

# 技术相关关键词
TECH_KEYWORDS = [
    'RDS', '数据库', '连接', '2013', 'timeout', 'pool',
    'Python', 'SQL', '索引', '查询', '性能',
    'API', '密钥', '配置', '环境变量',
    '部署', '服务', '进程', 'cron', '监控',
    '内存', '磁盘', 'CPU', '网络',
    '修复', 'bug', '错误', '异常', '故障',
    '模板', '子代理', '任务', '调度',
]


class Lesson:
    """学习到的教训"""
    def __init__(self, source_file: str, date: str, content: str, category: str = 'general'):
        self.source_file = source_file
        self.date = date
        self.content = content
        self.category = category
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'source_file': self.source_file,
            'date': self.date,
            'content': self.content,
            'category': self.category,
            'timestamp': self.timestamp,
        }


class MemoryLearner:
    """Memory 学习器"""
    
    def __init__(self):
        self.lessons: List[Lesson] = []
        self._load_existing_lessons()
    
    def _load_existing_lessons(self):
        """加载已学习的教训"""
        if LEARNED_LESSONS_FILE.exists():
            try:
                with open(LEARNED_LESSONS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data.get('lessons', []):
                        lesson = Lesson(
                            item['source_file'],
                            item['date'],
                            item['content'],
                            item.get('category', 'general')
                        )
                        self.lessons.append(lesson)
                logger.info(f"加载已有教训: {len(self.lessons)} 条")
            except Exception as e:
                logger.warning(f"加载教训失败: {e}")
    
    def _extract_date_from_filename(self, filename: str) -> str:
        """从文件名提取日期"""
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        return datetime.now().strftime('%Y-%m-%d')
    
    def _categorize_lesson(self, content: str) -> str:
        """分类教训"""
        content_lower = content.lower()
        
        if any(kw in content_lower for kw in ['数据库', 'RDS', 'SQL', '连接', '2013', 'pool']):
            return 'database'
        elif any(kw in content_lower for kw in ['API', '密钥', '配置', '环境变量', '.env']):
            return 'configuration'
        elif any(kw in content_lower for kw in ['部署', '服务', '进程', 'cron', '监控']):
            return 'infrastructure'
        elif any(kw in content_lower for kw in ['模板', '子代理', '任务', '调度', '执行']):
            return 'sds_execution'
        elif any(kw in content_lower for kw in ['修复', 'bug', '错误', '异常', '故障']):
            return 'debugging'
        elif any(kw in content_lower for kw in ['优化', '改进', '性能', '提速']):
            return 'optimization'
        else:
            return 'general'
    
    def parse_memory_file(self, filepath: Path) -> List[Lesson]:
        """解析单个 memory 文件"""
        lessons = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"读取文件失败 {filepath}: {e}")
            return lessons
        
        date = self._extract_date_from_filename(filepath.name)
        
        # 按段落分割
        paragraphs = content.split('\n\n')
        
        for para in paragraphs:
            para = para.strip()
            if len(para) < 20 or len(para) > 500:
                continue
            
            # 检查是否匹配教训模式
            is_lesson = False
            for pattern in LESSON_PATTERNS:
                if re.search(pattern, para):
                    is_lesson = True
                    break
            
            # 检查是否包含技术关键词
            has_tech = any(kw.lower() in para.lower() for kw in TECH_KEYWORDS)
            
            if is_lesson or (has_tech and ('问题' in para or '错误' in para or '修复' in para)):
                category = self._categorize_lesson(para)
                lesson = Lesson(
                    source_file=filepath.name,
                    date=date,
                    content=para,
                    category=category
                )
                lessons.append(lesson)
        
        return lessons
    
    def learn_from_memory(self, days: int = 7):
        """从最近的 memory 文件学习"""
        if not MEMORY_DIR.exists():
            logger.warning(f"Memory 目录不存在: {MEMORY_DIR}")
            return []
        
        cutoff = datetime.now() - timedelta(days=days)
        new_lessons = []
        
        for item in MEMORY_DIR.iterdir():
            if not item.is_file() or not item.suffix == '.md':
                continue
            
            # 检查文件修改时间
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime < cutoff:
                    continue
            except Exception:
                continue
            
            # 解析文件
            lessons = self.parse_memory_file(item)
            new_lessons.extend(lessons)
            logger.info(f"从 {item.name} 提取 {len(lessons)} 条教训")
        
        # 去重
        existing_contents = {l.content for l in self.lessons}
        unique_new = [l for l in new_lessons if l.content not in existing_contents]
        
        self.lessons.extend(unique_new)
        logger.info(f"新增 {len(unique_new)} 条教训（去重后）")
        
        return unique_new
    
    def save_lessons(self):
        """保存教训到文件"""
        data = {
            'total_lessons': len(self.lessons),
            'last_updated': datetime.now().isoformat(),
            'by_category': {},
            'lessons': [l.to_dict() for l in self.lessons],
        }
        
        # 按类别统计
        for lesson in self.lessons:
            cat = lesson.category
            if cat not in data['by_category']:
                data['by_category'][cat] = 0
            data['by_category'][cat] += 1
        
        with open(LEARNED_LESSONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"教训已保存: {LEARNED_LESSONS_FILE}")
    
    def get_relevant_lessons(self, task_title: str, task_description: str = '', limit: int = 3) -> List[Dict]:
        """获取与任务相关的历史教训"""
        text = (task_title + ' ' + task_description).lower()
        scored_lessons = []
        
        for lesson in self.lessons:
            score = 0
            
            # 类别匹配
            category_keywords = {
                'database': ['数据库', 'RDS', 'SQL', '连接', '查询', '存储'],
                'configuration': ['配置', '密钥', 'API', '环境变量', '设置'],
                'infrastructure': ['部署', '服务', '进程', '服务器', '监控'],
                'sds_execution': ['子代理', '任务', '执行', '模板', '调度'],
                'debugging': ['修复', '错误', 'bug', '异常', '调试'],
                'optimization': ['优化', '性能', '提速', '改进'],
            }
            
            if lesson.category in category_keywords:
                for kw in category_keywords[lesson.category]:
                    if kw in text:
                        score += 5
            
            # 内容关键词匹配
            lesson_text = lesson.content.lower()
            for word in text.split()[:10]:  # 只检查前10个词
                if len(word) > 2 and word in lesson_text:
                    score += 2
            
            if score > 0:
                scored_lessons.append({
                    **lesson.to_dict(),
                    'relevance_score': score
                })
        
        # 按分数排序
        scored_lessons.sort(key=lambda x: x['relevance_score'], reverse=True)
        return scored_lessons[:limit]
    
    def generate_lessons_prompt(self, task_title: str, task_description: str = '') -> str:
        """生成历史教训提示（供子代理使用）"""
        lessons = self.get_relevant_lessons(task_title, task_description)
        
        if not lessons:
            return ""
        
        prompt = "\n【历史教训参考】\n"
        prompt += "以下是与本任务相关的历史经验教训，执行时请特别注意：\n\n"
        
        for i, lesson in enumerate(lessons, 1):
            prompt += f"{i}. [{lesson['category']}] {lesson['date']}\n"
            prompt += f"   {lesson['content'][:200]}\n\n"
        
        prompt += "提示: 参考以上教训，避免重复之前的错误，采用已验证的最佳实践。\n"
        return prompt


# 全局实例
_learner_instance = None

def get_learner() -> MemoryLearner:
    """获取学习器单例"""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = MemoryLearner()
    return _learner_instance


def learn_from_recent_memory(days: int = 7) -> List[Dict]:
    """全局接口：从近期 memory 学习"""
    learner = get_learner()
    lessons = learner.learn_from_memory(days)
    learner.save_lessons()
    return [l.to_dict() for l in lessons]


def get_task_lessons(task_title: str, task_description: str = '') -> List[Dict]:
    """全局接口：获取任务相关的历史教训"""
    learner = get_learner()
    return learner.get_relevant_lessons(task_title, task_description)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    learner = MemoryLearner()
    
    # 测试学习
    new_lessons = learner.learn_from_memory(days=7)
    learner.save_lessons()
    
    # print(f"\n新增 {len(new_lessons)} 条教训")
    
    # 测试获取相关教训
    # print("\n=== 测试: 数据库任务 ===")
    lessons = learner.get_relevant_lessons("修复RDS连接超时问题")
    for l in lessons:
        # print(f"  - [{l['category']}] {l['content'][:80]}...")

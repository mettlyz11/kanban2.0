#!/usr/bin/env python3
"""
SDS自动任务生成器 V4.3 (Auto Task Generator)
新增功能:
1. NLP任务相似度检测算法 - 降低重复率
2. 任务质量评分模型 - 完整性、可执行性、战略匹配度
3. 任务失败自动回退与重试机制
4. 优化Research查询生成策略 - 多轮验证
"""

import os
import sys
import re
import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import Counter

# 添加lib路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lib.db_connector import get_db_connection, execute_query, execute_update

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/Users/mettlyz/.openclaw/workspace/logs/sds-task-generator-v43.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TaskGeneratorV43')


class TaskSimilarityDetector:
    """任务相似度检测器 - 使用NLP语义匹配"""
    
    def __init__(self):
        # 关键词权重配置
        self.keyword_weights = {
            '研究': 3.0, '分析': 2.5, '开发': 3.0, '实现': 3.0,
            '优化': 2.5, '升级': 2.5, '维护': 2.0, '监控': 2.0,
            '测试': 2.0, '验证': 2.0, '报告': 1.5, '文档': 1.5,
            '系统': 2.0, '项目': 2.0, '任务': 1.0, '数据': 2.0,
            '质量': 2.0, '性能': 2.0, '安全': 2.5, '风险': 2.0,
            '战略': 3.0, '目标': 2.5, '计划': 2.0, '执行': 2.0,
            'AI': 3.0, '模型': 2.5, '算法': 2.5, '学习': 2.5,
            '学术': 2.5, '论文': 2.0, '专利': 2.5, '商业': 2.5
        }
        self.stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        
    def tokenize(self, text: str) -> List[str]:
        """简单中文分词"""
        if not text:
            return []
        # 提取中文字符和英文单词
        tokens = []
        # 英文单词
        for match in re.finditer(r'[a-zA-Z]{2,}', text):
            tokens.append(match.group().lower())
        # 中文2-4字词
        for match in re.finditer(r'[\u4e00-\u9fa5]{2,4}', text):
            tokens.append(match.group())
        return [t for t in tokens if t not in self.stop_words]
    
    def extract_keywords(self, text: str) -> Dict[str, float]:
        """提取关键词及其权重"""
        tokens = self.tokenize(text)
        if not tokens:
            return {}
        
        # TF计算
        tf = Counter(tokens)
        max_freq = max(tf.values()) if tf else 1
        
        keywords = {}
        for token, freq in tf.items():
            weight = self.keyword_weights.get(token, 1.0)
            # TF * 自定义权重
            keywords[token] = (freq / max_freq) * weight
        
        return keywords
    
    def cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """余弦相似度计算"""
        if not vec1 or not vec2:
            return 0.0
        
        all_keys = set(vec1.keys()) | set(vec2.keys())
        if not all_keys:
            return 0.0
        
        # 点积
        dot_product = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in all_keys)
        
        # 模长
        norm1 = sum(v * v for v in vec1.values()) ** 0.5
        norm2 = sum(v * v for v in vec2.values()) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def jaccard_similarity(self, set1: set, set2: set) -> float:
        """Jaccard相似度"""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0
    
    def title_hash(self, title: str) -> str:
        """计算标题哈希值"""
        # 规范化标题（去标点、转小写）
        normalized = re.sub(r'[^\w\s\u4e00-\u9fa5]', '', title.lower())
        normalized = re.sub(r'\s+', '', normalized)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def calculate_similarity(self, task1: Dict, task2: Dict) -> Dict:
        """计算两个任务的相似度"""
        title1 = task1.get('title', '')
        title2 = task2.get('title', '')
        desc1 = task1.get('description', '') or ''
        desc2 = task2.get('description', '') or ''
        
        # 标题相似度（高权重）
        title_keywords1 = self.extract_keywords(title1)
        title_keywords2 = self.extract_keywords(title2)
        title_sim = self.cosine_similarity(title_keywords1, title_keywords2)
        
        # 描述相似度（中等权重）
        desc_keywords1 = self.extract_keywords(desc1)
        desc_keywords2 = self.extract_keywords(desc2)
        desc_sim = self.cosine_similarity(desc_keywords1, desc_keywords2)
        
        # 关键词集合相似度
        keywords1 = set(title_keywords1.keys()) | set(desc_keywords1.keys())
        keywords2 = set(title_keywords2.keys()) | set(desc_keywords2.keys())
        jaccard_sim = self.jaccard_similarity(keywords1, keywords2)
        
        # 综合相似度
        composite_sim = title_sim * 0.5 + desc_sim * 0.3 + jaccard_sim * 0.2
        
        return {
            'title_similarity': round(title_sim, 3),
            'description_similarity': round(desc_sim, 3),
            'jaccard_similarity': round(jaccard_sim, 3),
            'composite_similarity': round(composite_sim, 3),
            'is_duplicate': composite_sim > 0.75,
            'is_similar': composite_sim > 0.55,
            'common_keywords': list(keywords1 & keywords2)[:10]
        }
    
    def find_similar_tasks(self, new_task: Dict, existing_tasks: List[Dict], 
                           threshold: float = 0.55) -> List[Dict]:
        """查找与新任务相似的历史任务"""
        similar = []
        for existing in existing_tasks:
            sim_result = self.calculate_similarity(new_task, existing)
            if sim_result['composite_similarity'] >= threshold:
                similar.append({
                    'task_id': existing.get('id'),
                    'title': existing.get('title', ''),
                    'similarity': sim_result['composite_similarity'],
                    'is_duplicate': sim_result['is_duplicate'],
                    'common_keywords': sim_result['common_keywords']
                })
        
        return sorted(similar, key=lambda x: x['similarity'], reverse=True)


class TaskQualityScorer:
    """任务质量评分模型 - V4.3 新增"""
    
    def __init__(self):
        # 评分维度权重
        self.dimensions = {
            'completeness': 0.35,      # 完整性
            'executability': 0.35,     # 可执行性
            'strategic_alignment': 0.30 # 战略匹配度
        }
        
        # 战略关键词（与刘宇宙教授业务相关）
        self.strategic_keywords = {
            '和光智成': 5.0, 'AI材料': 4.0, '学术': 3.0, '论文': 3.0,
            '专利': 4.0, '商业化': 4.0, '融资': 4.0, '战略': 5.0,
            '深云智合': 4.0, '硅研新材': 4.0, '北航': 3.0, '化学': 3.0,
            'SDS': 3.0, '自我驱动': 3.0, '看板': 2.0, '任务': 1.0,
            '研发': 3.0, '产品': 3.0, '市场': 3.0, '销售': 3.0
        }
    
    def score_completeness(self, task: Dict) -> Tuple[float, List[str]]:
        """评估任务完整性"""
        score = 0.0
        feedback = []
        
        title = task.get('title', '') or ''
        desc = task.get('description', '') or ''
        
        # 标题长度 (15分)
        title_len = len(title)
        if title_len >= 20:
            score += 15
        elif title_len >= 10:
            score += 10
        else:
            score += 5
            feedback.append(f'标题偏短 ({title_len}字)，建议更具体')
        
        # 描述长度 (25分)
        desc_len = len(desc)
        if desc_len >= 200:
            score += 25
        elif desc_len >= 100:
            score += 20
        elif desc_len >= 50:
            score += 15
        else:
            score += 5
            feedback.append(f'描述过短 ({desc_len}字)，建议增加执行要点')
        
        # 验收标准完整性 (30分)
        has_acceptance = False
        acceptance_keywords = ['验收', '标准', '完成', '要求', '满足', '条件']
        for keyword in acceptance_keywords:
            if keyword in desc or keyword in title:
                has_acceptance = True
                break
        if has_acceptance:
            score += 30
        else:
            feedback.append('缺少明确的验收标准')
        
        # 执行要点明确性 (30分)
        has_exec_points = False
        exec_keywords = ['要点', '步骤', '执行', '操作', '流程', '方法']
        for keyword in exec_keywords:
            if keyword in desc or keyword in title:
                has_exec_points = True
                break
        if has_exec_points:
            score += 30
        else:
            feedback.append('缺少具体的执行要点')
        
        return score / 100, feedback
    
    def score_executability(self, task: Dict) -> Tuple[float, List[str]]:
        """评估任务可执行性"""
        score = 0.0
        feedback = []
        
        desc = task.get('description', '') or ''
        title = task.get('title', '') or ''
        combined = title + ' ' + desc
        
        # 具体行动动词 (25分)
        action_verbs = ['分析', '开发', '实现', '优化', '研究', '测试', 
                        '验证', '撰写', '设计', '构建', '部署', '监控']
        action_count = sum(1 for v in action_verbs if v in combined)
        if action_count >= 3:
            score += 25
        elif action_count >= 1:
            score += 15 + action_count * 3
        else:
            score += 5
            feedback.append('缺少具体行动动词')
        
        # 量化指标 (30分)
        has_quantitative = bool(re.search(r'\d+%|\d+个|\d+条|\d+字|\d+项', combined))
        if has_quantitative:
            score += 30
        else:
            feedback.append('缺少量化指标')
        
        # 时间/资源明确性 (20分)
        time_indicators = ['小时', '天', '周', '月', '日', '截至', '之前']
        has_time = any(t in combined for t in time_indicators)
        if has_time:
            score += 20
        else:
            score += 10
        
        # 依赖关系清晰 (25分)
        dependency_indicators = ['需要', '依赖', '基于', '使用', '工具', '方法']
        dep_count = sum(1 for d in dependency_indicators if d in combined)
        if dep_count >= 2:
            score += 25
        elif dep_count >= 1:
            score += 20
        else:
            score += 15
        
        return score / 100, feedback
    
    def score_strategic_alignment(self, task: Dict) -> Tuple[float, List[str]]:
        """评估任务战略匹配度"""
        score = 0.0
        feedback = []
        
        desc = task.get('description', '') or ''
        title = task.get('title', '') or ''
        combined = title + ' ' + desc
        
        # 战略关键词匹配 (60分)
        keyword_score = 0
        matched_keywords = []
        for keyword, weight in self.strategic_keywords.items():
            if keyword in combined:
                keyword_score += weight
                matched_keywords.append(keyword)
        
        if keyword_score >= 10:
            score += 60
        elif keyword_score >= 5:
            score += 40 + keyword_score * 2
        elif keyword_score > 0:
            score += 30 + keyword_score * 2
        else:
            score += 10
            feedback.append('战略相关性较低')
        
        # 优先级设置 (20分)
        priority = task.get('priority')
        if isinstance(priority, int) and priority >= 1:
            score += 20
        else:
            score += 10
        
        # 项目归属明确 (20分)
        project_id = task.get('project_id')
        if project_id:
            score += 20
        else:
            score += 10
            feedback.append('未明确项目归属')
        
        return score / 100, feedback
    
    def score_task(self, task: Dict) -> Dict:
        """综合评分"""
        completeness_score, completeness_feedback = self.score_completeness(task)
        executability_score, executability_feedback = self.score_executability(task)
        strategic_score, strategic_feedback = self.score_strategic_alignment(task)
        
        # 加权总分
        total_score = (
            completeness_score * self.dimensions['completeness'] +
            executability_score * self.dimensions['executability'] +
            strategic_score * self.dimensions['strategic_alignment']
        )
        
        return {
            'total_score': round(total_score, 3),
            'completeness': round(completeness_score, 3),
            'executability': round(executability_score, 3),
            'strategic_alignment': round(strategic_score, 3),
            'letter_grade': self.get_letter_grade(total_score),
            'pass_threshold': total_score >= 0.70,
            'feedback': {
                'completeness': completeness_feedback,
                'executability': executability_feedback,
                'strategic_alignment': strategic_feedback
            }
        }
    
    def get_letter_grade(self, score: float) -> str:
        """转换为字母等级"""
        if score >= 0.90:
            return 'A'
        elif score >= 0.80:
            return 'B'
        elif score >= 0.70:
            return 'C'
        elif score >= 0.60:
            return 'D'
        else:
            return 'F'


class TaskRetryManager:
    """任务重试管理器 - 失败自动回退与重试机制"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.retry_backoff = [1, 2, 4]  # 小时
    
    def get_retry_history(self, task_id: int) -> List[Dict]:
        """获取任务重试历史"""
        sql = """
            SELECT id, retry_count, last_retry_at, retry_reason, status
            FROM task_retries
            WHERE task_id = %s
            ORDER BY retry_count
        """
        return execute_query(sql, (task_id,))
    
    def can_retry(self, task_id: int) -> bool:
        """检查任务是否可以重试"""
        history = self.get_retry_history(task_id)
        if len(history) >= self.max_retries:
            return False
        
        if history:
            last_retry = history[-1]
            last_time = last_retry.get('last_retry_at')
            if last_time:
                # 检查退避时间
                retry_idx = min(len(history), len(self.retry_backoff) - 1)
                backoff_hours = self.retry_backoff[retry_idx]
                hours_since = (datetime.now() - last_time).total_seconds() / 3600
                if hours_since < backoff_hours:
                    return False
        
        return True
    
    def register_retry(self, task_id: int, reason: str) -> bool:
        """注册任务重试"""
        if not self.can_retry(task_id):
            return False
        
        history = self.get_retry_history(task_id)
        retry_count = len(history) + 1
        
        sql = """
            INSERT INTO task_retries 
            (task_id, retry_count, last_retry_at, retry_reason, status, created_at)
            VALUES (%s, %s, NOW(), %s, 'pending', NOW())
        """
        
        try:
            execute_update(sql, (task_id, retry_count, reason))
            logger.info(f"任务 #{task_id} 已注册第 {retry_count} 次重试: {reason}")
            return True
        except Exception as e:
            logger.error(f"注册重试失败: {e}")
            return False
    
    def analyze_failure_reason(self, task_id: int) -> str:
        """分析失败原因并生成重试策略"""
        sql = """
            SELECT execution_log, result_summary
            FROM tasks WHERE id = %s
        """
        result = execute_query(sql, (task_id,))
        
        if not result:
            return "未知原因"
        
        task = result[0]
        log = (task.get('execution_log') or '') + ' ' + (task.get('result_summary') or '')
        
        # 失败原因分类
        if any(k in log for k in ['超时', 'timeout', '连接', 'connection', '网络']):
            return "资源/网络问题 - 建议重试"
        elif any(k in log for k in ['参数', '配置', '格式', '语法']):
            return "配置问题 - 建议修正参数后重试"
        elif any(k in log for k in ['权限', '认证', '授权']):
            return "权限问题 - 需要人工介入"
        else:
            return "执行错误 - 建议检查逻辑后重试"


class ResearchQueryOptimizer:
    """Research查询优化器 - 多轮验证策略"""
    
    def __init__(self):
        self.validation_rounds = 3
    
    def generate_queries(self, topic: str, domain: str = 'general') -> List[Dict]:
        """生成多层级查询策略"""
        queries = []
        
        # 基础查询
        base_queries = self._generate_base_queries(topic, domain)
        for i, q in enumerate(base_queries):
            queries.append({
                'query': q,
                'round': 1,
                'type': 'exploratory',
                'priority': 'high' if i == 0 else 'medium'
            })
        
        # 深度查询（基于初步结果）
        deep_queries = self._generate_deep_queries(topic, domain)
        for q in deep_queries:
            queries.append({
                'query': q,
                'round': 2,
                'type': 'deep_dive',
                'priority': 'medium'
            })
        
        # 验证查询
        validation_queries = self._generate_validation_queries(topic)
        for q in validation_queries:
            queries.append({
                'query': q,
                'round': 3,
                'type': 'validation',
                'priority': 'low'
            })
        
        return queries
    
    def _generate_base_queries(self, topic: str, domain: str) -> List[str]:
        """生成基础探索性查询"""
        return [
            f"{topic} 最新研究进展",
            f"{topic} 行业报告 2025",
            f"{topic} 技术挑战 解决方案",
            f"{topic} 商业化案例"
        ]
    
    def _generate_deep_queries(self, topic: str, domain: str) -> List[str]:
        """生成深度查询"""
        return [
            f"{topic} 关键技术 实现细节",
            f"{topic} 性能优化 最佳实践",
            f"{topic} 未来趋势 专家预测"
        ]
    
    def _generate_validation_queries(self, topic: str) -> List[str]:
        """生成验证查询 - 交叉验证信息准确性"""
        return [
            f"{topic} 对比 替代方案",
            f"{topic} 缺点 局限性",
            f"{topic} 争议 讨论"
        ]
    
    def validate_results(self, results: List[Dict]) -> Dict:
        """验证查询结果质量"""
        validation = {
            'total_results': len(results),
            'diversity_score': 0.0,
            'conflict_detected': False,
            'confidence_score': 0.0
        }
        
        # 计算来源多样性
        sources = [r.get('source', 'unknown') for r in results]
        unique_sources = len(set(sources))
        validation['diversity_score'] = min(unique_sources / 5.0, 1.0)
        
        # 计算结果重叠度
        titles = [r.get('title', '') for r in results]
        if len(titles) > 1:
            # 简单标题相似度检测
            detector = TaskSimilarityDetector()
            sim_scores = []
            for i in range(len(titles)):
                for j in range(i + 1, len(titles)):
                    sim = detector.cosine_similarity(
                        detector.extract_keywords(titles[i]),
                        detector.extract_keywords(titles[j])
                    )
                    sim_scores.append(sim)
            if sim_scores:
                avg_sim = sum(sim_scores) / len(sim_scores)
                validation['confidence_score'] = 1.0 - avg_sim * 0.5
        
        return validation


class AutoTaskGeneratorV43:
    """自动任务生成器 V4.3 - 增强版"""
    
    def __init__(self):
        self.conn = None
        self.similarity_detector = TaskSimilarityDetector()
        self.quality_scorer = TaskQualityScorer()
        self.retry_manager = TaskRetryManager()
        self.research_optimizer = ResearchQueryOptimizer()
        
        # 任务模板库
        self.task_templates = {
            'system_maintenance': {
                'priority_mapping': {'high': 3, 'medium': 2, 'low': 1},
                'default_description': """
【执行要点】
1. 仔细分析当前系统状态
2. 按照优先级执行必要的维护操作
3. 记录所有变更和执行结果
4. 验证维护效果

【验收标准】
- execution_log ≥ 200字，详细记录执行过程
- result_summary ≥ 50字，总结核心成果
- 产出文件已保存并上传到附件
                """.strip()
            },
            'project_gap_filler': {
                'priority_mapping': {'high': 3, 'medium': 2, 'low': 1},
                'default_description': """
【执行要点】
1. 分析项目当前状态和目标
2. 拆解为具体可执行的子任务
3. 为每个子任务设置明确的验收标准
4. 创建任务并关联到对应项目

【验收标准】
- 至少创建3个具体的执行任务
- 每个任务都有明确的完成标准
- 任务优先级和依赖关系清晰
                """.strip()
            },
            'knowledge_maintenance': {
                'priority_mapping': {'high': 3, 'medium': 2, 'low': 1},
                'default_description': """
【执行要点】
1. 梳理近期执行的任务成果
2. 提取关键决策、经验教训、最佳实践
3. 更新对应领域的知识库文档
4. 整理归档重要执行记录

【验收标准】
- 至少更新1个核心知识文档
- 提炼至少3条关键经验
- 产出文件已保存并上传
                """.strip()
            },
            'system_health_check': {
                'priority_mapping': {'high': 3, 'medium': 2, 'low': 1},
                'default_description': """
【执行要点】
1. 检查所有SDS组件运行日志
2. 验证数据库连接和查询性能
3. 清理过期日志和临时文件
4. 检查磁盘空间和系统资源
5. 优化系统配置参数

【验收标准】
- 完整的健康检查报告
- 所有异常已处理或记录
- 系统资源利用率正常
                """.strip()
            },
            'academic_research': {
                'priority_mapping': {'high': 3, 'medium': 2, 'low': 1},
                'default_description': """
【执行要点】
1. 确定研究主题和关键词
2. 使用学术搜索工具获取最新文献
3. 分析研究热点和趋势
4. 生成研究报告或综述

【验收标准】
- 至少检索20篇相关文献
- 完整的研究分析报告
- 关键发现和建议清晰
                """.strip()
            }
        }
    
    def connect(self):
        """连接数据库"""
        try:
            self.conn = get_db_connection()
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
    
    def get_recent_tasks(self, days: int = 30) -> List[Dict]:
        """获取最近生成的任务（用于相似度检测）"""
        sql = f"""
            SELECT id, title, description, status, created_at
            FROM tasks
            WHERE created_at >= NOW() - INTERVAL {days} DAY
            ORDER BY created_at DESC
        """
        return execute_query(sql)
    
    def filter_duplicate_tasks(self, recommendations: List[Dict]) -> List[Dict]:
        """过滤重复和相似任务"""
        recent_tasks = self.get_recent_tasks(days=30)
        filtered = []
        duplicates = []
        
        for rec in recommendations:
            similar = self.similarity_detector.find_similar_tasks(rec, recent_tasks, threshold=0.75)
            
            if similar:
                duplicates.append({
                    'task': rec,
                    'similar_to': similar[:3]
                })
                logger.warning(f"检测到重复任务: {rec['title'][:50]}... 相似于 #{similar[0]['task_id']}")
            else:
                filtered.append(rec)
        
        logger.info(f"去重结果: 输入 {len(recommendations)}, 保留 {len(filtered)}, 过滤 {len(duplicates)}")
        return filtered
    
    def quality_filter_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """质量评分过滤任务"""
        scored_tasks = []
        
        for task in tasks:
            quality = self.quality_scorer.score_task(task)
            task['quality_score'] = quality
            
            if quality['pass_threshold']:
                scored_tasks.append(task)
                logger.info(f"任务通过质量检查: {task['title'][:50]}... 分数={quality['total_score']} ({quality['letter_grade']})")
            else:
                logger.warning(f"任务未通过质量检查: {task['title'][:50]}... 分数={quality['total_score']}")
                # 打印改进建议
                for dim, feedback in quality['feedback'].items():
                    if feedback:
                        logger.warning(f"  {dim}: {'; '.join(feedback)}")
        
        # 按质量分数排序
        scored_tasks.sort(key=lambda x: x['quality_score']['total_score'], reverse=True)
        return scored_tasks
    
    def create_task(self, task_data: Dict) -> Optional[int]:
        """创建单个看板任务"""
        try:
            template_type = task_data.get('task_type', 'system_maintenance')
            template = self.task_templates.get(template_type, self.task_templates['system_maintenance'])
            
            # 构建完整描述
            description = task_data.get('description', '') + "\n\n" + template['default_description']
            
            # 获取优先级
            priority = template['priority_mapping'].get(
                task_data.get('priority', 'medium'),
                2
            )
            
            # 获取项目ID
            project_id = task_data.get('project_id')
            if not project_id:
                # 查找默认项目
                results = execute_query(
                    "SELECT id FROM projects WHERE name LIKE %s OR name LIKE %s LIMIT 1",
                    ('%系统维护%', '%SDS%')
                )
                if results:
                    project_id = results[0]['id']
            
            # 插入任务
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (
                    title, description, status, priority, project_id,
                    task_type, requires_audit, created_at, updated_at,
                    quality_score
                ) VALUES (%s, %s, 'pending', %s, %s, 'auto_generated_v43', 0, NOW(), NOW(), %s)
            """, (
                task_data['title'],
                description,
                priority,
                project_id,
                task_data.get('quality_score', {}).get('total_score', 0)
            ))
            
            task_id = cursor.lastrowid
            
            # 设置number = id（确保唯一性）
            cursor.execute("""
                UPDATE tasks SET number = CAST(id AS CHAR) WHERE id = %s
            """, (task_id,))
            
            self.conn.commit()
            
            logger.info(f"✅ 成功创建任务 #{task_id}: {task_data['title']}")
            return task_id
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            self.conn.rollback()
            return None
    
    def create_tasks_from_recommendations(self, recommendations: List[Dict]) -> List[int]:
        """根据推荐列表批量创建任务（带V4.3增强）"""
        logger.info("=" * 60)
        logger.info("V4.3 任务生成流程开始")
        logger.info("=" * 60)
        
        # Step 1: 去重过滤
        logger.info("Step 1/3: 执行相似度检测与去重...")
        filtered = self.filter_duplicate_tasks(recommendations)
        
        # Step 2: 质量评分与过滤
        logger.info("Step 2/3: 执行质量评分...")
        quality_filtered = self.quality_filter_tasks(filtered)
        
        # Step 3: 创建任务
        logger.info("Step 3/3: 创建任务...")
        created_ids = []
        
        for task in quality_filtered:
            task_id = self.create_task(task)
            if task_id:
                created_ids.append(task_id)
        
        logger.info(f"任务生成完成: 共推荐 {len(recommendations)}, "
                   f"去重后 {len(filtered)}, 质量过滤后 {len(quality_filtered)}, "
                   f"成功创建 {len(created_ids)}")
        
        return created_ids
    
    def run_generation(self) -> Dict:
        """运行任务生成流程"""
        logger.info("=" * 60)
        logger.info("SDS自动任务生成器 V4.3 开始执行")
        logger.info("=" * 60)
        
        if not self.connect():
            return {'error': '数据库连接失败'}
        
        try:
            # 先运行分析器生成推荐
            from task_analyzer import TaskAnalyzer
            analyzer = TaskAnalyzer()
            analysis_results = analyzer.run_full_analysis()
            
            if not analysis_results or 'error' in analysis_results:
                logger.error("无效的分析结果")
                return {'error': '无效的分析结果'}
            
            # 从推荐创建任务
            recommendations = analysis_results.get('recommendations', [])
            created_ids = self.create_tasks_from_recommendations(recommendations)
            
            generation_record = {
                'timestamp': datetime.now().isoformat(),
                'version': 'V4.3',
                'total_recommendations': len(recommendations),
                'tasks_created': len(created_ids),
                'task_ids': created_ids
            }
            
            output_file = Path("/Users/mettlyz/.openclaw/workspace/logs/sds-generation-v43-latest.json")
            with open(output_file, 'w') as f:
                json.dump(generation_record, f, indent=2, ensure_ascii=False)
            
            logger.info(f"V4.3 任务生成完成，记录已保存到 {output_file}")
            return generation_record
            
        except Exception as e:
            logger.error(f"生成任务异常: {e}")
            return {'error': str(e)}
        finally:
            self.close()
            logger.info("=" * 60)


if __name__ == "__main__":
    generator = AutoTaskGeneratorV43()
    result = generator.run_generation()
    # print(json.dumps(result, indent=2, ensure_ascii=False))

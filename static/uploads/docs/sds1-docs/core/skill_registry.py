#!/usr/bin/env python3
"""
Skills 技能注册表
功能：
1. 扫描 workspace/skills/ 目录下所有技能
2. 解析 SKILL.md 提取技能名称、描述、入口命令
3. 根据任务类型匹配推荐技能
4. 子代理执行时自动注入可用技能

作者: SDS v4.6
创建: 2026-04-30
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger('SkillRegistry')

# 常量
SKILLS_DIR = Path.home() / '.openclaw' / 'workspace' / 'skills'
BUILTIN_SKILLS_DIR = Path('/opt/homebrew/lib/node_modules/openclaw/skills')
REGISTRY_FILE = Path.home() / '.openclaw' / 'workspace' / 'data' / 'skill_registry.json'


class Skill:
    """技能定义"""
    def __init__(self, name: str, path: Path, skill_type: str = 'custom'):
        self.name = name
        self.path = path
        self.skill_type = skill_type  # 'custom' 或 'builtin'
        self.description = ''
        self.command = ''
        self.when_to_use = []
        self.tags = []
        self._parse_skill_md()
    
    def _parse_skill_md(self):
        """解析 SKILL.md"""
        skill_md = self.path / 'SKILL.md'
        if not skill_md.exists():
            # 尝试在父目录查找
            skill_md = self.path.parent / 'SKILL.md' if self.path.name == 'execute' else None
        
        if skill_md and skill_md.exists():
            try:
                with open(skill_md, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取描述（第一个段落）
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() and not line.startswith('#'):
                        self.description = line.strip()[:200]
                        break
                
                # 提取使用场景
                if '## When to Use' in content or '## 使用场景' in content:
                    section = content.split('## When to Use')[1].split('##')[0] if '## When to Use' in content else content.split('## 使用场景')[1].split('##')[0]
                    self.when_to_use = [l.strip('- ').strip() for l in section.split('\n') if l.strip().startswith('-')][:5]
                
                # 提取命令（代码块中的 bash 命令）
                code_blocks = re.findall(r'```bash\s*(.*?)\s*```', content, re.DOTALL)
                if code_blocks:
                    self.command = code_blocks[0].strip().split('\n')[0][:200]
                
                # 提取标签（从名称和描述推断）
                self.tags = self._extract_tags(content)
                
            except Exception as e:
                logger.warning(f"解析 skill {self.name} 失败: {e}")
    
    def _extract_tags(self, content: str) -> List[str]:
        """从内容提取标签"""
        text = (self.name + ' ' + self.description + ' ' + content).lower()
        tags = []
        
        tag_map = {
            'search': ['搜索', '查找', '检索', 'search', 'fetch'],
            'download': ['下载', 'download', '获取'],
            'research': ['研究', '调研', '分析', 'research', 'analyze'],
            'document': ['文档', '文件', 'doc', 'pdf', 'document'],
            'communication': ['通信', '消息', '邮件', 'communication', 'message'],
            'finance': ['财务', '金融', '投资', 'finance', 'invest'],
            'academic': ['学术', '论文', '专利', 'academic', 'paper', 'patent'],
            'health': ['健康', '运动', '睡眠', 'health', 'exercise'],
            'system': ['系统', '监控', '维护', 'system', 'monitor'],
            'coding': ['代码', '开发', '编程', 'code', 'dev'],
        }
        
        for tag, keywords in tag_map.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)
        
        return tags
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'path': str(self.path),
            'skill_type': self.skill_type,
            'description': self.description,
            'command': self.command,
            'when_to_use': self.when_to_use,
            'tags': self.tags,
        }


class SkillRegistry:
    """技能注册表"""
    
    def __init__(self):
        self.skills: List[Skill] = []
        self._load_builtin_skills()
        self._load_custom_skills()
    
    def _load_builtin_skills(self):
        """加载内置技能"""
        if not BUILTIN_SKILLS_DIR.exists():
            return
        
        for item in BUILTIN_SKILLS_DIR.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                skill = Skill(item.name, item, 'builtin')
                if skill.description:  # 只添加有描述的技能
                    self.skills.append(skill)
        
        logger.info(f"加载内置技能: {len([s for s in self.skills if s.skill_type == 'builtin'])} 个")
    
    def _load_custom_skills(self):
        """加载自定义技能"""
        if not SKILLS_DIR.exists():
            return
        
        for item in SKILLS_DIR.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # 检查是否有 SKILL.md
                skill_md = item / 'SKILL.md'
                if skill_md.exists():
                    skill = Skill(item.name, item, 'custom')
                    self.skills.append(skill)
        
        logger.info(f"加载自定义技能: {len([s for s in self.skills if s.skill_type == 'custom'])} 个")
    
    def find_skills_for_task(self, task_title: str, task_description: str = '') -> List[Dict]:
        """为任务推荐合适的技能"""
        text = (task_title + ' ' + task_description).lower()
        scored_skills = []
        
        for skill in self.skills:
            score = 0
            
            # 名称匹配
            if skill.name.lower() in text:
                score += 10
            
            # 标签匹配
            for tag in skill.tags:
                if tag in text:
                    score += 5
            
            # 描述匹配
            if skill.description and any(word in skill.description.lower() for word in text.split()[:5]):
                score += 3
            
            # 使用场景匹配
            for use_case in skill.when_to_use:
                if any(word in use_case.lower() for word in text.split()[:5]):
                    score += 4
            
            if score > 0:
                scored_skills.append({
                    **skill.to_dict(),
                    'match_score': score
                })
        
        # 按分数排序
        scored_skills.sort(key=lambda x: x['match_score'], reverse=True)
        return scored_skills[:5]  # 返回前5个最匹配的技能
    
    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """按名称获取技能"""
        for skill in self.skills:
            if skill.name.lower() == name.lower():
                return skill
        return None
    
    def list_all_skills(self) -> List[Dict]:
        """列出所有技能"""
        return [s.to_dict() for s in self.skills]
    
    def save_registry(self):
        """保存注册表"""
        data = {
            'total': len(self.skills),
            'builtin': len([s for s in self.skills if s.skill_type == 'builtin']),
            'custom': len([s for s in self.skills if s.skill_type == 'custom']),
            'skills': self.list_all_skills(),
        }
        with open(REGISTRY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"注册表已保存: {REGISTRY_FILE}")
    
    def generate_skill_prompt(self, task_title: str, task_description: str = '') -> str:
        """为子代理生成技能使用提示"""
        matched_skills = self.find_skills_for_task(task_title, task_description)
        
        if not matched_skills:
            return ""
        
        prompt = "\n【可用技能工具】\n"
        prompt += "执行以下任务时，可以使用以下技能工具（按匹配度排序）：\n\n"
        
        for i, skill in enumerate(matched_skills, 1):
            prompt += f"{i}. **{skill['name']}** (匹配度: {skill['match_score']})\n"
            prompt += f"   描述: {skill['description'][:100]}\n"
            if skill['when_to_use']:
                prompt += f"   适用场景: {', '.join(skill['when_to_use'][:3])}\n"
            if skill['command']:
                prompt += f"   命令示例: `{skill['command'][:80]}`\n"
            prompt += "\n"
        
        prompt += "提示: 如果任务匹配上述技能，请优先使用技能工具而非通用方法。\n"
        return prompt


# 全局实例
_registry_instance = None

def get_registry() -> SkillRegistry:
    """获取注册表单例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = SkillRegistry()
    return _registry_instance


def find_skills_for_task(task_title: str, task_description: str = '') -> List[Dict]:
    """全局接口：为任务查找技能"""
    registry = get_registry()
    return registry.find_skills_for_task(task_title, task_description)


def generate_skill_prompt(task_title: str, task_description: str = '') -> str:
    """全局接口：生成技能提示"""
    registry = get_registry()
    return registry.generate_skill_prompt(task_title, task_description)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    registry = SkillRegistry()
    registry.save_registry()
    
    # 测试推荐
    # print("\n=== 测试: 专利搜索任务 ===")
    skills = registry.find_skills_for_task("搜索AI材料相关专利")
    for s in skills:
        # print(f"  - {s['name']} (分数: {s['match_score']})")
    
    # print("\n=== 测试: 论文下载任务 ===")
    skills = registry.find_skills_for_task("下载ACS论文")
    for s in skills:
        # print(f"  - {s['name']} (分数: {s['match_score']})")

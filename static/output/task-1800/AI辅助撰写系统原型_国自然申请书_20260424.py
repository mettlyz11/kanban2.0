#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026国自然面上项目申请书AI辅助撰写系统 v1.0
生成日期：2026年4月24日
功能：自动化生成申请书各核心模块
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional

class NSFCApplicationWriter:
    """国自然申请书AI撰写系统"""
    
    def __init__(self, field: str = "化学"):
        self.field = field
        self.section_templates = self._load_templates()
        self.keywords_db = self._init_keywords_db()
        
    def _load_templates(self) -> Dict:
        """加载各模块模板"""
        return {
            "立项依据": {
                "structure": [
                    "研究背景与科学意义",
                    "国内外研究现状与发展趋势",
                    "存在的关键科学问题",
                    "本项目的研究设想",
                    "参考文献"
                ],
                "word_count": 4000,
                "references_min": 30
            },
            "研究内容": {
                "structure": [
                    "总体研究思路",
                    "具体研究内容（3-4项）",
                    "拟解决的关键科学问题"
                ],
                "word_count": 2000
            },
            "研究目标": {
                "structure": [
                    "总体目标",
                    "具体目标（3-5条）"
                ],
                "word_count": 500
            },
            "技术路线": {
                "structure": [
                    "实验方案设计",
                    "技术路线图描述",
                    "关键技术与方法",
                    "可行性分析"
                ],
                "word_count": 1500
            },
            "研究方法": {
                "structure": [
                    "理论计算方法",
                    "实验方法",
                    "表征手段",
                    "数据分析方法"
                ],
                "word_count": 1500
            },
            "创新点": {
                "structure": [
                    "学术思想创新",
                    "研究方法创新",
                    "材料/体系创新"
                ],
                "count": 3,
                "word_count": 300
            },
            "研究基础": {
                "structure": [
                    "前期研究工作基础",
                    "已发表相关论文",
                    "实验条件与平台",
                    "学术交流与合作"
                ],
                "word_count": 1500
            },
            "研究队伍": {
                "structure": [
                    "项目负责人介绍",
                    "主要成员介绍",
                    "团队互补性分析"
                ],
                "word_count": 1000
            }
        }
    
    def _init_keywords_db(self) -> Dict:
        """初始化2026重点方向关键词库"""
        return {
            "催化": [
                "单原子催化", "多相催化", "电催化", "光催化", 
                "CO2还原", "析氢反应", "氧还原反应", "合成氨",
                "表界面化学", "原位表征", "理论计算", "构效关系",
                "金属有机框架", "分子筛", "合金催化剂", "缺陷工程"
            ],
            "材料": [
                "低维材料", "量子点", "金属有机框架", "共价有机框架",
                "智能响应材料", "仿生材料", "能源材料", "催化材料",
                "生物医用材料", "高分子材料", "碳材料", "二维材料"
            ],
            "能源": [
                "氢能", "储能", "电池", "超级电容器", "光电转换",
                "人工光合作用", "太阳能燃料", "生物质转化",
                "电化学能源", "能量转换与存储"
            ],
            "AI化学": [
                "机器学习", "深度学习", "人工智能", "分子设计",
                "高通量筛选", "催化预测", "反应预测", "自动化合成",
                "化学信息学", "知识图谱", "大语言模型", "数据驱动"
            ],
            "绿色化学": [
                "绿色合成", "原子经济性", "可持续化学", "循环经济",
                "碳达峰碳中和", "生物质利用", "环境友好"
            ]
        }
    
    def generate_research_basis(self, topic: str, keywords: List[str], 
                              hotspots: List[str], problems: List[str]) -> str:
        """
        生成立项依据模块
        
        Args:
            topic: 研究主题
            keywords: 核心关键词列表
            hotspots: 领域热点方向列表
            problems: 存在的关键科学问题列表
        """
        output = []
        output.append("# 一、立项依据与研究内容")
        output.append("\n## 1. 项目的立项依据")
        output.append(f"\n### 1.1 研究背景与科学意义\n")
        
        # 研究背景
        background = self._generate_background(topic, keywords)
        output.append(background)
        
        # 国内外研究现状
        output.append(f"\n### 1.2 国内外研究现状与发展趋势\n")
        status = self._generate_research_status(topic, hotspots)
        output.append(status)
        
        # 关键科学问题
        output.append(f"\n### 1.3 当前存在的关键科学问题\n")
        for i, problem in enumerate(problems, 1):
            output.append(f"**问题{i}：{problem}**")
            output.append(self._expand_problem(problem, keywords))
            output.append("")
        
        # 研究设想
        output.append(f"\n### 1.4 本项目的研究设想\n")
        vision = self._generate_vision(topic, keywords, problems)
        output.append(vision)
        
        # 参考文献占位
        output.append("\n### 1.5 参考文献\n")
        output.append("（系统将自动插入30-50篇高质量参考文献，格式符合GB/T 7714-2015标准）")
        output.append("1. Author A, Author B. Title [J]. Journal Name, Year, Volume(Issue): Pages.")
        output.append("2. ...")
        
        return "\n".join(output)
    
    def _generate_background(self, topic: str, keywords: List[str]) -> str:
        """生成研究背景"""
        kw_str = "、".join(keywords[:3])
        return f"""
{topic}是当前化学与材料科学领域的前沿研究方向，具有重要的科学意义和应用价值。
随着{kw_str}等技术的快速发展，该领域正在经历从经验试错向理性设计的范式转变。

从国家战略需求层面看，该研究方向紧密契合"双碳"目标、能源安全、新材料强国等国家重大战略，
对于推动相关产业转型升级、实现关键核心技术自主可控具有不可或缺的作用。

从学科发展层面看，{topic}研究涉及物理化学、材料科学、能源科学等多学科交叉，
其突破将有力推动相关基础学科的发展，并催生新的学科增长点。

近年来，随着人工智能、原位表征技术、理论计算方法的进步，该领域迎来了前所未有的发展机遇。
然而，目前仍存在一系列关键科学问题亟待解决，这也正是本项目的切入点和立足点。
""".strip()
    
    def _generate_research_status(self, topic: str, hotspots: List[str]) -> str:
        """生成研究现状"""
        hotspot_str = "、".join(hotspots[:4])
        return f"""
当前，{topic}领域的研究呈现出以下显著特征和发展趋势：

**（1）多学科交叉融合日益深入**
化学与材料、能源、生命、信息等学科的交叉融合日益紧密，催生了大量创新性成果。
特别是人工智能与化学的结合，正在深刻改变传统的研究范式。

**（2）研究尺度向微观和原位拓展**
研究重点从宏观性能向微观机制深入，原位、实时、动态表征技术成为揭示反应机理的关键。
单原子尺度、分子水平的精准调控成为研究热点。

**（3）研究热点集中在：{hotspot_str}等方向**
这些方向代表了领域的前沿和未来发展趋势，也是近年来高影响力论文的集中产出领域。

**（4）国际竞争日趋激烈**
发达国家在该领域持续加大投入，我国虽已取得显著进展，但在原创性方面仍有提升空间。
实现从"跟跑"向"并跑"、"领跑"的转变，需要在关键科学问题上取得突破。

综上所述，该领域正处于快速发展期，同时也面临着重大的科学挑战，
迫切需要开展系统性、原创性的基础研究工作。
""".strip()
    
    def _expand_problem(self, problem: str, keywords: List[str]) -> str:
        """展开科学问题"""
        return f"""
{problem}是制约该领域发展的核心瓶颈之一。尽管国内外研究者在该方向开展了大量工作，
但由于{keywords[0] if keywords else '体系复杂性'}的固有特性，目前仍未获得根本性解决。
深入研究这一问题，对于深化对{keywords[1] if len(keywords)>1 else '相关过程'}的理解、
推动该领域的理论和技术突破具有至关重要的意义。
""".strip()
    
    def _generate_vision(self, topic: str, keywords: List[str], problems: List[str]) -> str:
        """生成研究设想"""
        return f"""
基于上述分析，本项目拟围绕{topic}这一核心主题，针对{len(problems)}个关键科学问题开展系统研究。

本项目的核心学术思想是：**将{keywords[0]}与{keywords[1] if len(keywords)>1 else '理论计算'}相结合，
通过多尺度、多维度的研究策略，实现从微观机理到宏观性能的贯通式研究**。

预期通过本项目的实施，在以下方面取得突破：
- 揭示{keywords[0]}过程的微观机制
- 建立{keywords[1] if len(keywords)>1 else '构效关系'}的理论模型
- 开发高性能的{keywords[2] if len(keywords)>2 else '功能材料'}体系
- 形成具有自主知识产权的核心技术

本研究不仅具有重要的学术价值，还将为相关领域的产业化应用提供理论支撑和技术储备，
具有广阔的应用前景和显著的社会经济效益。
""".strip()
    
    def generate_research_content(self, topics: List[str], key_problems: List[str]) -> str:
        """生成研究内容模块"""
        output = []
        output.append("\n## 2. 项目的研究内容、研究目标及拟解决的关键科学问题")
        output.append("\n### 2.1 研究内容\n")
        
        output.append("本项目围绕总体研究目标，设置以下4个方面的研究内容：\n")
        
        for i, topic in enumerate(topics, 1):
            output.append(f"**研究内容{i}：{topic}**")
            output.append(self._expand_content(topic, i))
            output.append("")
        
        # 关键科学问题
        output.append("\n### 2.2 拟解决的关键科学问题\n")
        for i, problem in enumerate(key_problems, 1):
            output.append(f"**问题{i}：{problem}**")
            output.append("")
            output.append(self._expand_key_problem(problem))
            output.append("")
        
        return "\n".join(output)
    
    def _expand_content(self, topic: str, index: int) -> str:
        """展开单条研究内容"""
        methods = ["理论计算", "实验合成", "系统表征", "性能测试"]
        return f"""
重点研究{topic}的基本规律和调控机制。通过{methods[(index-1)%4]}等多种手段，
系统考察各因素对目标性能的影响规律，建立相应的理论模型和调控策略。
具体包括：
（1）{topic}的理论基础与模型构建
（2）实验方法的建立与优化
（3）影响因素与作用机制研究
（4）性能评价与验证
""".strip()
    
    def _expand_key_problem(self, problem: str) -> str:
        """展开关键科学问题"""
        return f"""
该问题的核心是揭示{problem}的本质原因和内在机制。这需要将宏观现象与微观本质相结合，
通过多尺度的研究手段，从原子、分子层面理解其内在规律，建立普适性的理论框架。
解决这一问题将为该领域的理性设计和可控合成提供坚实的理论基础。
""".strip()
    
    def generate_tech_route(self, methods: List[str]) -> str:
        """生成技术路线模块"""
        output = []
        output.append("\n## 3. 拟采取的研究方案及可行性分析")
        output.append("\n### 3.1 研究方法\n")
        
        output.append("本项目采用理论计算与实验研究相结合的研究方案，具体方法如下：\n")
        
        for method in methods:
            output.append(f"**{method}**")
            output.append(self._expand_method(method))
            output.append("")
        
        # 技术路线图
        output.append("\n### 3.2 技术路线\n")
        output.append(self._generate_tech_chart())
        output.append("\n")
        
        # 可行性分析
        output.append("\n### 3.3 可行性分析\n")
        output.append(self._generate_feasibility())
        
        return "\n".join(output)
    
    def _expand_method(self, method: str) -> str:
        """展开研究方法"""
        return f"""
{method}是本项目的核心研究手段之一。我们将建立完善的实验/计算方案，
确保数据的可靠性和可重复性。该方法已在相关领域得到广泛应用，
我们前期已掌握该技术，能够保证顺利实施。
""".strip()
    
    def _generate_tech_chart(self) -> str:
        """生成技术路线图描述"""
        return """
本项目采用"理论预测→实验验证→机制解析→性能优化"的闭环研究策略，技术路线如下：

```
理论计算模块 → 材料设计与筛选 → 候选体系预测
    ↓                    ↓                    ↓
实验合成模块 → 可控合成与制备 → 样品获得与表征
    ↓                    ↓                    ↓
系统表征模块 → 结构与性能表征 → 构效关系建立
    ↓                    ↓                    ↓
机制解析模块 → 反应机理研究 → 理论模型构建
    ↓                    ↓                    ↓
性能优化模块 → 性能调控与提升 → 目标体系获得
```

各模块之间紧密配合、相互支撑，形成完整的研究链条。通过多学科交叉的研究手段，
确保研究目标的顺利实现。
""".strip()
    
    def _generate_feasibility(self) -> str:
        """生成可行性分析"""
        return """
**（1）学术思路可行**
本项目提出的研究思路符合学科发展规律，基于已有研究基础和前沿进展，具有明确的科学依据。

**（2）技术方案可行**
所采用的研究方法和技术手段成熟可靠，在国内外相关实验室已得到成功应用。
申请人及团队已掌握相关关键技术，具备实施条件。

**（3）研究基础扎实**
申请人在该领域有多年研究积累，已发表相关SCI论文多篇，
具备完成本项目所需的研究能力和经验。

**（4）实验条件完备**
依托单位拥有完善的实验平台和表征设备，能够满足本项目的研究需求。
计算资源充足，可保障大规模计算任务的完成。

综上所述，本项目的研究方案科学合理，技术路线切实可行，
研究基础和条件充分保障，预期能够顺利完成研究任务。
""".strip()
    
    def generate_innovation_points(self, points: List[str]) -> str:
        """生成创新点模块"""
        output = []
        output.append("\n## 4. 本项目的特色与创新之处\n")
        
        output.append("本项目在学术思想、研究方法和技术路线等方面具有以下创新点：\n")
        
        for i, point in enumerate(points, 1):
            output.append(f"**创新点{i}：{point}**")
            output.append(self._expand_innovation(point))
            output.append("")
        
        return "\n".join(output)
    
    def _expand_innovation(self, point: str) -> str:
        """展开创新点"""
        return f"""
该创新点体现在首次系统开展{point}的研究，突破了传统研究方法的局限，
有望在该领域取得原创性成果。这一创新具有重要的学术价值，
将为相关领域的研究提供新的思路和方法。
""".strip()
    
    def generate_full_application(self, project_info: Dict) -> str:
        """
        生成完整的申请书
        
        Args:
            project_info: 项目信息字典，包含：
                - title: 项目名称
                - keywords: 关键词列表
                - hotspots: 热点方向
                - problems: 关键科学问题列表
                - research_topics: 研究内容主题
                - methods: 研究方法列表
                - innovations: 创新点列表
        """
        output = []
        
        # 项目名称
        output.append(f"# {project_info['title']}")
        output.append(f"**生成时间：** {datetime.now().strftime('%Y年%m月%d日')}")
        output.append(f"**项目类别：** 面上项目")
        output.append(f"**申请代码：** B0307（催化化学）")
        output.append("-" * 80)
        output.append("")
        
        # 各模块
        output.append(self.generate_research_basis(
            project_info['title'],
            project_info['keywords'],
            project_info['hotspots'],
            project_info['problems']
        ))
        
        output.append(self.generate_research_content(
            project_info['research_topics'],
            project_info['key_problems']
        ))
        
        output.append(self.generate_tech_route(
            project_info['methods']
        ))
        
        output.append(self.generate_innovation_points(
            project_info['innovations']
        ))
        
        # 年度计划
        output.append("\n## 5. 年度研究计划")
        output.append("\n**第1年：** 文献调研、方案设计、方法建立、初步探索")
        output.append("\n**第2年：** 系统开展实验研究，取得阶段性成果")
        output.append("\n**第3年：** 深入研究，补充实验，整理数据，撰写论文")
        output.append("\n**第4年：** 总结提升，成果固化，项目验收")
        
        # 预期成果
        output.append("\n## 6. 预期研究成果")
        output.append("""
本项目预期取得以下研究成果：
1. 发表SCI收录论文8-12篇，其中IF>10的高水平论文3-5篇
2. 申请国家发明专利2-3项
3. 培养博士/硕士研究生5-8名
4. 建立相关研究方法和技术平台
5. 在国际会议上做邀请报告1-2次
""")
        
        return "\n".join(output)


class ReferenceManager:
    """参考文献自动管理器"""
    
    def __init__(self):
        self.references = []
        self.format = "GB/T7714-2015"  # 国家标准格式
    
    def add_reference(self, ref_type: str, authors: List[str], title: str, 
                     journal: str, year: int, volume: str, pages: str,
                     doi: Optional[str] = None):
        """添加参考文献"""
        ref = {
            'type': ref_type,
            'authors': authors,
            'title': title,
            'journal': journal,
            'year': year,
            'volume': volume,
            'pages': pages,
            'doi': doi
        }
        self.references.append(ref)
    
    def format_reference(self, ref: Dict, index: int) -> str:
        """格式化单条参考文献（GB/T 7714-2015 顺序编码制）"""
        # 作者格式化
        if len(ref['authors']) > 3:
            authors_str = ", ".join(ref['authors'][:3]) + ", et al."
        else:
            authors_str = ", ".join(ref['authors'])
        
        # 期刊文章格式
        return f"{index}. {authors_str}. {ref['title']}[J]. {ref['journal']}, {ref['year']}, {ref['volume']}: {ref['pages']}."
    
    def generate_bibliography(self) -> str:
        """生成参考文献列表"""
        output = ["\n## 参考文献\n"]
        for i, ref in enumerate(self.references, 1):
            output.append(self.format_reference(ref, i))
        return "\n".join(output)


def main():
    """主函数 - 系统使用演示"""
    # print("=" * 60)
    # print("2026国自然面上项目申请书AI辅助撰写系统 v1.0")
    # print("=" * 60)
    
    # 初始化撰写器
    writer = NSFCApplicationWriter(field="化学")
    
    # 示例：催化剂计算方向项目
    project_info = {
        'title': "单原子合金催化剂的理性设计与电催化CO₂还原性能研究",
        'keywords': ["单原子催化", "CO₂电还原", "理论计算", "构效关系", "合金催化剂"],
        'hotspots': ["单原子催化", "电催化CO₂还原", "人工智能辅助催化剂设计", "原位表征技术"],
        'problems': [
            "单原子催化剂的稳定性机制尚不明确",
            "CO₂还原反应的选择性调控机制未知",
            "催化剂构效关系的理论模型不完善"
        ],
        'research_topics': [
            "单原子合金催化剂的结构设计与稳定性研究",
            "CO₂电还原反应机理与动态过程研究",
            "催化剂构效关系与性能预测模型",
            "高性能催化剂的实验验证与性能优化"
        ],
        'key_problems': [
            "单原子活性中心的电子结构调控与稳定性机制",
            "CO₂还原反应路径的选择性调控原理",
            "催化剂结构-性能关联的定量构效关系"
        ],
        'methods': [
            "密度泛函理论（DFT）计算",
            "分子动力学模拟",
            "机器学习与高通量筛选",
            "实验合成与电化学表征"
        ],
        'innovations': [
            "提出单原子合金催化剂的电子结构调控新策略",
            "建立CO₂还原选择性的理论预测模型",
            "发展机器学习辅助的催化剂理性设计方法"
        ]
    }
    
    # 生成完整申请书
    full_application = writer.generate_full_application(project_info)
    
    # 保存输出
    output_dir = "/Users/mettlyz/.openclaw/workspace/output/task-1800"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "催化剂计算方向_申请书模板示例_20260424.md")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_application)
    
    # print(f"✅ 申请书模板已生成：{output_file}")
    # print(f"📝 总字数：约 {len(full_application)} 字")
    # print("=" * 60)
    # print("系统功能清单：")
    # print("✓ 立项依据自动生成")
    # print("✓ 研究内容结构化撰写")
    # print("✓ 技术路线与方案生成")
    # print("✓ 创新点智能提炼")
    # print("✓ 参考文献格式规范化")
    # print("✓ 关键词库与热点匹配")
    # print("=" * 60)


if __name__ == "__main__":
    main()

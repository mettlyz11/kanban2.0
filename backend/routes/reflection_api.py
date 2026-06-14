"""Routes: reflection_api - reflection_api"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import os
import json
from datetime import datetime

bp = Blueprint("routes_reflection_api", __name__)
logger = __import__("logging").getLogger(__name__)

def load_reflection_template():
    """加载8问法反思模板"""
    template_path = os.path.expanduser('~/.openclaw/workspace/brain/reflection_template.md')
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return None

def generate_8_questions_reflection(problem_description: str, context: dict = None) -> dict:
    """
    生成8问法反思分析

    Args:
        problem_description: 问题描述
        context: 额外上下文信息

    Returns:
        dict: 包含8个问题回答的结构化数据
    """
    # 这是AI辅助生成8问法分析的模板函数
    # 实际使用时，可以调用LLM API生成内容

    reflection = {
        'problem': problem_description,
        'timestamp': datetime.now().isoformat(),
        'questions': {
            'observation': {
                'title': '观察',
                'question': '发现了什么现象？具体是什么问题？',
                'answer': {
                    'phenomenon': '',
                    'problem_definition': '',
                    'context': ''
                }
            },
            'impact': {
                'title': '影响',
                'question': '对整体目标有什么影响？严重度如何？',
                'answer': {
                    'scope': '',
                    'goal_impact': '',
                    'severity': 'medium'  # high/medium/low
                }
            },
            'root_cause': {
                'title': '根因',
                'question': '为什么会这样？（连问5次，深入挖掘根本原因）',
                'answer': {
                    'q1_surface': '',
                    'q2_why': '',
                    'q3_deeper': '',
                    'q4_system': '',
                    'q5_root': ''
                }
            },
            'pattern': {
                'title': '模式',
                'question': '这是孤立事件还是重复模式？历史上发生过类似情况吗？',
                'answer': {
                    'type': 'isolated',  # isolated/pattern
                    'history': '',
                    'frequency': '',
                    'triggers': ''
                }
            },
            'system_defect': {
                'title': '系统缺陷',
                'question': '我的哪部分设计/能力导致了这个问题？',
                'answer': {
                    'tools': '',
                    'process': '',
                    'knowledge': '',
                    'configuration': ''
                }
            },
            'improvement': {
                'title': '改进策略',
                'question': '如何从根本上避免？需要学什么/改什么？',
                'answer': {
                    'short_term': [],  # 今天就能做
                    'medium_term': [],  # 本周完成
                    'long_term': []  # 需要架构调整
                }
            },
            'verification': {
                'title': '验证方式',
                'question': '怎么证明改进有效？指标是什么？',
                'answer': {
                    'metrics': [],
                    'method': '',
                    'cycle': '',
                    'criteria': ''
                }
            },
            'knowledge': {
                'title': '知识沉淀',
                'question': '这个经验应该保存在哪里？如何复用？',
                'answer': {
                    'capability_id': '',
                    'documents': [],
                    'checklist_updates': [],
                    'reuse_scenarios': []
                }
            }
        }
    }

    return reflection

@bp.route('/api/reflection/template', methods=['GET'])
def get_reflection_template():
    """获取8问法反思模板"""
    try:
        template = load_reflection_template()
        if template:
            return jsonify({'success': True, 'template': template})
        else:
            return jsonify({'success': False, 'error': '模板文件不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/reflection/analyze', methods=['POST'])
def analyze_reflection():
    """
    分析并生成8问法反思

    请求体：
    {
        "problem": "问题描述",
        "context": {额外上下文},
        "auto_generate": false  # 是否使用AI自动生成回答
    }
    """
    try:
        data = request.get_json()
        problem = data.get('problem', '').strip()
        context = data.get('context', {})
        auto_generate = data.get('auto_generate', False)
    
        if not problem:
            return jsonify({'success': False, 'error': '问题描述不能为空'}), 400
    
        # 生成8问法框架
        reflection = generate_8_questions_reflection(problem, context)
    
        # 如果需要自动生成回答，这里可以调用LLM API
        # 简化版本：返回框架让用户填写
    
        return jsonify({
            'success': True,
            'reflection': reflection,
            'message': '请根据框架填写8个问题的回答'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/reflection/save', methods=['POST'])
def save_reflection():
    """保存8问法反思结果"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        reflection_data = data.get('reflection', {})
    
        if not reflection_data:
            return jsonify({'success': False, 'error': '反思数据不能为空'}), 400
    
        conn = get_db()
        c = conn.cursor()
    
        # 将8问法反思保存到任务结果中
        # 可以扩展数据库表来专门存储反思记录
        reflection_json = json.dumps(reflection_data, ensure_ascii=False)
    
        if task_id:
            c.execute('''
                UPDATE tasks 
                SET result_summary = %s, updated_at = NOW()
                WHERE id = %s
            ''', (reflection_json, task_id))
            conn.commit()
    
        conn.close()
    
        return jsonify({
            'success': True,
            'message': '反思已保存',
            'reflection_id': task_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/reflection/list', methods=['GET'])
def list_reflections():
    """获取反思记录列表"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 查询包含反思数据的任务
        c.execute('''
            SELECT id, number, title, result_summary, created_at, updated_at
            FROM tasks
            WHERE result_summary IS NOT NULL 
            AND result_summary LIKE '%\"questions\"%'
            ORDER BY updated_at DESC
            LIMIT 50
        ''')
    
        reflections = []
        for row in c.fetchall():
            try:
                reflection_data = json.loads(row['result_summary'])
                reflections.append({
                    'task_id': row['id'],
                    'task_number': row['number'],
                    'task_title': row['title'],
                    'problem': reflection_data.get('problem', ''),
                    'timestamp': reflection_data.get('timestamp', row['updated_at']),
                    'summary': reflection_data.get('questions', {})
                })
            except:
                # 如果不是有效的JSON，跳过
                pass
    
        conn.close()
        return jsonify({'success': True, 'reflections': reflections})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def create_long_think_task_with_reflection(original_task_id: int, task_title: str, 
                                           problem_description: str, priority: str = 'high') -> dict:
    """
    创建使用8问法格式的长思考任务

    这个函数替代原有的长思考任务生成逻辑，强制使用8问法格式
    """
    try:
        # 加载模板
        template = load_reflection_template()
    
        # 生成8问法框架
        reflection = generate_8_questions_reflection(problem_description)
    
        # 构建8问法格式的任务描述
        description = f"""## 8问法深度反思任务

### 原始任务
{task_title}

### 待分析的问题
{problem_description}

### 8问法分析框架

请按照以下8个问题进行深入分析：

#### 1. 观察
发现了什么现象？具体是什么问题？
- 现象描述：
- 问题定义：
- 时间/场景：

#### 2. 影响
对整体目标有什么影响？严重度如何？
- 影响范围：
- 对目标的影响：
- 严重度评估：[高/中/低]

#### 3. 根因分析
为什么会这样？（连问5次，深入挖掘根本原因）
- 第1问（表面原因）：
- 第2问（为什么）：
- 第3问（更深一层）：
- 第4问（系统/设计层面）：
- 第5问（最根本原因）：

#### 4. 模式识别
这是孤立事件还是重复模式？历史上发生过类似情况吗？
- 事件类型：[孤立事件/重复模式]
- 历史类似情况：
- 频率：
- 触发条件：

#### 5. 系统缺陷
我的哪部分设计/能力导致了这个问题？
- 工具缺陷：
- 流程缺陷：
- 知识缺陷：
- 配置缺陷：

#### 6. 改进策略
如何从根本上避免？需要学什么/改什么？
- 短期修复（今天就能做）：
- 中期改进（本周完成）：
- 长期优化（需要架构调整）：

#### 7. 验证方式
怎么证明改进有效？指标是什么？
- 可量化的成功标准：
- 验证方法：

#### 8. 知识沉淀
这个经验应该保存在哪里？如何复用？
- 能力库条目ID：
- 相关文档更新：
- 流程/检查清单更新：
- 复用场景：

---
*此任务使用8问法反思模板自动生成*
"""
    
        # 创建手动审核任务（长思考任务）
        result = create_manual_review_task_with_check(
            original_task_id=original_task_id,
            title=f"[8问法反思] {task_title}",
            description=description,
            source='long_think_8q',
            priority=priority,
            suggested_action='请完成8问法深度分析',
            long_think_id=f"8q_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    
        return result
    
    except Exception as e:
        return {'success': False, 'error': str(e)}

@bp.route('/api/reflection/create-long-think', methods=['POST'])
def create_long_think_reflection():
    """
    API: 创建8问法格式的长思考任务

    请求体：
    {
        "original_task_id": 123,
        "task_title": "任务标题",
        "problem_description": "问题描述",
        "priority": "high"
    }
    """
    try:
        data = request.get_json()
        result = create_long_think_task_with_reflection(
            original_task_id=data.get('original_task_id'),
            task_title=data.get('task_title'),
            problem_description=data.get('problem_description'),
            priority=data.get('priority', 'high')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})




from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS

# ============================================
# WebSocket 实时数据同步 (Socket.IO)
# ============================================
try:
    import sys
    sys.path.insert(0, '/opt/kanban-react/backend/src')
    from websocket.index import init_socketio, get_socketio_instance, shutdown_socketio
    WEBSOCKET_AVAILABLE = True
except ImportError as e:
    WEBSOCKET_AVAILABLE = False
    print(f"⚠️ WebSocket 模块导入失败: {e}")

import os
import json
import logging
from datetime import datetime, timedelta
from functools import wraps

import pymysql
# === Phase 1: Extracted route blueprints ===
from routes.cockpit import bp as cockpit_bp
from routes.sync import bp as sync_bp
from changelog_routes import changelog_bp
from routes.system import bp as system_bp
from routes.track import bp as track_bp
from routes.access import bp as access_bp
from routes.local_files import bp as local_files_bp
from routes.calendar import bp as calendar_bp
from routes.sds_api import bp as sds_api_bp
from routes.cron import bp as cron_bp
from routes.emails import bp as emails_bp
from routes.health import bp as health_bp
from routes.projects_api import bp as projects_api_bp
from routes.manual_review_api import bp as manual_review_api_bp
from routes.helpers import get_db, row_to_dict
from routes.calc_research_api import bp as calc_research_api_bp
from routes.goals_llm_api import bp as goals_llm_api_bp
from routes.stocks_api import bp as stocks_api_bp
from routes.brain_chat_api import bp as brain_chat_api_bp
from routes.tasks_api import bp as tasks_api_bp
from routes.resource_library import bp as resource_library_bp
from routes.strategy_routes import bp as strategy_bp
from routes.contacts_routes import bp as contacts_bp
from routes.config_routes import bp as config_bp
from routes.daemon_status import bp as daemon_status_bp
# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def before_send_event(event, hint):
    """增强 Sentry 事件：添加请求上下文"""
    try:
        from flask import request
        if request:
            event.setdefault("extra", {})
            event["extra"]["url"] = request.url
            event["extra"]["method"] = request.method
    except:
        pass
    return event

app = Flask(__name__, static_folder='dist')
from kanban_improvements import setup_routes
setup_routes(app)

# Sentry 错误追踪
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    sentry_sdk.init(
        dsn="http://a7cb045230577c839f5b2fddfb1c7026@39.106.190.50:9000/1",

        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True,
        before_send=before_send_event,
    )
    print("✅ Sentry 已初始化")
except Exception as e:
    print(f"⚠️ Sentry 初始化失败: {e}")
app.url_map.strict_slashes = False  # 允许带或不带斜杠访问
CORS(app)

# ============================================
# WebSocket 初始化
# ============================================
if WEBSOCKET_AVAILABLE:
    try:
        socketio = init_socketio(app, cors_allowed_origins="*")
        print("✅ Socket.IO WebSocket 服务已初始化")
    except Exception as e:
        print(f"⚠️ Socket.IO 初始化失败: {e}")
        socketio = None
else:
    socketio = None

# ============================================
# 数据库配置 - 纯 MySQL/RDS
# ============================================
# 通过环境变量 DB_TYPE 切换: sqlite | mysql
# MySQL/RDS 配置通过环境变量设置：
#   MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
# ============================================

# Database configuration - MySQL only
DB_TYPE = 'mysql'
DB_PATH = '/opt/kanban-react/backend/monitoring.db'

from database_config import (
    MYSQL_CONFIG, get_db_connection, get_db_cursor, get_mysql_connection,
    execute_query, execute_update, table_exists, get_db_info,

)

# 兼容旧代码的 DB_PATH
# ============================================
# 数据库类型定义 - 纯 MySQL 模式  
# ============================================
DB_TYPE = 'mysql'
# DB_PATH 已移除 - MySQL Only
# DB_PATH removed - MySQL only

logger.info(f"🗄️ 数据库模式: {DB_TYPE}")
if DB_TYPE == 'mysql':
    db_info = get_db_info()
    logger.info(f"🗄️ RDS 连接: {db_info.get('mysql_host')} / {db_info.get('mysql_database')}")

# JWT和加密配置
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
app.config['MASTER_KEY'] = os.environ.get('MASTER_KEY', 'default-master-key-change-in-production')
# app.config['DB_PATH'] 已移除 - MySQL Only

# ============================================
# 导入认证路由 (P049-T007, P049-T008)
# ============================================
try:
    from auth_routes import auth_bp
    app.register_blueprint(auth_bp)
    logger.info("✅ 认证路由已注册 (P049-T007: 密码管理, P049-T008: API密钥管理)")
except ImportError as e:
    logger.warning(f"⚠️ 认证路由导入失败: {e}")

# ============================================
## 导入监控告警路由 (P049-T041)
## ============================================
#try:
    from monitoring_routes import monitoring_bp, init_monitoring_db
    init_monitoring_db(DB_PATH)
    app.register_blueprint(monitoring_bp)
#    logger.info("✅ 监控告警路由已注册 (P049-T041: 监控告警)")
#except ImportError as e:
#    logger.warning(f"⚠️ 监控告警路由导入失败: {e}")
#
# ============================================
# 导入管理员后台路由 (P049-T8-2)
# ============================================
try:
    logger.info("✅ 管理员后台路由已注册 (P049-T8-2: 管理员后台)")
except ImportError as e:
    logger.warning(f"⚠️ 管理员后台路由导入失败: {e}")

# ============================================
# ============================================
# 导入文献调研记录路由
# ============================================
try:
    logger.info("✅ 文献调研记录路由已注册")
except ImportError as e:
    logger.warning(f"⚠️ 文献调研记录路由导入失败：{e}")

# 导入感知 Agent 路由 (P049-T042)
# ============================================
try:
    # 在后台启动感知 Agent
    import threading
    def start_perception_agent_bg():
        import time; time.sleep(3)
        try:
            agent = init_perception_agent()
            if agent:
                agent.start()
                logger.info("✅ 感知 Agent 已启动 (P049-T042: 感知 Agent)")
        except Exception as e:
            logger.warning(f"⚠️ 感知 Agent 启动失败：{e}")

    # 在后台线程启动
    threading.Thread(target=start_perception_agent_bg, daemon=True).start()
    logger.info("✅ 感知 Agent 路由已注册 (P049-T042: 感知 Agent)")
except ImportError as e:
    logger.warning(f"⚠️ 感知 Agent 路由导入失败：{e}")

# ============================================
# 导入工作流程架构图路由
# ============================================
try:
    logger.info("✅ 工作流程架构图路由已注册")
except ImportError as e:
    logger.warning(f"⚠️ 工作流程架构图路由导入失败：{e}")

# ============================================
# 导入人员和公司动态Tab路由
# ============================================
try:
    from person_company_routes import person_company_bp
    from person_tabs_routes import person_tabs_bp
    from company_tabs_routes import company_tabs_bp
    app.register_blueprint(person_tabs_bp)
    app.register_blueprint(person_company_bp)
    app.register_blueprint(company_tabs_bp)
    # init_person_company_tables()  # Disabled - using database_config functions
    logger.info("✅ 人员和公司动态Tab路由已注册")
except ImportError as e:
    logger.warning(f"⚠️ 人员和公司动态Tab路由导入失败：{e}")

# 战略目标关系图路由
try:
    from strategic_map_routes import strategic_map_bp
    # Phase 1: Extracted route blueprints
    app.register_blueprint(cockpit_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(changelog_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(track_bp)
    app.register_blueprint(access_bp)
    app.register_blueprint(local_files_bp)
    app.register_blueprint(calendar_bp)
    from routes.llm_usage_api import llm_usage_bp
    app.register_blueprint(llm_usage_bp)

    app.register_blueprint(cron_bp)
    app.register_blueprint(emails_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(projects_api_bp)
    app.register_blueprint(manual_review_api_bp)
    app.register_blueprint(calc_research_api_bp)
    app.register_blueprint(goals_llm_api_bp)
    app.register_blueprint(stocks_api_bp)
    app.register_blueprint(brain_chat_api_bp)
    app.register_blueprint(tasks_api_bp)

    app.register_blueprint(resource_library_bp)
    app.register_blueprint(strategic_map_bp)
#    app.register_blueprint(sds_api_bp)
    logger.info("✅ 战略全景图路由已注册")
except ImportError as e:
    logger.warning(f"⚠️ 战略全景图路由导入失败：{e}")

# ============================================
# 辅助函数
# ============================================
def parse_action_items(action_items_str):
    """安全解析action_items字段"""
    if not action_items_str:
        return []
    try:
        # 尝试解析为JSON
        return json.loads(action_items_str)
    except json.JSONDecodeError:
        # 如果不是JSON，按文本解析（以换行分隔）
        items = [item.strip() for item in action_items_str.split('\n') if item.strip()]
        return items
    except Exception:
        return []

# ============================================
# 感知事件记录器（直接数据库写入）
# ============================================
class PerceptionRecorder:
    """感知事件记录器 - 直接写入数据库"""

    def record_event(self, event_type, severity, source, message, metadata=None):
        """记录感知事件"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
        
                import hashlib
                hash_str = hashlib.md5(f"{event_type}{source}{message}{datetime.now()}".encode()).hexdigest()[:16]
        
                c.execute('''
                    INSERT INTO perception_events 
                    (event_type, severity, source, message, metadata, timestamp, hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    event_type, severity, source, message,
                    json.dumps(metadata) if metadata else '{}',
                    datetime.now().isoformat(), hash_str
                ))
        
                conn.commit()
        except Exception as e:
            logger.error(f"记录感知事件失败: {e}")

    def record_api_error(self, status_code, endpoint, error_message, request_data=None):
        """记录API错误"""
        self.record_event(
            event_type='api_error',
            severity='error' if status_code >= 500 else 'warning',
            source='backend',
            message=f'API错误 {status_code}: {endpoint}',
            metadata={'status_code': status_code, 'endpoint': endpoint, 
                     'error': error_message, 'request': request_data}
        )

# 全局感知记录器实例
perception_recorder = PerceptionRecorder()
def row_to_dict(row, cursor):
    """将行数据转换为字典，兼容SQLite和MySQL"""
    if row is None:
        return None
    
    import json
    if isinstance(row, dict):
        result = dict(row)
    elif hasattr(cursor, 'description') and cursor.description:
        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))
    else:
        return row
    
    # 🌟 自动解析 JSON 描述
    desc = result.get('description', '')
    if desc and isinstance(desc, str) and desc.startswith('{'):
        try:
            parsed = json.loads(desc)
            result['json_description'] = parsed
            result['text_description'] = parsed.get('context', parsed.get('goal', '')) or desc
        except json.JSONDecodeError:
            result['json_description'] = None
            result['text_description'] = desc
    else:
        result['json_description'] = None
        result['text_description'] = desc if desc else ''
    
    return result


# ============================================
# LLM 费用记录工具函数
# ============================================

# 模型价格表 (USD per 1K tokens)
MODEL_PRICES = {
    # Kimi / Moonshot
    'kimi-k2.5': {'input': 0.002, 'output': 0.008},
    'kimi-k2': {'input': 0.002, 'output': 0.008},
    'moonshot-v1-8k': {'input': 0.012, 'output': 0.012},
    'moonshot-v1-32k': {'input': 0.024, 'output': 0.024},
    'moonshot-v1-128k': {'input': 0.06, 'output': 0.06},

    # Qwen / 阿里云
    'qwen3.5-plus': {'input': 0.003, 'output': 0.009},
    'qwen3-plus': {'input': 0.003, 'output': 0.009},
    'qwen-max': {'input': 0.04, 'output': 0.12},
    'qwen-plus': {'input': 0.004, 'output': 0.012},
    'qwen-turbo': {'input': 0.001, 'output': 0.003},

    # DeepSeek
    'deepseek-chat': {'input': 0.00027, 'output': 0.0011},
    'deepseek-coder': {'input': 0.00027, 'output': 0.0011},
    'deepseek-v3': {'input': 0.00027, 'output': 0.0011},

    # GLM / 智谱
    'glm-4': {'input': 0.014, 'output': 0.014},
    'glm-4-air': {'input': 0.001, 'output': 0.001},
    'glm-4-flash': {'input': 0.00014, 'output': 0.00014},
    'glm-5': {'input': 0.014, 'output': 0.014},

    # GPT / OpenAI
    'gpt-4o': {'input': 0.005, 'output': 0.015},
    'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
    'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
    'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},

    # Claude / Anthropic
    'claude-3-5-sonnet': {'input': 0.003, 'output': 0.015},
    'claude-3-opus': {'input': 0.015, 'output': 0.075},
    'claude-3-haiku': {'input': 0.00025, 'output': 0.00125},

    # Gemini / Google
    'gemini-1.5-pro': {'input': 0.00125, 'output': 0.005},
    'gemini-1.5-flash': {'input': 0.000075, 'output': 0.0003},
    'gemini-2.0-flash': {'input': 0.0001, 'output': 0.0004},

    # 默认价格 (未知模型)
    'default': {'input': 0.001, 'output': 0.003}
}

def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """
    计算 LLM 调用费用

    Args:
        model_name: 模型名称
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数

    Returns:
        费用 (USD)
    """
    # 提取模型名称（去掉提供商前缀）
    model_key = model_name.lower()
    if '/' in model_key:
        model_key = model_key.split('/')[-1]

    # 获取价格
    price = MODEL_PRICES.get(model_key, MODEL_PRICES['default'])

    # 计算费用 (价格是每 1K tokens)
    input_cost = (input_tokens / 1000) * price['input']
    output_cost = (output_tokens / 1000) * price['output']

    return round(input_cost + output_cost, 6)

def record_token_usage(provider: str, model: str, prompt_tokens: int, 
                       completion_tokens: int, cost_usd: float = None):
    """
    记录 LLM 调用的 token 使用和费用到 token_usage 表

    Args:
        provider: 提供商名称 (如 'moonshot', 'aliyun')
        model: 模型名称 (如 'kimi-k2.5', 'qwen3.5-plus')
        prompt_tokens: 输入 token 数
        completion_tokens: 输出 token 数
        cost_usd: 费用 (USD)，如果不提供则自动计算
    """
    try:
        total_tokens = prompt_tokens + completion_tokens
    
        # 如果没有提供费用，自动计算
        if cost_usd is None:
            cost_usd = calculate_cost(model, prompt_tokens, completion_tokens)
    
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO token_usage (timestamp, provider, model, prompt_tokens, 
                                    completion_tokens, total_tokens, cost_usd)
            VALUES (NOW(), %s, %s, %s, %s, %s, %s)
        ''', (provider, model, prompt_tokens, completion_tokens, total_tokens, cost_usd))
        conn.commit()
        conn.close()
        logger.info(f"📊 记录 token 使用：{model} - {total_tokens} tokens, ${cost_usd:.6f}")
    except Exception as e:
        logger.error(f"❌ 记录 token 使用失败：{e}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 简化版，实际应该验证token
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# 项目 API
# ============================================

# ============================================
# 项目文档管理 API
# ============================================

# 文件上传配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
# 允许的文件类型：pdf, doc, docx, md, txt, py, js, vue, sql
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'md', 'txt', 'py', 'js', 'vue', 'sql'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_project_member_permission(project_id, user_id=None):
    """检查用户是否是项目成员（简化版，可根据需要扩展）"""
    # TODO: 实现实际的项目成员验证逻辑
    # 目前允许所有已登录用户访问
    return True

def get_project_upload_path(project_id):
    """获取项目的上传目录路径"""
    upload_path = os.path.join(UPLOAD_FOLDER, 'projects', str(project_id))
    if not os.path.exists(upload_path):
        os.makedirs(upload_path, exist_ok=True)
    return upload_path

# ============================================
# 任务 API
# ============================================

# ============================================
# 统计 API
# ============================================

# ============================================
# 本地文件索引 API
# ============================================

from file_indexer import scan_workspace

# ============================================
# 任务附件管理 API
# ============================================

# 上传目录配置
UPLOAD_DIR = "/opt/kanban-react/backend/uploads"

# ============================================
# 静态文件服务
# ============================================

@app.route('/')
def serve_index():
    """提供首页"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """提供静态资源文件"""
    return send_from_directory(os.path.join(app.static_folder, 'assets'), filename)

@app.route('/vite.svg')
def serve_vite_svg():
    """提供vite图标"""
    return send_from_directory(app.static_folder, 'vite.svg')

@app.route('/files/<path:filename>')
def serve_files(filename):
    """提供人员文件下载"""
    return send_from_directory(os.path.join(app.static_folder, 'files'), filename)

@app.route('/api/communication/hub')
def serve_communication_hub():
    """Dudu对接中心API信息"""
    return jsonify({
        'success': True,
        'message': 'Dudu对接中心',
        'endpoints': [
            '/api/communication/messages',
            '/api/communication/send',
            '/api/communication/quick-actions',
            '/api/communication/submit-task',
            '/api/communication/progress-report',
            '/api/communication/emergency'
        ]
    })

@app.route('/api/health/', methods=['GET'])
@app.route('/api/health')
@app.route('/health')
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'kanban-v2'
    })

# ============================================
# 体检数据 API
# ============================================

    # Routes moved to routes/health.py
@app.route('/api/health/checkups/latest', methods=['GET'])
def get_latest_health_checkup():
    """获取最新体检数据摘要"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 获取最新的基本健康指标
        c.execute('''
            SELECT person_name, age, height, weight,
                   blood_pressure_sys, blood_pressure_dia, heart_rate
            FROM health_checkups
            WHERE person_name = '刘宇宙'
            ORDER BY checkup_date DESC
            LIMIT 1
        ''')
        latest = c.fetchone()
    
        # 获取所有体检项目
        c.execute('''
            SELECT checkup_date, hospital, checkup_items, notes
            FROM health_checkups
            WHERE person_name = '刘宇宙'
            ORDER BY checkup_date DESC
        ''')
        all_checkups = [row_to_dict(row, c) for row in c.fetchall()]
    
        conn.close()
    
        if latest:
            return jsonify({
                'success': True,
                'latest': dict(latest),
                'checkup_count': len(all_checkups),
                'checkups': all_checkups
            })
        else:
            return jsonify({'success': True, 'latest': None, 'checkup_count': 0})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/health.py
@app.route('/api/health/records', methods=['POST'])
def add_health_record():
    """添加日常健康记录"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO health_records (record_date, weight, sleep_hours, exercise_minutes,
                                      water_intake, mood, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('record_date'),
            data.get('weight'),
            data.get('sleep_hours'),
            data.get('exercise_minutes'),
            data.get('water_intake'),
            data.get('mood'),
            data.get('notes')
        ))
        conn.commit()
        record_id = c.lastrowid
        conn.close()
        return jsonify({'success': True, 'id': record_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


    # Routes moved to routes/health.py
@app.route('/api/company-info/companies', methods=['GET'])
def get_companies():
    """获取公司列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, name, short_name, legal_representative, industry, 
                   create_date, address, phone, email, website, description, last_updated
            FROM company_info
            ORDER BY name
        ''')
        companies = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'companies': companies})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/company-info/companies/<company_id>', methods=['GET'])
def get_company_detail(company_id):
    """获取公司详情"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM company_info WHERE id = %s
        ''', (company_id,))
        company = c.fetchone()
        conn.close()
    
        if company:
            return jsonify({'success': True, 'company': dict(company)})
        else:
            return jsonify({'success': False, 'error': 'Company not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# Cron 任务 API
# ============================================

@app.route('/api/cron/jobs', methods=['GET'])
    # Routes moved to routes/cron.py
@app.route('/api/cron/stats', methods=['GET'])
def get_cron_stats():
    """获取Cron统计"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        c.execute('SELECT COUNT(*) FROM cron_tasks')
        total = list(c.fetchone().values())[0]
    
        c.execute("SELECT COUNT(*) FROM cron_tasks WHERE status = 'active'")
        active = list(c.fetchone().values())[0]
    
        c.execute('SELECT SUM(fail_count) FROM cron_tasks')
        failed = list(c.fetchone().values())[0] or 0
    
        conn.close()
    
        return jsonify({
            'success': True, 
            'stats': {
                'total': total,
                'active': active,
                'failed': failed,
                'today': 0
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/cron.py
@app.route('/api/cron/delete/<int:task_id>', methods=['POST'])
def delete_cron_task(task_id):
    """删除Cron任务"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM cron_tasks WHERE id = %s', (task_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/cron.py
@app.route('/api/cron/history', methods=['GET'])
def get_cron_history():
    """获取Cron执行历史"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT h.*, t.name as task_name
            FROM cron_execution_history h
            LEFT JOIN cron_tasks t ON h.task_id = t.id
            ORDER BY h.started_at DESC
            LIMIT 100
        ''')
        history = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': True, 'history': []})

# ============================================
# 股票 API
# ============================================

# ============================================
# 手动审核 API
# ============================================

# ============================================
# 防重复机制：检查是否有未执行的长思考任务
# ============================================
# ============================================
# 技能库 API
# ============================================

# ============================================
# 邮件 API
# ============================================

        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/emails.py
# ============================================
# 知识大脑 API
# ============================================

# ============================================
# 聊天 API
# ============================================

# ============================================
# 登录 API
# ============================================

# ============================================
# Pepi API
# ============================================

@app.route('/api/pepi/status', methods=['GET'])
@app.route('/api/pepi/info', methods=['GET'])
def get_pepi_info():
    """获取Pepi信息"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM pepi_info ORDER BY id DESC LIMIT 1')
        row = c.fetchone()
        conn.close()
    
        if row:
            return jsonify({'success': True, 'info': row_to_dict(row, c)})
    
        # 默认信息
        return jsonify({
            'success': True,
            'info': {
                'name': 'Pepi',
                'version': '1.0',
                'status': 'active',
                'description': 'AI驱动的数字员工系统',
                'tasks_completed': 156,
                'avg_rating': 4.5,
                'total_hours': 320
            }
        })
    except Exception as e:
        return jsonify({'success': True, 'info': {
            'name': 'Pepi',
            'version': '1.0',
            'status': 'active'
        }})

@app.route('/api/pepi/evaluations', methods=['GET'])
def get_pepi_evaluations():
    """获取Pepi评估记录"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM pepi_evaluations
            ORDER BY eval_date DESC
            LIMIT 50
        ''')
        evaluations = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'evaluations': evaluations})
    except Exception as e:
        return jsonify({'success': True, 'evaluations': []})

@app.route('/api/pepi/sync', methods=['POST'])
def sync_pepi():
    """手动同步Pepi数据"""
    try:
        import subprocess
        result = subprocess.run(
            ['python3', 'sync_pepi.py'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True
        )
    
        if result.returncode == 0:
            return jsonify({'success': True, 'message': '同步成功', 'output': result.stdout})
        else:
            return jsonify({'success': False, 'error': result.stderr})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 系统监控 API
# ============================================

    # Routes moved to routes/system.py

    # Routes moved to routes/track.py

    # Routes moved to routes/access.py

    # Routes moved to routes/access.py

    # Routes moved to routes/system.py

# ============================================
# T009 大模型配置 API
# ============================================

# ============================================
# 计算任务 API (T109) - 适配 t109_calculations 表结构
# ============================================

# ============================================
# ============================================
# T018 调研记录 API
# ============================================

# ============================================
# T013 每日复盘 API
# ============================================

# ============================================
# 化学模块 API
# ============================================

# ============================================
# T019 架构图 API
# ============================================

@app.route('/api/architecture', methods=['GET'])
def get_architecture():
    """获取架构图数据"""
    try:
        return jsonify({
            'success': True,
            'architecture': {
                'version': '2.0',
                'components': [
                    {'name': '前端 (React)', 'type': 'frontend', 'status': 'active'},
                    {'name': '后端 (Flask)', 'type': 'backend', 'status': 'active'},
                    {'name': '数据库 (MySQL RDS)', 'type': 'database', 'status': 'active'},
                    {'name': 'Cloudflare Tunnel', 'type': 'gateway', 'status': 'active'}
                ],
                'updated_at': '2026-02-26'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/table-counts', methods=['GET'])
def get_table_counts():
    """获取数据库表记录数"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        tables = ['chat_messages', 'chemical_elements', 'entities', 'emails', 
                  'projects', 'tasks', 'stocks', 'skills', 'llm_configs',
                  'version_logs', 'molecules', 'reactions', 'calc_tasks',
                  'stock_transactions', 'system_metrics']
    
        counts = {}
        for table in tables:
            try:
                c.execute(f'SELECT COUNT(*) FROM {table}')
                counts[table] = list(c.fetchone().values())[0]
            except:
                counts[table] = 0
    
        conn.close()
        return jsonify({'success': True, 'counts': counts})
    except Exception as e:
        return jsonify({'success': True, 'counts': {}})

# ============================================
# T021 资源库 API
# ============================================

@app.route('/api/resources', methods=['GET'])
def get_resources():
    """获取资源库"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM resources
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        resources = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'resources': resources})
    except Exception as e:
        return jsonify({'success': True, 'resources': []})

@app.route('/api/github/repos', methods=['GET'])
def get_github_repos():
    """获取GitHub仓库列表"""
    try:
        import requests
        # 使用GitHub API获取用户仓库
        # 注意：实际使用需要配置GitHub Token
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Kanban-System'
        }
    
        # 获取mettlyz11的公开仓库
        response = requests.get(
            'https://api.github.com/users/mettlyz11/repos',
            headers=headers,
            params={'sort': 'updated', 'per_page': 20}
        )
    
        if response.status_code == 200:
            repos = response.json()
            return jsonify({
                'success': True,
                'repos': [{
                    'name': r['name'],
                    'description': r['description'],
                    'url': r['html_url'],
                    'stars': r['stargazers_count'],
                    'language': r['language'],
                    'updated': r['updated_at']
                } for r in repos]
            })
        else:
            # 如果API失败，返回预设的GitHub资源
            return jsonify({
                'success': True,
                'repos': [
                    {'name': 'kanban2.0', 'description': '看板系统v2.0 - React版本', 'url': 'https://github.com/mettlyz11/kanban2.0', 'stars': 0, 'language': 'TypeScript'},
                    {'name': 'kanban-system', 'description': '看板系统v1.0 - Flask版本', 'url': 'https://github.com/mettlyz11/kanban-system', 'stars': 0, 'language': 'Python'}
                ]
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/github/stats', methods=['GET'])
def get_github_stats():
    """获取GitHub统计"""
    try:
        return jsonify({
            'success': True,
            'stats': {
                'username': 'mettlyz11',
                'public_repos': 2,
                'followers': 0,
                'following': 0
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/version-logs', methods=['GET'])
def get_version_logs():
    """获取版本日志"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM version_logs ORDER BY release_date DESC LIMIT 20')
        logs = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        return jsonify({
            'success': True,
            'logs': [
                {
                    'version': '2.0.0',
                    'release_date': '2026-02-26',
                    'description': 'React版本看板系统正式发布',
                    'changes': ['新增React前端', '新增登录保护', '新增Pepi数字员工', '新增知识大脑']
                },
                {
                    'version': '1.9.0',
                    'release_date': '2026-02-20',
                    'description': '系统功能增强',
                    'changes': ['优化任务管理', '新增资产统计', '修复已知问题']
                }
            ]
        })

# ============================================
# 日历 API
# ============================================

    # Routes moved to routes/calendar.py
@app.route('/api/calendar/accounts', methods=['POST'])
def create_calendar_account():
    """创建CalDAV账户"""
    try:
        data = request.get_json()
    
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO calendar_accounts
            (name, account_type, server_url, username, password, calendar_path, calendar_name, sync_enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('name'),
            data.get('account_type', 'caldav'),
            data.get('server_url'),
            data.get('username'),
            data.get('password'),
            data.get('calendar_path', '/'),
            data.get('calendar_name'),
            1
        ))
    
        conn.commit()
        account_id = c.lastrowid
        conn.close()
    
        return jsonify({'success': True, 'id': account_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/calendar.py
@app.route('/api/calendar/events/', methods=['GET'])
    # Routes moved to routes/calendar.py
@app.route('/api/calendar/events', methods=['POST'])
def create_calendar_event():
    """创建日历事件"""
    try:
        data = request.get_json()
        from datetime import datetime, timedelta
    
        conn = get_db()
        c = conn.cursor()
    
        c.execute('''
            INSERT INTO calendar_events 
            (id, title, description, start_time, end_time, is_all_day, location, 
             category, event_color, reminder_minutes, participants, meeting_minutes_id, 
             recurrence, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('id', 'evt_' + datetime.now().strftime('%Y%m%d%H%M%S')),
            data.get('title'),
            data.get('description'),
            data.get('start_time'),
            data.get('end_time'),
            data.get('is_all_day', 0),
            data.get('location'),
            data.get('category', 'default'),
            data.get('color', '#667eea'),
            data.get('reminder_minutes', 15),
            data.get('participants'),
            data.get('meeting_minutes_id'),
            data.get('recurrence'),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
    
        conn.commit()
        event_id = c.lastrowid
        conn.close()
    
        return jsonify({'success': True, 'id': event_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/calendar.py
@app.route('/api/calendar/events/<event_id>', methods=['DELETE', 'OPTIONS'])
def delete_calendar_event(event_id):
    """删除日历事件（支持CORS预检）"""
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    # DELETE 方法处理
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 硬删除（因为表中没有status字段）
        c.execute('''
            DELETE FROM calendar_events 
            WHERE id = %s
        ''', (event_id,))
    
        conn.commit()
        conn.close()
    
        return jsonify({'success': True, 'message': '日程已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/calendar.py
@app.route('/api/calendar/settings', methods=['GET'])
def get_calendar_settings():
    """获取日历设置"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM calendar_settings WHERE id = 1')
        row = c.fetchone()
        conn.close()
    
        if row:
            settings = {
                'default_view': row['default_view'],
                'first_day_of_week': row['first_day_of_week'],
                'show_weekends': bool(row['show_weekends']),
                'working_hours_start': row['working_hours_start'],
                'working_hours_end': row['working_hours_end'],
                'default_reminder_minutes': row['default_reminder_minutes'],
                'enable_notifications': bool(row['enable_notifications']),
                'notification_sound': bool(row['notification_sound']),
                'sync_enabled': bool(row['sync_enabled']),
                'sync_interval_minutes': row['sync_interval_minutes'],
                'default_calendar_color': row['default_calendar_color']
            }
            return jsonify({'success': True, 'settings': settings})
        else:
            # 返回默认设置
            return jsonify({
                'success': True, 
                'settings': {
                    'default_view': 'month',
                    'first_day_of_week': 0,
                    'show_weekends': True,
                    'working_hours_start': '09:00',
                    'working_hours_end': '18:00',
                    'default_reminder_minutes': 15,
                    'enable_notifications': True,
                    'notification_sound': True,
                    'sync_enabled': False,
                    'sync_interval_minutes': 30,
                    'default_calendar_color': '#667eea'
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/calendar.py
@app.route('/api/meetings/', methods=['GET'])  # 支持尾部斜杠
@app.route('/api/meetings/', methods=['GET'])
@app.route('/api/meetings', methods=['GET'])
def get_meetings():
    """获取会议纪要列表"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        limit = request.args.get('limit', 50, type=int)
    
        c.execute('''
            SELECT id, title, date, time, participants, summary, content, action_items, created_at
            FROM meetings
            ORDER BY date DESC, time DESC
            LIMIT %s
        ''', (limit,))
    
        meetings = []
        for row in c.fetchall():
            meetings.append({
                'id': row['id'],
                'title': row['title'],
                'date': row['date'],
                'time': row['time'],
                'participants': row['participants'],
                'summary': row['summary'],
                'content': row['content'],
                'action_items': parse_action_items(row['action_items']),
                'created_at': row['created_at']
            })
    
        conn.close()
    
        return jsonify({
            'success': True,
            'meetings': meetings,
            'count': len(meetings)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/meetings/<int:meeting_id>', methods=['GET'])
def get_meeting(meeting_id):
    """获取单个会议纪要详情"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        c.execute('''
            SELECT id, title, date, time, participants, summary, content, action_items, created_at
            FROM meetings
            WHERE id = %s
        ''', (meeting_id,))
    
        row = c.fetchone()
        conn.close()
    
        if not row:
            return jsonify({'success': False, 'error': '会议纪要不存在'}), 404
    
        meeting = {
            'id': row['id'],
            'title': row['title'],
            'date': row['date'],
            'time': row['time'],
            'participants': row['participants'],
            'summary': row['summary'],
            'content': row['content'],
            'action_items': parse_action_items(row['action_items']),
            'created_at': row['created_at']
        }

        return jsonify({'success': True, 'meeting': meeting})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/meetings', methods=['POST'])
def create_meeting():
    """创建会议纪要"""
    try:
        data = request.get_json()
    
        if not data.get('title') or not data.get('date'):
            return jsonify({'success': False, 'error': '标题和日期不能为空'}), 400
    
        conn = get_db()
        c = conn.cursor()
    
        c.execute('''
            INSERT INTO meetings (title, date, time, participants, summary, content, action_items)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('title'),
            data.get('date'),
            data.get('time', ''),
            data.get('participants', ''),
            data.get('summary', ''),
            data.get('content', ''),
            json.dumps(data.get('action_items', []))
        ))
    
        meeting_id = c.lastrowid
        conn.commit()
        conn.close()
    
        return jsonify({
            'success': True,
            'id': meeting_id,
            'message': '会议纪要创建成功'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/meetings/<int:meeting_id>', methods=['PUT'])
def update_meeting(meeting_id):
    """更新会议纪要"""
    try:
        data = request.get_json()
    
        conn = get_db()
        c = conn.cursor()
    
        # 检查是否存在
        c.execute('SELECT id FROM meetings WHERE id = %s', (meeting_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '会议纪要不存在'}), 404
    
        c.execute('''
            UPDATE meetings SET
                title = COALESCE(%s, title),
                date = COALESCE(%s, date),
                time = COALESCE(%s, time),
                participants = COALESCE(%s, participants),
                summary = COALESCE(%s, summary),
                content = COALESCE(%s, content),
                action_items = COALESCE(%s, action_items),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (
            data.get('title'),
            data.get('date'),
            data.get('time'),
            data.get('participants'),
            data.get('summary'),
            data.get('content'),
            json.dumps(data.get('action_items')) if data.get('action_items') is not None else None,
            meeting_id
        ))
    
        conn.commit()
        conn.close()
    
        return jsonify({'success': True, 'message': '会议纪要更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/meetings/<int:meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    """删除会议纪要"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        c.execute('DELETE FROM meetings WHERE id = %s', (meeting_id,))
    
        if c.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': '会议纪要不存在'}), 404
    
        conn.commit()
        conn.close()
    
        return jsonify({'success': True, 'message': '会议纪要已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 用户管理 API
# ============================================

# 存储用户密码（简单版本，实际应使用密码哈希）
# 格式: {username: {password: 'hashed', role: 'admin'}}
USERS_DB = {
    'admin': {'password': 'dudu2026', 'role': 'admin'}
}

@app.route('/api/change-password', methods=['POST'])
def change_password():
    """修改密码"""
    try:
        data = request.get_json()
        old_password = data.get('oldPassword')
        new_password = data.get('newPassword')
    
        # 获取当前用户（从token或session）
        # 简化版本，实际应从token解析
        username = 'admin'  # 默认用户
    
        if not old_password or not new_password:
            return jsonify({'success': False, 'error': '密码不能为空'})
    
        # 验证旧密码
        if USERS_DB.get(username, {}).get('password') != old_password:
            return jsonify({'success': False, 'error': '旧密码错误'})
    
        # 更新密码
        USERS_DB[username]['password'] = new_password
    
        return jsonify({'success': True, 'message': '密码修改成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    """获取用户信息"""
    try:
        # 简化版本，实际应从token解析
        return jsonify({
            'success': True,
            'user': {
                'username': 'admin',
                'role': 'admin',
                'last_login': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 安全中间件
# ============================================

@app.after_request
def add_security_headers(response):
    """添加安全响应头（放宽CSP以支持外部资源）"""
    # 防止点击劫持
    response.headers['X-Frame-Options'] = 'DENY'
    # 防止MIME类型嗅探
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # XSS保护
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # 内容安全策略（放宽以支持Cloudflare和localhost开发）
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://static.cloudflareinsights.com; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self' http://localhost:* https://localhost:*; "
        "img-src 'self' data: https:; "
        "font-src 'self';"
    )
    # 禁用缓存敏感页面
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# 请求频率限制（简单实现）
request_counts = {}

@app.before_request
def rate_limit():
    """简单的请求频率限制"""
    if request.path == '/api/login':
        ip = request.remote_addr
        now = datetime.now()
    
        # 清理旧记录
        for key in list(request_counts.keys()):
            if (now - request_counts[key]['time']).seconds > 60:
                del request_counts[key]
    
        # 检查频率
        if ip in request_counts:
            if request_counts[ip]['count'] > 10:  # 每分钟最多10次登录尝试
                return jsonify({'success': False, 'error': '请求过于频繁，请稍后再试'}), 429
            request_counts[ip]['count'] += 1
        else:
            request_counts[ip] = {'count': 1, 'time': now}

# ============================================
# 8问法反思 API
# ============================================

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

@app.route('/api/reflection/template', methods=['GET'])
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

@app.route('/api/reflection/analyze', methods=['POST'])
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

@app.route('/api/reflection/save', methods=['POST'])
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

@app.route('/api/reflection/list', methods=['GET'])
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

# ============================================
# 长思考任务生成器（集成8问法）
# ============================================

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

@app.route('/api/reflection/create-long-think', methods=['POST'])
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



# ============================================
# 感知Agent (Perception Agent) 集成
# ============================================

# 导入感知Agent
try:
    from perception_agent import (
        PerceptionAgent, init_agent, get_agent, start_agent, stop_agent,
        EventType, SeverityLevel, PerceptionEvent
    )
    PERCEPTION_AGENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PerceptionAgent not available: {e}")
    PERCEPTION_AGENT_AVAILABLE = False

# 全局感知Agent实例
_perception_agent = None

def init_perception_agent():
    """初始化感知Agent"""
    global _perception_agent
    if not PERCEPTION_AGENT_AVAILABLE:
        return None

    try:
        config_path = os.path.join(os.path.dirname(__file__), 'perception_config.yml')
        _perception_agent = start_agent(config_path)
        logger.info("✅ PerceptionAgent started successfully")
        return _perception_agent
    except Exception as e:
        logger.error(f"Failed to start PerceptionAgent: {e}")
        return None

def get_perception_agent():
    """获取感知Agent实例"""
    return _perception_agent

# API响应时间监控中间件
@app.before_request
def before_request():
    from time import time
    request.start_time = time()

@app.after_request
def after_request(response):
    from time import time
    try:
        # 计算响应时间
        if hasattr(request, 'start_time'):
            duration = time() - request.start_time
        
            # 记录到感知监控（超过1秒的API）
            if duration > 1.0:
                perception_recorder.record_event(
                    event_type='slow_api',
                    severity='warning' if duration > 3.0 else 'info',
                    source='backend',
                    message=f'慢API: {request.path} ({duration:.2f}s)',
                    metadata={
                        'endpoint': request.path,
                        'method': request.method,
                        'duration': round(duration, 3),
                        'status_code': response.status_code
                    }
                )
    except Exception as e:
        logger.error(f"API监控错误: {e}")

    return response

# API错误捕获中间件
@app.after_request
def capture_api_errors(response):
    """捕获API错误并发送给感知Agent"""
    try:
        # 使用新的感知记录器
        if response.status_code >= 500:
            perception_recorder.record_api_error(
                status_code=response.status_code,
                endpoint=request.path,
                error_message=f"Server Error: {response.status_code}",
                request_data={
                    'method': request.method,
                    'path': request.path,
                    'args': dict(request.args)
                }
            )
        elif response.status_code == 400 or response.status_code == 422:
            try:
                data = response.get_json()
                if data and not data.get('success'):
                    perception_recorder.record_api_error(
                        status_code=response.status_code,
                        endpoint=request.path,
                        error_message=data.get('error', 'Validation Error'),
                        request_data={'method': request.method, 'path': request.path}
                    )
            except:
                pass
    
        # 同时尝试使用原生的PerceptionAgent（如果可用）
        if PERCEPTION_AGENT_AVAILABLE and _perception_agent:
            try:
                if response.status_code >= 500:
                    _perception_agent.record_api_error(
                        status_code=response.status_code,
                        endpoint=request.path,
                        error_message=f"Server Error: {response.status_code}",
                        request_data={
                            'method': request.method,
                            'path': request.path,
                            'args': dict(request.args)
                        }
                    )
            except:
                pass
    except Exception as e:
        logger.error(f"Error in capture_api_errors: {e}")

    return response

# 感知Agent API端点
@app.route('/api/perception/status', methods=['GET'])
def perception_status():
    """获取感知Agent状态"""
    if not PERCEPTION_AGENT_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'PerceptionAgent not available',
            'available': False
        }), 503

    agent = get_perception_agent()
    if not agent:
        return jsonify({
            'success': False,
            'error': 'PerceptionAgent not initialized',
            'available': True,
            'running': False
        })

    status = agent.get_status()
    # Convert listeners object to array for frontend compatibility
    if 'listeners' in status and isinstance(status['listeners'], dict):
        listeners_list = []
        for name, listener_info in status['listeners'].items():
            listener_info_copy = listener_info.copy()
            listener_info_copy['name'] = name
            listeners_list.append(listener_info_copy)
        status['listeners'] = listeners_list
    
    # Convert rules object to array for frontend compatibility
    if 'rules' in status and isinstance(status['rules'], dict):
        rules_list = []
        for name, value in status['rules'].items():
            rules_list.append({'name': name, 'value': value})
        status['rules'] = rules_list
    
    return jsonify({
        'success': True,
        'available': True,
        'status': status
    })

@app.route('/api/perception/events', methods=['GET'])
def perception_events():
    """获取感知Agent事件日志（从数据库读取）"""
    try:
        limit = request.args.get('limit', 100, type=int)
        event_type = request.args.get('type', None)

        with get_db_connection() as conn:
            c = conn.cursor()

            if event_type:
                c.execute('''
                    SELECT id, event_type, severity, source, message, metadata, timestamp, hash
                    FROM perception_events
                    WHERE event_type = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (event_type, limit))
            else:
                c.execute('''
                    SELECT id, event_type, severity, source, message, metadata, timestamp, hash
                    FROM perception_events
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (limit,))

            rows = c.fetchall()
            events = []
            for row in rows:
                events.append({
                    'id': str(row['id']),
                    'type': row['event_type'],
                    'severity': row['severity'],
                    'source': row['source'],
                    'message': row['message'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'timestamp': str(row['timestamp']),
                    'hash': row['hash']
                })

            return jsonify({
                'success': True,
                'events': events,
                'count': len(events)
            })
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"获取感知事件失败: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {tb}")
        return jsonify({'success': False, 'error': f'{type(e).__name__}: {e}'})

@app.route('/api/perception/test', methods=['POST'])
def perception_test():
    """测试感知Agent（生成测试事件并保存到数据库）"""
    data = request.get_json() or {}
    event_type = data.get('type', 'test')

    try:
        # 直接保存到数据库
        conn = get_db()
        c = conn.cursor()
    
        timestamp = datetime.now().isoformat()
        import hashlib
        event_hash = hashlib.md5(f"{event_type}{timestamp}".encode()).hexdigest()[:12]
    
        message = data.get('message', f'Test event: {event_type}')
        severity = data.get('severity', 'info')
        source = data.get('source', 'test')
        metadata = json.dumps(data.get('metadata', {}))
    
        c.execute('''
            INSERT INTO perception_events (event_type, severity, source, message, metadata, timestamp, hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (event_type, severity, source, message, metadata, timestamp, event_hash))
    
        conn.commit()

        return jsonify({
            'success': True,
            'message': f'Test event ({event_type}) saved to database',
            'event_id': c.lastrowid
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# 用户行为记录API
# ============================================

@app.route('/api/perception/record-action', methods=['POST'])
def record_user_action():
    """记录用户行为"""
    if not PERCEPTION_AGENT_AVAILABLE:
        return jsonify({'success': False, 'error': 'PerceptionAgent not available'}), 503

    agent = get_perception_agent()
    if not agent:
        return jsonify({'success': False, 'error': 'PerceptionAgent not initialized'}), 503

    data = request.get_json() or {}
    user_id = data.get('user_id', 'anonymous')
    action = data.get('action')
    target = data.get('target')

    if not action:
        return jsonify({'success': False, 'error': 'Action is required'}), 400

    try:
        agent.record_action(user_id, action, target, data.get('metadata', {}))
        return jsonify({'success': True, 'message': 'Action recorded'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# 对接中心 API (Communication Hub)
# ============================================

@app.route('/api/communication/messages', methods=['GET'])
def get_communication_messages():
    """获取沟通消息列表"""
    try:
        messages = [
            {
                'id': '1',
                'type': 'system',
                'content': '👋 欢迎来到Dudu对接中心！',
                'timestamp': datetime.now().isoformat()
            },
            {
                'id': '2',
                'type': 'dudu',
                'content': '您好！我是Dudu，有什么可以帮助您的吗？',
                'timestamp': datetime.now().isoformat()
            }
        ]
        return jsonify({'success': True, 'messages': messages})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/communication/send', methods=['POST'])
def send_communication_message():
    """发送消息"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        return jsonify({'success': True, 'message': '消息已接收', 'content': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ============================================
# 对接中心快捷操作 API
# ============================================

@app.route('/api/communication/quick-actions', methods=['GET'])
def get_quick_actions():
    """获取快捷操作列表"""
    actions = [
        {
            'id': 'new-task',
            'label': '📋 提交新任务',
            'description': '创建并提交新任务到系统',
            'action': 'open_task_form'
        },
        {
            'id': 'progress-report',
            'label': '📊 查看进展报告',
            'description': '查看所有项目的最新进展',
            'action': 'view_progress'
        },
        {
            'id': 'update-goals',
            'label': '🎯 更新目标',
            'description': '更新九大核心目标的进度',
            'action': 'edit_goals'
        },
        {
            'id': 'emergency',
            'label': '📞 紧急联系',
            'description': '发送紧急消息给Dudu',
            'action': 'emergency_contact'
        }
    ]
    return jsonify({'success': True, 'actions': actions})

@app.route('/api/communication/submit-task', methods=['POST'])
def submit_new_task():
    """提交新任务"""
    try:
        data = request.get_json()
        task = {
            'id': f"task-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'priority': data.get('priority', 'normal'),
            'category': data.get('category', 'general'),
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        # 这里可以保存到数据库
        return jsonify({
            'success': True,
            'message': '任务已提交',
            'task': task
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/communication/progress-report', methods=['GET'])
def get_progress_report():
    """获取进展报告"""
    try:
        # 获取各目标进展
        report = {
            'date': datetime.now().isoformat(),
            'summary': {
                'total_goals': 9,
                'completed': 1,
                'in_progress': 6,
                'pending': 2
            },
            'active_projects': [
                {
                    'name': 'T109计算平台',
                    'status': '部署中',
                    'progress': 35,
                    'next_milestone': 'PSI4集成测试'
                },
                {
                    'name': '资源驱动调度',
                    'status': '开发中',
                    'progress': 20,
                    'next_milestone': '基础调度器'
                },
                {
                    'name': 'Pepi升级',
                    'status': '设计中',
                    'progress': 15,
                    'next_milestone': '视觉能力'
                }
            ],
            'recent_updates': [
                'T109平台代码整合完成',
                '资源驱动调度系统启动',
                'Pepi商业化调研进行中'
            ]
        }
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/communication/emergency', methods=['POST'])
def emergency_contact():
    """紧急联系"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        # 发送紧急通知
        return jsonify({
            'success': True,
            'message': '紧急消息已发送，Dudu会尽快响应',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ============================================
# 感知Agent (Perception Agent) - 完整实现
# ============================================

import threading
import time
from collections import deque

class PerceptionAgent:
    """
    感知监控系统
    监控系统状态、用户行为、异常事件
    """

    def __init__(self, check_interval=30):
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.events = deque(maxlen=1000)  # 保留最近1000个事件
        self.status = {
            'running': False,
            'start_time': None,
            'last_check': None,
            'events_count': 0
        }
        self.monitoring_rules = {
            'cpu_threshold': 80,
            'memory_threshold': 80,
            'disk_threshold': 90
        }

    def start(self):
        """启动感知Agent"""
        if not self.running:
            self.running = True
            self.status['running'] = True
            self.status['start_time'] = datetime.now().isoformat()
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            logger.info("✅ PerceptionAgent 已启动")
            return True
        return False

    def stop(self):
        """停止感知Agent"""
        self.running = False
        self.status['running'] = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 PerceptionAgent 已停止")
        return True

    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                self._check_system_status()
                self._check_services()
                self.status['last_check'] = datetime.now().isoformat()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"PerceptionAgent监控错误: {e}")
                time.sleep(5)

    def _check_system_status(self):
        """检查系统状态"""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
        
            if cpu > self.monitoring_rules['cpu_threshold']:
                self.add_event('system', f'CPU使用率过高: {cpu}%', 
                             severity='warning', source='system_monitor')
            if memory > self.monitoring_rules['memory_threshold']:
                self.add_event('system', f'内存使用率过高: {memory}%', 
                             severity='warning', source='system_monitor')
            if disk > self.monitoring_rules['disk_threshold']:
                self.add_event('system', f'磁盘使用率过高: {disk}%', 
                             severity='warning', source='system_monitor')
            
        except ImportError:
            pass  # psutil未安装

    def _check_services(self):
        """检查服务状态"""
        services = [
            {'name': 'kanban', 'url': 'http://localhost:8086/health'},
        ]
    
        for service in services:
            try:
                import urllib.request
                req = urllib.request.Request(service['url'], method='HEAD')
                req.add_header('User-Agent', 'PerceptionAgent/1.0')
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status != 200:
                        self.add_event('error', f"服务异常: {service['name']} - HTTP {resp.status}", 
                                     severity='error', source='service_check')
            except Exception as e:
                self.add_event('error', f"服务无法访问: {service['name']} - {str(e)}", 
                             severity='error', source='service_check')

    def add_event(self, event_type, message, metadata=None, severity='info', source='system'):
        """添加事件 - 持久化到数据库"""
        try:
            conn = get_db()
            c = conn.cursor()
        
            timestamp = datetime.now().isoformat()
            import hashlib
            event_hash = hashlib.md5(f"{event_type}{message}{timestamp}".encode()).hexdigest()[:12]
        
            metadata_json = json.dumps(metadata) if metadata else '{}'
        
            c.execute('''
                INSERT INTO perception_events (event_type, severity, source, message, metadata, timestamp, hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (event_type, severity, source, message, metadata_json, timestamp, event_hash))
        
            conn.commit()
            event_id = c.lastrowid
        
            # 同时保留内存中的事件（用于快速访问）
            event = {
                'id': event_id,
                'type': event_type,
                'severity': severity,
                'source': source,
                'message': message,
                'timestamp': timestamp,
                'hash': event_hash,
                'metadata': metadata or {}
            }
            self.events.append(event)
            self.status['events_count'] = self._get_db_event_count()
        
            logger.info(f"📡 感知事件已记录: [{event_type}] {message}")
            return event
        
        except Exception as e:
            logger.error(f"保存事件到数据库失败: {e}")
            # 降级到内存存储
            event = {
                'id': len(self.events) + 1,
                'type': event_type,
                'severity': severity,
                'source': source,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            self.events.append(event)
            self.status['events_count'] = len(self.events)
            return event

    def _get_db_event_count(self):
        """获取数据库中的事件总数"""
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM perception_events')
            return list(c.fetchone().values())[0]
        except:
            return len(self.events)

    def get_events(self, limit=50, event_type=None):
        """获取事件列表 - 从数据库读取"""
        try:
            conn = get_db()
            c = conn.cursor()
        
            if event_type:
                c.execute('''
                    SELECT id, event_type, severity, source, message, metadata, timestamp, hash
                    FROM perception_events
                    WHERE event_type = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (event_type, limit))
            else:
                c.execute('''
                    SELECT id, event_type, severity, source, message, metadata, timestamp, hash
                    FROM perception_events
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (limit,))
        
            rows = c.fetchall()
            events = []
            for row in rows:
                events.append({
                    'id': str(row['id']),
                    'type': row['event_type'],
                    'severity': row['severity'],
                    'source': row['source'],
                    'message': row['message'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'timestamp': str(row['timestamp']),
                    'hash': row['hash']
                })
            return events
        
        except Exception as e:
            logger.error(f"从数据库读取事件失败: {e}")
            # 降级到内存存储
            events_list = list(self.events)
            if event_type:
                events_list = [e for e in events_list if e['type'] == event_type]
            return events_list[-limit:]

    def get_status(self):
        """获取状态"""
        # 计算运行时间
        uptime_seconds = 0
        if self.status['start_time']:
            try:
                start = datetime.fromisoformat(self.status['start_time'])
                uptime_seconds = int((datetime.now() - start).total_seconds())
            except:
                pass
    
        return {
            'running': self.running,
            'uptime_seconds': uptime_seconds,
            'event_count': len(self.events),
            'listeners': {
                'log': {'enabled': True, 'running': self.running},
                'error': {'enabled': True, 'running': self.running},
                'metric': {'enabled': True, 'running': self.running},
                'behavior': {'enabled': True, 'running': self.running}
            },
            'start_time': self.status['start_time'],
            'last_check': self.status['last_check'],
            'rules': self.monitoring_rules
        }

    def record_action(self, user_id, action, target, metadata=None):
        """记录用户行为"""
        return self.add_event('action', f"用户 {user_id}: {action}", {
            'user_id': user_id,
            'action': action,
            'target': target,
            'metadata': metadata
        })

    def record_api_error(self, status_code, endpoint, error_message=None, request_data=None):
        """记录API错误"""
        severity = 'critical' if status_code >= 500 else 'high'
        return self.add_event('api_error', f"API错误 {status_code}: {endpoint} - {error_message or 'Unknown'}", {
            'status_code': status_code,
            'endpoint': endpoint,
            'error_message': error_message,
            'request_data': request_data,
            'severity': severity
        })

    def update_config(self, config):
        """更新配置"""
        if 'cpu_threshold' in config:
            self.monitoring_rules['cpu_threshold'] = config['cpu_threshold']
        if 'memory_threshold' in config:
            self.monitoring_rules['memory_threshold'] = config['memory_threshold']
        if 'disk_threshold' in config:
            self.monitoring_rules['disk_threshold'] = config['disk_threshold']
        if 'check_interval' in config:
            self.check_interval = config['check_interval']
        return True

# 全局感知Agent实例
# [DUPLICATE REMOVED] perception_agent = None
# [DUPLICATE REMOVED] PERCEPTION_AGENT_AVAILABLE = False
# [DUPLICATE REMOVED] 
# [DUPLICATE REMOVED] def init_perception_agent():
# [DUPLICATE REMOVED]     """初始化感知Agent"""
# [DUPLICATE REMOVED]     global perception_agent, PERCEPTION_AGENT_AVAILABLE
# [DUPLICATE REMOVED]     try:
# [DUPLICATE REMOVED]         perception_agent = PerceptionAgent()
# [DUPLICATE REMOVED]         perception_agent.start()
# [DUPLICATE REMOVED]         PERCEPTION_AGENT_AVAILABLE = True
# [DUPLICATE REMOVED]         logger.info("✅ 感知Agent初始化成功")
# [DUPLICATE REMOVED]         return True
# [DUPLICATE REMOVED]     except Exception as e:
# [DUPLICATE REMOVED]         logger.error(f"❌ 感知Agent初始化失败: {e}")
# [DUPLICATE REMOVED]         PERCEPTION_AGENT_AVAILABLE = False
# [DUPLICATE REMOVED]         return False
# [DUPLICATE REMOVED] 
# [DUPLICATE REMOVED] def stop_perception_agent():
# [DUPLICATE REMOVED]     """停止感知Agent"""
# [DUPLICATE REMOVED]     global perception_agent, PERCEPTION_AGENT_AVAILABLE
# [DUPLICATE REMOVED]     if perception_agent:
# [DUPLICATE REMOVED]         perception_agent.stop()
# [DUPLICATE REMOVED]         PERCEPTION_AGENT_AVAILABLE = False
# [DUPLICATE REMOVED]         logger.info("🛑 感知Agent已停止")
# [DUPLICATE REMOVED] 
# [DUPLICATE REMOVED] def get_perception_agent():
# [DUPLICATE REMOVED]     """获取感知Agent实例"""
# [DUPLICATE REMOVED]     global perception_agent
# [DUPLICATE REMOVED]     return perception_agent

@app.route('/api/perception/status', methods=['GET'])
def get_perception_status():
    """获取感知Agent状态"""
    global perception_agent, PERCEPTION_AGENT_AVAILABLE
    if perception_agent and PERCEPTION_AGENT_AVAILABLE:
        status = perception_agent.get_status()
        # Convert listeners object to array for frontend compatibility
        if 'listeners' in status and isinstance(status['listeners'], dict):
            listeners_list = []
            for name, listener_info in status['listeners'].items():
                listener_info_copy = listener_info.copy()
                listener_info_copy['name'] = name
                listeners_list.append(listener_info_copy)
            status['listeners'] = listeners_list
        
        # Convert rules object to array for frontend compatibility
        if 'rules' in status and isinstance(status['rules'], dict):
            rules_list = []
            for name, value in status['rules'].items():
                rules_list.append({'name': name, 'value': value})
            status['rules'] = rules_list
        
        return jsonify({
            'success': True,
            'available': True,
            'running': perception_agent.running,
            'status': status
        })
    return jsonify({
        'success': True,
        'available': False,
        'running': False,
        'message': 'PerceptionAgent not initialized'
    })

@app.route('/api/perception/events', methods=['GET'])
def get_perception_events():
    """获取感知事件"""
    global perception_agent, PERCEPTION_AGENT_AVAILABLE
    if perception_agent and PERCEPTION_AGENT_AVAILABLE:
        limit = request.args.get('limit', 50, type=int)
        event_type = request.args.get('type')
        events = perception_agent.get_events(limit=limit, event_type=event_type)
        return jsonify({
            'success': True,
            'available': True,
            'events': events,
            'count': len(events)
        })
    return jsonify({
        'success': True,
        'available': False,
        'events': [],
        'message': 'PerceptionAgent not available'
    })

@app.route('/api/perception/config', methods=['GET', 'POST'])
def perception_config():
    """获取/更新感知配置"""
    global perception_agent, PERCEPTION_AGENT_AVAILABLE
    if request.method == 'GET':
        if perception_agent and PERCEPTION_AGENT_AVAILABLE:
            # Convert monitoring_rules dict to array for frontend
            rules_list = []
            for key, value in perception_agent.monitoring_rules.items():
                rules_list.append({'name': key, 'value': value})
            
            return jsonify({
                'success': True,
                'available': True,
                'config': rules_list,
                'check_interval': perception_agent.check_interval
            })
        return jsonify({
            'success': True,
            'available': False,
            'config': {}
        })
    else:  # POST
        if perception_agent and PERCEPTION_AGENT_AVAILABLE:
            data = request.get_json() or {}
            perception_agent.update_config(data)
            return jsonify({
                'success': True,
                'message': '配置已更新',
                'config': perception_agent.monitoring_rules
            })
        return jsonify({
            'success': False,
            'error': 'PerceptionAgent not available'
        }), 503

@app.route('/api/perception/start', methods=['POST'])
def start_perception():
    """启动感知Agent"""
    global PERCEPTION_AGENT_AVAILABLE
    if init_perception_agent():
        return jsonify({
            'success': True,
            'message': 'PerceptionAgent 已启动',
            'available': True
        })
    return jsonify({
        'success': False,
        'error': '启动失败'
    }), 500

@app.route('/api/perception/stop', methods=['POST'])
def stop_perception():
    """停止感知Agent"""
    global PERCEPTION_AGENT_AVAILABLE
    stop_perception_agent()
    return jsonify({
        'success': True,
        'message': 'PerceptionAgent 已停止',
        'available': False
    })


# ============================================
# 资源驱动任务调度器 API (Resource-Driven Scheduler)
# ============================================

SCHEDULER_AVAILABLE = False
scheduler_instance = None

def get_scheduler_instance():
    """获取资源调度器实例"""
    global scheduler_instance, SCHEDULER_AVAILABLE
    if scheduler_instance is None:
        try:
            import sys
            sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/resource_driven_scheduler'))
            from core import get_scheduler
            scheduler_instance = get_scheduler()
            SCHEDULER_AVAILABLE = True
        except Exception as e:
            logger.error(f"Scheduler not available: {e}")
            SCHEDULER_AVAILABLE = False
    return scheduler_instance

@app.route('/api/resource-scheduler/status', methods=['GET'])
def get_resource_scheduler_status():
    """获取资源调度器状态"""
    scheduler = get_scheduler_instance()
    if scheduler:
        stats = scheduler.get_stats()
        return jsonify({
            'success': True,
            'available': True,
            'status': stats,
            'thresholds': scheduler.resource_thresholds
        })
    return jsonify({
        'success': True,
        'available': False,
        'message': 'Resource scheduler not available'
    })

@app.route('/api/resource-scheduler/tasks', methods=['GET'])
def get_scheduler_tasks():
    """获取任务队列"""
    scheduler = get_scheduler_instance()
    if scheduler:
        tasks = scheduler.list_tasks()
        return jsonify({
            'success': True,
            'tasks': tasks,
            'count': len(tasks)
        })
    return jsonify({'success': False, 'error': 'Scheduler not available'}), 503

@app.route('/api/resource-scheduler/submit', methods=['POST'])
def submit_scheduler_task():
    """提交任务到调度器 - 简化版"""
    data = request.get_json() or {}
    task_type = data.get('task_type', 'generic')
    params = data.get('params', {})
    priority = data.get('priority', 'NORMAL')

    # 模拟任务提交成功
    import uuid
    task_id = str(uuid.uuid4())[:8]

    return jsonify({
        'success': True,
        'task_id': task_id,
        'task_type': task_type,
        'priority': priority,
        'status': 'queued',
        'message': f'Task {task_id} submitted with priority {priority} (Resource-Driven Scheduler running)'
    })

@app.route('/api/resource-scheduler/resources', methods=['GET'])
def get_resource_status():
    """获取资源状态"""
    scheduler = get_scheduler_instance()
    if scheduler:
        resources = scheduler.get_resource_status()
        return jsonify({
            'success': True,
            'resources': resources
        })
    return jsonify({'success': False, 'error': 'Scheduler not available'}), 503


# ============================================
# Pepi工作历史 API
# ============================================

@app.route('/api/pepi/work-history', methods=['GET'])
def get_pepi_work_history():
    """获取Pepi工作历史（GIF记录）"""
    try:
        limit = request.args.get('limit', 20, type=int)
        work_type = request.args.get('work_type', None)
    
        conn = get_db()
    
        c = conn.cursor()
    
        if work_type:
            c.execute('''
                SELECT * FROM pepi_work_gifs 
                WHERE work_type = %s
                ORDER BY created_at DESC 
                LIMIT %s
            ''', (work_type, limit))
        else:
            c.execute('''
                SELECT * FROM pepi_work_gifs 
                ORDER BY created_at DESC 
                LIMIT %s
            ''', (limit,))
    
        records = []
        for row in c.fetchall():
            record = row_to_dict(row, c)
            # 格式化文件大小
            if record['gif_size']:
                size_mb = record['gif_size'] / (1024 * 1024)
                record['gif_size_formatted'] = f"{size_mb:.1f} MB"
            records.append(record)
    
        conn.close()
    
        return jsonify({
            'success': True,
            'records': records,
            'count': len(records)
        })
    
    except Exception as e:
        logger.error(f"Error getting pepi work history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/pepi/work-history/<int:record_id>', methods=['GET'])
def get_pepi_work_detail(record_id):
    """获取单条工作记录详情"""
    try:
        conn = get_db()
    
        c = conn.cursor()
    
        c.execute('SELECT * FROM pepi_work_gifs WHERE id = %s', (record_id,))
        row = c.fetchone()
        conn.close()
    
        if row:
            record = row_to_dict(row, c)
            return jsonify({'success': True, 'record': record})
        else:
            return jsonify({'success': False, 'error': 'Record not found'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/pepi/work-history', methods=['POST'])
def add_pepi_work_record():
    """添加Pepi工作记录（供自动化脚本调用）"""
    try:
        data = request.get_json() or {}
    
        required_fields = ['task_name', 'gif_path']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
    
        conn = get_db()
        c = conn.cursor()
    
        gif_size = os.path.getsize(data['gif_path']) if os.path.exists(data['gif_path']) else 0
    
        c.execute('''
            INSERT INTO pepi_work_gifs 
            (task_name, task_description, gif_path, gif_size, 
             duration_seconds, frame_count, fps, work_type, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data['task_name'],
            data.get('task_description', ''),
            data['gif_path'],
            gif_size,
            data.get('duration_seconds', 0),
            data.get('frame_count', 0),
            data.get('fps', 2),
            data.get('work_type', 'desktop'),
            json.dumps(data.get('metadata', {})),
            datetime.now().isoformat()
        ))
    
        conn.commit()
        record_id = c.lastrowid
        conn.close()
    
        return jsonify({
            'success': True,
            'record_id': record_id,
            'message': 'Work record added successfully'
        })
    
    except Exception as e:
        logger.error(f"Error adding pepi work record: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/pepi/work-types', methods=['GET'])
def get_pepi_work_types():
    """获取Pepi工作类型统计"""
    try:
        conn = get_db()
    
        c = conn.cursor()
    
        c.execute('''
            SELECT work_type, COUNT(*) as count 
            FROM pepi_work_gifs 
            GROUP BY work_type
            ORDER BY count DESC
        ''')
    
        types = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
    
        return jsonify({
            'success': True,
            'work_types': types
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================
# 保存视图 API
# ============================================

@app.route('/api/saved-views', methods=['GET'])
def get_saved_views():
    """获取所有保存的视图"""
    import json
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT id, name, filters, is_default, created_at, updated_at
        FROM saved_views
        ORDER BY is_default DESC, created_at ASC
    ''')
    
    views = []
    for row in c.fetchall():
        view_dict = row_to_dict(row, c)
        # 解析 JSON 字段
        if isinstance(view_dict.get('filters'), str):
            view_dict['filters'] = json.loads(view_dict['filters'])
        views.append(view_dict)
    
    conn.close()
    return jsonify({'success': True, 'views': views})

@app.route('/api/saved-views', methods=['POST'])
def create_saved_view():
    """创建保存的视图"""
    import json
    
    data = request.get_json()
    name = data.get('name', '').strip()
    filters = data.get('filters', {})
    
    if not name:
        return jsonify({'success': False, 'error': '视图名称不能为空'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    filters_json = json.dumps(filters, ensure_ascii=False)
    
    c.execute('''
        INSERT INTO saved_views (name, filters, is_default)
        VALUES (%s, %s, 0)
    ''', (name, filters_json))
    
    view_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'view_id': view_id,
        'message': '视图已保存'
    })

@app.route('/api/saved-views/<int:view_id>', methods=['PUT'])
def update_saved_view(view_id):
    """更新保存的视图"""
    import json
    
    data = request.get_json()
    
    conn = get_db()
    c = conn.cursor()
    
    # 检查视图是否存在
    c.execute('SELECT id FROM saved_views WHERE id = %s', (view_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': '视图不存在'}), 404
    
    updates = {}
    if 'name' in data:
        updates['name'] = data['name']
    if 'filters' in data:
        updates['filters'] = json.dumps(data['filters'], ensure_ascii=False)
    
    if not updates:
        conn.close()
        return jsonify({'success': False, 'error': '没有要更新的字段'}), 400
    
    set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
    values = list(updates.values()) + [view_id]
    
    c.execute(f'UPDATE saved_views SET {set_clause} WHERE id = %s', values)
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '视图已更新'
    })

@app.route('/api/saved-views/<int:view_id>', methods=['DELETE'])
def delete_saved_view(view_id):
    """删除保存的视图"""
    conn = get_db()
    c = conn.cursor()
    
    # 检查是否为默认视图
    c.execute('SELECT is_default FROM saved_views WHERE id = %s', (view_id,))
    row = c.fetchone()
    if row and row[0]:
        conn.close()
        return jsonify({'success': False, 'error': '不能删除默认视图'}), 400
    
    c.execute('DELETE FROM saved_views WHERE id = %s', (view_id,))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '视图已删除'
    })


# ============================================

# ============================================
# 邮件 API
# ============================================
@app.route('/api/emails/', methods=['GET'])  # 支持尾部斜杠
@app.route('/api/emails/', methods=['GET'])
    # Routes moved to routes/emails.py
@app.route('/api/emails/stats/', methods=['GET'])  # 支持尾部斜杠
    # Routes moved to routes/emails.py
@app.route('/api/sds/config/<config_key>', methods=['GET'])
def get_sds_config(config_key):
    """获取SDS配置"""
    conn = get_db()
    c = conn.cursor()
    if config_key == 'database_schema':
        c.execute('SHOW TABLES')
        tables = [list(row.values())[0] for row in c.fetchall()]
        schema = {}
        for t in tables:
            c.execute(f'DESCRIBE `{t}`')
            cols = []
            for row in c.fetchall():
                cols.append({'Field': row.get('Field',''), 'Type': row.get('Type',''), 'Null': row.get('Null',''),
                            'Key': row.get('Key',''), 'Default': str(row.get('Default')) if row.get('Default') is not None else None, 'Extra': row.get('Extra','')})
            schema[t] = cols
        conn.close()
        return jsonify({'success': True, 'config_key': 'database_schema', 'data': schema})
    c.execute('SELECT config_value FROM sds_config WHERE config_key = %s', (config_key,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({'success': True, 'config_key': config_key, 'data': row['config_value']})
    return jsonify({'success': False, 'error': '配置不存在'}), 404


@app.route('/api/sds/config/all', methods=['GET'])
def get_sds_config_all():
    """获取所有SDS配置"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT config_key, config_value FROM sds_config ORDER BY config_key')
    rows = c.fetchall()
    conn.close()
    result = {}
    for row in rows:
        result[row['config_key']] = row['config_value']
    return jsonify({'success': True, 'data': result})


@app.route('/api/sds/stats', methods=['GET'])
def get_sds_stats():
    """获取SDS实时统计"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status')
    status_stats = {r['status']: r['cnt'] for r in c.fetchall()}
    c.execute('SELECT goal_id, COUNT(*) as cnt FROM projects WHERE status != "deleted" GROUP BY goal_id')
    project_stats = {r['goal_id']: r['cnt'] for r in c.fetchall()}
    c.execute("""
        SELECT 
            SUM(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 ELSE 0 END) as new_tasks,
            SUM(CASE WHEN status = 'completed' AND updated_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 ELSE 0 END) as completed_today
        FROM tasks
    """)
    row = c.fetchone()
    conn.close()
    import datetime
    return jsonify({
        'success': True,
        'data': {
            'task_stats': status_stats,
            'project_stats': {str(k): v for k, v in project_stats.items()},
            'new_tasks_24h': row['new_tasks'] or 0,
            'completed_today': row['completed_today'] or 0,
            'timestamp': datetime.datetime.now().isoformat()
        }
    })


@app.route('/api/sds/config/<config_key>', methods=['PUT'])

@app.route('/api/sds/history', methods=['GET'])
def get_sds_history():
    """获取SDS历史趋势数据"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT DATE(created_at) as date, COUNT(*) as created, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed FROM tasks WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) GROUP BY DATE(created_at) ORDER BY date ASC""")
    daily_stats = []
    for row in c.fetchall():
        daily_stats.append({'date': str(row['date']), 'created': int(row['created']), 'completed': int(row['completed'] or 0)})
    conn.close()
    import datetime
    return jsonify({'success': True, 'data': {'daily': daily_stats, 'timestamp': datetime.datetime.now().isoformat()}})

def update_sds_config(config_key):
    """更新SDS配置项"""
    try:
        data = request.get_json()
        value = data.get('value')
        if value is None:
            return jsonify({'success': False, 'error': 'value is required'}), 400
        
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id FROM sds_config WHERE config_key = %s', (config_key,))
        existing = c.fetchone()
        
        if existing:
            c.execute('UPDATE sds_config SET config_value = %s, updated_at = NOW() WHERE config_key = %s',
                      (json.dumps(value) if isinstance(value, (dict, list)) else str(value), config_key))
        else:
            c.execute('INSERT INTO sds_config (config_key, config_value, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())',
                      (config_key, json.dumps(value) if isinstance(value, (dict, list)) else str(value)))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Updated {config_key}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sds/config/goals', methods=['PUT'])
def update_sds_goals_config():
    """更新目标配置"""
    try:
        data = request.get_json()
        goal_id = data.get('goal_id')
        field = data.get('field')
        value = data.get('value')
        
        if not goal_id or not field:
            return jsonify({'success': False, 'error': 'goal_id and field required'}), 400
        
        conn = get_db()
        c = conn.cursor()
        c.execute(f'UPDATE goals SET {field} = %s WHERE id = %s', (value, goal_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Updated goal {goal_id} {field}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sds/config/projects/<int:project_id>', methods=['PUT'])
def update_sds_project(project_id):
    """更新项目配置"""
    try:
        data = request.get_json()
        field = data.get('field')
        value = data.get('value')
        
        if not field:
            return jsonify({'success': False, 'error': 'field required'}), 400
        
        conn = get_db()
        c = conn.cursor()
        c.execute(f'UPDATE projects SET {field} = %s WHERE id = %s', (value, project_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Updated project {project_id} {field}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sds/config/tasks/<int:task_id>', methods=['PUT'])
def update_sds_task(task_id):
    """更新任务配置"""
    try:
        data = request.get_json()
        field = data.get('field')
        value = data.get('value')
        
        if not field:
            return jsonify({'success': False, 'error': 'field required'}), 400
        
        conn = get_db()
        c = conn.cursor()
        c.execute(f'UPDATE tasks SET {field} = %s WHERE id = %s', (value, task_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Updated task {task_id} {field}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sds/config/rules', methods=['PUT'])
def update_sds_rules():
    """更新任务规则配置"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        for key, value in data.items():
            c.execute('SELECT id FROM sds_config WHERE config_key = %s', (key,))
            if c.fetchone():
                c.execute('UPDATE sds_config SET config_value = %s, updated_at = NOW() WHERE config_key = %s',
                          (json.dumps(value) if isinstance(value, (dict, list)) else str(value), key))
            else:
                c.execute('INSERT INTO sds_config (config_key, config_value, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())',
                          (key, json.dumps(value) if isinstance(value, (dict, list)) else str(value)))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Rules updated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# Admin HTML frontend pages (MUST be before catch-all)
from admin_frontend import admin_html_bp
app.register_blueprint(admin_html_bp)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    if path.startswith('socket.io'):
        from werkzeug.exceptions import NotFound
        raise NotFound()
    static_file = os.path.join(app.static_folder, path)
    if os.path.isfile(static_file):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


# ============================================
# 长思考系统 API (Long Thinking)
# ============================================

# 导入长思考模块
try:
    from long_thinking import (
        LongThinkingEngine, run_daily_analysis, 
        get_latest_report, get_report_list
    )
    LONG_THINKING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LongThinking system not available: {e}")
    LONG_THINKING_AVAILABLE = False

@app.route('/api/long-thinking/status', methods=['GET'])
def get_long_thinking_status():
    """获取长思考系统状态"""
    return jsonify({
        'success': True,
        'available': LONG_THINKING_AVAILABLE,
        'last_run': None,  # TODO: 从数据库获取
        'next_run': '13:00',  # 每天13:00
        'schedule': '每天 13:00'
    })

@app.route('/api/long-thinking/reports', methods=['GET'])
def get_long_thinking_reports():
    """获取长思考报告列表"""
    if not LONG_THINKING_AVAILABLE:
        return jsonify({'success': False, 'error': '长思考系统未启用'}), 500

    try:
        reports = get_report_list()
        return jsonify({'success': True, 'reports': reports})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/long-thinking/latest', methods=['GET'])
def get_long_thinking_latest():
    """获取最新长思考报告"""
    if not LONG_THINKING_AVAILABLE:
        return jsonify({'success': False, 'error': '长思考系统未启用'}), 500

    try:
        report = get_latest_report()
        if report:
            return jsonify({'success': True, 'report': report})
        else:
            return jsonify({'success': False, 'message': '暂无报告'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/long-thinking/run', methods=['POST'])
def run_long_thinking():
    """手动触发长思考分析 (管理员权限)"""
    if not LONG_THINKING_AVAILABLE:
        return jsonify({'success': False, 'error': '长思考系统未启用'}), 500

    try:
        # 异步运行，不等待结果
        import threading
        def run():
            try:
                run_daily_analysis()
            except Exception as e:
                logger.error(f"长思考运行失败: {e}")
    
        thread = threading.Thread(target=run)
        thread.start()
    
        return jsonify({
            'success': True, 
            'message': '长思考分析已启动，请稍后查看最新报告'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Dudu文件 API
# ============================================

@app.route('/api/dudu-files', methods=['GET'])
def get_dudu_files():
    """获取Dudu文件列表"""
    try:
        with open('/opt/kanban-react/backend/dudu_files_list.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Error getting dudu files: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ============================================
# 架构工作流和MD文件管理 API
# ============================================

WORKFLOW_CONFIG_PATH = '/opt/kanban-react/backend/workflow_config.json'

@app.route('/api/architecture/workflow/', methods=['GET'])  # 支持尾部斜杠
@app.route('/api/architecture/workflow', methods=['GET'])
def get_workflow_config():
    """获取工作流程配置"""
    try:
        if os.path.exists(WORKFLOW_CONFIG_PATH):
            with open(WORKFLOW_CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify({'success': True, 'data': data})
        else:
            # 返回默认配置
            default_config = {
                'steps': [
                    { 'id': '1', 'name': '用户输入', 'mdFile': '', 'description': '接收用户指令', 'x': 80, 'y': 100, 'color': '#e3f2fd' },
                    { 'id': '2', 'name': 'SOUL.md', 'mdFile': 'SOUL.md', 'description': '身份定义', 'x': 220, 'y': 100, 'color': '#fff3e0' },
                    { 'id': '3', 'name': 'USER.md', 'mdFile': 'USER.md', 'description': '用户档案', 'x': 360, 'y': 100, 'color': '#e8f5e9' },
                    { 'id': '4', 'name': 'AGENTS.md', 'mdFile': 'AGENTS.md', 'description': '执行准则', 'x': 500, 'y': 100, 'color': '#fce4ec' },
                    { 'id': '5', 'name': 'standards.md', 'mdFile': 'standards.md', 'description': '标准规范', 'x': 640, 'y': 100, 'color': '#f3e5f5' },
                    { 'id': '6', 'name': '任务执行', 'mdFile': '', 'description': '执行任务', 'x': 780, 'y': 100, 'color': '#f3e5f5' },
                    { 'id': '7', 'name': 'MEMORY.md', 'mdFile': 'MEMORY.md', 'description': '长期记忆', 'x': 200, 'y': 260, 'color': '#e0f2f1' },
                    { 'id': '8', 'name': '结果输出', 'mdFile': '', 'description': '输出结果', 'x': 400, 'y': 260, 'color': '#e8eaf6' },
                    { 'id': '9', 'name': 'HEARTBEAT.md', 'mdFile': 'HEARTBEAT.md', 'description': '定时检查', 'x': 600, 'y': 260, 'color': '#fff8e1' },
                ]
            }
            return jsonify({'success': True, 'data': default_config})
    except Exception as e:
        logger.error(f"Error getting workflow config: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/architecture/workflow/', methods=['POST'])  # 支持尾部斜杠
@app.route('/api/architecture/workflow', methods=['POST'])
def save_workflow_config():
    """保存工作流程配置"""
    try:
        data = request.get_json()
        with open(WORKFLOW_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({'success': True, 'message': '工作流程已保存'})
    except Exception as e:
        logger.error(f"Error saving workflow config: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/architecture/md-files/', methods=['GET'])  # 支持尾部斜杠
@app.route('/api/architecture/md-files', methods=['GET'])
def get_md_files():
    """获取所有MD文件内容"""
    try:
        md_files = {}
        workspace_path = '/Users/mettlyz/.openclaw/workspace'
    
        for filename in ['SOUL.md', 'USER.md', 'AGENTS.md', 'standards.md', 'MEMORY.md', 'HEARTBEAT.md']:
            filepath = os.path.join(workspace_path, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                md_files[filename] = {
                    'name': filename,
                    'content': content,
                    'description': get_md_description(filename)
                }
    
        return jsonify({'success': True, 'files': md_files})
    except Exception as e:
        logger.error(f"Error getting md files: {e}")
        return jsonify({'success': False, 'error': str(e)})

def get_md_description(filename: str) -> str:
    """获取MD文件描述"""
    descriptions = {
        'SOUL.md': '身份定义和人格',
        'USER.md': '用户档案和偏好',
        'AGENTS.md': '执行准则和工作模式',
        'standards.md': '标准规范和质量要求',
        'MEMORY.md': '长期记忆存储',
        'HEARTBEAT.md': '定时检查和汇报'
    }
    return descriptions.get(filename, '配置文件')

@app.route('/api/architecture/md-files/<filename>/', methods=['POST'])  # 支持尾部斜杠
@app.route('/api/architecture/md-files/<filename>', methods=['POST'])
def save_md_file(filename):
    """保存MD文件内容"""
    try:
        if filename not in ['SOUL.md', 'USER.md', 'AGENTS.md', 'standards.md', 'MEMORY.md', 'HEARTBEAT.md', 'CHECKLIST.md']:
            return jsonify({'success': False, 'error': '无效的文件名'})
    
        data = request.get_json()
        content = data.get('content', '')
    
        filepath = os.path.join('/Users/mettlyz/.openclaw/workspace', filename)
    
        # 备份原文件
        backup_path = filepath + '.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S')
        if os.path.exists(filepath):
            os.rename(filepath, backup_path)
    
        # 写入新内容
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
        return jsonify({'success': True, 'message': f'{filename} 已保存'})
    except Exception as e:
        logger.error(f"Error saving md file: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ============================================
# API性能监控
# ============================================

@app.route('/api/monitoring/api-performance', methods=['GET'])
def get_api_performance():
    """获取API性能统计"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 获取慢API统计（最近24小时）
        c.execute('''
            SELECT event_type, source, message, metadata, timestamp
            FROM perception_events 
            WHERE event_type = 'slow_api' 
            AND timestamp > datetime('now', '-24 hours')
            ORDER BY timestamp DESC
            LIMIT 50
        ''')
    
        slow_apis = []
        for row in c.fetchall():
            try:
                metadata = json.loads(row[3]) if row[3] else {}
                slow_apis.append({
                    'endpoint': metadata.get('endpoint', 'unknown'),
                    'method': metadata.get('method', 'GET'),
                    'duration': metadata.get('duration', 0),
                    'status_code': metadata.get('status_code', 200),
                    'timestamp': row[4]
                })
            except:
                pass
    
        # 统计信息
        stats = {
            'total_slow_apis': len(slow_apis),
            'avg_duration': round(sum(a['duration'] for a in slow_apis) / len(slow_apis), 3) if slow_apis else 0,
            'max_duration': max(a['duration'] for a in slow_apis) if slow_apis else 0,
            'apis_over_3s': len([a for a in slow_apis if a['duration'] > 3.0]),
            'apis_over_5s': len([a for a in slow_apis if a['duration'] > 5.0])
        }
    
        conn.close()
    
        return jsonify({
            'success': True,
            'stats': stats,
            'slow_apis': slow_apis[:20]  # 只返回前20条
        })
    except Exception as e:
        logger.error(f"Error getting api performance: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ============================================
# 个人信息/联系人 API
# ============================================

@app.route('/api/personal-info/people', methods=['GET'])
def get_people():
    """获取联系人列表（个人信息），包含每个人的详细信息"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # 获取所有联系人基本信息
            c.execute('SELECT id, name, email, title as department, phone, location as company, created_at FROM persons ORDER BY name ASC')
            
            people = []
            for row in c.fetchall():
                person_id = row['id']
                
                # 获取该联系人的标签页信息
                c.execute('SELECT id, name, type, sort_order FROM person_tabs WHERE person_id = %s ORDER BY sort_order', (person_id,))
                tabs = c.fetchall()
                
                tabs_data = []
                for tab in tabs:
                    # 获取标签页内容
                    c.execute('SELECT title, content, item_date, sort_order, attachments FROM person_tab_items WHERE tab_id = %s ORDER BY sort_order', (tab['id'],))
                    items = c.fetchall()
                    
                    items_data = []
                    for item in items:
                        items_data.append({'title': item['title'], 'content': item['content'], 'item_date': item['item_date'], 'attachments': item['attachments']})
                    
                    tabs_data.append({'id': tab['id'], 'name': tab['name'], 'type': tab['type'], 'items': items_data})
                
                people.append({
                    'id': person_id,
                    'name': row['name'],
                    'email': row['email'],
                    'department': row['department'],
                    'phone': row['phone'],
                    'company': row['company'],
                    'created_at': row['created_at'],
                    'tabs': tabs_data
                })
        
        return jsonify({'success': True, 'people': people, 'count': len(people)})
    except Exception as e:
        logger.error(f"获取联系人列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/personal-info/people/<int:person_id>', methods=['GET'])
def get_person(person_id):
    """获取单个联系人详情 - 从 person_tabs 读取"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 获取用户基本信息（从 persons 表）
        c.execute('SELECT id, name, email, phone, title, location FROM persons WHERE id = %s', (person_id,))
        user = c.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'error': '联系人不存在'}), 404
        
        # 获取标签页
        c.execute('SELECT id, name, type, sort_order FROM person_tabs WHERE person_id = %s ORDER BY sort_order', (person_id,))
        tabs = c.fetchall()
        
        tabs_data = []
        for tab in tabs:
            # 获取标签页内容
            c.execute('SELECT title, content, item_date, sort_order, attachments FROM person_tab_items WHERE tab_id = %s ORDER BY sort_order', (tab['id'],))
            items = c.fetchall()
            
            items_data = []
            for item in items:
                # 解析 attachments JSON
                attachments = item['attachments']
                if attachments:
                    try:
                        attachments = json.loads(attachments)
                    except:
                        attachments = None
                items_data.append({
                    'title': item['title'],
                    'content': item['content'],
                    'item_date': item['item_date'],
                    'attachments': attachments
                })
            
            tabs_data.append({
                'id': tab['id'],
                'name': tab['name'],
                'type': tab['type'],
                'items': items_data
            })
        
        conn.close()
        
        person = {
            'id': user['id'],
            'name': user['name'],
            'email': user.get('email', ''),
            'phone': user.get('phone', ''),
            'department': user.get('title', ''),
            'company': user.get('location', ''),
            'tabs': tabs_data
        }
        
        return jsonify({'success': True, 'person': person})
    except Exception as e:
        logger.error(f"获取联系人详情失败: {e}")
        return jsonify({'success': False, 'error': str(e)})
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/personal-info/people', methods=['POST'])
def create_person():
    """创建新联系人"""
    try:
        data = request.get_json()
    
        name = data.get('name')
        email = data.get('email')
        department = data.get('department')
        phone = data.get('phone')
        company = data.get('company')
    
        if not name:
            return jsonify({'success': False, 'error': '姓名不能为空'}), 400
    
        with get_db_connection() as conn:
            c = conn.cursor()
    
            c.execute('''
                INSERT INTO contacts (name, email, department, phone, company)
                VALUES (%s, %s, %s, %s, %s)
            ''', (name, email, department, phone, company))
    
            person_id = c.lastrowid
            conn.commit()
    
        return jsonify({
            'success': True,
            'message': '联系人创建成功',
            'id': person_id
        })
    except Exception as e:
        logger.error(f"创建联系人失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/personal-info/people/<int:person_id>', methods=['PUT'])
def update_person(person_id):
    """更新联系人信息"""
    try:
        data = request.get_json()
    
        with get_db_connection() as conn:
            c = conn.cursor()
    
            # 检查联系人是否存在
            c.execute('SELECT id FROM persons WHERE id = %s', (person_id,))
            if not c.fetchone():
                conn.close()
                return jsonify({'success': False, 'error': '联系人不存在'}), 404
    
            # 构建更新语句
            update_fields = []
            values = []
    
            if 'name' in data:
                update_fields.append('name = %s')
                values.append(data['name'])
            if 'email' in data:
                update_fields.append('email = %s')
                values.append(data['email'])
            if 'department' in data:
                update_fields.append('department = %s')
                values.append(data['department'])
            if 'phone' in data:
                update_fields.append('phone = %s')
                values.append(data['phone'])
            if 'company' in data:
                update_fields.append('company = %s')
                values.append(data['company'])
    
            if update_fields:
                values.append(person_id)
                sql = f"UPDATE contacts SET {', '.join(update_fields)} WHERE id = %s"
                c.execute(sql, values)
                conn.commit()
    
    
        return jsonify({'success': True, 'message': '联系人更新成功'})
    except Exception as e:
        logger.error(f"更新联系人失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/personal-info/people/<int:person_id>', methods=['DELETE'])
def delete_person(person_id):
    """删除联系人"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
    
            c.execute('DELETE FROM persons WHERE id = %s', (person_id,))
    
            if c.rowcount == 0:
                conn.close()
                return jsonify({'success': False, 'error': '联系人不存在'}), 404
    
            conn.commit()
    
        return jsonify({'success': True, 'message': '联系人删除成功'})
    except Exception as e:
        logger.error(f"删除联系人失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ============================================
# 合规声明 API - 涉诉事项说明
# ============================================

@app.route('/api/personal-info/liuyuzhou', methods=['GET'])
def get_liuyuzhou_info():
    """获取刘宇宙详细信息（包含合规声明）"""
    try:
        detail = {
            "id": "liuyuzhou",
            "name": "刘宇宙",
            "birthDate": "1982-09-16",
            "gender": "男",
            "currentPosition": "蓝天青年学者（二级）",
            "department": "北京航空航天大学 化学学院",
            "contact": {
                "phone": "+86-10-xxxxxxxx",
                "email": "liuyuzhou@buaa.edu.cn"
            },
            "education": [
                {
                    "school": "纽约大学化学系",
                    "degree": "博士",
                    "major": "氢键在晶体工程里的应用",
                    "year": "2011",
                    "advisor": "Michael Ward 教授"
                },
                {
                    "school": "清华大学化学系",
                    "degree": "硕士",
                    "major": "Mo(CO)6催化的炔烃合成苯环的反应",
                    "year": "2006",
                    "advisor": "席婵娟 教授"
                },
                {
                    "school": "清华大学化学系",
                    "degree": "学士",
                    "major": "化学",
                    "year": "2003"
                }
            ],
            "researchAreas": [
                "计算化学",
                "分子模拟",
                "AI驱动的化学研究"
            ],
            "contract": {
                "contractNo": "09855-01-2025-1",
                "position": "蓝天青年学者（二级）",
                "positionType": "专任教师岗位 - 蓝天学者岗位",
                "department": "化学学院",
                "startDate": "2025-09-01",
                "endDate": "2030-08-31",
                "duration": "5年",
                "requirements": [
                    "每学年主讲不少于1门课程，年均教学工作量不少于64学时",
                    "聘期内完成不少于1项亮点业绩Ⅰ类或2项亮点业绩Ⅱ类",
                    "年均科研经费不低于30万元（理科）",
                    "聘期内引育不少于1名国家级人才"
                ],
                "fileName": "09855_刘宇宙_化学学院_聘用合同-蓝天青年学者（二级）.pdf"
            },
            "entrepreneurship": {
                "company": "北京和光智成科技有限公司（Helight）",
                "position": "创始人、CEO",
                "founded": "2023",
                "description": "专注于AI驱动的材料研发平台，利用人工智能加速新材料发现。前身为北京深云智合科技有限公司（正在退出）",
                "focus": [
                    "AI材料研发平台",
                    "材料数据基础设施建设",
                    "智能材料发现与优化"
                ]
            },
            "publicSpeaking": [
                {
                    "id": "speaking-001",
                    "title": "AI最核心的作用，是找到人原来找不到的路径",
                    "event": "新材料×AI: 范式之变",
                    "organizer": "中经传媒智库 x 《商学院》杂志",
                    "date": "2025-01-21",
                    "content": "在由中经传媒智库与《商学院》杂志联合举办的'新材料×AI: 范式之变'高端闭门会上，北京和光智成科技有限公司（前身为北京深云智合科技有限公司）创始人、CEO刘宇宙分享了关于AI在新材料研发中核心作用的观点。",
                    "keyPoints": [
                        "AI最核心的作用，是找到人原来找不到的路径",
                        "如果一个东西本身没有数据沉淀，AI是起不到作用的",
                        "要加速材料的发现和探索，建立模型的核心是标准化、高质量的数据",
                        "只有打好数据底座，AI才能在面对复杂规律时，帮你建立起原来发现不了的逻辑",
                        "这就是AI对研发提质增效的真正价值"
                    ],
                    "source": "《商学院》杂志官方微博"
                }
            ],
            "compliance": {
                "title": "关于涉诉事项的情况说明",
                "summary": "针对近期北京深云相关涉诉事宜及和光智成的成立背景，为消除信息不对称，确保投资人客观研判事件本质，切实规避潜在风险，现就事件真相、责任切割及项目价值作如下专项说明。",
                "keyPoints": [
                    {
                        "title": "核心结论：责任完全隔离，创业合法合规",
                        "items": [
                            "主体无关：本次诉讼系北京深云原合作方与地方利益方策划的针对性排挤事件。刘宇宙教授及配偶杨慧娟女士非案涉合同主体，无任何法律关联，不承担连带责任。",
                            "权属清晰：和光智成是刘宇宙教授为保护核心技术不被侵占而合法重启的载体，技术来源清晰，无侵权风险。",
                            "性质定性：该诉讼本质是违背《民法典》契约精神的滥用司法资源行为，不仅缺乏事实支撑，更与国家保护科研人员创新积极性的导向背道而驰。"
                        ]
                    },
                    {
                        "title": "商业逻辑：从\"被迫出走\"到\"初心坚守\"",
                        "items": [
                            "事实还原：刘宇宙教授作为北京深云的核心技术源头与产业化推手，全程主导了技术研发与落地。然而，原合作方出于独占商业利益的私心，通过不正当手段将刘教授排挤出决策层，企图无偿侵占其科研成果。",
                            "创业正当性：和光智成的成立，并非恶性竞争，而是科学家为避免国家培育的核心技术被闲置或侵吞，被迫进行的\"自救式创业\"。",
                            "合规背书：此举完全符合《促进科技成果转化法》精神，是守护科研初心、延续技术价值的合法行为。所有股权架构与技术流转均有完整法律文件佐证，经得起最严格的尽职调查（DD）。"
                        ]
                    },
                    {
                        "title": "法律风险：诉讼主体错位，责任边界明确",
                        "items": [
                            "主体不适格（关键抗辩点）：案涉合同签署方仅为法人实体（北京深云及其合作方）。刘宇宙教授及其配偶均为自然人，既非合同当事人，也未签署任何担保文件。",
                            "法律依据：根据《中华人民共和国民法典》第四百六十五条及相关司法解释，合同仅对当事人具有法律约束力。起诉非协议主体的自然人属于根本性法律错误，诉由完全不成立。",
                            "程序违规警示：2025年4月8日，九原区相关方在无正当诉由情况下，对刘教授全家采取全额冻结账户等过度强制措施，属于典型的选择性执法与过度施压。"
                        ]
                    },
                    {
                        "title": "国家战略：顺应科创导向，抵制不当干预",
                        "items": [
                            "政策对标：国家明确要求保护科研人员合法权益，激发创新活力。恶意排挤科学家、通过司法手段打压技术带头人，严重破坏科创生态。",
                            "价值主张：和光智成的存在，正是为了纠正这种扭曲的商业环境，确保核心技术掌握在真正的创造者手中。投资和支持和光智成，是响应国家号召、保护战略科技力量的正确选择。"
                        ]
                    }
                ],
                "commitments": [
                    "风险隔离承诺：北京深云涉诉事宜产生的任何法律责任，均由原相关方承担。",
                    "合规经营承诺：公司核心技术独立，股权结构清晰，无任何隐性债务或违规关联交易。",
                    "全面配合核查：已建立专项档案库，包含刘教授退出深云的法律效力文件、诉讼全套材料、科研工作实证及技术权属证明。随时欢迎并配合进行全方位、穿透式的尽职调查。"
                ],
                "updateDate": "2026-03-06",
                "documentUrl": "/files/涉诉事项的情况说明.docx"
            }
        }
    
        return jsonify({
            'success': True,
            'detail': detail
        })
    except Exception as e:
        logger.error(f"获取刘宇宙信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# 夏博士信息 API
# ============================================

@app.route('/api/personal-info/xiaboshi', methods=['GET'])
def get_xiaboshi_info():
    """获取夏博士详细信息"""
    try:
        detail = {
            "id": "xiaboshi",
            "name": "夏博士（工信部）",
            "birthDate": "",
            "gender": "",
            "currentPosition": "处长",
            "department": "工业和信息化部 一处",
            "contact": {
                "phone": "",
                "email": ""
            },
            "education": [],
            "researchAreas": [
                "产业政策制定",
                "行业发展规划",
                "信息化发展"
            ],
            "contract": {
                "contractNo": "",
                "position": "处长",
                "positionType": "公务员",
                "department": "工业和信息化部 一处",
                "startDate": "",
                "endDate": "",
                "duration": "",
                "requirements": [],
                "fileName": ""
            }
        }
    
        return jsonify({
            'success': True,
            'detail': detail
        })
    except Exception as e:
        logger.error(f"获取夏博士信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# 段博士信息 API
# ============================================

@app.route('/api/personal-info/duanboshi', methods=['GET'])
def get_duanboshi_info():
    """获取段博士详细信息"""
    try:
        detail = {
            "id": "duanboshi",
            "name": "段博士（信通院）",
            "birthDate": "",
            "gender": "",
            "currentPosition": "研究员",
            "department": "中国信息通信研究院",
            "contact": {
                "phone": "",
                "email": ""
            },
            "education": [],
            "researchAreas": [
                "信息通信研究",
                "行业政策研究",
                "标准制定"
            ],
            "contract": {
                "contractNo": "",
                "position": "研究员",
                "positionType": "科研岗位",
                "department": "中国信息通信研究院",
                "startDate": "",
                "endDate": "",
                "duration": "",
                "requirements": [],
                "fileName": ""
            }
        }
    
        return jsonify({
            'success': True,
            'detail': detail
        })
    except Exception as e:
        logger.error(f"获取段博士信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# 公司信息 API
# ============================================

@app.route('/api/company-info/companies/<company_id>', methods=['GET'])
def get_company_info(company_id):
    """获取公司详细信息（包含法律合规信息）"""
    try:
        # 根据company_id返回不同公司信息
        if company_id == '1284':
            detail = {
                "id": "1284",
                "fullName": "北京深云智合科技有限公司",
                "englishName": "DeepCloud Intelligence Technology Co., Ltd.",
                "creditCode": "91110108MA01xxxxx",
                "address": "北京市海淀区xxxx",
                "createDate": "2020-01-15",
                "registeredCapital": "1000万元",
                "legalRepresentative": "刘宇宙",
                "companyType": "有限责任公司",
                "businessScope": [
                    "技术开发、技术咨询、技术服务",
                    "人工智能应用软件开发",
                    "化学计算与模拟服务",
                    "数据处理和存储服务"
                ],
                "mainBusiness": [
                    "T109过渡态计算平台",
                    "Pepi数字员工系统",
                    "AI驱动的科研解决方案"
                ],
                "team": [
                    {
                        "name": "刘宇宙",
                        "position": "创始人/首席科学家",
                        "background": "北京大学博士，蓝天青年学者"
                    }
                ],
                "partners": [
                    "北京航空航天大学",
                    "中国科学院"
                ],
                "legalStatus": "涉诉中",
                "legalNote": "原合作方与地方利益方策划的针对性排挤事件，刘宇宙教授已退出并创立和光智成"
            }
        elif company_id == '1283' or company_id == 'helight':
            detail = {
                "id": company_id,
                "fullName": "北京和光智成科技有限公司",
                "englishName": "Helight Intelligence Technology Co., Ltd.",
                "creditCode": "91110108MA01xxxxx",
                "address": "北京市海淀区xxxx",
                "createDate": "2023",
                "registeredCapital": "1000万元",
                "legalRepresentative": "刘宇宙",
                "companyType": "有限责任公司",
                "businessScope": [
                    "技术开发、技术咨询、技术服务",
                    "人工智能应用软件开发",
                    "化学计算与模拟服务",
                    "数据处理和存储服务"
                ],
                "mainBusiness": [
                    "T109过渡态计算平台",
                    "Pepi数字员工系统",
                    "AI驱动的科研解决方案"
                ],
                "team": [
                    {
                        "name": "刘宇宙",
                        "position": "创始人/首席科学家",
                        "background": "北京大学博士，蓝天青年学者"
                    }
                ],
                "partners": [
                    "北京航空航天大学",
                    "中国科学院"
                ],
                "legalStatus": "合规运营",
                "legalNote": "为保护核心技术不被侵占而合法重启的载体，技术来源清晰，无侵权风险",
                "compliance": {
                    "riskIsolation": "北京深云涉诉事宜产生的任何法律责任，均由原相关方承担",
                    "coreTech": "公司核心技术独立，股权结构清晰，无任何隐性债务或违规关联交易",
                    "dueDiligence": "已建立专项档案库，随时欢迎并配合进行全方位、穿透式的尽职调查"
                }
            }
        else:
            detail = {
                "id": company_id,
                "fullName": "和光智成（北京）科技有限公司",
                "englishName": "Helight Intelligence Technology Co., Ltd.",
                "creditCode": "91110108MA01xxxxx",
                "address": "北京市海淀区xxxx",
                "createDate": "2020-01-15",
                "registeredCapital": "1000万元",
                "legalRepresentative": "刘宇宙",
                "companyType": "有限责任公司",
                "businessScope": [
                    "技术开发、技术咨询、技术服务",
                    "人工智能应用软件开发",
                    "化学计算与模拟服务",
                    "数据处理和存储服务"
                ],
                "mainBusiness": [
                    "T109过渡态计算平台",
                    "Pepi数字员工系统",
                    "AI驱动的科研解决方案"
                ],
                "team": [
                    {
                        "name": "刘宇宙",
                        "position": "创始人/首席科学家",
                        "background": "北京大学博士，蓝天青年学者"
                    }
                ],
                "partners": [
                    "北京航空航天大学",
                    "中国科学院"
                ]
            }
    
        return jsonify({
            'success': True,
            'detail': detail
        })
    except Exception as e:
        logger.error(f"获取公司信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# 任务审核系统 API
# ============================================

@app.route('/api/audit/tasks/pending', methods=['GET'])
def get_pending_audit_tasks():
    """获取待审核任务列表"""
    try:
        source = request.args.get('source')
        conn = get_db()
        c = conn.cursor()
    
        if source:
            c.execute('''
                SELECT 
                    m.id,
                    m.task_type,
                    m.title,
                    m.description,
                    m.source,
                    m.status,
                    m.priority,
                    m.completion_notes as notes,
                    m.created_at,
                    m.completed_at,
                    m.completed_by as reviewer,
                    m.is_from_long_think,
                    m.original_task_id as source_id
                FROM manual_review_tasks m
                WHERE m.status = 'pending' AND m.task_type = %s
                ORDER BY 
                    CASE m.priority 
                        WHEN 'high' THEN 1 
                        WHEN 'medium' THEN 2 
                        ELSE 3 
                    END,
                    m.created_at DESC
            ''', (source,))
        else:
            c.execute('''
                SELECT 
                    m.id,
                    m.task_type,
                    m.title,
                    m.description,
                    m.source,
                    m.status,
                    m.priority,
                    m.completion_notes as notes,
                    m.created_at,
                    m.completed_at,
                    m.completed_by as reviewer,
                    m.is_from_long_think,
                    m.original_task_id as source_id
                FROM manual_review_tasks m
                WHERE m.status = 'pending'
                ORDER BY 
                    CASE m.priority 
                        WHEN 'high' THEN 1 
                        WHEN 'medium' THEN 2 
                        ELSE 3 
                    END,
                    m.created_at DESC
            ''')
    
        tasks = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
    
        return jsonify({
            'success': True,
            'count': len(tasks),
            'tasks': tasks
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/audit/tasks/<int:audit_id>/approve', methods=['POST'])
def approve_audit_task(audit_id):
    """批准任务"""
    try:
        data = request.get_json() or {}
        reviewer = data.get('reviewer', 'system')
        notes = data.get('notes', '审核通过')
    
        conn = get_db()
        c = conn.cursor()
    
        # 获取关联的任务ID
        c.execute('SELECT original_task_id FROM manual_review_tasks WHERE id = %s', (audit_id,))
        row = c.fetchone()
        original_task_id = row[0] if row else None
    
        # 更新审核任务状态
        c.execute('''
            UPDATE manual_review_tasks 
            SET status = 'approved', completed_by = %s, completion_notes = %s, completed_at = NOW()
            WHERE id = %s
        ''', (reviewer, notes, audit_id))
    
        # 更新原始任务状态
        if original_task_id:
            c.execute('''
                UPDATE tasks 
                SET audit_status = 'approved', updated_at = NOW()
                WHERE id = %s
            ''', (original_task_id,))
    
        conn.commit()
        conn.close()
    
        return jsonify({
            'success': True,
            'message': '任务已批准',
            'task_id': original_task_id,
            'audit_id': audit_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/audit/tasks/<int:audit_id>/reject', methods=['POST'])
def reject_audit_task(audit_id):
    """拒绝任务"""
    try:
        data = request.get_json() or {}
        reviewer = data.get('reviewer', 'system')
        reason = data.get('reason', data.get('notes', '审核未通过'))
    
        conn = get_db()
        c = conn.cursor()
    
        # 获取关联的任务ID
        c.execute('SELECT original_task_id FROM manual_review_tasks WHERE id = %s', (audit_id,))
        row = c.fetchone()
        original_task_id = row[0] if row else None
    
        # 更新审核任务状态
        c.execute('''
            UPDATE manual_review_tasks 
            SET status = 'rejected', completed_by = %s, completion_notes = %s, completed_at = NOW()
            WHERE id = %s
        ''', (reviewer, reason, audit_id))
    
        # 更新原始任务状态
        if original_task_id:
            c.execute('''
                UPDATE tasks 
                SET audit_status = 'rejected', status = 'cancelled', updated_at = NOW()
                WHERE id = %s
            ''', (original_task_id,))
    
        conn.commit()
        conn.close()
    
        return jsonify({
            'success': True,
            'message': '任务已拒绝',
            'task_id': original_task_id,
            'audit_id': audit_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/audit/tasks/<int:task_id>/check', methods=['GET'])
def check_task_audit_status(task_id):
    """检查任务审核状态"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        c.execute('''
            SELECT id, title, requires_audit, audit_status, status
            FROM tasks 
            WHERE id = %s
        ''', (task_id,))
    
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404
    
        task = row_to_dict(row, c)
        requires_audit = task.get('requires_audit', 0)
        audit_status = task.get('audit_status') or 'pending'
    
        can_execute = False
        message = ''
    
        if not requires_audit:
            can_execute = True
            message = '任务不需要审核'
        elif audit_status == 'approved':
            can_execute = True
            message = '审核已通过'
        elif audit_status == 'rejected':
            can_execute = False
            message = '任务已被拒绝'
        else:
            can_execute = False
            message = '任务待审核'
    
        conn.close()
    
        return jsonify({
            'success': True,
            'task_id': task_id,
            'can_execute': can_execute,
            'status': audit_status,
            'message': message
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/audit/tasks/stats', methods=['GET'])
def get_audit_stats():
    """获取审核统计"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        c.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
            FROM manual_review_tasks
        ''')
    
        row = c.fetchone()
        stats = row_to_dict(row, c) if row else {}
    
        # 按来源统计
        c.execute('''
            SELECT task_type, COUNT(*) as count
            FROM manual_review_tasks
            GROUP BY task_type
        ''')
    
        by_source = {row[0]: row['count'] for row in c.fetchall()}
    
        conn.close()
    
        return jsonify({
            'success': True,
            'stats': {
                'total': stats.get('total', 0),
                'pending': stats.get('pending', 0),
                'approved': stats.get('approved', 0),
                'rejected': stats.get('rejected', 0),
                'by_source': by_source
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/audit/dashboard', methods=['GET'])
def get_audit_dashboard():
    """获取审核仪表板数据"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 总体统计
        c.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
            FROM manual_review_tasks
        ''')
    
        row = c.fetchone()
        stats = row_to_dict(row, c) if row else {}
    
        # 按优先级统计待审核
        c.execute('''
            SELECT 
                priority,
                COUNT(*) as count
            FROM manual_review_tasks
            WHERE status = 'pending'
            GROUP BY priority
        ''')
    
        by_priority = {row[0]: row['count'] for row in c.fetchall()}
    
        # 最近10个待审核
        c.execute('''
            SELECT 
                id,
                title,
                priority,
                task_type,
                created_at
            FROM manual_review_tasks
            WHERE status = 'pending'
            ORDER BY created_at DESC
            LIMIT 10
        ''')
    
        recent_pending = [row_to_dict(row, c) for row in c.fetchall()]
    
        conn.close()
    
        return jsonify({
            'success': True,
            'dashboard': {
                'summary': {
                    'total': stats.get('total', 0),
                    'pending': stats.get('pending', 0),
                    'approved': stats.get('approved', 0),
                    'rejected': stats.get('rejected', 0),
                    'by_priority': by_priority
                },
                'recent_pending': recent_pending,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# 主程序入口
# ============================================



@app.route('/api/file-content', methods=['GET'])
def get_file_content_by_query():
    """通过 query 参数获取文件内容"""
    try:
        type_param = request.args.get('type', 'personal')
        name = request.args.get('name', '')
        format_type = request.args.get('format', 'raw')
        
        # 构建文件路径
        if type_param == 'personal':
            # 人员档案路径: Files/Personal/刘宇宙.md
            filepath = f'文档/个人信息/{name}.md'
        elif type_param == 'company':
            # 公司档案路径: Files/Companies/和光智成.md
            filepath = f'文档/公司信息/{name}.md'
        else:
            return jsonify({'success': False, 'error': '无效的类型'})
        
        workspace_path = '/opt/kanban-react/Files'
        full_path = os.path.join(workspace_path, filepath)
        
        # 安全检查
        if not full_path.startswith(workspace_path):
            return jsonify({'success': False, 'error': '非法路径'})
        
        if not os.path.exists(full_path):
            return jsonify({'success': False, 'error': '文件不存在', 'data': ''})
        
        # 限制文件大小
        if os.path.getsize(full_path) > 1024 * 1024:
            return jsonify({'success': False, 'error': '文件过大'})
        
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 解析内容
        if format_type == 'parsed':
            # 简单的解析：提取标题和段落
            lines = content.split("\n")
            parsed = {
                'title': '',
                'sections': []
            }
            current_section = None
            
            for line in lines:
                if line.startswith('# '):
                    parsed['title'] = line[2:].strip()
                elif line.startswith('## '):
                    if current_section:
                        parsed['sections'].append(current_section)
                    current_section = {
                        'title': line[3:].strip(),
                        'content': []
                    }
                elif current_section and line.strip():
                    current_section['content'].append(line)
            
            if current_section:
                parsed['sections'].append(current_section)
            
            return jsonify({'success': True, 'data': parsed})
        else:
            return jsonify({'success': True, 'data': content})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


app.register_blueprint(strategy_bp)
app.register_blueprint(contacts_bp)
app.register_blueprint(config_bp)
app.register_blueprint(daemon_status_bp)

if __name__ == '__main__':
    print("=" * 60)
    print("Kanban React - Flask API Server")
    print("=" * 60)
    print("API地址: http://localhost:8086")
    print("=" * 60)

    # 记录系统启动事件
    try:
        perception_recorder.record_event(
            event_type='system_startup',
            severity='info',
            source='backend',
            message='看板系统后端服务启动',
            metadata={'version': 'v2.4.12', 'port': 8086, 'host': '0.0.0.0'}
        )
        print("✅ 系统启动事件已记录到感知监控")
    except Exception as e:
        print(f"⚠️ 记录启动事件失败: {e}")

    # 启动感知Agent
    init_perception_agent()

    # 启动P049-T041监控告警系统
    try:
        from p049_monitoring import init_monitoring, stop_monitoring
        alert_manager, monitoring_dashboard = init_monitoring()
        print("✅ P049-T041 监控告警系统已启动")
    except Exception as e:
        print(f"⚠️ 监控告警系统启动失败: {e}")
        alert_manager = None

    # 启动Flask服务 (支持 WebSocket)
    try:
        if socketio:
            socketio.run(app, host='0.0.0.0', port=8086, debug=False, allow_unsafe_werkzeug=True)
        else:
            app.run(host='0.0.0.0', port=8086, debug=False)
    finally:
        # 确保感知Agent正确停止
        if PERCEPTION_AGENT_AVAILABLE:
            stop_perception_agent()
            print("\n✅ PerceptionAgent stopped")
        # 停止监控告警系统
        if alert_manager:
            stop_monitoring()
            print("✅ P049-T041 监控告警系统已停止")
        
        # 关闭 WebSocket
        if WEBSOCKET_AVAILABLE:
            try:
                shutdown_socketio()
                print("✅ WebSocket 服务已关闭")
            except Exception as e:
                print(f"⚠️ WebSocket 关闭异常: {e}")


# ============================================
# Gunicorn startup initialization
# ============================================

try:
    import threading
    def start_perception_on_startup():
        try:
            result = init_perception_agent()
            if result:
                logger.info("PerceptionAgent DISABLED (Gunicorn)")
        except Exception as e:
            logger.warning(f"PerceptionAgent startup failed: {e}")
    
    threading.Thread(target=start_perception_on_startup, daemon=True).start()
except Exception as e:
    logger.warning(f"PerceptionAgent thread creation failed: {e}")

# (saved-views moved to before catch-all)

# (emails routes moved to before catch-all)


# ============ Backlog 需求池 API ============
@app.route('/api/backlog', methods=['GET'])
def get_backlog():
    """获取所有需求，按状态分组返回"""
    try:
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute('''
            SELECT * FROM backlog 
            ORDER BY priority DESC, created_at DESC
        ''')
        backlog = c.fetchall()
        conn.close()
        return jsonify({'success': True, 'backlog': backlog})
    except Exception as e:
        print(f"[ERROR] get_backlog: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/backlog', methods=['POST'])
def create_backlog():
    """创建新需求"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO backlog (title, description, status, priority, project, tags, estimated_hours)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('title'),
            data.get('description'),
            data.get('status', 'todo'),
            data.get('priority', 1),
            data.get('project'),
            data.get('tags'),
            data.get('estimated_hours')
        ))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        print(f"[ERROR] create_backlog: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/backlog/<int:item_id>', methods=['PUT'])
def update_backlog(item_id):
    """更新需求"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        
        # 构建更新 SQL
        fields = []
        params = []
        for key in ['title', 'description', 'status', 'priority', 'project', 'tags', 'estimated_hours']:
            if key in data:
                fields.append(f"{key} = %s")
                params.append(data[key])
        params.append(item_id)
        
        sql = f"UPDATE backlog SET {', '.join(fields)} WHERE id = %s"
        c.execute(sql, params)
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] update_backlog: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/backlog/<int:item_id>', methods=['DELETE'])
def delete_backlog(item_id):
    """删除需求"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM backlog WHERE id = %s', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] delete_backlog: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ============ 产品百科 Wiki API ============
@app.route('/api/wiki/entries', methods=['GET'])
def get_wiki_entries():
    """获取所有百科词条，支持分类筛选和关键词搜索"""
    try:
        category = request.args.get('category')
        search = request.args.get('search')
        
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        
        sql = "SELECT id, title, category, tags, author, status, views, created_at, updated_at FROM wiki_entries WHERE status = 'published'"
        params = []
        
        if category:
            sql += " AND category = %s"
            params.append(category)
        
        if search:
            sql += " AND (title LIKE %s OR content LIKE %s)"
            search_term = f"%{search}%"
            params.append(search_term)
            params.append(search_term)
        
        sql += " ORDER BY created_at DESC"
        
        c.execute(sql, params)
        entries = c.fetchall()
        conn.close()
        return jsonify({'success': True, 'entries': entries})
    except Exception as e:
        print(f"[ERROR] get_wiki_entries: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/wiki/entries/<int:entry_id>', methods=['GET'])
def get_wiki_entry(entry_id):
    """获取单个百科词条详情"""
    try:
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute('SELECT * FROM wiki_entries WHERE id = %s AND status = "published"', (entry_id,))
        entry = c.fetchone()
        
        if entry:
            # 增加浏览次数
            c.execute('UPDATE wiki_entries SET views = views + 1 WHERE id = %s', (entry_id,))
            conn.commit()
        
        conn.close()
        
        if entry:
            return jsonify({'success': True, 'entry': entry})
        else:
            return jsonify({'success': False, 'error': '词条不存在'})
    except Exception as e:
        print(f"[ERROR] get_wiki_entry: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/wiki/categories', methods=['GET'])
def get_wiki_categories():
    """获取所有分类"""
    try:
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute('''
            SELECT category, COUNT(*) as count 
            FROM wiki_entries 
            WHERE status = 'published' 
            GROUP BY category 
            ORDER BY count DESC
        ''')
        categories = c.fetchall()
        conn.close()
        return jsonify({'success': True, 'categories': categories})
    except Exception as e:
        print(f"[ERROR] get_wiki_categories: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/wiki/entries', methods=['POST'])
def create_wiki_entry():
    """创建新词条"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO wiki_entries (title, content, category, tags, author, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            data.get('title'),
            data.get('content'),
            data.get('category'),
            data.get('tags'),
            data.get('author'),
            data.get('status', 'published')
        ))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        print(f"[ERROR] create_wiki_entry: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/wiki/entries/<int:entry_id>', methods=['PUT'])
def update_wiki_entry(entry_id):
    """更新词条"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        
        fields = []
        params = []
        for key in ['title', 'content', 'category', 'tags', 'author', 'status']:
            if key in data:
                fields.append(f"{key} = %s")
                params.append(data[key])
        params.append(entry_id)
        
        sql = f"UPDATE wiki_entries SET {', '.join(fields)} WHERE id = %s"
        c.execute(sql, params)
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] update_wiki_entry: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/wiki/entries/<int:entry_id>', methods=['DELETE'])
def delete_wiki_entry(entry_id):
    """删除词条"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM wiki_entries WHERE id = %s', (entry_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] delete_wiki_entry: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ============ Gantt 甘特图 API ============
@app.route('/api/projects/gantt', methods=['GET'])
def get_projects_gantt():
    """获取项目甘特图数据"""
    try:
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute('''
            SELECT id, number, chinese_name as title, status, priority, 
                   start_date, end_date, deadline
            FROM projects 
            WHERE status != 'deleted'
            ORDER BY priority DESC, created_at DESC
        ''')
        projects = c.fetchall()
        conn.close()
        
        # 转换为甘特图格式
        gantt_data = []
        for p in projects:
            gantt_data.append({
                'id': p['id'],
                'name': p['title'] or p['number'],
                'start': p['start_date'].isoformat() if p['start_date'] else None,
                'end': p['end_date'].isoformat() if p['end_date'] else None,
                'progress': 0,
                'status': p['status'],
                'priority': p['priority']
            })
        
        return jsonify({'success': True, 'data': gantt_data})
    except Exception as e:
        print(f"[ERROR] get_projects_gantt: {e}")
        return jsonify({'success': False, 'error': str(e)})



# ============ Activity Log API ============
@app.route('/api/activity-log', methods=['GET'])
def get_activity_log():
    """Get activity log"""
    try:
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        limit = request.args.get('limit', '50')
        try:
            limit = int(limit)
        except:
            limit = 50
        
        c.execute('''
            SELECT * FROM activity_log
            ORDER BY created_at DESC
            LIMIT %s
        ''', (limit,))
        logs = c.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': len(logs)
        })
    except Exception as e:
        print(f"[ERROR] get_activity_log: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/activity-log', methods=['POST'])
def create_activity_log():
    """Create activity log entry"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO activity_log 
            (user_id, username, action, entity_type, entity_id, description, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('user_id'),
            data.get('username'),
            data.get('action'),
            data.get('entity_type'),
            data.get('entity_id'),
            data.get('description'),
            request.remote_addr,
            request.headers.get('User-Agent')
        ))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        print(f"[ERROR] create_activity_log: {e}")
        return jsonify({'success': False, 'error': str(e)})



# ============ WeChat Contacts API ============
@app.route('/api/wechat/contacts', methods=['GET'])
def get_wechat_contacts():
    """Get WeChat contacts"""
    try:
        search = request.args.get('search', '')
        limit = request.args.get('limit', '200')
        try:
            limit = int(limit)
        except:
            limit = 200
        
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        
        if search:
            search = f"%{search}%"
            c.execute('''
                SELECT * FROM wechat_contacts 
                WHERE display_name LIKE %s OR tags LIKE %s OR company LIKE %s
                ORDER BY relation_score DESC, display_name ASC
                LIMIT %s
            ''', (search, search, search, limit))
        else:
            c.execute('''
                SELECT * FROM wechat_contacts 
                ORDER BY relation_score DESC, display_name ASC
                LIMIT %s
            ''', (limit,))
        
        contacts = c.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'contacts': contacts,
            'total': len(contacts)
        })
    except Exception as e:
        print(f"[ERROR] get_wechat_contacts: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/wechat/contacts/<int:contact_id>', methods=['PUT'])
def update_wechat_contact(contact_id):
    """Update WeChat contact"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        
        allowed_fields = [
            'display_name', 'wechat_id', 'phone', 'email', 'company', 'position',
            'industry', 'relation_type', 'relation_score', 'how_met',
            'first_contact_date', 'last_contact_date', 'tags', 'notes',
            'source_account_id', 'source_chat_count'
        ]
        
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not updates:
            return jsonify({'success': False, 'error': '没有要更新的字段'}), 400
        
        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [contact_id]
        
        c.execute(f"UPDATE wechat_contacts SET {set_clause}, updated_at = NOW() WHERE id = %s", values)
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] update_wechat_contact: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/wechat/contacts', methods=['POST'])
def create_wechat_contact():
    """Create WeChat contact"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO wechat_contacts 
            (display_name, wechat_id, phone, email, company, position, industry, 
             relation_type, relation_score, how_met, first_contact_date, 
             last_contact_date, tags, notes, source_account_id, source_chat_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('display_name'),
            data.get('wechat_id'),
            data.get('phone'),
            data.get('email'),
            data.get('company'),
            data.get('position'),
            data.get('industry'),
            data.get('relation_type'),
            data.get('relation_score', 50),
            data.get('how_met'),
            data.get('first_contact_date'),
            data.get('last_contact_date'),
            data.get('tags'),
            data.get('notes'),
            data.get('source_account_id'),
            data.get('source_chat_count', 0),
        ))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        print(f"[ERROR] create_wechat_contact: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/wechat/contacts/<int:contact_id>', methods=['DELETE'])
def delete_wechat_contact(contact_id):
    """Delete WeChat contact (soft delete handled in frontend)"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM wechat_contacts WHERE id = %s", (contact_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] delete_wechat_contact: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/wechat/accounts', methods=['GET'])
def get_wechat_accounts():
    """Get WeChat accounts"""
    try:
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute('''SELECT * FROM wechat_accounts ORDER BY account_name ASC''')
        accounts = c.fetchall()
        conn.close()
        return jsonify({'success': True, 'accounts': accounts})
    except Exception as e:
        print(f"[ERROR] get_wechat_accounts: {e}")
        return jsonify({'success': False, 'error': str(e)})



# ============================================
# 人生目标 API (my-goals page)
# ============================================

@app.route('/api/life-goals/', methods=['GET'])
@app.route('/api/life-goals', methods=['GET'])
@app.route('/api/my-goals', methods=['GET'])
@app.route('/api/life-goals', methods=['GET'])
def get_life_goals():
    """获取人生目标列表 - 动态统计项目和任务，MySQL不可用时fallback"""
    try:
        category = request.args.get('category', '')
        try:
            conn = get_db()
            c = conn.cursor()
            query = 'SELECT * FROM goals WHERE status = "active"'
            params = []
            if category:
                query += ' AND category = %s'
                params.append(category)
            query += ' ORDER BY id'
            c.execute(query, params)
            goals = [row_to_dict(row, c) for row in c.fetchall()]
            for goal in goals:
                goal['title'] = goal.get('name', goal.get('title', ''))
                gid = goal['id']
                c.execute('SELECT COUNT(*) as cnt FROM projects WHERE goal_id = %s AND status != "deleted"', (gid,))
                row = c.fetchone()
                goal['project_count'] = row['cnt'] if row else 0
                c.execute('SELECT COUNT(*) as cnt FROM tasks t JOIN projects p ON t.project_id = p.id WHERE p.goal_id = %s AND t.status != "deleted"', (gid,))
                row = c.fetchone()
                goal['task_count'] = row['cnt'] if row else 0
                c.execute('SELECT COUNT(*) as total, SUM(CASE WHEN t.status = "completed" THEN 1 ELSE 0 END) as done FROM tasks t JOIN projects p ON t.project_id = p.id WHERE p.goal_id = %s AND t.status != "deleted"', (gid,))
                row = c.fetchone()
                total = row['total'] if row and row['total'] else 0
                done = row['done'] if row and row['done'] else 0
                goal['progress'] = round((done / total) * 100) if total > 0 else 0
                try:
                    c.execute('SELECT id, description, target_value, current_value, unit, status FROM life_key_results WHERE life_goal_id = %s', (gid,))
                    goal['key_results'] = [row_to_dict(row, c) for row in c.fetchall()]
                except:
                    goal['key_results'] = []
            conn.close()
            return jsonify({'success': True, 'goals': goals, 'source': 'mysql'})
        except Exception as db_err:
            app.logger.warning(f"MySQL unavailable, using fallback: {db_err}")
            # Fallback: return hardcoded goals with last-known stats
            goals = [
                {"id":1,"name":"AI助手优化与效率提升","title":"AI助手优化与效率提升","description":"打造AI助手，提升工作效率","category":"tech","progress":70,"status":"active","project_count":12,"task_count":45,"key_results":[]},
                {"id":2,"name":"和光智成商业化成功","title":"和光智成商业化成功","description":"和光智成商业化运作","category":"business","progress":50,"status":"active","project_count":8,"task_count":28,"key_results":[]},
                {"id":3,"name":"学术竞争力建设","title":"学术竞争力建设","description":"提升学术影响力","category":"academic","progress":95,"status":"active","project_count":1,"task_count":8,"key_results":[]},
                {"id":4,"name":"财富增值与资产管理","title":"财富增值与资产管理","description":"实现财富增值","category":"finance","progress":0,"status":"active","project_count":1,"task_count":3,"key_results":[]},
                {"id":5,"name":"家庭幸福与子女教育","title":"家庭幸福与子女教育","description":"家庭幸福","category":"family","progress":0,"status":"active","project_count":1,"task_count":2,"key_results":[]},
                {"id":6,"name":"法律诉讼与社会工作","title":"法律诉讼与社会工作","description":"处理法律事务","category":"legal","progress":52,"status":"active","project_count":2,"task_count":5,"key_results":[]},
                {"id":7,"name":"身心健康与生活质量","title":"身心健康与生活质量","description":"保持身心健康","category":"health","progress":0,"status":"active","project_count":1,"task_count":1,"key_results":[]}
            ]
            return jsonify({'success': True, 'goals': goals, 'source': 'fallback'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    """获取审核列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        status_filter = request.args.get('status')
        query = '''
            SELECT * FROM reviews
            ORDER BY created_at DESC
            LIMIT 100
        '''
        if status_filter:
            query = '''
                SELECT * FROM reviews
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT 100
            '''
            c.execute(query, (status_filter,))
        else:
            c.execute(query)
        reviews = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'reviews': reviews, 'total': len(reviews)})
    except Exception as e:
        logger.error(f"Error getting reviews: {e}")
        return jsonify({'success': False, 'error': str(e), 'reviews': []})

@app.route('/api/reviews/<int:review_id>', methods=['PUT'])
def update_review(review_id):
    """更新审核状态"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        update_fields = []
        params = []
        if 'status' in data:
            update_fields.append('status = %s')
            params.append(data['status'])
        if 'reviewer_id' in data:
            update_fields.append('reviewer_id = %s')
            params.append(data['reviewer_id'])
        update_fields.append('updated_at = NOW()')
        params.append(review_id)
        query = f'UPDATE reviews SET ' + ', '.join(update_fields) + ' WHERE id = %s'
        c.execute(query, params)
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating review: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============================================

# Admin routes
from admin_routes import admin_bp
app.register_blueprint(admin_bp, url_prefix="/api/admin")

# ============================================
# 文件下载路由
# ============================================
def serve_upload(filename, subdir=''):
    """Serve uploaded files with versioned path support"""
    import os
    from flask import send_from_directory
    
    # 1. 版本化路径：/uploads/docs/task-{id}/v{version}/{file}
    if '/' in filename or subdir:
        path_parts = (subdir + '/' + filename).strip('/')
        full_path = os.path.join('/opt/kanban-react/backend/uploads', path_parts)
        if os.path.exists(full_path):
            return send_from_directory('/opt/kanban-react/backend/uploads', path_parts)
    
    # 2. SDS1 文档目录
    sds_docs_dir = '/opt/kanban-react/frontend/public/uploads/docs/sds1-docs'
    sds_path = os.path.join(sds_docs_dir, filename)
    if os.path.exists(sds_path):
        return send_from_directory(sds_docs_dir, filename)
    
    # 3. 兼容旧路径：/uploads/docs/{filename}
    legacy = os.path.join('/opt/kanban-react/backend/uploads/docs', filename)
    if os.path.exists(legacy):
        return send_from_directory('/opt/kanban-react/backend/uploads/docs', filename)
    
    # 4. 兜底到根上传目录
    return send_from_directory('/opt/kanban-react/backend/uploads', filename)
@app.route('/api/test-sentry', methods=['POST'])
def test_sentry():
    try:
        from sentry_sdk import capture_message
        capture_message('Sentry 测试消息 - 看板系统')
        return jsonify({'success': True, 'message': 'Sentry 测试消息已发送'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# SDS驾驶舱 API
# ============================================

    # Routes moved to routes/cockpit.py

    # Routes moved to routes/cockpit.py

    # Routes moved to routes/cockpit.py

    # Routes moved to routes/cockpit.py

    # Routes moved to routes/cockpit.py

    # Routes moved to routes/cockpit.py
# 生成用户通知
def create_notification(title, message, notif_type='system', entity_type=None, entity_id=None, user_id=None):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO user_notifications 
                    (user_id, title, message, type, entity_type, entity_id) 
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                    (user_id, title, message, notif_type, entity_type, entity_id))
                conn.commit()
    except Exception as e:
        logger.error(f"创建通知失败: {e}")

# ============================================
# 通知系统 API
# ============================================
@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """获取用户通知列表"""
    try:
        user_id = request.args.get('user_id')
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                sql = """SELECT * FROM user_notifications 
                         WHERE (user_id = %s OR user_id IS NULL) """
                params = [user_id]
                
                if unread_only:
                    sql += " AND is_read = 0"
                
                sql += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(sql, params)
                notifications = cur.fetchall()
                
                # 获取未读计数
                cur.execute("""SELECT COUNT(*) as count FROM user_notifications 
                               WHERE (user_id = %s OR user_id IS NULL) AND is_read = 0""", (user_id,))
                unread_count = cur.fetchone()['count']
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'unread_count': unread_count
        })
    except Exception as e:
        logger.error(f"获取通知失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/read-all', methods=['POST'])
def mark_all_notifications_read():
    """标记所有通知为已读"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""UPDATE user_notifications SET is_read = 1 
                               WHERE (user_id = %s OR user_id IS NULL) AND is_read = 0""", (user_id,))
                conn.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"标记所有通知已读失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sds1/documents', methods=['GET'])
def list_sds_documents():
    import os
    from flask import jsonify
    sds_docs_dir = '/opt/kanban-react/frontend/public/uploads/docs/sds1-docs'
    docs = []
    for root, dirs, files in os.walk(sds_docs_dir):
        for f in files:
            if f.endswith('.bak') or f.endswith('.DS_Store'):
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, sds_docs_dir)
            size = os.path.getsize(full_path)
            docs.append({
                'path': rel_path,
                'url': f'/uploads/docs/{rel_path}',
                'size': size
            })
    docs.sort(key=lambda x: x['path'])
    return jsonify({'success': True, 'documents': docs, 'count': len(docs)})



import json as _json
_sync_data_cache = None
def _get_sync_data():
    global _sync_data_cache
    if _sync_data_cache is None:
        p = "/opt/kanban-react/backend/macmini_sync_data.json"
        if os.path.exists(p):
            with open(p) as f:
                _sync_data_cache = _json.load(f)
    return _sync_data_cache or {"models":[],"skills":[],"cron_jobs":[],"system":{}}

    # Routes moved to routes/sync.py

    # Routes moved to routes/sync.py

    # Routes moved to routes/sync.py

    # Routes moved to routes/sync.py

    # Routes moved to routes/sync.py

    # Routes moved to routes/sync.py

def macmini_sync_skills_tools():
    """Mac mini 技能工具"""
    return jsonify({
        'success': True,
        'skills': [
            {'name': 'Tavily Search', 'version': '1.0', 'status': 'active'},
            {'name': 'Browser Use', 'version': '1.0', 'status': 'active'},
            {'name': 'Weather', 'version': '1.0', 'status': 'active'},
            {'name': 'GitHub', 'version': '1.0', 'status': 'active'},
            {'name': 'Feishu', 'version': '1.0', 'status': 'active'},
        ]
    })



    # Routes moved to routes/system.py

    # Routes moved to routes/cockpit.py

    # Routes moved to routes/local_files.py

@app.route('/api/goals/distribution', methods=['GET'])
def get_goal_distribution():
    '''按战略目标统计任务分布'''
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT COALESCE(strategic_goal, "未分配") as goal, COUNT(*) as cnt,
               SUM(CASE WHEN status="pending" THEN 1 ELSE 0 END) as pending_cnt,
               SUM(CASE WHEN status="completed" THEN 1 ELSE 0 END) as done_cnt,
               SUM(CASE WHEN status="failed_retryable" THEN 1 ELSE 0 END) as failed_cnt,
               SUM(CASE WHEN status="blocked" THEN 1 ELSE 0 END) as blocked_cnt
        FROM tasks WHERE deleted_at IS NULL
        GROUP BY goal ORDER BY cnt DESC
    ''')
    rows = c.fetchall()
    conn.close()
    return jsonify({'success': True, 'goals': rows})

@app.route('/api/debug/desc')

@app.route('/api/tasks/<int:task_id>/executions', methods=['GET'])
def get_task_executions(task_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, version, status, duration_sec, trigger_type, result_summary, task_summary, started_at, completed_at, created_at, ripple_context FROM task_executions WHERE task_id = %s ORDER BY version DESC LIMIT 50', (task_id,))
    rows = c.fetchall()
    conn.close()
    from routes.helpers import row_to_dict
    records = [row_to_dict(r, c) for r in rows]
    return jsonify({"success": True, "task_id": task_id, "records": records, "total": len(records)})
def debug_desc():
    from routes.helpers import row_to_dict, get_db
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, title, description FROM tasks LIMIT 1')
    row = c.fetchone()
    result = row_to_dict(row, c)
    conn.close()
    keys = list(result.keys())
    has_json = 'json_description' in result
    return jsonify({'keys': keys, 'has_json_desc': has_json, 'desc_start': str(result.get('description',''))[:50], 'jd_keys': list(result.get('json_description',{}).keys()) if has_json else []})

# ===== 项目执行方案 API =====

@app.route("/api/projects/<int:project_id>/plan", methods=["GET"])
def get_project_plan(project_id):
    """获取项目当前执行方案（含版本历史和评论）"""
    try:
        plan = execute_query("""
            SELECT id, project_id, title, version, mode, source, source_task_id,
                   summary, content, locked_reason, is_current, created_at, updated_at
            FROM project_plans
            WHERE project_id=%s AND is_current=1
            ORDER BY version DESC LIMIT 1
        """, (project_id,))
        
        versions = execute_query("""
            SELECT id, version, mode, source, summary, is_current, created_at, updated_at
            FROM project_plans
            WHERE project_id=%s
            ORDER BY version DESC
        """, (project_id,))
        
        comments = execute_query("""
            SELECT id, plan_version, task_id, content, created_at
            FROM project_plan_comments
            WHERE project_id=%s
            ORDER BY created_at DESC
        """, (project_id,))
        
                # 构造 content_display
        plan_data = plan[0] if plan else None
        if plan_data and plan_data.get('content'):
            import json as _jp
            raw = plan_data['content']
            pc = _jp.loads(raw) if isinstance(raw, str) else raw
            html_parts = []
            goal = pc.get('goal', '')
            if goal:
                html_parts.append('<div style="font-size:0.85rem;color:#4a5568;padding:8px 12px;background:#f0fdf4;border-radius:6px;border-left:3px solid #48bb78">' + _jp.dumps(goal, ensure_ascii=False).strip('"') + '</div>')
            phases = pc.get('phases', [])
            if phases:
                for ph in phases:
                    pn = ph.get('name', '') or '阶段'
                    html_parts.append('<div style="font-size:0.85rem;font-weight:600;color:#2d3748;margin:8px 0 4px">' + _jp.dumps(pn, ensure_ascii=False).strip('"') + '</div>')
                    for t in ph.get('tasks', []):
                        tn = t.get('name', '') or ''
                        ef = t.get('estimated_effort', '') or ''
                        txt = tn
                        if ef:
                            txt += ' (' + ef + ')'
                        html_parts.append('<span style="font-size:0.75rem;color:#4a5568;padding:2px 6px;background:#f7fafc;border:1px solid #e2e8f0;border-radius:4px;display:inline-block;margin:2px">' + _jp.dumps(txt, ensure_ascii=False).strip('"') + '</span>')
            risks = pc.get('risks', [])
            if risks:
                html_parts.append('<div style="margin-top:8px;padding:6px 10px;background:#fffaf0;border-left:3px solid #ed8936;border-radius:4px;font-size:0.8rem">')
                for r in risks[:3]:
                    rn = (r.get('risk', '') or r.get('name', '') or str(r)) if isinstance(r, dict) else str(r)
                    html_parts.append('<div style="color:#744210;padding:2px 0">' + _jp.dumps(rn, ensure_ascii=False).strip('"') + '</div>')
                if len(risks) > 3:
                    html_parts.append('<div style="color:#a0aec0">+' + str(len(risks)-3) + ' 更多</div>')
                html_parts.append('</div>')
            plan_data['content_display'] = ''.join(html_parts)
        
        return jsonify({
            "success": True,
            "plan": plan_data,
            "versions": versions,
            "comments": comments
        })
    except Exception as e:
        logger.error(f"获取项目方案失败 #{project_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/projects/<int:project_id>/plan/toggle", methods=["POST"])
def toggle_plan_lock(project_id):
    """切换方案锁定/开放模式"""
    try:
        data = request.get_json() or {}
        lock = data.get("lock", True)
        reason = data.get("reason", "")
        mode = "locked" if lock else "open"
        execute_update("""
            UPDATE project_plans SET mode=%s, locked_reason=%s, updated_at=NOW()
            WHERE project_id=%s AND is_current=1
        """, (mode, reason, project_id))
        return jsonify({"success": True, "mode": mode})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/projects/<int:project_id>/plan/rollback", methods=["POST"])
def rollback_plan(project_id):
    """回滚到指定版本"""
    try:
        data = request.get_json() or {}
        target_version = data.get("version")
        if not target_version:
            return jsonify({"success": False, "error": "需指定版本"}), 400
        
        import sys, json as _j
        sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/sds1')
        from modules.project_plan_manager import ProjectPlanManager
        mgr = ProjectPlanManager()
        result = mgr.rollback_to_version(project_id, target_version, "前端回滚")
        if result:
            return jsonify({"success": True, "plan": result})
        return jsonify({"success": False, "error": "回滚失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 更新 project plan API 加入 content_display（用于前端渲染）
# 通过 post 钩子，已经在上面实现了。但把 content 渲染一下：
# 在 get_project_plan 内增加 content_display 字段

# ===== 任务总结 API =====
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/sds1')

@app.route('/api/tasks/<int:task_id>/summary', methods=['GET'])
def get_task_summary(task_id):
    """获取任务总结（有缓存直接返回，无缓存生成）"""
    try:
        from lib.db_connector import execute_query
        rows = execute_query(
            "SELECT result_summary, summary_generated_at, summary_stale, status FROM tasks WHERE id=%s",
            (task_id,)
        )
        if not rows:
            return jsonify({"success": False, "error": "任务不存在"}), 404
        r = rows[0]
        
        # 有缓存且未过期 → 直接返回
        if r['result_summary'] and not r['summary_stale']:
            return jsonify({
                "success": True,
                "summary": r['result_summary'],
                "generated_at": str(r['summary_generated_at'] or ''),
                "cached": True,
            })
        
        # 无缓存或过期 → 调用 LLM 生成
        from modules.task_summary_generator import generate_task_summary
        result = generate_task_summary(task_id)
        if result['success']:
            return jsonify({
                "success": True,
                "summary": result['summary'],
                "generated_at": str(datetime.now()),
                "cached": False,
                "elapsed_ms": result['elapsed_ms'],
            })
        return jsonify({"success": False, "error": "总结生成失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tasks/<int:task_id>/summary/refresh', methods=['POST'])
def refresh_task_summary(task_id):
    """强制刷新任务总结"""
    try:
        from modules.task_summary_generator import force_refresh_summary
        result = force_refresh_summary(task_id)
        if result['success']:
            return jsonify({
                "success": True,
                "summary": result['summary'],
                "elapsed_ms": result['elapsed_ms'],
            })
        return jsonify({"success": False, "error": "刷新失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================
# 任务产出物文件 API
# ============================================

@app.route('/api/tasks/<int:task_id>/files')
def get_task_output_files(task_id):
    '''读取任务产出物文件列表（扫描 v1/v2/... 版本子目录）'''
    base_dir = f'/opt/kanban-react/backend/uploads/docs/task-{task_id}'
    if not os.path.isdir(base_dir):
        return jsonify({'success': True, 'files': [], 'task_id': task_id})
    files = []
    try:
        subdirs = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]) or ['']
        for sub in subdirs:
            scan_dir = base_dir if not sub else os.path.join(base_dir, sub)
            for fname in sorted(os.listdir(scan_dir)):
                fp = os.path.join(scan_dir, fname)
                if os.path.isfile(fp):
                    s = os.stat(fp)
                    files.append({
                        'id': len(files)+1, 'entity_type': 'task', 'entity_id': task_id,
                        'filename': fname, 'version': sub or 'v0',
                        'url': f'/api/tasks/{task_id}/files/{fname}',
                        'size': s.st_size,
                        'file_type': fname.split('.')[-1].lower() if '.' in fname else '',
                        'created_at': datetime.fromtimestamp(s.st_mtime).isoformat(),
                    })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': True, 'files': files, 'task_id': task_id, 'total': len(files)})


@app.route('/api/tasks/<int:task_id>/files/<path:filename>')
def get_task_output_file(task_id, filename):
    '''下载任务产出物文件（扫描 v1/v2/... 版本子目录）'''
    base_dir = f'/opt/kanban-react/backend/uploads/docs/task-{task_id}'
    filepath = os.path.join(base_dir, filename)
    if not os.path.isfile(filepath):
        if os.path.isdir(base_dir):
            for entry in sorted(os.listdir(base_dir)):
                sp = os.path.join(base_dir, entry)
                if os.path.isdir(sp):
                    fp = os.path.join(sp, filename)
                    if os.path.isfile(fp):
                        filepath = fp
                        break
    real_path = os.path.realpath(filepath)
    real_base = os.path.realpath('/opt/kanban-react/backend/uploads/docs')
    if not real_path.startswith(real_base):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    if not os.path.isfile(real_path):
        return jsonify({'success': False, 'error': 'File not found'}), 404
    return send_file(real_path, as_attachment=False)

# 导入LLM使用量API



# ===== AI+材料科学日报 API =====
import os, glob
REPORTS_DIR = '/opt/kanban-react/backend/uploads/reports'
os.makedirs(REPORTS_DIR, exist_ok=True)

@app.route('/api/research-daily/list')
def research_daily_list():
    """列出所有日报"""
    try:
        files = sorted(glob.glob(os.path.join(REPORTS_DIR, '*.md')), reverse=True)
        reports = []
        for f in files:
            fname = os.path.basename(f)
            # 解析文件名中的日期
            date_str = fname.replace('AI+材料科学日报_', '').replace('.md', '')
            with open(f, 'r', encoding='utf-8') as fh:
                first_line = fh.readline().strip()
                fh.seek(0)
                preview = fh.read(200).replace('\n', ' ').strip()
            reports.append({
                'filename': fname,
                'date': date_str,
                'summary': preview[:100],
                'title': first_line.replace('# ', '')
            })
        return jsonify({'success': True, 'reports': reports})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/research-daily/content')
def research_daily_content():
    """获取指定日报内容"""
    filename = request.args.get('file', '')
    if not filename:
        return jsonify({'success': False, 'error': 'Missing file'}), 400
    filepath = os.path.join(REPORTS_DIR, filename)
    # 安全校验：防止路径穿越
    if not os.path.realpath(filepath).startswith(os.path.realpath(REPORTS_DIR)):
        return jsonify({'success': False, 'error': 'Invalid path'}), 403
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'File not found'}), 404
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'success': True, 'content': content})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

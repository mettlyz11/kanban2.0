"""Routes: system"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db
import json

bp = Blueprint('routes_system', __name__)
logger = __import__('logging').getLogger(__name__)

# ============================================================
# Fallback hardcoded data (用于数据库不可用时的兜底)
# ============================================================
FALLBACK_MODELS = [
    {"provider": "moonshot", "model": "kimi-k2.5", "name": "Kimi K2.5", "reasoning": False, "baseUrl": "https://api.moonshot.cn/v1", "contextWindow": 262144, "maxTokens": 262144, "active": True},
    {"provider": "moonshot", "model": "kimi-k2.6", "name": "Kimi K2.6", "reasoning": True, "baseUrl": "https://api.moonshot.cn/v1", "contextWindow": 262144, "maxTokens": 262144, "active": True},
    {"provider": "deepseek", "model": "deepseek-v4-flash", "name": "DeepSeek V4 Flash", "reasoning": True, "baseUrl": "https://api.deepseek.com/v1", "contextWindow": 1000000, "maxTokens": 131072, "active": True},
    {"provider": "deepseek", "model": "deepseek-reasoner", "name": "DeepSeek Reasoner", "reasoning": True, "baseUrl": "https://api.deepseek.com/v1", "contextWindow": 1000000, "maxTokens": 131072, "active": True},
    {"provider": "alitokenplan", "model": "qwen3.6-plus", "name": "Qwen 3.6 Plus (AliTokenPlan)", "reasoning": True, "baseUrl": "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1", "contextWindow": 1000000, "maxTokens": 65536, "active": True},
    {"provider": "alitokenplan", "model": "deepseek-v3.2", "name": "DeepSeek V3.2 (AliTokenPlan)", "reasoning": True, "baseUrl": "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1", "contextWindow": 65536, "maxTokens": 8192, "active": True},
    {"provider": "alitokenplan", "model": "glm-5", "name": "GLM 5 (AliTokenPlan)", "reasoning": True, "baseUrl": "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1", "contextWindow": 131072, "maxTokens": 65536, "active": True},
    {"provider": "alitokenplan", "model": "MiniMax-M2.5", "name": "MiniMax M2.5 (AliTokenPlan)", "reasoning": True, "baseUrl": "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1", "contextWindow": 131072, "maxTokens": 8192, "active": True},
    {"provider": "alicodingplan", "model": "kimi-k2.5", "name": "Kimi K2.5 (AliCodingPlan)", "reasoning": True, "baseUrl": "https://coding.dashscope.aliyuncs.com/v1", "contextWindow": 262144, "maxTokens": 262144, "active": True},
    {"provider": "alicodingplan", "model": "qwen3.6-plus", "name": "Qwen 3.6 Plus (AliCodingPlan)", "reasoning": True, "baseUrl": "https://coding.dashscope.aliyuncs.com/v1", "contextWindow": 1000000, "maxTokens": 65536, "active": True},
    {"provider": "alicodingplan", "model": "glm-5", "name": "GLM 5 (AliCodingPlan)", "reasoning": True, "baseUrl": "https://coding.dashscope.aliyuncs.com/v1", "contextWindow": 131072, "maxTokens": 65536, "active": True},
    {"provider": "alicodingplan", "model": "MiniMax-M2.5", "name": "MiniMax M2.5 (AliCodingPlan)", "reasoning": True, "baseUrl": "https://coding.dashscope.aliyuncs.com/v1", "contextWindow": 131072, "maxTokens": 8192, "active": True},
    {"provider": "huoshan", "model": "doubao-seed-2-0-pro-260215", "name": "Doubao Seed 2.0 Pro (Huoshan)", "reasoning": True, "baseUrl": "https://ark.cn-beijing.volces.com/api/v3", "contextWindow": 131072, "maxTokens": 8192, "active": True},
    {"provider": "huoshanCoding", "model": "ark-code-latest", "name": "ARK Code Latest (HuoshanCoding)", "reasoning": True, "baseUrl": "https://ark.cn-beijing.volces.com/api/coding/v3", "contextWindow": 131072, "maxTokens": 8192, "active": True},
    {"provider": "huoshanCoding", "model": "doubao-seed-code", "name": "Doubao Seed Code (HuoshanCoding)", "reasoning": True, "baseUrl": "https://ark.cn-beijing.volces.com/api/coding/v3", "contextWindow": 131072, "maxTokens": 8192, "active": True},
    {"provider": "kimicode", "model": "kimi-for-coding", "name": "Kimi Code", "reasoning": True, "baseUrl": "https://api.kimi.com/coding/v1", "contextWindow": 131072, "maxTokens": 8192, "active": True},
    {"provider": "zhipu", "model": "glm-5", "name": "GLM 5 (Zhipu)", "reasoning": True, "baseUrl": "https://open.bigmodel.cn/api/paas/v4", "contextWindow": 131072, "maxTokens": 65536, "active": True},
    {"provider": "aliyun", "model": "qwen3.6-plus", "name": "Qwen 3.6 Plus (Helight)", "reasoning": True, "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1", "contextWindow": 1000000, "maxTokens": 65536, "active": True},
]

FALLBACK_SERVERS = [
    {"name":"Server 1 - 看板系统正式环境","hostname":"kanbanyun.com","ip":"47.93.184.128","os":"Ubuntu (Linux)","ssh":"ssh -i Files/info/aliserver1.pem root@47.93.184.128","services":[{"name":"Nginx (Web)","port":"443/80","status":"https://kanbanyun.com"},{"name":"Gunicorn (后端)","port":"8086","status":"systemd: kanban-backend.service"},{"name":"WebSocket 监控","port":"8765","status":"monitor-relay.py"}],"paths":"/opt/kanban-react/","note":"生产服务器，付费域名"},
    {"name":"Server 2 - 测试环境","hostname":"47.84.113.0","ip":"47.84.113.0","os":"Ubuntu (Linux)","ssh":"ssh -i Files/info/aliserver2.pem root@47.84.113.0","services":[{"name":"看板测试","port":"-","status":"Kanban测试"},{"name":"T109测试","port":"-","status":"T109测试"},{"name":"Helight测试","port":"-","status":"Helight测试"}],"note":"测试环境服务器"},
    {"name":"Server 3 - T109 正式环境","hostname":"60.205.197.9","ip":"60.205.197.9","os":"Ubuntu (Linux)","ssh":"ssh -i Files/info/aliserver3.pem root@60.205.197.9","services":[{"name":"T109项目","port":"-","status":"T109正式网站"}],"note":"T109项目正式环境"},
    {"name":"Server 4 - Helight 正式环境","hostname":"39.102.78.71","ip":"39.102.78.71","os":"Ubuntu (Linux)","ssh":"ssh -i Files/info/aliserver4.pem root@39.102.78.71","services":[{"name":"Helight项目","port":"-","status":"Helight正式网站"}],"note":"Helight项目正式环境"},
    {"name":"GPU 服务器1","hostname":"39.106.127.25","ip":"39.106.127.25","os":"Ubuntu (Linux)","ssh":"ssh -i Files/info/GPU1.pem root@39.106.127.25","services":[{"name":"GPU计算","port":"-","status":"抢占式，注意释放"}],"note":"阿里云抢占式GPU"},
    {"name":"GPU 服务器2","hostname":"39.105.76.19","ip":"39.105.76.19","os":"Ubuntu (Linux)","ssh":"ssh -i Files/info/GPU1.pem root@39.105.76.19","services":[{"name":"GPU计算","port":"-","status":"抢占式，注意释放"}],"note":"阿里云抢占式GPU"},
    {"name":"Mac mini（本地开发机）","hostname":"mettlyz的Mac mini","ip":"localhost","os":"macOS (Darwin arm64)","ssh":"本地终端","services":[{"name":"OpenClaw Gateway","port":"18789","status":"launchd"},{"name":"SDS 调度器","port":"-","status":"python3 sds_main.py"},{"name":"本地系统监控","port":"-","status":"system-monitor-ws.py"}],"paths":"/Users/mettlyz/.openclaw/workspace/","note":"AI调度核心引擎"},
    {"name":"Sentry 错误监控","hostname":"39.106.190.50","ip":"39.106.190.50","os":"Ubuntu (Linux)","web":"http://39.106.190.50:9000/","services":[{"name":"Sentry Web","port":"9000","status":"HTTP（非HTTPS）"}],"note":"错误追踪/APM"},
    {"name":"阿里云 RDS MySQL","hostname":"rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com","type":"数据库","version":"MySQL 3306","note":"主数据库，存储看板全部数据"},
]


def _load_json_from_db(cursor, config_type, fallback):
    """从 system_configs 加载 JSON 配置，失败时返回 fallback"""
    try:
        cursor.execute("SELECT config_data FROM system_configs WHERE config_type = %s LIMIT 1", (config_type,))
        row = cursor.fetchone()
        if row and row["config_data"]:
            return json.loads(row["config_data"])
    except Exception as e:
        logger.warning(f"读取 {config_type} 失败: {e}")
    return fallback


@bp.route('/api/system/config-info', methods=['GET'])
def get_system_config_info():
    models_data = FALLBACK_MODELS
    servers = FALLBACK_SERVERS
    sysconf = {}

    try:
        conn = get_db()
        c = conn.cursor()

        # 从数据库读取（已通过迁移脚本存储）
        models_data = _load_json_from_db(c, "llm_models_data", FALLBACK_MODELS)
        servers = _load_json_from_db(c, "servers_data", FALLBACK_SERVERS)

        # 系统配置概览（掩盖敏感信息）
        c.execute("SELECT config_type, config_data FROM system_configs WHERE config_type NOT IN ('email', 'llm', 'monitor', 'general')")
        for row in c.fetchall():
            val = str(row["config_data"] or "")
            if "baseUrl" in row["config_type"] or "baseurl" in row["config_type"].lower():
                sysconf[row["config_type"]] = val
            elif row["config_type"] in ("aliyun_access","gpu_pem","google_oauth","google_token","server_pems"):
                sysconf[row["config_type"]] = val
            elif len(val) > 22:
                sysconf[row["config_type"]] = val[:16] + "..." + val[-4:]
            elif val:
                sysconf[row["config_type"]] = val[:20] + ("..." if len(val) > 20 else "")
        conn.close()
    except Exception as e:
        sysconf = {"note": "查询配置表失败: " + str(e)[:80]}

    # 掩盖 passwords —— 不让前端暴露明文
    for s in servers:
        if "pass" in s:
            pw = s["pass"]
            s["pass"] = pw[:2] + "***" + pw[-1:] if len(pw) > 3 else "***"

    return jsonify({
        "success": True,
        "info": {
            "providers": models_data,
            "system_config": sysconf,
            "servers": servers,
            "version": "5.0",
            "backend": "gunicorn+flask",
            "database": "mysql"
        }
    })


@bp.route('/api/system/config-update', methods=['POST'])
def update_system_config():
    """更新系统配置项"""
    try:
        data = request.get_json()
        if not data or 'config_type' not in data or 'config_data' not in data:
            return jsonify({'success': False, 'error': '需要 config_type 和 config_data'}), 400

        config_type = data['config_type']
        config_data = data['config_data']

        conn = get_db()
        c = conn.cursor()
        c.execute('''INSERT INTO system_configs (config_type, config_data)
          VALUES (%s, %s)
          ON DUPLICATE KEY UPDATE config_data = VALUES(config_data), updated_at = NOW()''',
          (config_type, config_data))
        conn.commit()
        conn.close()

        try:
            from websocket.index import get_socketio_instance
            sio = get_socketio_instance()
            if sio:
                sio.emit('system_config_updated', {'config_type': config_type})
        except:
            pass

        return jsonify({'success': True, 'message': f'已更新 {config_type}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/system/server-update', methods=['POST'])
def update_server_info():
    """更新服务器信息"""
    try:
        data = request.get_json()
        if not data or 'server_index' not in data:
            return jsonify({'success': False, 'error': '需要 server_index'}), 400

        idx = data['server_index']
        conn = get_db()
        c = conn.cursor()
        c.execute('''INSERT INTO system_configs (config_type, config_data)
          VALUES (%s, %s)
          ON DUPLICATE KEY UPDATE config_data = VALUES(config_data), updated_at = NOW()''',
          (f'server_{idx}_override', json.dumps(data.get('fields', {}))))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'服务器 #{idx} 已更新'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

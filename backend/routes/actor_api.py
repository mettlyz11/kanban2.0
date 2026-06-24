"""Routes: actor_api - 扮演者代理（SSH 隧道 → 本地 :18791）"""
from flask import Blueprint, jsonify, request
import json, urllib.request, logging, time, os, threading, difflib, hashlib
from datetime import datetime
from routes.modes_config import MODES, auto_select_mode, ROLE_FORMATS, retrieve_from_vector_db, VECTOR_CONFIG
from concurrent.futures import ThreadPoolExecutor, as_completed



# ---- Tool Functions ----
TOOL_FUNCTIONS = {
    "paper_search": lambda q: {"result": "论文搜索: " + q, "source": "arxiv"},
    "patent_search": lambda q: {"result": "专利搜索: " + q, "source": "uspto"},
    "market_size": lambda i: {"result": "市场规模: " + i + " 100亿 增速15%"},
    "kanban_status": lambda: {"active": 5, "completed": 10},
}

def _process_tool_calls(resp):
    msg = resp.get('choices', [{}])[0].get('message', {})
    tcs = msg.get('tool_calls', [])
    if not tcs:
        return msg.get('content', '')
    c = msg.get('content', '') or ''
    parts = [c]
    for tc in tcs:
        if tc.get('type') == 'function':
            fn = tc.get('function', {})
            name = fn.get('name', '')
            try: args = json.loads(fn.get('arguments', '{}'))
            except Exception as e: args = {}
            result = name + " executed"
            parts.append("[Tool:" + name + "] " + result)
    return '\n'.join(parts)

bp = Blueprint("routes_actor_api", __name__)
logger = logging.getLogger(__name__)

GLOBAL_CONTEXT = ''
_GLOBAL_CTX_MTIME = 0
_GLOBAL_CTX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dist', 'llm_global_context.txt')

def _load_global_context():
    global GLOBAL_CONTEXT, _GLOBAL_CTX_MTIME
    try:
        if os.path.exists(_GLOBAL_CTX_PATH):
            mtime = os.path.getmtime(_GLOBAL_CTX_PATH)
            if mtime > _GLOBAL_CTX_MTIME:
                with open(_GLOBAL_CTX_PATH) as f:
                    GLOBAL_CONTEXT = f.read()[:2000]
                _GLOBAL_CTX_MTIME = mtime
    except Exception:
        pass

def get_global_context():
    """每次调用都检查文件是否更新"""
    _load_global_context()
    return GLOBAL_CONTEXT

_load_global_context()
ACTOR_URL = "http://127.0.0.1:18791/v1/chat/completions"
ACTOR_TIMEOUT = 2400

# ─── 角色配置 ────────────────────────────────
ROLES = {
    "researcher": {
        "name": "子墨",
        "scope": "academic",
        "emoji": "🔬",
        "tools": [
            "paper_search",
            "patent_search"
        ],
        "background": "中科院材料学博士，10年AI+材料研究经验",
        "style": "严谨、数据驱动、喜欢引用文献",
        "prompt": """你是子墨，中科院材料学博士，10年AI+材料研究经验。

【角色特点】
- 严谨、数据驱动、喜欢引用文献
- 善于发现技术盲区和潜在风险
- 回答必有数据支撑

【输出格式】
1. **核心观点**（50字以内）
2. **论据支撑**（3点，每点引用来源）
3. **技术细节**（关键参数/指标）
4. **潜在风险**（2-3点）
5. **建议行动**（可执行步骤）

【约束】
- 必须引用具体文献或数据来源
- 不确定的地方明确标注
【生图能力】当用户需要配图、示意图、logo时，你可以使用 generate_image 或 generate_logo 工具。不要说自己没有图像能力。"""
    },
    "analyst": {
        "name": "计然",
        "scope": "business",
        "emoji": "📊",
        "tools": [
            "market_size",
            "competitor_map",
            "trl_assessment"
        ],
        "background": "麦肯锡资深顾问，专注硬科技商业化",
        "style": "务实、以古鉴今、善用类比、关注ROI",
        "prompt": """你是计然，麦肯锡资深顾问，深谙"旱则资舟，水则资车"的商道。

【角色特点】
- 务实、以古鉴今、善用类比
- 关注ROI和商业可行性
- 善于发现市场机会

【输出格式】
1. **商业洞察**（50字以内）
2. **市场规模**（TAM/SAM/SOM）
3. **竞品对标**（3家，关键指标对比）
4. **商业模式**（收入来源、成本结构）
5. **风险与建议**（SWOT分析）

【约束】
- 数据必须有来源或合理估算依据
- 避免空话套话
- 当用户需要投资分析图、logo、配图时，可以使用 generate_image 或 generate_logo 工具
- 注意：不要说自己没有图像能力，你确实可以用

- 当用户需要风险示意图、logo、配图时，可以使用 generate_image 或 generate_logo 工具
- 注意：不要说自己没有图像能力，你确实可以用

- 当用户需要图表、logo、配图时，可以使用 generate_image 或 generate_logo 工具
- 注意：不要说自己没有图像能力，你确实可以用

- 当用户需要战略图、logo、概念图时，可以使用 generate_image 或 generate_logo 工具
- 注意：不要说自己没有图像能力，你确实可以用

- 当用户需要商业模型图、趋势图、logo时，可以使用 generate_image 或 generate_logo 工具
- 注意：不要说自己没有图像能力，你确实可以用

- 当用户需要配图、示意图时，可以使用 generate_image 工具
- 注意：不要说自己没有图像能力，你确实可以用

【生图能力】当用户需要商业模型图、趋势图、logo时，你可以使用 generate_image 或 generate_logo 工具。不要说自己没有图像能力。"""
    },
    "strategist": {
        "name": "卧龙",
        "scope": "full",
        "emoji": "🧠",
        "tools": [
            "project_db",
            "kanban_status",
            "contact_network"
        ],
        "background": "前BAT战略总监，主导过3个独角兽的战略规划",
        "style": "高屋建瓴、系统思考、善于取舍",
        "prompt": """你是卧龙，前BAT战略总监，主导过3个独角兽的战略规划。

【角色特点】
- 高屋建瓴、系统思考
- 善于取舍、关注长期价值
- 能从0到1设计完整战略

【输出格式】
1. **战略判断**（50字以内，核心结论）
2. **全景分析**（产业格局、关键变量）
3. **战略选项**（3个，优劣对比）
4. **推荐策略**（All-in/渐进/观望）
5. **关键里程碑**（18个月路线图）

【约束】
- 必须有明确的选择和理由
- 考虑资源约束和现实条件
【生图能力】当用户需要战略图、logo、概念图时，你可以使用 generate_image 或 generate_logo 工具。不要说自己没有图像能力。"""
    },
    "finance": {
        "name": "陶朱",
        "scope": "business",
        "emoji": "💰",
        "tools": [
            "burn_rate",
            "valuation_model",
            "cap_table_sim"
        ],
        "background": "红杉资本合伙人，投过10+硬科技独角兽",
        "style": "精于计算、关注现金流、保守与激进并存",
        "prompt": """你是陶朱，红杉资本合伙人，投过10+硬科技独角兽。

【角色特点】
- 精于计算、关注现金流
- 保守与激进并存
- 善于识别价值拐点

【输出格式】
1. **估值判断**（区间+核心假设）
2. **财务模型**（3年预测，关键假设）
3. **投资回报**（IRR、MOIC、回本周期）
4. **融资建议**（轮次、金额、估值区间）
5. **风险量化**（敏感性分析）

【约束】
- 所有数字必须有计算逻辑
- 明确标注假设条件
- 区分乐观/基准/悲观情景
【生图能力】当用户需要图表、logo、配图时，你可以使用 generate_image 或 generate_logo 工具。不要说自己没有图像能力。"""
    },
    "risk": {
        "name": "韩非",
        "scope": "full",
        "emoji": "⚠️",
        "tools": [
            "failure_case_db",
            "scenario_sim",
            "red_flag_check"
        ],
        "background": "顶级律所合伙人，专注科技合规，处理过100+技术纠纷",
        "style": "冷峻、直击要害、法条精准、不留情面",
        "prompt": """你是韩非，顶级律所合伙人，专注科技合规。

【角色特点】
- 冷峻、直击要害
- 法条精准、不留情面
- 善于发现隐藏风险

【输出格式】
1. **风险警示**（50字以内，最高优先级风险）
2. **法律风险**（合规性、知识产权、合同）
3. **技术风险**（可行性、替代性、迭代风险）
4. **市场风险**（竞争、政策、需求变化）
5. **缓释建议**（具体措施、优先级）

【约束】
- 风险必须分级（高/中/低）
- 引用具体法规或判例
- 不粉饰、不回避
【生图能力】当用户需要风险示意图、logo、配图时，你可以使用 generate_image 或 generate_logo 工具。不要说自己没有图像能力。"""
    },
    "investor": {
        "name": "白圭",
        "scope": "business",
        "emoji": "👀",
        "tools": [
            "comparable_deals",
            "pitch_score",
            "term_sheet_analyzer"
        ],
        "background": "天使投资人，个人投出5个独角兽，IRR 45%+",
        "style": "看人看事、直觉敏锐、决策果断、关注人",
        "prompt": """你是白圭，天使投资人，个人投出5个独角兽，IRR 45%+。

【角色特点】
- 看人看事、直觉敏锐
- 决策果断、关注人
- 善于发现被低估的机会

【输出格式】
1. **投资判断**（投/不投/观望，50字理由）
2. **团队评估**（创始人、核心团队、股权结构）
3. **市场时机**（成熟度、竞争窗口、政策环境）
4. **估值判断**（合理区间、谈判策略）
5. **关键条款**（对赌、回购、优先清算）

【约束】
- 必须有明确的投资决策
- 关注团队胜过技术
- 考虑退出路径
【生图能力】当用户需要投资分析图、logo、配图时，你可以使用 generate_image 或 generate_logo 工具。不要说自己没有图像能力。"""
    },
    "ROLE_LIST": [
        "researcher",
        "analyst",
        "strategist",
        "finance",
        "risk",
        "investor"
    ]
}
@bp.route('/api/actor/health', methods=['GET'])
def actor_health():
    try:
        req = urllib.request.Request("http://127.0.0.1:18791/health")
        with urllib.request.urlopen(req, timeout=60) as r:
            return jsonify({"ok": True, "actor": json.loads(r.read())})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 503


@bp.route('/api/actor/roles', methods=['GET'])
def actor_roles():
    """获取所有可用角色"""
    return jsonify({"ok": True, "roles": ROLES})


@bp.route('/api/actors', methods=['GET'])
def actors_alias():
    return jsonify({"ok": True, "roles": ROLES})


@bp.route('/api/actor/modes', methods=['GET'])
def actor_modes():
    from routes import modes_config
    return jsonify({
        "ok": True,
        "modes": MODES,
        "categories": getattr(modes_config, "MODE_CATEGORIES", {}),
        "scene_modes": getattr(modes_config, "SCENE_MODES", {}),
    })


@bp.route('/api/llm/global-context', methods=['GET'])
def llm_global_context():
    # Expose health/metadata without leaking full prompt content.
    ctx = get_global_context() or ""
    exists = os.path.exists(_GLOBAL_CTX_PATH)
    mtime = os.path.getmtime(_GLOBAL_CTX_PATH) if exists else None
    return jsonify({
        "ok": True,
        "exists": exists,
        "mtime": mtime,
        "length": len(ctx),
        "sha256": hashlib.sha256(ctx.encode("utf-8")).hexdigest() if ctx else None,
    })

import re as _re

def _collect_images(value, limit=20):
    """Recursively collect image metadata from history payloads."""
    images = []
    seen = set()
    def add(url, meta=None):
        if not url:
            return
        url = str(url).strip()
        if not url or url in seen:
            return
        seen.add(url)
        item = {'url': url}
        if isinstance(meta, dict):
            for k in ('prompt', 'alt', 'reason', 'role', 'name'):
                if meta.get(k):
                    item[k] = meta.get(k)
        images.append(item)
    def walk(obj):
        if len(images) >= limit:
            return
        if isinstance(obj, dict):
            if obj.get('url') and any(k in obj for k in ('prompt','alt','reason')):
                add(obj.get('url'), obj)
            for key in ('image_url', 'local_url'):
                if obj.get(key):
                    add(obj.get(key), obj)
            img = obj.get('image')
            if isinstance(img, dict):
                add(img.get('url'), img)
                walk(img)
            imgs = obj.get('images')
            if isinstance(imgs, list):
                for it in imgs:
                    if isinstance(it, dict):
                        add(it.get('url'), it)
                    elif isinstance(it, str):
                        add(it, {})
            for k2 in ('output', 'task', 'reply', 'final_report', 'conclusion'):
                if isinstance(obj.get(k2), str):
                    for m in _re.finditer(r'!\[.*?\]\((https?://[^\s)]+|/[^\s)]+(?:jpe?g|png|gif|webp|svg)(?:\?[^\s)]*)?)\)', obj[k2]):
                        add(m.group(1), {})
                    for m in _re.finditer(r'(https?://[^\s]*\.(?:jpe?g|png|gif|webp|svg)[^\s]*)', obj[k2]):
                        add(m.group(1), {})
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(obj, list):
            for it in obj:
                walk(it)
    walk(value)
    return images[:limit]

@bp.route('/api/actor/chat', methods=['POST'])
def actor_chat():
    """与扮演者对话（可选角色）"""
    data = request.get_json(silent=True) or {}
    msgs = data.get('messages', [])
    if not msgs:
        return jsonify({"error": "messages required"}), 400

    role = data.get('role', '').strip()
    scope = data.get('knowledge_scope', 'full')
    max_tokens = int(data.get('max_tokens', 2000))
    session_id = str(data.get('session_id') or '')
    mode = data.get('mode', 'explore')

    # 处理 auto 模式
    if mode == 'auto':
        mode = auto_select_mode(msgs[-1].get('content', '') if msgs else '', 'chat')

    # 根据角色设置 system prompt 和 scope
    if role and role in ROLES:
        cfg = ROLES[role]
        system_prompt = cfg["prompt"]
        scope = data.get('knowledge_scope') or cfg["scope"]
        if system_prompt:
            ctx = ("\n\n[全局上下文]\n" + get_global_context()) if get_global_context() else ""
            combined = system_prompt + ctx
            # 注入模式 prompt
            from routes.modes_config import MODES
            mode_cfg = MODES.get(mode, MODES.get("explore", {}))
            mode_prompt = mode_cfg.get("prompt", "")
            if mode_prompt:
                combined += "\n\n【当前模式】\n" + mode_prompt
            msgs = [{"role": "system", "content": combined}] + msgs

    body = json.dumps({
        "model": "actor", "messages": msgs,
        "max_tokens": 80000, "session_id": session_id,
        "knowledge_scope": scope, "role": role,
    }).encode()

    req = urllib.request.Request(
        ACTOR_URL, data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=ACTOR_TIMEOUT) as r:
            resp = json.loads(r.read())
        elapsed = time.time() - t0
        reply_text = resp.get("choices", [{}])[0].get("message", {}).get("content", "")

        # 优先使用扮演者服务返回的图片（如果工具调用已生成）
        actor_image = resp.get('image')
        image_url = None
        img_prompt = None
        reason = 'actor_tool'

        if actor_image and actor_image.get('url'):
            image_url = actor_image['url']
            img_prompt = actor_image.get('prompt', '')
            reason = actor_image.get('tool', 'actor_tool')
            print(f'[Actor] 使用扮演者返回的图片: {image_url[:60]}...')
        else:
            # 检查是否需要生图（延迟导入避免循环引用）
            from routes.brainstorm_api import should_generate_image, generate_seedream_image, _llm_extract_visual_prompt
            should_gen, _, reason = should_generate_image(msgs[-1].get('content', ''), [{'content': reply_text}])
            img_prompt = None  # 初始化
            if should_gen:
                try:
                    # 使用 LLM 从对话中提取 visual prompt
                    question = msgs[-1].get('content', '')
                    chat_context = '\n'.join([m.get('content', '') for m in msgs[-3:] if m.get('content')])
                    img_prompt = _llm_extract_visual_prompt(question, f"对话内容：\n{chat_context}\n\n回复：\n{reply_text}")
                    image_url = generate_seedream_image(img_prompt)
                except Exception as e:
                    print(f'Chat image generation failed: {e}')

        result = {
            "ok": True, "elapsed_s": round(elapsed, 1),
            "reply": reply_text,
        }
        if image_url:
            result["image"] = {"url": image_url, "prompt": img_prompt or '', "reason": reason}

        try:
            user_text = ''
            for m in reversed(msgs):
                if m.get('role') == 'user':
                    user_text = m.get('content', '')
                    break
            hist_id = _history_id()
            chat_entry = {
                'id': hist_id,
                'type': 'chat',
                'role': role,
                'scope': scope,
                'mode': mode,
                'messages': msgs[-20:],
                'reply': reply_text,
                'image': result.get('image'),
                'images': _collect_images(result.get('image')),
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'elapsed_s': round(elapsed, 1),
            }
            _append_history(CHAT_HISTORY_FILE, chat_entry)
            _append_unified_history({
                'id': hist_id,
                'type': 'chat',
                'task': user_text or (reply_text[:120] if reply_text else '单聊'),
                'status': 'completed',
                'output': _safe_text(reply_text + (('\n\n![配图](' + image_url + ')') if image_url else ''), 12000),
                'images': _collect_images(result.get('image')),
                'metadata': {'role': role, 'scope': scope, 'mode': mode, 'image': result.get('image'), 'images': _collect_images(result.get('image'))},
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_s': round(elapsed, 1),
            })
            result['history_id'] = hist_id
        except Exception as e:
            logger.error(f'Failed to save chat history: {e}')

        return jsonify(result)
    except Exception as e:
        elapsed = time.time() - t0
        return jsonify({"ok": False, "error": str(e), "elapsed_s": round(elapsed, 1)}), 502


@bp.route('/api/actor/crew-run', methods=['POST'])
def actor_crew_run():
    data = request.get_json(silent=True) or {}
    body = json.dumps({'task': data.get('task', '')}).encode()
    req = urllib.request.Request(
        'http://127.0.0.1:18791/crew/run', data=body,
        headers={'Content-Type': 'application/json'}, method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=3600) as r:
            return jsonify(json.loads(r.read()))
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 502


@bp.route('/api/actor/crew-status', methods=['GET'])
def actor_crew_status():
    try:
        req = urllib.request.Request('http://127.0.0.1:18791/crew/status')
        with urllib.request.urlopen(req, timeout=60) as r:
            return jsonify(json.loads(r.read()))
    except Exception as e:
        return jsonify({'ok': False, 'status': 'error', 'error': str(e)}), 502


@bp.route('/api/actor/crew-cancel', methods=['POST'])
def actor_crew_cancel():
    try:
        req = urllib.request.Request(
            'http://127.0.0.1:18791/crew/cancel', data=b'{}',
            headers={'Content-Type': 'application/json'}, method='POST',
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return jsonify(json.loads(r.read()))
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 502



# ── 历史记录辅助函数 ──────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(DATA_DIR, 'crew_history.json')
CHAT_HISTORY_FILE = os.path.join(DATA_DIR, 'chat_history.json')
ROUNDTABLE_HISTORY_FILE = os.path.join(DATA_DIR, 'roundtable_history.json')
BRAINSTORM_HISTORY_FILE = os.path.join(DATA_DIR, 'brainstorm_history.json')


def _safe_text(value, limit=4000):
    if value is None:
        return ''
    try:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    except Exception:
        text = str(value)
    return text[-limit:]


def _history_id():
    return str(int(time.time() * 1000))


def _append_history(filepath, entry, limit=100):
    history = _load_history(filepath)
    history.insert(0, entry)
    _save_history(filepath, history[:limit])
    return entry.get('id')


def _append_unified_history(entry, limit=100):
    history = _load_history(HISTORY_FILE)
    history.insert(0, entry)
    _save_history(HISTORY_FILE, history[:limit])
    return entry.get('id')

def _load_history(filepath=None):
    fp = filepath or HISTORY_FILE
    try:
        with open(fp) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def _save_history(arg1, arg2=None):
    """Save history. Supports both _save_history(data) and _save_history(filepath, data)"""
    if arg2 is None:
        fp, data = HISTORY_FILE, arg1
    else:
        fp, data = arg1, arg2
    try:
        with open(fp, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f'Failed to save history to {fp}: {e}')


@bp.route('/api/actor/crew-save', methods=['POST'])
def actor_crew_save():
    try:
        data = request.get_json(silent=True) or {}
        h = _load_history()
        entry = {
            'id': _history_id() + str(len(h)),
            'type': data.get('type') or 'crew',
            'task': data.get('task') or '',
            'status': data.get('status') or 'unknown',
            'output': _safe_text(data.get('output') or '', 8000),
            'metadata': data.get('metadata') or {},
            'images': _collect_images(data),
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_s': data.get('duration_s') or 0,
        }
        h.insert(0, entry)
        _save_history(h[:50])
        return jsonify({'ok': True, 'id': entry['id']})
    except Exception as e:
        logger.error(f'crew-save error: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'ok': False, 'error': str(e)}), 500


def _all_actor_history_entries():
    entries = []
    for fp, default_type in [
        (HISTORY_FILE, 'crew'),
        (CHAT_HISTORY_FILE, 'chat'),
        (ROUNDTABLE_HISTORY_FILE, 'roundtable'),
        (BRAINSTORM_HISTORY_FILE, 'brainstorm'),
    ]:
        for e in _load_history(fp):
            if isinstance(e, dict):
                item = dict(e)
                item.setdefault('type', default_type)
                entries.append(item)
    def key(e):
        return str(e.get('created_at') or e.get('timestamp') or e.get('id') or '')
    entries.sort(key=key, reverse=True)
    return entries


def _entry_title(e):
    if e.get('task'):
        return e.get('task')
    if e.get('question'):
        return e.get('question')
    msgs = e.get('messages') or []
    if isinstance(msgs, list):
        for m in reversed(msgs):
            if isinstance(m, dict) and m.get('role') == 'user' and m.get('content'):
                return m.get('content')
    if e.get('reply'):
        return e.get('reply')[:120]
    return e.get('type') or 'history'


@bp.route('/api/actor/crew-history', methods=['GET'])
def actor_crew_history():
    summary = []
    seen = set()
    for e in _all_actor_history_entries():
        try:
            eid = str(e.get('id', ''))
            etype = e.get('type', 'crew')
            dedup = (etype, eid)
            if eid and dedup in seen:
                continue
            seen.add(dedup)
            imgs = e.get('images') or _collect_images(e)
            summary.append({
                'id': eid,
                'type': etype,
                'task': (_entry_title(e) or '')[:120],
                'status': e.get('status', 'completed' if etype in ('chat','roundtable','brainstorm') else 'unknown'),
                'created_at': e.get('created_at') or e.get('timestamp') or '',
                'duration_s': e.get('duration_s') or e.get('elapsed_s') or 0,
                'has_image': bool(imgs),
                'images': imgs[:3],
            })
        except Exception:
            continue
    return jsonify({'ok': True, 'history': summary[:200]})


@bp.route('/api/actor/crew-history/<entry_id>', methods=['GET'])
def actor_crew_history_detail(entry_id):
    for e in _all_actor_history_entries():
        if str(e.get('id')) == str(entry_id):
            if not e.get('images'):
                e['images'] = _collect_images(e)
            if not e.get('output'):
                if e.get('final_report'):
                    e['output'] = e.get('final_report')
                elif e.get('conclusion'):
                    e['output'] = e.get('conclusion')
                elif e.get('reply'):
                    e['output'] = e.get('reply')
                else:
                    e['output'] = json.dumps(e, ensure_ascii=False)[:12000]
            e.setdefault('task', _entry_title(e))
            return jsonify({'ok': True, 'entry': e})
    return jsonify({'ok': False, 'error': 'not found'}), 404


@bp.route('/api/actor/crew-similar', methods=['POST'])
def actor_crew_similar():
    data = request.get_json(silent=True) or {}
    task = (data.get('task') or '').strip().lower()
    if not task:
        return jsonify({'ok': True, 'matches': []})
    h = _load_history()
    matches = []
    for e in h:
        if not e.get('task'): continue
        ratio = difflib.SequenceMatcher(None, task, e['task'].lower()).ratio()
        if ratio > 0.3:
            matches.append({
                'id': e['id'], 'task': e['task'][:120], 'status': e['status'],
                'created_at': e['created_at'], 'similarity': round(ratio, 3),
            })
    matches.sort(key=lambda x: -x['similarity'])
    return jsonify({'ok': True, 'matches': matches[:5]})


@bp.route('/api/actor/roundtable', methods=['POST'])
def actor_roundtable():
    """圆桌模式：真圆桌，串行多轮，每角色配图"""
    data = request.get_json(silent=True) or {}
    question = data.get('question', '')
    selected = data.get('roles', ROLES.get('ROLE_LIST', ['researcher','analyst','strategist']))
    mode = data.get("mode", "consensus")
    image_mode = bool(data.get("image_mode", False))
    max_tokens = int(data.get("max_tokens", 2500) or 2500)
    timeout_s = int(data.get("timeout_s", 300) or 300)
    try:
        max_rounds = int(data.get("max_rounds", len(selected)) or len(selected))
    except Exception:
        max_rounds = len(selected)
    max_rounds = max(1, min(max_rounds, 30))
    # 圆桌 UI 的“轮数”语义是发言次数上限，不是角色数量。
    # 旧逻辑只遍历 selected 一次，导致用户填 7 但只选 2 个角色时只跑 2 轮。
    role_sequence = [r for r in selected if r in ROLES and r != "ROLE_LIST"]
    if role_sequence:
        role_sequence = [role_sequence[i % len(role_sequence)] for i in range(max_rounds)]
    else:
        role_sequence = []
    if mode == "auto":
        mode = auto_select_mode(question, "roundtable")
    if not question:
        return jsonify({'ok': False, 'error': 'question required'}), 400

    # 使用统一模式配置
    mode_cfg = MODES.get(mode, MODES.get('consensus', {}))
    mode_suffix = mode_cfg.get('prompt', MODES.get('consensus', {}).get('prompt', ''))

    results = []
    context = []  # 存储前面角色的回复作为上下文

    # 串行调用每个角色，传递上下文
    for round_index, role_key in enumerate(role_sequence, 1):
        if role_key not in ROLES or role_key == 'ROLE_LIST':
            continue
        cfg = ROLES[role_key]

        # 检索向量库
        vector_ctx = ""
        if VECTOR_CONFIG["enabled"]:
            try:
                docs = retrieve_from_vector_db(question, top_k=3)
                if docs:
                    vector_ctx = "\n\n【相关知识库】\n" + "\n---\n".join([
                        f"《{d['title']}》：{d['content'][:300]}..." for d in docs
                    ])
            except Exception as e:
                print(f"Vector retrieval error: {e}")

        # 构建带上下文的 prompt
        ctx_text = ""
        if context:
            ctx_parts = []
            for c in context:
                part = f"{c['name']}（{c['role']}）:\n{c['reply'][:500]}"
                # 如果有图片，加入视觉分析
                if c.get('image') and c['image'].get('url'):
                    try:
                        from routes.brainstorm_api import analyze_image_with_vision
                        img_analysis = analyze_image_with_vision(c['image']['url'], c['reply'][:200])
                        if img_analysis:
                            part += f"\n[配图分析：{img_analysis.get('analysis', '图片已生成')}]"
                    except Exception:
                        part += "\n[配图已生成]"
                ctx_parts.append(part)
            ctx_text = "\n\n【前面专家的观点】\n" + "\n---\n".join(ctx_parts)

        user_content = f"请从你的专业角度分析以下问题（300-500字）。这是圆桌第{round_index}/{max_rounds}轮发言，请结合前序观点推进讨论，避免重复：\n\n{question}\n\n{mode_suffix}{vector_ctx}{ctx_text}"

        global_ctx = ('\n\n【全局上下文】\n' + get_global_context()) if get_global_context() else ''
        mode_ctx = ('\n\n【当前模式】\n' + mode_suffix) if mode_suffix else ''
        msgs = [{'role': 'system', 'content': cfg['prompt'] + global_ctx + mode_ctx},
                {'role': 'user', 'content': user_content}]
        body = json.dumps({
            'model': 'actor', 'messages': msgs,
            'max_tokens': max_tokens, 'temperature': 0.3, 'knowledge_scope': data.get('knowledge_scope') if data.get('knowledge_scope') not in (None, '', 'auto') else cfg['scope'],
            'role': role_key,
        }).encode()

        try:
            req = urllib.request.Request('http://127.0.0.1:18791/v1/chat/completions', data=body,
                                          headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                resp = json.loads(r.read())
            reply = _process_tool_calls(resp)

            # 为该角色生成配图
            image_url = None
            img_prompt = None  # 初始化
            try:
                from routes.brainstorm_api import should_generate_image, generate_seedream_image, auto_optimize_image, _llm_extract_visual_prompt
                explicit_img = image_mode or ('【生图】' in question) or ('[生图]' in question) or any(k in question for k in ['生成图片','生成图像','画图','出图','配图','生成logo','生成Logo','生成LOGO'])
                should_gen, _, reason = should_generate_image(question, [{'content': reply}]) if explicit_img else (False, '', 'image_mode_off')
                if image_mode and explicit_img and not should_gen:
                    should_gen, reason = True, 'image_mode_on'
                if explicit_img and should_gen:
                    # 使用 LLM 从圆桌讨论中提取 visual prompt
                    if results:
                        roundtable_context = '\n'.join([f"{r.get('name', r.get('role', ''))}: {r.get('reply', '')}" for r in results])
                        full_context = f"已有观点：\n{roundtable_context}\n\n当前发言：\n{reply}"
                    else:
                        full_context = f"问题：{question}\n\n当前发言：\n{reply}"
                    img_prompt = _llm_extract_visual_prompt(question, full_context)
                    image_url = generate_seedream_image(img_prompt)

                    # 自动优化2轮
                    if image_url:
                        try:
                            # 优化轮数 = 总角色数
                            total_roles = len(selected)
                            optimize_iterations = min(total_roles, 5)  # 取总角色数，最多5轮
                            final_url, optimize_log = auto_optimize_image(
                                image_url,
                                img_prompt,
                                reply[:100],
                                max_iterations=optimize_iterations
                            )
                            if final_url and final_url != image_url:
                                image_url = final_url
                        except Exception as e:
                            print(f'Roundtable auto optimize error: {e}')
            except Exception as e:
                print(f'Roundtable image generation for {role_key} failed: {e}')

            result = {
                'role': role_key,
                'name': cfg.get('name', role_key),
                'emoji': cfg.get('emoji', ''),
                'reply': reply,
                'ok': True,
                'round_index': round_index,
                'max_rounds': max_rounds,
                'image': {'url': image_url, 'prompt': img_prompt if image_url else ''} if image_url else None
            }
            results.append(result)
            context.append(result)  # 加入上下文

        except Exception as e:
            results.append({
                'role': role_key,
                'name': cfg.get('name', role_key),
                'emoji': cfg.get('emoji', ''),
                'error': str(e),
                'ok': False,
                'round_index': round_index,
                'max_rounds': max_rounds
            })

    # 主持人最终总结：必须明确指出最佳方案/最佳图片
    final_report = ''
    best_role = None
    best_image = None
    try:
        discussion_lines = []
        candidates = []
        for idx, r in enumerate(results, 1):
            if not r.get('ok'):
                continue
            image_note = ''
            if r.get('image') and r['image'].get('url'):
                image_note = f"\n配图URL: {r['image']['url']}\n配图Prompt: {r['image'].get('prompt','')}"
                candidates.append(r)
            discussion_lines.append(f"方案{idx}｜{r.get('emoji','')} {r.get('name', r.get('role',''))}：\n{r.get('reply','')[:1200]}{image_note}")
        final_prompt = (
            '你是圆桌主持人孔子。请基于以下专家发言与配图候选，输出最终总结。\n'
            '要求：1）必须明确写出【最佳方案】是哪位专家/哪张图；2）说明为什么它最好；'
            '3）给出可执行修改建议；4）如果主题是logo/视觉设计，要从品牌识别、可记忆性、科技感、商业可用性四方面评分。\n'
            '输出小节必须包含：最佳方案、选择理由、评分排序、风险与修改建议、下一步。\n\n'
            f'主题：{question}\n\n圆桌内容：\n' + '\n---\n'.join(discussion_lines)
        )
        bd = json.dumps({
            'model': 'actor',
            'messages': [{'role': 'system', 'content': '你是孔子，负责主持圆桌并做最终裁决。'}, {'role': 'user', 'content': final_prompt}],
            'max_tokens': 2500,
            'temperature': 0.25,
            'knowledge_scope': 'full'
        }).encode()
        rq = urllib.request.Request('http://127.0.0.1:18791/v1/chat/completions', data=bd, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(rq, timeout=300) as rp:
            final_report = json.loads(rp.read()).get('choices', [{}])[0].get('message', {}).get('content', '')
        # 尽量从总结中匹配获胜专家；匹配不到则默认取最后一个有图且成功的候选
        for r in results:
            name = r.get('name') or r.get('role')
            if name and final_report and name in final_report:
                best_role = r
                break
        if not best_role:
            best_role = candidates[-1] if candidates else (results[-1] if results else None)
        if best_role and best_role.get('image'):
            best_image = best_role.get('image')
        if best_role and '最佳方案' not in final_report[:200]:
            final_report = f"【最佳方案】{best_role.get('emoji','')} {best_role.get('name', best_role.get('role',''))} 的方案\n\n" + final_report
    except Exception as e:
        print('Roundtable final report failed:', e)
        ok_results = [r for r in results if r.get('ok')]
        best_role = next((r for r in reversed(ok_results) if r.get('image')), ok_results[-1] if ok_results else None)
        if best_role:
            best_image = best_role.get('image')
            final_report = (
                f"【最佳方案】{best_role.get('emoji','')} {best_role.get('name', best_role.get('role',''))} 的方案。\n\n"
                f"【选择理由】该方案是圆桌讨论中最完整、且已产生可视化输出的候选，适合作为下一轮优化基础。\n\n"
                f"【下一步】以这张图为主稿，继续优化字体、色彩、图形识别度和商业落地版本。"
            )

    # Save to history
    history_id = None
    try:
        history_id = _history_id()
        entry = {
            'id': history_id,
            'type': 'roundtable',
            'question': question,
            'roles': selected,
            'requested_max_rounds': max_rounds,
            'actual_rounds': len(results),
            'results': results,
            'final_report': final_report,
            'best_role': best_role,
            'image': best_image,
            'images': _collect_images({'results': results, 'best_role': best_role, 'image': best_image}),
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        _append_history(ROUNDTABLE_HISTORY_FILE, entry)
        _append_unified_history({
            'id': history_id,
            'type': 'roundtable',
            'task': question,
            'status': 'completed',
            'output': _safe_text((final_report or '') + (('\n\n![圆桌配图](' + best_image.get('url') + ')') if isinstance(best_image, dict) and best_image.get('url') else '') or results, 12000),
            'images': _collect_images({'results': results, 'best_role': best_role, 'image': best_image}),
            'metadata': {'roles': selected, 'requested_max_rounds': max_rounds, 'actual_rounds': len(results), 'results': results, 'best_role': best_role, 'image': best_image, 'images': _collect_images({'results': results, 'best_role': best_role, 'image': best_image})},
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_s': 0,
        })
    except Exception as e:
        logger.error(f'Failed to save roundtable history: {e}')

    return jsonify({'ok': True, 'rounds': results, 'requested_max_rounds': max_rounds, 'actual_rounds': len(results), 'final_report': final_report, 'best_role': best_role, 'image': best_image, 'history_id': history_id})


@bp.route('/api/actor/chat-history', methods=['GET'])
def actor_chat_history():
    history = _load_history(CHAT_HISTORY_FILE)
    return jsonify({'ok': True, 'history': history[:100]})


@bp.route('/api/actor/chat-history/<entry_id>', methods=['GET'])
def actor_chat_history_detail(entry_id):
    for e in _load_history(CHAT_HISTORY_FILE):
        if str(e.get('id')) == str(entry_id):
            return jsonify({'ok': True, 'entry': e})
    return jsonify({'ok': False, 'error': 'not found'}), 404


@bp.route('/api/actor/roundtable-history', methods=['GET'])
def actor_roundtable_history():
    history = _load_history(ROUNDTABLE_HISTORY_FILE)
    summary = []
    for e in history[:100]:
        summary.append({
            'id': str(e.get('id', '')),
            'type': 'roundtable',
            'timestamp': e.get('created_at') or e.get('timestamp') or '',
            'created_at': e.get('created_at') or e.get('timestamp') or '',
            'question': e.get('question', ''),
            'participants': [ROLES.get(r, {}).get('name', r) for r in (e.get('roles') or [])],
            'round_count': e.get('actual_rounds') or len(e.get('results') or e.get('rounds') or []),
            'requested_max_rounds': e.get('requested_max_rounds'),
            'consensus': bool(e.get('final_report')),
            'has_image': bool(e.get('images') or _collect_images(e)),
            'images': (e.get('images') or _collect_images(e))[:3],
        })
    return jsonify({'ok': True, 'history': summary})


@bp.route('/api/actor/roundtable-history/<entry_id>', methods=['GET'])
def actor_roundtable_history_detail(entry_id):
    for e in _load_history(ROUNDTABLE_HISTORY_FILE):
        if str(e.get('id')) == str(entry_id):
            return jsonify({'ok': True, 'entry': e})
    return jsonify({'ok': False, 'error': 'not found'}), 404

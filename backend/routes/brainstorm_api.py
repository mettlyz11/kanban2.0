"""
Brainstorm routes - separate module to avoid corrupting actor_api.py
"""
from flask import Blueprint, jsonify, request, Response, stream_with_context
import json, urllib.request, os, logging
from routes.actor_tools import TOOL_REGISTRY

bp = Blueprint("brainstorm_api", __name__)
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
BRAINSTORM_HISTORY_FILE = os.path.join(DATA_DIR, 'brainstorm_history.json')
UNIFIED_HISTORY_FILE = os.path.join(DATA_DIR, 'crew_history.json')


def _load_history(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_history(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error('Failed to save history to %s: %s', filepath, e)


def _safe_text(value, limit=12000):
    if value is None:
        return ''
    try:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    except Exception:
        text = str(value)
    return text[-limit:]


def _history_id():
    import time
    return str(int(time.time() * 1000))


def _collect_images(value, limit=20):
    """Recursively collect generated image metadata from brainstorm history."""
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
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(obj, list):
            for it in obj:
                walk(it)
    walk(value)
    return images[:limit]


def _append_history(filepath, entry, limit=100):
    history = _load_history(filepath)
    history.insert(0, entry)
    _save_history(filepath, history[:limit])
    return entry.get('id')


def _save_brainstorm_history(question, agents, rounds, conclusion, metadata=None):
    import time
    hist_id = _history_id()
    created_at = time.strftime('%Y-%m-%d %H:%M:%S')
    entry = {
        'id': hist_id,
        'type': 'brainstorm',
        'question': question,
        'agents': agents,
        'rounds': rounds,
        'conclusion': conclusion,
        'metadata': metadata or {},
        'images': _collect_images({'rounds': rounds, 'conclusion': conclusion}),
        'created_at': created_at,
    }
    _append_history(BRAINSTORM_HISTORY_FILE, entry)
    _append_history(UNIFIED_HISTORY_FILE, {
        'id': hist_id,
        'type': 'brainstorm',
        'task': question,
        'status': 'completed',
        'output': _safe_text((conclusion or '') + ''.join(['\n\n![脑风暴配图](' + img.get('url','') + ')' for img in _collect_images({'rounds': rounds})[:6]]) or rounds, 20000),
        'images': _collect_images({'rounds': rounds, 'conclusion': conclusion}),
        'metadata': {'agents': agents, 'rounds': rounds, 'images': _collect_images({'rounds': rounds, 'conclusion': conclusion}), **(metadata or {})},
        'created_at': created_at,
        'duration_s': 0,
    })
    return hist_id

# Brainstorm timeout budget: each round has two actor calls.
# User rule: 960s per actor call, so 10 rounds => 10 * 2 * 960 = 19200s total budget.
BRAINSTORM_AGENT_TIMEOUT = 960

ROLES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'routes', 'actor_api.py')
GLOBAL_CONTEXT = ''
_GLOBAL_CTX_MTIME = 0
_GLOBAL_CTX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dist', 'llm_global_context.txt')


def _load_global_context():
    """Load shared LLM global context, capped to avoid bloated brainstorm prompts."""
    global GLOBAL_CONTEXT, _GLOBAL_CTX_MTIME
    try:
        if os.path.exists(_GLOBAL_CTX_PATH):
            mtime = os.path.getmtime(_GLOBAL_CTX_PATH)
            if mtime > _GLOBAL_CTX_MTIME:
                with open(_GLOBAL_CTX_PATH, encoding='utf-8') as f:
                    GLOBAL_CONTEXT = f.read()
                _GLOBAL_CTX_MTIME = mtime
    except Exception as e:
        logger.warning('Failed to load LLM global context: %s', e)


def get_global_context(limit: int = 6000) -> str:
    _load_global_context()
    ctx = GLOBAL_CONTEXT or ''
    return ctx if limit is None else ctx[:limit]



def _get_roles():
    """Dynamically import ROLES from actor_api.py"""
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("actor_mod", ROLES_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, 'ROLES', {})

ROLES = _get_roles()

# Tool functions - real implementations
TOOLS = {
    "paper_search": lambda q: _run_tool("paper_search", q),
    "patent_search": lambda q: _run_tool("patent_search", q),
    "market_size": lambda i: _run_tool("market_size", i),
    "kanban_status": lambda: _run_tool("kanban_status", None),
    "failure_case_db": lambda s: _run_tool("failure_case_db", s),
}


# ========== Image generation helpers used by actor_api / brainstorm ===========
IMAGE_KEYWORDS = ['示意图', '流程图', '架构图', '设计图', '原型图', '效果图',
                  '可视化', '展示', '呈现', '外观', '界面', 'UI', 'logo', '标志',
                  '配图', '插图', '草图', '蓝图', '模型图', '概念图', '思维导图',
                  '脑图', '关系图', '网络图', '生成图片', '画一张', '画个图', '做个图']


def should_generate_image(question: str, messages: list = None) -> tuple:
    """Return (should_generate, prompt, reason). Kept as public helper for actor_api."""
    question = question or ''
    marked = ['【生图】', '[生图]', '(生图)']
    if any(m in question for m in marked):
        clean_q = question
        for m in marked:
            clean_q = clean_q.replace(m, '')
        clean_q = clean_q.strip()
        return True, f"基于以下主题创作配图：{clean_q}", 'user_marked'
    text = question.lower()
    if messages:
        for msg in messages[-3:]:
            if isinstance(msg, dict):
                text += ' ' + str(msg.get('content') or msg.get('reply') or '').lower()
    for keyword in IMAGE_KEYWORDS:
        if keyword.lower() in text:
            return True, f"创作关于'{question[:80]}'的配图", 'keyword_triggered'
    return False, None, None


def _get_huoshan_api_key():
    # Prefer Huoshan Agent Plan key from service env file. The host may still
    # export legacy HUOSHAN_API_KEY/ARK_API_KEY values that are invalid for
    # /api/plan/v3, so do not let process env shadow HUOSHAN_PLAN_API_KEY.
    key_names = ('HUOSHAN_PLAN_API_KEY', 'HUOSHAN_API_KEY', 'ARK_API_KEY')
    for env_path in ('/etc/default/kanban-api.env', '/etc/environment'):
        try:
            if os.path.exists(env_path):
                values = {}
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#') or '=' not in line:
                            continue
                        name, value = line.split('=', 1)
                        name = name.replace('export ', '').strip()
                        if name in key_names:
                            values[name] = value.strip().strip('"').strip("'")
                for name in key_names:
                    if values.get(name):
                        return values[name]
        except Exception as e:
            logger.warning('Failed to load API key from %s: %s', env_path, e)
    for name in key_names:
        key = os.environ.get(name)
        if key:
            return key.strip()
    return ''


def _extract_visual_prompt(text: str) -> str:
    import re
    text = re.sub(r"[#*_\[\]`|:>-]", ' ', text or '')
    text = ' '.join(text.split())[:700]
    return (text + '。高品质视觉呈现，精细细节，专业构图')[:900]


def _llm_extract_visual_prompt(question, debate_content):
    """Generate an English visual prompt; fallback is deterministic and safe."""
    try:
        api_key = _get_huoshan_api_key()
        if not api_key:
            return _extract_visual_prompt(str(question) + '，' + str(debate_content)[:300])
        url = 'https://ark.cn-beijing.volces.com/api/plan/v3/chat/completions'
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key}
        system = 'You are a professional AI image prompt engineer. Output only one English prompt, 50-100 words.'
        user = 'Original request:\n' + str(question) + '\n\nDiscussion/context:\n' + str(debate_content)[:3000]
        body = json.dumps({'model': 'glm-latest', 'messages': [
            {'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            'max_tokens': 220, 'temperature': 0.7}).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=45) as r:
            resp = json.loads(r.read())
        prompt = resp.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        return prompt or _extract_visual_prompt(str(question) + '，' + str(debate_content)[:300])
    except Exception as e:
        logger.warning('LLM visual prompt extraction failed: %s', e)
        return _extract_visual_prompt(str(question) + '，' + str(debate_content)[:300])


def generate_seedream_image(prompt: str, reference_image_url: str = None) -> str:
    """Use Seedream image generation, return local URL when download succeeds, otherwise remote URL."""
    try:
        api_key = _get_huoshan_api_key()
        if not api_key:
            logger.error('HUOSHAN_PLAN_API_KEY/HUOSHAN_API_KEY/ARK_API_KEY not set')
            return None
        url = 'https://ark.cn-beijing.volces.com/api/plan/v3/images/generations'
        body = {'model': 'doubao-seedream-5.0-lite', 'prompt': prompt, 'width': 1920, 'height': 1920, 'response_format': 'url'}
        if reference_image_url:
            body['image'] = reference_image_url
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key}
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read())
        remote_url = (resp.get('data') or [{}])[0].get('url')
        if not remote_url:
            logger.error('Seedream returned no image: %s', str(resp)[:300])
            return None
        try:
            local_url = _download_image_to_local(remote_url)
            return local_url or remote_url
        except Exception as e:
            logger.warning('Image local download failed: %s', e)
            return remote_url
    except Exception as e:
        logger.error('Seedream failed: %s', e)
        return None


def auto_optimize_image(image_url: str, prompt: str, context: str, max_iterations: int = 2) -> tuple:
    """Safe optimization hook. For stability, return original image with a log."""
    return image_url, [{'iteration': 0, 'status': 'skipped', 'reason': 'optimization disabled in stable helper'}]


def analyze_image_with_vision(image_url: str, context: str) -> dict:
    """Lightweight vision analysis fallback used by roundtable context."""
    return {'analysis': '图片已生成，当前跳过视觉复评。', 'suggestions': []}




def _clean_image_intent(text: str) -> str:
    """Remove explicit image-generation markers for text-only fallback."""
    text = text or ''
    for token in ['【生图】', '[生图]', '(生图)', '生成图片', '配图', '画图', '出图']:
        text = text.replace(token, '')
    return text.strip()


def _compact_role_prompt(role_cfg: dict, text_only: bool = False) -> str:
    """Short brainstorm system prompt. Keep role personality, avoid huge role prompt."""
    name = role_cfg.get('name', '专家')
    background = role_cfg.get('background', '')
    style = role_cfg.get('style', '')
    base = (
        f"你是{name}。{background}。风格：{style}。\n"
        "脑风暴规则：先给文字，不要只给图片；必须结合全局上下文中的用户身份、公司目标和战略目标。\n"
        "每轮固定输出：\n"
        "1. 核心判断：一句话；\n"
        "2. 设计/方案建议：3条，每条不超过35字；\n"
        "3. 本轮最值得保留的元素：1条；\n"
        "4. 如果需要生图，最后补一句'生图提示：...'。\n"
        "总字数控制在180字以内。"
    )
    if text_only:
        base += "\n本次只输出文字，禁止调用工具，禁止输出Markdown图片。"
    else:
        base += "\n若主题包含logo/生图/配图，可以调用生图工具，但必须保留上述文字观点。"
    return base


def _short_context(context: str, limit: int = 1200) -> str:
    context = context or ''
    return context[-limit:] if len(context) > limit else context


def _optimize_brainstorm_prompt(role_cfg, question: str, round_num: int, context: str, reference_image_url: str = None, text_only: bool = False) -> str:
    """Two-stage prompt assembly: merge all materials, then optimize for the current purpose.

    Do not blindly take the first N chars of global context. The optimizer sees the
    full available global context (bounded only by a high safety cap) plus task goal,
    role, previous rounds and image reference, then emits a compact final prompt.
    """
    global_ctx = get_global_context(6000) or ''
    materials = (
        f"【任务目的】围绕用户当前问题进行连续脑风暴，结合刘宇宙/和光智成/AI+材料科学/商业化目标，产生可执行观点与可迭代图片。\n"
        f"【当前问题】{question}\n"
        f"【轮次】第{round_num}轮\n"
        f"【角色】{role_cfg.get('name','专家')}｜{role_cfg.get('background','')}｜风格：{role_cfg.get('style','')}\n"
        f"【LLM全局上下文全文】\n{global_ctx}\n"
        f"【上一轮文字与图片记忆】\n{context or '(首次，无上一轮)'}\n"
        f"【参考图片URL】{reference_image_url or '无'}\n"
        f"【输出硬约束】先文字后图片；180字以内；必须回应上一轮优缺点；若有参考图，说明如何基于参考图改进；必须服务和光智成商业化与品牌识别。"
    )
    optimizer_system = (
        "你是Prompt Optimizer。你的任务不是回答问题，而是把原始材料压缩成给业务专家LLM使用的最终提示词。"
        "必须按当前目的选择最相关信息，特别注意全局上下文中任何位置的重要信息，不允许只取开头。"
        "输出中文最终提示词，控制在900字以内，包含：目标、关键背景、上一轮继承点、参考图要求、输出格式。"
    )
    try:
        body = json.dumps({
            'model': 'actor',
            'messages': [
                {'role': 'system', 'content': optimizer_system},
                {'role': 'user', 'content': materials}
            ],
            'max_tokens': 1800,
            'temperature': 0.15,
            'knowledge_scope': 'full',
            'tools': []
        }).encode()
        req = urllib.request.Request('http://127.0.0.1:18791/v1/chat/completions', data=body, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
        prompt = resp.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        if prompt:
            return prompt[:1400]
    except Exception as e:
        logger.warning('Prompt optimizer failed, using deterministic compact prompt: %s', e)
    # Fallback: keep end+head mix instead of first chars only.
    ctx = global_ctx[:1200] + ('\n...\n' + global_ctx[-1200:] if len(global_ctx) > 2400 else '')
    return (
        f"目标：针对“{question}”进行第{round_num}轮连续脑风暴，必须服务和光智成商业化和品牌识别。\n"
        f"角色：{role_cfg.get('name','专家')}，{role_cfg.get('background','')}，风格：{role_cfg.get('style','')}。\n"
        f"关键全局上下文：\n{ctx}\n"
        f"上一轮记忆：\n{context or '(首次，无上一轮)'}\n"
        f"参考图片：{reference_image_url or '无'}。\n"
        f"要求：先回应上一轮优缺点，再提出本轮改进；180字以内；若生图，先写生图提示，再用参考图迭代。"
    )[:1400]


def _format_brainstorm_context(rounds, limit: int = 1800) -> str:
    """Compact cross-round memory: text + image urls, not huge transcripts."""
    lines = []
    for rd in (rounds or [])[-2:]:
        for m in rd:
            if not isinstance(m, dict) or not m.get('ok'):
                continue
            name = (m.get('emoji','') + ' ' + m.get('name','')).strip()
            reply = _sanitize_actor_reply(m.get('reply','') or '').replace('\n', ' ')[:260]
            img = m.get('image_url') or ((m.get('images') or [{}])[0].get('url') if m.get('images') else '')
            line = f"第{m.get('round','?')}轮 {name}: {reply}"
            if img:
                line += f"\n参考图片URL: {img}"
            lines.append(line)
    text = '\n---\n'.join(lines) if lines else '(首次，无上一轮)'
    return text[-limit:] if len(text) > limit else text


def _last_brainstorm_image(rounds) -> str:
    for rd in reversed(rounds or []):
        for m in reversed(rd or []):
            if not isinstance(m, dict):
                continue
            img = m.get('image_url') or ((m.get('images') or [{}])[0].get('url') if m.get('images') else '')
            if img:
                return img
    return ''




def _generate_text_only_viewpoint(role_key, role_cfg, question, context, round_num, timeout_s=120):
    """Fallback when actor returns image-only content.

    Do a second lightweight call with no tools and with image intent stripped,
    so every brainstorm round has an actual textual viewpoint for the left side.
    """
    try:
        q = _clean_image_intent(question)
        msgs = [
            {'role': 'system', 'content': _compact_role_prompt(role_cfg, text_only=True)},
            {'role': 'user', 'content': f'主题：{q}\n上下文摘要：{_short_context(context, 900)}\n请输出第{round_num}轮纯文字观点，必须有具体判断和建议。'}
        ]
        body = {
            'model': 'actor', 'messages': msgs,
            'max_tokens': 4000, 'knowledge_scope': role_cfg.get('scope', 'full'),
            'role': role_key, 'tools': []
        }
        req = urllib.request.Request('http://127.0.0.1:18791/v1/chat/completions',
            data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            resp = json.loads(r.read())
        msg = resp.get('choices', [{}])[0].get('message', {})
        text = _sanitize_actor_reply(msg.get('content', '') or '')
        text, _imgs = _split_text_and_images(text)
        return text.strip()
    except Exception as e:
        logger.warning('Text-only fallback failed for brainstorm round %s/%s: %s', role_key, round_num, e)
        return ''


def _split_text_and_images(text: str):
    """Split markdown image links out of an actor reply.

    Returns (clean_text, images). images is a list of {alt,url}. This lets the UI
    render each brainstorm message as left=text and right=image instead of the
    image markdown swallowing the textual viewpoint.
    """
    import re
    text = text or ''
    images = []
    def repl(m):
        alt = (m.group(1) or '配图').strip()
        url = (m.group(2) or '').strip()
        if url:
            images.append({'alt': alt, 'url': url})
        return ''
    clean = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', repl, text)
    # Remove image-only banners from text column, but keep real prose.
    lines = []
    for line in clean.splitlines():
        stripped = line.strip()
        if stripped in ('🎨 配图已生成:', '🎨 配图已生成', '配图已生成:', '配图已生成'):
            continue
        lines.append(line)
    clean = '\n'.join(lines).strip()
    return clean, images


def _sanitize_actor_reply(text: str) -> str:
    """Remove noisy internal tool-call errors from actor replies before UI display.

    The actor service may still return useful content/images after an internal tool
    error, e.g. "(工具调用错误: HTTP Error 400: Bad Request)" followed by a
    generated image. Keep the useful content and hide only the implementation
    error lines.
    """
    if not text:
        return text or ''
    noisy_tokens = [
        '工具调用错误',
        'tool call error',
        'Tool call error',
        'HTTP Error 400: Bad Request',
    ]
    cleaned = []
    for line in str(text).splitlines():
        if any(tok in line for tok in noisy_tokens):
            logger.warning('Sanitized actor tool-error line from brainstorm reply: %s', line[:200])
            continue
        cleaned.append(line)
    # Collapse excessive leading blank lines after removing error banners.
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    return '\n'.join(cleaned).strip()


def _run_tool(name, arg):
    """Run a tool via TOOL_REGISTRY, return JSON string"""
    import json as _j
    mapper = {
        "paper_search": (TOOL_REGISTRY["paper_search"], arg),
        "patent_search": (TOOL_REGISTRY["patent_search"], arg),
        "market_size": (TOOL_REGISTRY["market_size"], arg),
        "kanban_status": (TOOL_REGISTRY["kanban_status"], None),
        "failure_case_db": (TOOL_REGISTRY["failure_case_db"], arg),
    }
    if name in mapper:
        fn, a = mapper[name]
        try:
            if a is not None:
                r = fn(a)
            else:
                r = fn()
            return _j.dumps(r, ensure_ascii=False)
        except Exception as e:
            logger.error("Tool error " + name + ": " + str(e))
            return _j.dumps({"error": str(e)})
    return name + " executed"


def _explicit_image_requested(question: str) -> bool:
    q = question or ''
    explicit = ['【生图】', '[生图]', '#生图', '生成图片', '生成一张图', '生成图像', '画图', '出图', '配图', '生图模式']
    logo_intent = ['生成logo', '生成Logo', '生成LOGO', '设计logo并生成', 'logo【生图】', 'Logo【生图】', 'LOGO【生图】']
    return any(x in q for x in explicit + logo_intent)


def _call_agent(role_key, role_cfg, question, context, round_num, max_tokens=2500, timeout_s=BRAINSTORM_AGENT_TIMEOUT, reference_image_url=None, image_mode=False):
    """Call actor service with a compact brainstorm prompt."""
    optimized_prompt = _optimize_brainstorm_prompt(role_cfg, question, round_num, context, reference_image_url=reference_image_url)
    msgs = [
        {'role': 'system', 'content': _compact_role_prompt(role_cfg)},
        {'role': 'user', 'content': optimized_prompt}
    ]
    body = {
        'model': 'actor', 'messages': msgs,
        'max_tokens': max_tokens, 'knowledge_scope': role_cfg['scope'],
        'role': role_key, 'tools': role_cfg.get('tools', []),
    }
    try:
        req = urllib.request.Request('http://127.0.0.1:18791/v1/chat/completions',
            data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            resp = json.loads(r.read())
        # Process tool calls
        msg = resp.get('choices', [{}])[0].get('message', {})
        tcs = msg.get('tool_calls', [])
        c = _sanitize_actor_reply(msg.get('content', '') or '')
        parts = [c] if c else []
        for tc in (tcs or []):
            if tc.get('type') == 'function':
                fn = tc.get('function', {})
                n = fn.get('name', '')
                try:
                    a = json.loads(fn.get('arguments', '{}'))
                except:
                    a = {}
                if n in TOOLS:
                    result = TOOLS[n](**a) if a else TOOLS[n]()
                    parts.append('[Tool:' + n + '] ' + str(result))
                    logger.info("\U0001f527 \u8111\u7210\u5de5\u5177\u8c03\u7528: " + n + " args=" + str(a))
                else:
                    parts.append('[Tool:' + n + ' unknown')
        reply = _sanitize_actor_reply('\n'.join(parts))
        text_reply, images = _split_text_and_images(reply)
        # If this is a visual task, ensure the generated image can inherit the previous round image.
        try:
            explicit_img = bool(image_mode) or _explicit_image_requested(question)
            should_img, _base_prompt, _reason = should_generate_image(question, [{'content': text_reply}, {'content': context}]) if explicit_img else (False, '', 'image_mode_off')
            if explicit_img and should_img and not images:
                visual_prompt = _llm_extract_visual_prompt(question, (text_reply or reply) + '\n' + (context or ''))
                if reference_image_url:
                    visual_prompt = 'Use the reference image as the starting point; preserve the best visual identity, improve composition, typography, color and brand clarity. ' + visual_prompt
                gen_url = generate_seedream_image(visual_prompt, reference_image_url=reference_image_url)
                if gen_url:
                    images = [{'alt': '本轮配图', 'url': gen_url, 'prompt': visual_prompt}]
        except Exception as e:
            logger.warning('Reference image generation skipped: %s', e)
        if images and not text_reply.strip():
            text_reply = _generate_text_only_viewpoint(role_key, role_cfg, question, context, round_num)
        if images and not text_reply.strip():
            text_reply = '本轮已生成右侧配图；文字观点生成为空，建议以配图表达的流程/结构为基础继续讨论。'
        # Keep backward-compatible reply, plus structured fields for new UI.
        return {'role': role_key, 'name': role_cfg['name'], 'emoji': role_cfg['emoji'], 'reply': text_reply or reply, 'images': images, 'image_url': images[0]['url'] if images else None, 'ok': True, 'round': round_num}
    except Exception as e:
        logger.error("\u274c \u8111\u7210\u8c03\u7528\u5931\u8d25: " + str(e))
        return {'role': role_key, 'name': role_cfg['name'], 'emoji': role_cfg['emoji'], 'error': str(e), 'ok': False, 'round': round_num}


@bp.route('/api/actor/brainstorm', methods=['POST'])
def brainstorm():
    data = request.get_json(silent=True) or {}
    question = data.get('question', '')
    max_r = data.get('max_rounds', 3)
    image_mode = bool(data.get('image_mode', False))
    if not question: return jsonify({'ok': False, 'error': 'question required'}), 400
    import random
    avail = [k for k in ROLES.keys() if k != 'ROLE_LIST']
    a = data.get('agent_a', '').strip() or random.choice(avail)
    b = data.get('agent_b', '').strip()
    rem = [r for r in avail if r != a]
    b = b if b in rem else random.choice(rem)
    ca, cb = ROLES[a], ROLES[b]

    def _fmt(rs):
        return _format_brainstorm_context(rs)

    rs = []
    for rn in range(1, max_r + 1):
        ctx = _fmt(rs) if rs else '(首次)'
        ma = _call_agent(a, ca, question, ctx, rn, reference_image_url=_last_brainstorm_image(rs), image_mode=image_mode)
        ctx = _fmt(rs + [[ma]])
        mb = _call_agent(b, cb, question, ctx, rn, reference_image_url=_last_brainstorm_image(rs + [[ma]]), image_mode=image_mode)
        rs.append([ma, mb])

    conclusion = ''
    try:
        fc = _fmt(rs)
        ms = [{'role': 'system', 'content': '你是总结者。'}, {'role': 'user', 'content': '请结合LLM全局上下文总结以下脑风暴，并明确指出哪一个方案/观点最好、为什么最好、建议下一步怎么做。必须包含小节：最佳方案、选择理由、风险、下一步。\nLLM全局上下文摘要：' + get_global_context(3000) + '\n主题：' + question + '\n\n' + fc}]
        bd = json.dumps({'model': 'actor', 'messages': ms, 'max_tokens': 2500, 'knowledge_scope': 'full'}).encode()
        rq = urllib.request.Request('http://127.0.0.1:18791/v1/chat/completions', data=bd, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(rq, timeout=max(BRAINSTORM_AGENT_TIMEOUT, int(max_r) * 30)) as rp:
            conclusion = json.loads(rp.read()).get('choices', [{}])[0].get('message', {}).get('content', '')
    except:
        pass

    agents_info = {'agent_a': {'role': a, 'name': ca['name'], 'emoji': ca['emoji']},
                   'agent_b': {'role': b, 'name': cb['name'], 'emoji': cb['emoji']}}
    history_id = None
    try:
        history_id = _save_brainstorm_history(question, agents_info, rs, conclusion, {'mode': data.get('mode'), 'max_rounds': max_r, 'image_mode': image_mode})
    except Exception as e:
        logger.error('Failed to save brainstorm history: %s', e)

    return jsonify({
        'ok': True, 'question': question,
        'agents': agents_info,
        'rounds': rs, 'conclusion': conclusion,
        'history_id': history_id
    })


@bp.route('/api/actor/brainstorm/stream', methods=['POST'])
def brainstorm_stream():
    return _brainstorm_stream_from_data(request.get_json(silent=True) or {})


def _brainstorm_stream_from_data(data):
    question = data.get('question', '')
    max_r = data.get('max_rounds', 3)
    image_mode = bool(data.get('image_mode', False))
    if not question:
        def _e():
            yield 'event: error\ndata: {"error":"question required"}\n\n'
        return Response(stream_with_context(_e()), mimetype='text/event-stream')
    import random
    avail = [k for k in ROLES.keys() if k != 'ROLE_LIST']
    a = data.get('agent_a', '').strip() or random.choice(avail)
    b = data.get('agent_b', '').strip()
    rem = [r for r in avail if r != a]
    b = b if b in rem else random.choice(rem)
    ca, cb = ROLES[a], ROLES[b]

    def _fmt(rs):
        return _format_brainstorm_context(rs)

    def _gen():
        yield 'event: init\ndata: ' + json.dumps({
            'agents': {'agent_a': {'role': a, 'name': ca['name'], 'emoji': ca['emoji']},
                       'agent_b': {'role': b, 'name': cb['name'], 'emoji': cb['emoji']}},
            'question': question, 'max_rounds': max_r,
            'timeout_budget_s': int(max_r) * 2 * BRAINSTORM_AGENT_TIMEOUT,
            'agent_timeout_s': BRAINSTORM_AGENT_TIMEOUT
        }) + '\n\n'
        rs = []
        for rn in range(1, max_r + 1):
            ctx = _fmt(rs) if rs else '(首次)'
            yield 'event: progress\ndata: ' + json.dumps({'type': 'progress', 'round': rn, 'max_rounds': max_r, 'agent': 'agent_a', 'name': ca.get('name', a), 'message': f'第{rn}/{max_r}轮：{ca.get("name", a)} 思考中...'}) + '\n\n'
            ma = _call_agent(a, ca, question, ctx, rn, reference_image_url=_last_brainstorm_image(rs), image_mode=image_mode)
            yield 'event: message\ndata: ' + json.dumps({'type': 'agent_a', 'round': rn, 'data': ma}) + '\n\n'
            ctx = _fmt(rs + [[ma]])
            yield 'event: progress\ndata: ' + json.dumps({'type': 'progress', 'round': rn, 'max_rounds': max_r, 'agent': 'agent_b', 'name': cb.get('name', b), 'message': f'第{rn}/{max_r}轮：{cb.get("name", b)} 思考中...'}) + '\n\n'
            mb = _call_agent(b, cb, question, ctx, rn, reference_image_url=_last_brainstorm_image(rs + [[ma]]), image_mode=image_mode)
            yield 'event: message\ndata: ' + json.dumps({'type': 'agent_b', 'round': rn, 'data': mb}) + '\n\n'
            rs.append([ma, mb])
        conclusion = ''
        try:
            fc = _fmt(rs)
            ms = [{'role': 'system', 'content': '你是总结者。'}, {'role': 'user', 'content': '请结合LLM全局上下文总结以下脑风暴，并明确指出哪一个方案/观点最好、为什么最好、建议下一步怎么做。必须包含小节：最佳方案、选择理由、风险、下一步。\nLLM全局上下文摘要：' + get_global_context(3000) + '\n主题：' + question + '\n\n' + fc}]
            bd = json.dumps({'model': 'actor', 'messages': ms, 'max_tokens': 2500, 'knowledge_scope': 'full'}).encode()
            rq = urllib.request.Request('http://127.0.0.1:18791/v1/chat/completions', data=bd, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(rq, timeout=max(BRAINSTORM_AGENT_TIMEOUT, int(max_r) * 30)) as rp:
                conclusion = json.loads(rp.read()).get('choices', [{}])[0].get('message', {}).get('content', '')
        except:
            pass
        history_id = None
        try:
            agents_info = {'agent_a': {'role': a, 'name': ca['name'], 'emoji': ca['emoji']},
                           'agent_b': {'role': b, 'name': cb['name'], 'emoji': cb['emoji']}}
            history_id = _save_brainstorm_history(question, agents_info, rs, conclusion, {'mode': data.get('mode'), 'max_rounds': max_r, 'image_mode': image_mode, 'stream': True})
        except Exception as e:
            logger.error('Failed to save streamed brainstorm history: %s', e)
        yield 'event: conclusion\ndata: ' + json.dumps({'conclusion': conclusion, 'history_id': history_id}) + '\n\n'

    return Response(stream_with_context(_gen()), mimetype='text/event-stream')


@bp.route('/api/actor/brainstorm/continue', methods=['POST'])
def brainstorm_continue():
    """Continue a streaming brainstorm session.

    Frontend calls this endpoint when localStorage contains an unfinished
    brainstorm. Reuse the same streaming implementation and pass historical
    messages as context so the request does not fail with HTTP 405.
    """
    data = request.get_json(silent=True) or {}
    history = data.get('history') or []
    question = data.get('question', '')
    if history:
        try:
            hist_lines = []
            for item in history[-20:]:
                payload = item.get('data') if isinstance(item, dict) else None
                if isinstance(payload, dict):
                    name = payload.get('name') or item.get('type', 'agent')
                    reply = payload.get('reply') or payload.get('error') or ''
                    if reply:
                        hist_lines.append(f'{name}: {reply}')
            if hist_lines:
                data['question'] = question + '\n\n【已有脑风暴上下文，继续讨论，不要重复前文】\n' + '\n'.join(hist_lines)
        except Exception as e:
            logger.warning('Failed to fold brainstorm history: %s', e)
    return _brainstorm_stream_from_data(data)

def _download_image_to_local(image_url: str, max_retries: int = 3) -> str:
    """下载远程图片到本地存储，返回本地URL（带重试）"""
    import urllib.request
    import os
    from datetime import datetime
    import time
    
    for attempt in range(max_retries):
        try:
            upload_dir = '/opt/kanban-react/backend/uploads/brainstorm'
            os.makedirs(upload_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            import hashlib
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
            filename = f'brainstorm_{timestamp}_{url_hash}.jpg'
            local_path = os.path.join(upload_dir, filename)
            
            req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=480) as response:
                with open(local_path, 'wb') as f:
                    f.write(response.read())
            
            # 验证下载的图片
            is_valid, error_msg = _validate_image(local_path)
            if not is_valid:
                logger.error(f'Image validation failed: {error_msg}')
                try:
                    os.remove(local_path)
                except:
                    pass
                return None
            
            return f'/uploads/brainstorm/{filename}'
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + __import__('random').random()
                logger.warning(f'Download attempt {attempt+1}/{max_retries} failed: {e}')
                time.sleep(wait)
                continue
            logger.error(f'Failed to download image after {max_retries} attempts: {e}')
            return None
    return None

def _validate_image(image_path: str) -> tuple:
    """验证图片是否有效"""
    try:
        import os
        from PIL import Image
        
        if not os.path.exists(image_path):
            return False, f'Image file not found: {image_path}'
        
        file_size = os.path.getsize(image_path)
        if file_size == 0:
            return False, 'Image file is empty'
        if file_size < 1024:
            return False, f'Image too small ({file_size} bytes)'
        
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                if width < 10 or height < 10:
                    return False, f'Image dimensions too small: {width}x{height}'
                img.verify()
        except Exception as e:
            return False, f'Image format error: {e}'
        
        return True, ''
    except Exception as e:
        return False, f'Validation error: {e}'


@bp.route('/api/actor/brainstorm-history', methods=['GET'])
def brainstorm_history():
    history = _load_history(BRAINSTORM_HISTORY_FILE)
    summary = []
    for e in history[:100]:
        agents = e.get('agents') or {}
        participants = []
        for v in agents.values():
            if isinstance(v, dict):
                participants.append(v.get('name') or v.get('role') or '')
        summary.append({
            'id': str(e.get('id', '')),
            'type': 'brainstorm',
            'created_at': e.get('created_at', ''),
            'timestamp': e.get('created_at', ''),
            'question': e.get('question', ''),
            'participants': [x for x in participants if x],
            'round_count': len(e.get('rounds') or []),
            'has_conclusion': bool(e.get('conclusion')),
        })
    return jsonify({'ok': True, 'history': summary})


@bp.route('/api/actor/brainstorm-history/<entry_id>', methods=['GET'])
def brainstorm_history_detail(entry_id):
    for e in _load_history(BRAINSTORM_HISTORY_FILE):
        if str(e.get('id')) == str(entry_id):
            return jsonify({'ok': True, 'entry': e})
    return jsonify({'ok': False, 'error': 'not found'}), 404

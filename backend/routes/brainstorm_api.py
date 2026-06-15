"""
Brainstorm routes - separate module to avoid corrupting actor_api.py
"""
from flask import Blueprint, jsonify, request, Response, stream_with_context
import json, urllib.request, os, logging
from routes.actor_tools import TOOL_REGISTRY

bp = Blueprint("brainstorm_api", __name__)
logger = logging.getLogger(__name__)

ROLES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'routes', 'actor_api.py')

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


def _call_agent(role_key, role_cfg, question, context, round_num, max_tokens=80000):
    """Call actor service with tools"""
    msgs = [
        {'role': 'system', 'content': role_cfg['prompt']},
        {'role': 'user', 'content': '讨论主题：' + question + '\n\n上下文：' + context + '\n\n请发表观点。'}
    ]
    body = {
        'model': 'actor', 'messages': msgs,
        'max_tokens': max_tokens, 'knowledge_scope': role_cfg['scope'],
        'role': role_key, 'tools': role_cfg.get('tools', []),
    }
    try:
        req = urllib.request.Request('http://127.0.0.1:18791/v1/chat/completions',
            data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read())
        # Process tool calls
        msg = resp.get('choices', [{}])[0].get('message', {})
        tcs = msg.get('tool_calls', [])
        c = msg.get('content', '') or ''
        parts = [c]
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
        reply = '\n'.join(parts)
        return {'role': role_key, 'name': role_cfg['name'], 'emoji': role_cfg['emoji'], 'reply': reply, 'ok': True, 'round': round_num}
    except Exception as e:
        logger.error("\u274c \u8111\u7210\u8c03\u7528\u5931\u8d25: " + str(e))
        return {'role': role_key, 'name': role_cfg['name'], 'emoji': role_cfg['emoji'], 'error': str(e), 'ok': False, 'round': round_num}


@bp.route('/api/actor/brainstorm', methods=['POST'])
def brainstorm():
    data = request.get_json(silent=True) or {}
    question = data.get('question', '')
    max_r = data.get('max_rounds', 3)
    if not question: return jsonify({'ok': False, 'error': 'question required'}), 400
    import random
    avail = [k for k in ROLES.keys() if k != 'ROLE_LIST']
    a = data.get('agent_a', '').strip() or random.choice(avail)
    b = data.get('agent_b', '').strip()
    rem = [r for r in avail if r != a]
    b = b if b in rem else random.choice(rem)
    ca, cb = ROLES[a], ROLES[b]

    def _fmt(rs):
        ls = []
        for rd in rs:
            for m in rd:
                if m.get('ok'): ls.append(m['emoji'] + ' ' + m['name'] + ': ' + m['reply'])
        return '\n'.join(ls)

    rs = []
    for rn in range(1, max_r + 1):
        ctx = _fmt(rs) if rs else '(首次)'
        ma = _call_agent(a, ca, question, ctx, rn)
        ctx = _fmt(rs + [[ma]])
        mb = _call_agent(b, cb, question, ctx, rn)
        rs.append([ma, mb])

    conclusion = ''
    try:
        fc = _fmt(rs)
        ms = [{'role': 'system', 'content': '你是总结者。'}, {'role': 'user', 'content': '总结：' + question + '\n\n' + fc}]
        bd = json.dumps({'model': 'actor', 'messages': ms, 'max_tokens': 80000, 'knowledge_scope': 'full'}).encode()
        rq = urllib.request.Request('http://127.0.0.1:18791/v1/chat/completions', data=bd, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(rq, timeout=120) as rp:
            conclusion = json.loads(rp.read()).get('choices', [{}])[0].get('message', {}).get('content', '')
    except:
        pass

    return jsonify({
        'ok': True, 'question': question,
        'agents': {'agent_a': {'role': a, 'name': ca['name'], 'emoji': ca['emoji']},
                   'agent_b': {'role': b, 'name': cb['name'], 'emoji': cb['emoji']}},
        'rounds': rs, 'conclusion': conclusion
    })


@bp.route('/api/actor/brainstorm/stream', methods=['POST'])
def brainstorm_stream():
    data = request.get_json(silent=True) or {}
    question = data.get('question', '')
    max_r = data.get('max_rounds', 3)
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
        ls = []
        for rd in rs:
            for m in rd:
                if m.get('ok'): ls.append(m['emoji'] + ' ' + m['name'] + ': ' + m['reply'])
        return '\n'.join(ls)

    def _gen():
        yield 'event: init\ndata: ' + json.dumps({
            'agents': {'agent_a': {'role': a, 'name': ca['name'], 'emoji': ca['emoji']},
                       'agent_b': {'role': b, 'name': cb['name'], 'emoji': cb['emoji']}},
            'question': question, 'max_rounds': max_r
        }) + '\n\n'
        rs = []
        for rn in range(1, max_r + 1):
            ctx = _fmt(rs) if rs else '(首次)'
            ma = _call_agent(a, ca, question, ctx, rn)
            yield 'event: message\ndata: ' + json.dumps({'type': 'agent_a', 'round': rn, 'data': ma}) + '\n\n'
            ctx = _fmt(rs + [[ma]])
            mb = _call_agent(b, cb, question, ctx, rn)
            yield 'event: message\ndata: ' + json.dumps({'type': 'agent_b', 'round': rn, 'data': mb}) + '\n\n'
            rs.append([ma, mb])
        conclusion = ''
        try:
            fc = _fmt(rs)
            ms = [{'role': 'system', 'content': '你是总结者。'}, {'role': 'user', 'content': '总结：' + question + '\n\n' + fc}]
            bd = json.dumps({'model': 'actor', 'messages': ms, 'max_tokens': 80000, 'knowledge_scope': 'full'}).encode()
            rq = urllib.request.Request('http://127.0.0.1:18791/v1/chat/completions', data=bd, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(rq, timeout=120) as rp:
                conclusion = json.loads(rp.read()).get('choices', [{}])[0].get('message', {}).get('content', '')
        except:
            pass
        yield 'event: conclusion\ndata: ' + json.dumps({'conclusion': conclusion}) + '\n\n'

    return Response(stream_with_context(_gen()), mimetype='text/event-stream')

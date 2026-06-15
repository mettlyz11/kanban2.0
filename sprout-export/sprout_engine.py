#!/usr/bin/env python3
"""SproutOS Growth Engine v2 — Persistence · Priority · LLM · Scenarios"""
import json, os, sys, uuid, time, sqlite3, threading, urllib.request
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

SPROUT_DIR = Path.home() / '.sprout'
SPROUT_DIR.mkdir(exist_ok=True)

LLM_API = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
LLM_KEY = os.environ.get('HUOSHAN_API_KEY') or os.environ.get('ARK_API_KEY', '')
LLM_MODEL = "doubao-seed-2-0-pro-260215"

# ─── PERSISTENCE ───
def _db():
    conn = sqlite3.connect(str(SPROUT_DIR / 'sprout.db'))
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        token TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')), plan TEXT DEFAULT 'free')''')
    conn.execute('''CREATE TABLE IF NOT EXISTS garden_assignments (
        garden_id TEXT, user_token TEXT, role TEXT DEFAULT 'owner',
        PRIMARY KEY (garden_id, user_token))''')
    conn.row_factory = sqlite3.Row
    conn.execute('''CREATE TABLE IF NOT EXISTS gardens (
        id TEXT PRIMARY KEY, goal TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')), scenario TEXT DEFAULT '',
        leaves TEXT DEFAULT '[]', diary TEXT DEFAULT '[]')''')
    conn.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, metric TEXT NOT NULL,
        operator TEXT NOT NULL, threshold REAL NOT NULL, duration_min INTEGER DEFAULT 5,
        enabled INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now')))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY, user_token TEXT NOT NULL, plan TEXT NOT NULL,
        amount TEXT NOT NULL, status TEXT DEFAULT 'pending', paid_at TEXT,
        created_at TEXT DEFAULT (datetime('now')))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        user_token TEXT PRIMARY KEY, plan TEXT NOT NULL, expires_at TEXT,
        updated_at TEXT DEFAULT (datetime('now')))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS listings (
        id TEXT PRIMARY KEY, garden_id TEXT NOT NULL, title TEXT NOT NULL,
        price TEXT DEFAULT '¥0', description TEXT DEFAULT '', status TEXT DEFAULT 'draft',
        created_at TEXT DEFAULT (datetime('now')))''')
    return conn

db_lock = threading.Lock()

def save_garden(gid, goal, leaves, diary, scenario=''):
    with db_lock:
        db = _db()
        db.execute('INSERT OR REPLACE INTO gardens (id,goal,scenario,leaves,diary,updated_at) VALUES (?,?,?,?,?,datetime("now"))',
                   (gid, goal, scenario, json.dumps(leaves), json.dumps(diary)))
        db.commit(); db.close()

def load_garden(gid):
    with db_lock:
        db = _db()
        r = db.execute('SELECT * FROM gardens WHERE id=?', (gid,)).fetchone()
        db.close(); return dict(r) if r else None

def list_gardens():
    with db_lock:
        db = _db()
        rows = db.execute('SELECT id,goal,scenario,updated_at,length(leaves) as leaf_count FROM gardens ORDER BY updated_at DESC LIMIT 20').fetchall()
        db.close(); return [dict(r) for r in rows]

# ─── PRIORITY ENGINE ───
def calc_priority(leaf, all_leaves):
    score, lid = 0, leaf.get('id','')
    deps = leaf.get('deps', leaf.get('dependencies',[]))
    if any(lid in l.get('deps',[]) for l in all_leaves): score += 2
    if leaf.get('complexity',3) <= 2: score += 1
    existing_ids = [l.get('id','') for l in all_leaves]
    if all(d in existing_ids for d in deps): score += 1
    return min(score,5)

def suggest_next(all_leaves):
    existing_ids = [l.get('id','') for l in all_leaves]
    candidates = []
    for leaf in all_leaves:
        for dep_id in leaf.get('deps',[]):
            if dep_id not in existing_ids:
                candidates.append((calc_priority({'id':dep_id,'complexity':1,'deps':[]}, all_leaves), dep_id))
    for tid, tmpl in TEMPLATES.items():
        if tid not in existing_ids and all(d in existing_ids for d in tmpl.get('dependencies',[])):
            candidates.append((calc_priority(tmpl, all_leaves), tid))
    candidates.sort(reverse=True)
    return [c[1] for c in candidates[:5]]

# ─── TEMPLATES ───
TEMPLATES = {
    "bookkeeping": {"name":"记账","description":"记录收入和支出","dependencies":[],"complexity":1,"emoji":"📝"},
    "category": {"name":"分类管理","description":"自动归类收支","dependencies":["bookkeeping"],"complexity":2,"emoji":"🏷️ufe0f"},
    "report": {"name":"报表","description":"生成图表和报告","dependencies":["bookkeeping"],"complexity":3,"emoji":"📊"},
    "budget": {"name":"预算","description":"设定预算和告警","dependencies":["category"],"complexity":3,"emoji":"🎯"},
    "import_export": {"name":"数据导入导出","description":"从外部源导入数据","dependencies":["bookkeeping"],"complexity":2,"emoji":"📦"},
}

# ─── SCENARIOS ───
SCENARIOS = {
    "research": {"name":"科研管理系统","emoji":"🔬","leaves":[
        {"id":"paper_lib","name":"文献库","description":"论文专利增删查改","deps":[],"emoji":"📚","complexity":2},
        {"id":"paper_import","name":"文献导入","description":"从DOI/arXiv自动导入","deps":["paper_lib"],"emoji":"📥","complexity":2},
        {"id":"paper_tag","name":"文献标签","description":"自定义标签+AI自动分类","deps":["paper_lib"],"emoji":"🏷️","complexity":3},
        {"id":"paper_search","name":"文献检索","description":"全文+语义检索","deps":["paper_lib"],"emoji":"🔍","complexity":3},
        {"id":"reference_gen","name":"参考文献生成","description":"自动生成引用格式","deps":["paper_lib"],"emoji":"📝","complexity":2},
        {"id":"exp_tracker","name":"实验记录","description":"实验日志、参数、结果","deps":[],"emoji":"🧪","complexity":2},
        {"id":"exp_calc","name":"数据计算","description":"实验结果自动计算+图表","deps":["exp_tracker"],"emoji":"📊","complexity":3},
        {"id":"exp_compare","name":"实验对比","description":"多组实验横向对比","deps":["exp_calc"],"emoji":"⚖️","complexity":3},
        {"id":"project_plan","name":"项目计划","description":"课题里程碑+任务分配","deps":[],"emoji":"📋","complexity":2},
        {"id":"grant_tracker","name":"经费追踪","description":"项目经费使用记录","deps":["project_plan"],"emoji":"💰","complexity":2},
        {"id":"team_view","name":"团队看板","description":"团队成员进度卡片","deps":["project_plan"],"emoji":"👥","complexity":3},
        {"id":"pub_tracker","name":"发表追踪","description":"论文投稿状态+会议提醒","deps":["paper_lib"],"emoji":"🏆","complexity":3},
        {"id":"data_backup","name":"数据备份","description":"自动备份到云端","deps":[],"emoji":"💾","complexity":1},
    ]},
    "finance": {"name":"个人财务系统","emoji":"💰","leaves":[
        {"id":"bookkeeping","name":"记账","deps":[],"emoji":"📝","complexity":1,"description":"记录收支"},
        {"id":"category","name":"分类管理","deps":["bookkeeping"],"emoji":"🏷️","complexity":2,"description":"自动归类"},
        {"id":"report","name":"报表","deps":["bookkeeping"],"emoji":"📊","complexity":3,"description":"图表报告"},
        {"id":"budget","name":"预算","deps":["category"],"emoji":"🎯","complexity":3,"description":"预算告警"},
        {"id":"import_export","name":"导入导出","deps":["bookkeeping"],"emoji":"📦","complexity":2,"description":"银行/支付宝导入"},
    ]},
    "company": {"name":"公司管理系统","emoji":"🏢","leaves":[
        {"id":"crm","name":"客户管理","deps":[],"emoji":"👤","complexity":2,"description":"客户信息与跟进"},
        {"id":"project","name":"项目管理","deps":[],"emoji":"📋","complexity":2,"description":"项目进度任务"},
        {"id":"finance","name":"财务","deps":[],"emoji":"💰","complexity":2,"description":"收入支出发票"},
        {"id":"hr","name":"人事","deps":[],"emoji":"👥","complexity":2,"description":"员工考勤"},
        {"id":"doc_mgr","name":"文档管理","deps":[],"emoji":"📄","complexity":1,"description":"合同文档版本"},
    ]},
}

# ─── LLM ───
def call_llm(system, user):
    if not LLM_KEY: return json.dumps({"error":"no LLM key"})
    body = json.dumps({"model":LLM_MODEL,"messages":[
        {"role":"system","content":system},{"role":"user","content":user}
    ],"max_tokens":2000,"temperature":0.3,"stream":False}).encode()
    req = urllib.request.Request(LLM_API, data=body,
        headers={"Content-Type":"application/json","Authorization":f"Bearer {LLM_KEY}"})
    try:
        r = json.loads(urllib.request.urlopen(req,timeout=30).read())
        return r['choices'][0]['message']['content']
    except Exception as e:
        return json.dumps({"error":str(e)})

# ─── HTTP HANDLER ───
class SproutHandler(BaseHTTPRequestHandler):
    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin','*')
        self.end_headers()
        payload = json.dumps(data, ensure_ascii=True)
        self.wfile.write(payload.encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.end_headers()

    def _p(self):
        return self.path.replace('/api/sprout','') or '/'

    def do_GET(self):
        p = self._p()
        if p == '/templates': self._send_json(TEMPLATES)
        elif p == '/scenarios':
            self._send_json({k:{'name':v['name'],'emoji':v['emoji'],'count':len(v['leaves'])} for k,v in SCENARIOS.items()})
        elif p == '/health': self._send_json({"status":"ok","engine":"sprout","version":"0.2"})
        elif p == '/gardens': self._send_json(list_gardens())
        elif p.startswith('/garden/'): self._send_json(load_garden(p[8:]) or {'error':'not found'})
        elif p == '/market/listings':
            db=_db(); rows=db.execute('SELECT * FROM listings ORDER BY created_at DESC LIMIT 50').fetchall(); db.close()
            self._send_json([dict(r) for r in rows])
        elif p == '/alerts/log':
            log_path = SPROUT_DIR / 'alert_log.jsonl'
            if log_path.exists():
                with open(log_path) as lf: lines = lf.readlines()[-20:]
                self._send_json([json.loads(l) for l in lines])
            else: self._send_json([])
        elif p == '/alerts/rules':
            with db_lock:
                db = _db()
                rows = db.execute('SELECT id,name,metric,operator,threshold,duration_min,enabled FROM alerts ORDER BY created_at DESC').fetchall()
                db.close()
                self._send_json([dict(r) for r in rows])
        elif p == '/export/view':
            # Return HTML for export page
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            html = '''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SproutOS 导出</title><style>body{background:#0f172a;color:#e2e8f0;font-family:system-ui;max-width:700px;margin:0 auto;padding:20px}.card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:24px;margin:16px 0}h1{font-size:24px}.btn{padding:10px 24px;border:none;border-radius:8px;cursor:pointer;font-size:14px;background:#22c55e;color:#fff;font-weight:600}.info{color:#64748b;font-size:11px}</style></head><body>
<h1>x1f331 SproutOS</h1>
<div class="card"><h2>x1f4e6 导出你的系统</h2><p style="color:#94a3b8">你的树可以带走。所有数据、所有功能、所有生长历史。</p>
<p style="color:#475569;font-size:12px">格式：SproutOS Package (.json)<br>部署：docker compose up<br>兼容：任何有 Node.js/Docker 的环境</p>
<a href="/api/sprout/export/latest" class="btn">x1f4e5 下载最新导出</a></div>
<div class="card"><h2>x2696ufe0f 协议</h2><p style="color:#94a3b8;font-size:12px">你养的系统是你的。MIT License。自由使用、修改、分发。</p></div>
<div style="text-align:center;color:#475569;font-size:10px;margin-top:32px">SproutOS Growth Engine v0.2</div></body></html>'''
            self.wfile.write(html.encode())
        elif p == '/market/list':
            lid=str(uuid.uuid4())[:8]
            garden_id=body.get('garden_id','')
            title=body.get('title') or body.get('goal') or 'Untitled Garden'
            price=body.get('price','¥0')
            description=body.get('description','')
            db=_db(); db.execute('INSERT OR REPLACE INTO listings (id,garden_id,title,price,description,status) VALUES (?,?,?,?,?,?)',(lid,garden_id,title,price,description,'listed')); db.commit(); db.close()
            self._send_json({'id':lid,'garden_id':garden_id,'title':title,'price':price,'status':'listed'})
        elif p == '/alert/create':
            speech = body.get('speech', '')
            # Use LLM to parse
            result = self.handle_alert_parse(speech)
            if 'error' in result:
                self._send_json(result)
                return
            aid = str(uuid.uuid4())[:8]
            with db_lock:
                db = _db()
                db.execute('INSERT INTO alerts (id,name,metric,operator,threshold,duration_min) VALUES (?,?,?,?,?,?)',
                    (aid, result.get('name','Alert'), result['metric'], result['operator'], result['threshold'], result.get('duration_min',5)))
                db.commit()
                db.close()
            result['id'] = aid
            self._send_json(result)
        elif p == "/payment/create":
            plan = body.get("plan", "growth")
            prices = {"seed": "0", "growth": "19", "bloom": "99", "garden": "499"}
            oid = str(uuid.uuid4())[:12]
            db = _db()
            db.execute('INSERT INTO orders (id,user_token,plan,amount,status) VALUES (?,?,?,?,?)',
                       (oid, body.get("user_token",""), plan, prices.get(plan, "19"), "pending"))
            db.commit()
            db.close()
            self._send_json({"order_id": oid, "plan": plan, "amount": prices.get(plan, "19"), "status": "pending"})
        elif p == "/payment/status":
            oid = body.get("order_id", "")
            db = _db()
            r = db.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
            db.close()
            self._send_json(dict(r) if r else {"error": "not found"})
        elif p == "/payment/webhook":
            oid = body.get("order_id", "")
            db = _db()
            db.execute("UPDATE orders SET status='paid', paid_at=datetime('now') WHERE id=?", (oid,))
            db.execute("INSERT OR REPLACE INTO subscriptions (user_token,plan,expires_at) VALUES (?,?,datetime('now','+30 days'))",
                       (body.get("user_token",""), body.get("plan","growth")))
            db.commit()
            db.close()
            self._send_json({"status": "ok", "order_id": oid})
        elif p == "/payment/qr":
            oid = body.get("order_id", "")
            db = _db()
            order = db.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
            db.close()
            if not order:
                self._send_json({"error": "order not found"})
            else:
                import qrcode, io, base64
                pay_url = f"https://kanbanyun.com/payment/confirm?id={oid}"
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(pay_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                qr_b64 = base64.b64encode(buffer.getvalue()).decode()
                o = dict(order)
                self._send_json({"order_id": oid, "amount": o.get("amount", "19"), "qr_code": f"data:image/png;base64,{qr_b64}", "pay_url": pay_url, "methods": ["wechat", "alipay"]})
        elif p == "/payment/confirm":
            oid = body.get("order_id", "")
            db = _db()
            db.execute("UPDATE orders SET status='paid', paid_at=datetime('now') WHERE id=?", (oid,))
            order = db.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
            if order:
                o = dict(order)
                db.execute("INSERT OR REPLACE INTO subscriptions (user_token,plan,expires_at) VALUES (?,?,datetime('now','+30 days'))", (o.get("user_token",""), o.get("plan","growth")))
            db.commit()
            db.close()
            self._send_json({"status": "success", "order_id": oid})
        else: self._send_json({"error":"unknown path"})

    def do_POST(self):
        length = int(self.headers.get('Content-Length',0))
        body = json.loads(self.rfile.read(length)) if length else {}
        p = self._p()
        if p == '/parse':
            self._send_json(json.loads(self.handle_parse(body)))
        elif p == '/grow':
            result = json.loads(self.handle_grow(body))
            gid = body.get('garden_id','')
            if gid and result.get('action') in ('grow','prune'):
                old_leaves = body.get('current_leaves',[])
                if result['action']=='grow' and result.get('leaf'):
                    new_leaf = result['leaf']; new_leaf['status']='growing'
                    new_leaves = old_leaves + [new_leaf]
                elif result['action']=='prune' and result.get('target'):
                    new_leaves = [l for l in old_leaves if l.get('id')!=result['target']]
                else: new_leaves = old_leaves
                diary = body.get('diary',[])
                diary.insert(0,{'time':time.strftime('%H:%M:%S'),'event':'Sprout: '+result['action']})
                try: save_garden(gid,body.get('goal',''),new_leaves,diary,body.get('scenario',''))
                except: pass
            self._send_json(result)
        elif p == '/scenario':
            s = SCENARIOS.get(body.get('name',''))
            if s: self._send_json({'name':s['name'],'emoji':s['emoji'],'leaves':s['leaves']})
            else: self._send_json({'error':'not found','available':list(SCENARIOS.keys())})
        elif p == '/suggest':
            self._send_json({'suggestions':suggest_next(body.get('leaves',[]))})
        elif p == '/auth/register':
            name = body.get('name', 'anonymous')
            import hashlib
            token = hashlib.md5((name+str(time.time())).encode()).hexdigest()[:16]
            db = _db()
            db.execute('INSERT OR IGNORE INTO users (token,name) VALUES (?,?)', (token, name))
            db.commit()
            user = db.execute('SELECT * FROM users WHERE token=?', (token,)).fetchone()
            db.close()
            self._send_json({'token': token, 'user': dict(user)})
        elif p == '/garden/save':
            gid = body.get('id',str(uuid.uuid4()))
            save_garden(gid,body.get('goal',''),body.get('leaves',[]),body.get('diary',[]),body.get('scenario',''))
            self._send_json({'id':gid,'saved':True})
        elif p == '/market/listings':
            db=_db(); rows=db.execute('SELECT * FROM listings ORDER BY created_at DESC LIMIT 50').fetchall(); db.close()
            self._send_json([dict(r) for r in rows])
        elif p == '/alerts/log':
            log_path = SPROUT_DIR / 'alert_log.jsonl'
            if log_path.exists():
                with open(log_path) as lf: lines = lf.readlines()[-20:]
                self._send_json([json.loads(l) for l in lines])
            else: self._send_json([])
        elif p == '/alerts/rules':
            with db_lock:
                db = _db()
                rows = db.execute('SELECT id,name,metric,operator,threshold,duration_min,enabled FROM alerts ORDER BY created_at DESC').fetchall()
                db.close()
                self._send_json([dict(r) for r in rows])
        elif p == '/export/view':
            # Return HTML for export page
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            html = '''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SproutOS 导出</title><style>body{background:#0f172a;color:#e2e8f0;font-family:system-ui;max-width:700px;margin:0 auto;padding:20px}.card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:24px;margin:16px 0}h1{font-size:24px}.btn{padding:10px 24px;border:none;border-radius:8px;cursor:pointer;font-size:14px;background:#22c55e;color:#fff;font-weight:600}.info{color:#64748b;font-size:11px}</style></head><body>
<h1>x1f331 SproutOS</h1>
<div class="card"><h2>x1f4e6 导出你的系统</h2><p style="color:#94a3b8">你的树可以带走。所有数据、所有功能、所有生长历史。</p>
<p style="color:#475569;font-size:12px">格式：SproutOS Package (.json)<br>部署：docker compose up<br>兼容：任何有 Node.js/Docker 的环境</p>
<a href="/api/sprout/export/latest" class="btn">x1f4e5 下载最新导出</a></div>
<div class="card"><h2>x2696ufe0f 协议</h2><p style="color:#94a3b8;font-size:12px">你养的系统是你的。MIT License。自由使用、修改、分发。</p></div>
<div style="text-align:center;color:#475569;font-size:10px;margin-top:32px">SproutOS Growth Engine v0.2</div></body></html>'''
            self.wfile.write(html.encode())
        elif p == '/market/list':
            lid=str(uuid.uuid4())[:8]
            garden_id=body.get('garden_id','')
            title=body.get('title') or body.get('goal') or 'Untitled Garden'
            price=body.get('price','¥0')
            description=body.get('description','')
            db=_db(); db.execute('INSERT OR REPLACE INTO listings (id,garden_id,title,price,description,status) VALUES (?,?,?,?,?,?)',(lid,garden_id,title,price,description,'listed')); db.commit(); db.close()
            self._send_json({'id':lid,'garden_id':garden_id,'title':title,'price':price,'status':'listed'})
        elif p == '/alert/create':
            speech = body.get('speech', '')
            # Use LLM to parse
            result = self.handle_alert_parse(speech)
            if 'error' in result:
                self._send_json(result)
                return
            aid = str(uuid.uuid4())[:8]
            with db_lock:
                db = _db()
                db.execute('INSERT INTO alerts (id,name,metric,operator,threshold,duration_min) VALUES (?,?,?,?,?,?)',
                    (aid, result.get('name','Alert'), result['metric'], result['operator'], result['threshold'], result.get('duration_min',5)))
                db.commit()
                db.close()
            result['id'] = aid
            self._send_json(result)
        elif p == "/payment/create":
            plan = body.get("plan", "growth")
            prices = {"seed": "0", "growth": "19", "bloom": "99", "garden": "499"}
            oid = str(uuid.uuid4())[:12]
            db = _db()
            db.execute('INSERT INTO orders (id,user_token,plan,amount,status) VALUES (?,?,?,?,?)',
                       (oid, body.get("user_token",""), plan, prices.get(plan, "19"), "pending"))
            db.commit()
            db.close()
            self._send_json({"order_id": oid, "plan": plan, "amount": prices.get(plan, "19"), "status": "pending"})
        elif p == "/payment/status":
            oid = body.get("order_id", "")
            db = _db()
            r = db.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
            db.close()
            self._send_json(dict(r) if r else {"error": "not found"})
        elif p == "/payment/webhook":
            oid = body.get("order_id", "")
            db = _db()
            db.execute("UPDATE orders SET status='paid', paid_at=datetime('now') WHERE id=?", (oid,))
            db.execute("INSERT OR REPLACE INTO subscriptions (user_token,plan,expires_at) VALUES (?,?,datetime('now','+30 days'))",
                       (body.get("user_token",""), body.get("plan","growth")))
            db.commit()
            db.close()
            self._send_json({"status": "ok", "order_id": oid})
        else: self._send_json({"error":"unknown path"})

    def handle_parse(self, body):
        goal = body.get('goal','')
        existing = body.get('existing_leaves',[])
        sys_prompt = '你是一个目标解析引擎。将用户目标拆解为功能叶子列表。\n返回 JSON 数组，每项: {"id":"唯一id","name":"名称","description":"描述","deps":["依赖id"],"emoji":"表情符","complexity":1-5}\n只返回 JSON。'
        prompt = '用户目标：'+goal+'\n已有功能：'+json.dumps(existing,ensure_ascii=False)+'\n返回建议新增的功能（1-3个，优先级排序）：'
        return call_llm(sys_prompt, prompt)

    def handle_grow(self, body):
        speech = body.get('speech','')
        leaves = body.get('current_leaves',[])
        sys_prompt = '你是一个生长决策引擎。用户说了句话，你决定下一步长什么。\n可以是:\n- {"action":"grow","leaf":{"id":"...","name":"...","emoji":"...","deps":[],"complexity":1}}\n- {"action":"prune","target":"leaf_id","suggestion":"..."}\n- {"action":"query","description":"..."}\n- {"action":"guide","target":"leaf_id","direction":"..."}\n只返回 JSON。'
        prompt = '用户说:"'+speech+'"\n当前叶子:'+json.dumps(leaves,ensure_ascii=False)+'\n请解析意图返回JSON。'
        return call_llm(sys_prompt, prompt)

    def handle_alert_parse(self, speech):
        sys_prompt = 'Parse user alert requirement into JSON. Return: {"metric":"...","operator":">|<|>=|<=","threshold":number,"duration_min":number,"name":"..."}'
        prompt = 'User said: "' + speech + '"'
        result = call_llm(sys_prompt, prompt)
        try:
            return json.loads(result)
        except:
            return {"error": "parse failed", "raw": result}

def check_alerts():
    import random
    while True:
        time.sleep(60)
        try:
            db = _db()
            rules = db.execute('SELECT * FROM alerts WHERE enabled=1').fetchall()
            for rule in rules:
                r = dict(rule)
                current = random.uniform(10,100)
                if 'cpu' in r['metric'].lower():
                    try: import psutil; current = psutil.cpu_percent()
                    except: current = random.uniform(30,95)
                triggered = False
                if r['operator'] == '>' and current > r['threshold']: triggered = True
                elif r['operator'] == '<' and current < r['threshold']: triggered = True
                if triggered:
                    log_path = SPROUT_DIR / 'alert_log.jsonl'
                    with open(log_path,'a') as lf:
                        lf.write(json.dumps({'time':time.time(),'rule_id':r['id'],'name':r['name'],'metric':r['metric'],'current':round(current,1),'threshold':r['threshold']})+'\n')
                    # print(f"[{time.strftime('%H:%M:%S')}] ALERT: {r['name']}")
            db.close()
        except: pass

def start_server(port=18795):
    _db()
    t = threading.Thread(target=check_alerts, daemon=True)
    t.start()
    # print('[SproutOS] Alert monitor started')
    HTTPServer(('127.0.0.1',port), SproutHandler).serve_forever()

if __name__ == '__main__':
    start_server()

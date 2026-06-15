#!/usr/bin/env python3
"""SproutOS Engine v0.3 - Payment Ready"""
import json, os, sys, uuid, time, sqlite3, threading, urllib.request, qrcode, io, base64
from pathlib import Path
from datetime import datetime

SPROUT_DIR = Path.home() / '.sprout'
SPROUT_DIR.mkdir(exist_ok=True)
DB_PATH = SPROUT_DIR / 'sprout.db'

def _db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = _db()
    db.execute('''CREATE TABLE IF NOT EXISTS gardens (
        id TEXT PRIMARY KEY, goal TEXT, leaves TEXT, diary TEXT,
        scenario TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        token TEXT PRIMARY KEY, name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY, user_token TEXT, plan TEXT, amount TEXT,
        status TEXT, paid_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        user_token TEXT PRIMARY KEY, plan TEXT, expires_at TIMESTAMP
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS listings (
        id TEXT PRIMARY KEY, garden_id TEXT, title TEXT, price TEXT,
        description TEXT, status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY, name TEXT, metric TEXT, operator TEXT,
        threshold REAL, duration_min INTEGER, enabled INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS wechat_bridge_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, msg TEXT, sent INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.commit()
    db.close()

init_db()

SCENARIOS = {
    'research': {'name':'科研管理系统','emoji':'🔬','leaves':[
        {'id':'r1','name':'文献调研','status':'growing','deps':[]},
        {'id':'r2','name':'实验设计','status':'pending','deps':['r1']},
        {'id':'r3','name':'数据采集','status':'pending','deps':['r2']},
        {'id':'r4','name':'论文撰写','status':'pending','deps':['r3']},
        {'id':'r5','name':'投稿跟踪','status':'pending','deps':['r4']}
    ]},
    'finance': {'name':'个人财务系统','emoji':'💰','leaves':[
        {'id':'f1','name':'收支记录','status':'growing','deps':[]},
        {'id':'f2','name':'预算规划','status':'pending','deps':['f1']},
        {'id':'f3','name':'投资跟踪','status':'pending','deps':['f2']}
    ]},
    'company': {'name':'公司管理系统','emoji':'🏢','leaves':[
        {'id':'c1','name':'团队管理','status':'growing','deps':[]},
        {'id':'c2','name':'项目追踪','status':'pending','deps':['c1']},
        {'id':'c3','name':'财务报告','status':'pending','deps':['c2']}
    ]}
}

def save_garden(gid, goal, leaves, diary, scenario):
    db = _db()
    db.execute('INSERT OR REPLACE INTO gardens (id,goal,leaves,diary,scenario) VALUES (?,?,?,?,?)',
               (gid, goal, json.dumps(leaves), json.dumps(diary), scenario))
    db.commit()
    db.close()

def suggest_next(leaves):
    pending = [l for l in leaves if l.get('status')=='pending']
    growing = [l for l in leaves if l.get('status')=='growing']
    if not growing and pending:
        return [{'action':'grow','target':pending[0]['id'],'reason':'开始第一个任务'}]
    return []

class Handler:
    def __init__(self, request, client_address, server):
        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()
    
    def setup(self):
        self.rfile = self.request.makefile('rb', -1)
        self.wfile = self.request.makefile('wb', 0)
    
    def finish(self):
        self.wfile.flush()
        self.rfile.close()
        self.wfile.close()
    
    def handle(self):
        self.raw_requestline = self.rfile.readline(65537)
        if not self.raw_requestline:
            return
        self.parse_request()
        mname = 'do_' + self.command
        if hasattr(self, mname):
            method = getattr(self, mname)
            method()
        else:
            self.send_error(501)
    
    def parse_request(self):
        parts = self.raw_requestline.decode('iso-8859-1').split()
        self.command = parts[0] if parts else ''
        self.path = parts[1] if len(parts) > 1 else ''
        self.headers = {}
        while True:
            line = self.rfile.readline().decode('iso-8859-1').strip()
            if not line:
                break
            if ':' in line:
                k, v = line.split(':', 1)
                self.headers[k.strip().lower()] = v.strip()
    
    def send_error(self, code):
        self.send_response(code)
        self.end_headers()
    
    def send_response(self, code, message=None):
        self.wfile.write(f"HTTP/1.1 {code} OK\\r\\n".encode())
    
    def send_header(self, key, value):
        self.wfile.write(f"{key}: {value}\\r\\n".encode())
    
    def end_headers(self):
        self.wfile.write(b"\\r\\n")
    
    def _p(self):
        return self.path.replace('/api/sprout', '').replace('/sprout', '') or '/'
    
    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=True).encode())
    
    def do_GET(self):
        p = self._p()
        if p == '/health':
            self._send_json({'status':'ok','engine':'sprout','version':'0.3'})
        elif p == '/scenarios':
            self._send_json({k:{'name':v['name'],'emoji':v['emoji'],'leaf_count':len(v['leaves'])} for k,v in SCENARIOS.items()})
        elif p == '/gardens':
            db = _db()
            rows = db.execute('SELECT id, goal, scenario, created_at FROM gardens ORDER BY created_at DESC').fetchall()
            db.close()
            self._send_json([dict(r) for r in rows])
        elif p.startswith('/garden/'):
            gid = p.split('/')[-1]
            db = _db()
            row = db.execute('SELECT * FROM gardens WHERE id=?', (gid,)).fetchone()
            db.close()
            if row:
                r = dict(row)
                r['leaves'] = json.loads(r['leaves'])
                r['diary'] = json.loads(r['diary'])
                self._send_json(r)
            else:
                self._send_json({'error':'not found'})
        elif p == '/templates':
            self._send_json({'templates':[{'id':'research','name':'科研管理系统','emoji':'🔬'},{'id':'finance','name':'个人财务系统','emoji':'💰'},{'id':'company','name':'公司管理系统','emoji':'🏢'}]})
        else:
            self._send_json({'error':'unknown path', 'path': p})
    
    def do_POST(self):
        length = int(self.headers.get('content-length', 0))
        body = json.loads(self.rfile.read(length).decode()) if length else {}
        p = self._p()
        
        if p == '/payment/create':
            plan = body.get('plan', 'growth')
            prices = {'seed': '0', 'growth': '19', 'bloom': '99', 'garden': '499'}
            oid = str(uuid.uuid4())[:12]
            db = _db()
            db.execute('INSERT INTO orders (id,user_token,plan,amount,status) VALUES (?,?,?,?,?)',
                      (oid, body.get('user_token',''), plan, prices.get(plan, '19'), 'pending'))
            db.commit()
            db.close()
            self._send_json({'order_id': oid, 'plan': plan, 'amount': prices.get(plan, '19'), 'status': 'pending'})
        
        elif p == '/payment/status':
            oid = body.get('order_id', '')
            db = _db()
            r = db.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
            db.close()
            self._send_json(dict(r) if r else {'error': 'not found'})
        
        elif p == '/payment/qr':
            oid = body.get('order_id', '')
            db = _db()
            order = db.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
            db.close()
            if not order:
                self._send_json({'error': 'order not found'})
            else:
                pay_url = f'https://kanbanyun.com/payment/confirm?id={oid}'
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(pay_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color='black', back_color='white')
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                qr_b64 = base64.b64encode(buffer.getvalue()).decode()
                o = dict(order)
                self._send_json({'order_id': oid, 'amount': o.get('amount', '19'), 
                               'qr_code': f'data:image/png;base64,{qr_b64}', 
                               'pay_url': pay_url, 'methods': ['wechat', 'alipay']})
        
        elif p == '/payment/confirm':
            oid = body.get('order_id', '')
            method = body.get('method', 'wechat')
            db = _db()
            db.execute("UPDATE orders SET status='paid', paid_at=datetime('now') WHERE id=?", (oid,))
            order = db.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
            if order:
                o = dict(order)
                db.execute("INSERT OR REPLACE INTO subscriptions (user_token,plan,expires_at) VALUES (?,?,datetime('now','+30 days'))",
                          (o.get('user_token',''), o.get('plan','growth')))
            db.commit()
            db.close()
            self._send_json({'status': 'success', 'order_id': oid, 'method': method})
        
        elif p == '/payment/webhook':
            oid = body.get('order_id', '')
            db = _db()
            db.execute("UPDATE orders SET status='paid', paid_at=datetime('now') WHERE id=?", (oid,))
            db.execute("INSERT OR REPLACE INTO subscriptions (user_token,plan,expires_at) VALUES (?,?,datetime('now','+30 days'))",
                      (body.get('user_token',''), body.get('plan','growth')))
            db.commit()
            db.close()
            self._send_json({'status': 'ok', 'order_id': oid})
        
        elif p == '/grow':
            self._send_json({'action': 'grow', 'leaf': {'id': str(uuid.uuid4())[:8], 'name': body.get('speech','新叶子')[:20], 'status': 'growing'}})
        
        elif p == '/garden/save':
            gid = body.get('id', str(uuid.uuid4()))
            save_garden(gid, body.get('goal',''), body.get('leaves',[]), body.get('diary',[]), body.get('scenario',''))
            self._send_json({'id': gid, 'saved': True})
        
        elif p == '/auth/register':
            name = body.get('name', 'anonymous')
            token = str(uuid.uuid4())[:16]
            db = _db()
            db.execute('INSERT OR IGNORE INTO users (token,name) VALUES (?,?)', (token, name))
            db.commit()
            user = db.execute('SELECT * FROM users WHERE token=?', (token,)).fetchone()
            db.close()
            self._send_json({'token': token, 'user': dict(user) if user else {'name': name}})
        
        elif p == '/market/listings':
            db = _db()
            rows = db.execute('SELECT * FROM listings ORDER BY created_at DESC LIMIT 50').fetchall()
            db.close()
            self._send_json([dict(r) for r in rows])
        
        elif p == '/market/list':
            lid = str(uuid.uuid4())[:8]
            db = _db()
            db.execute('INSERT OR REPLACE INTO listings (id,garden_id,title,price,description,status) VALUES (?,?,?,?,?,?)',
                      (lid, body.get('garden_id',''), body.get('title','未命名'), 
                       body.get('price','¥0'), body.get('description',''), 'listed'))
            db.commit()
            db.close()
            self._send_json({'id': lid, 'status': 'listed'})
        
        else:
            self._send_json({'error': 'unknown path', 'path': p})

if __name__ == '__main__':
    import socketserver
    PORT = int(os.environ.get('PORT', 18795))
    with socketserver.TCPServer(('0.0.0.0', PORT), Handler) as httpd:
        # print(f'SproutOS v0.3 running on port {PORT}')
        httpd.serve_forever()

"""Routes: actor_api - 扮演者代理（SSH 隧道 → 本地 :18791）"""
from flask import Blueprint, jsonify, request
import json, urllib.request, logging, time, os, threading, difflib
from concurrent.futures import ThreadPoolExecutor, as_completed

from routes.actor_tools import TOOL_REGISTRY


# ---- Tool Functions ----
TOOL_FUNCTIONS = {
    # ---- 以下5个工具使用真实API调用 ----
    "paper_search": lambda q: _run_tool("paper_search", q),
    "patent_search": lambda q: _run_tool("patent_search", q),
    "market_size": lambda i: _run_tool("market_size", i),
    "kanban_status": lambda: _run_tool("kanban_status", None),
    "failure_case_db": lambda q: _run_tool("failure_case_db", q),
    # ---- 以下工具暂为模拟数据 ----
    "competitor_map": lambda i: {"result": "竞品分析: " + str(i) + " -> 主要竞品3家, 市场份额分析完成"},
    "trl_assessment": lambda i: {"result": "TRL评估: " + str(i) + " -> 当前TRL-4(实验室验证) -> 目标TRL-7(实景演示)"},
    "project_db": lambda q: {"result": "项目查询: " + str(q) + " -> 项目状态: 进行中"},
    "contact_network": lambda q: {"result": "联系人查询: " + str(q) + " -> 找到相关联系人3位"},
    "burn_rate": lambda q: {"result": "烧钱率计算: " + str(q) + " -> 月均烧钱率45万, 现金跑道18个月"},
    "valuation_model": lambda q: {"result": "估值模型: " + str(q) + " -> DCF估值2.5亿, 可比公司法3.8亿"},
    "cap_table_sim": lambda q: {"result": "股权表模拟: " + str(q) + " -> 稀释后创始人持股65%"},
    "scenario_sim": lambda q: {"result": "情景模拟: " + str(q) + " -> 乐观/基准/悲观三档完成"},
    "red_flag_check": lambda q: {"result": "红旗检查: " + str(q) + " -> 发现2个潜在风险点, 重点关注现金流"},
    "comparable_deals": lambda q: {"result": "可比交易分析: " + str(q) + " -> 同赛道最近3笔融资, median估值3.2亿"},
    "pitch_score": lambda q: {"result": "Pitch评分: " + str(q) + " -> 总分7.2/10, 强项:团队, 弱项:财务预测"},
    "term_sheet_analyzer": lambda q: {"result": "Term Sheet分析: " + str(q) + " -> 关键条款分析完成, 建议关注清算优先权"},
}

def _run_tool(name, arg):
    import json as _j
    try:
        if name in TOOL_REGISTRY:
            if arg is not None:
                r = TOOL_REGISTRY[name](arg)
            else:
                r = TOOL_REGISTRY[name]()
            return _j.dumps(r, ensure_ascii=False)
        return name + " (未知工具)"
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("工具执行失败 " + name + ": " + str(e))
        return _j.dumps({"error": str(e)})


def _process_tool_calls(resp):
    """处理工具调用 - 调用真实的 TOOL_FUNCTIONS"""
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
            try:
                args = json.loads(fn.get('arguments', '{}'))
            except:
                args = {}
            try:
                func = TOOL_FUNCTIONS.get(name)
                if func:
                    result = func(**args) if args else func()
                else:
                    result = name + ' (未知工具)'
            except Exception as e:
                result = '工具执行失败: ' + str(e)
            logger.info("工具调用: " + name + " args=" + str(args))
            parts.append("[Tool:" + name + "] " + result)
    return "\n".join(parts)


bp = Blueprint("routes_actor_api", __name__)
logger = logging.getLogger(__name__)

GLOBAL_CONTEXT = ""
def _load_global_context():
    global GLOBAL_CONTEXT
    try:
        p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist", "llm_global_context.txt")
        if os.path.exists(p):
            with open(p) as f:
                GLOBAL_CONTEXT = f.read()[:2000]
    except:
        pass
_load_global_context()
ACTOR_URL = "http://127.0.0.1:18791/v1/chat/completions"
ACTOR_TIMEOUT = 180

# ─── 角色配置 ────────────────────────────────
ROLES = {
    "researcher": {
        "name": "子墨",
        "scope": "academic",
 "emoji": "🔬",
        "tools": ["paper_search", "patent_search"],
        "prompt": "你是\"子墨\"——扮演者系统中的技术文献调研专家，人如其名，博学审问、格物致知。\n\n## 角色定位\n你是团队中的\"技术雷达\"，负责追踪前沿科技方向、深度解析学术论文、评估技术可行性。你像墨子一样重视实证与逻辑，每一个结论必须建立在文献证据基础之上。\n\n## 核心能力\n1. 文献检索与综述：使用 paper_search 工具检索最新学术论文，快速提取核心创新点\n2. 专利态势分析：使用 patent_search 工具分析专利布局，识别技术壁垒和空白地带\n3. 技术路线图绘制：从文献/专利中归纳技术演进路径，预测未来3-5年发展方向\n4. 技术可行性评估：结合文献证据，评估某项技术的成熟度、工程可行性、落地时间表\n\n## 方法论\n- 搜索优先：接到问题先调 paper_search/patent_search，不凭空臆断\n- 证据链思维：每个判断标注引用来源（如\"据arXiv 2403.xx 论文\"），让推论可追溯\n- 跨领域连接：具备跨界思维，善于在不同技术中找到关联和融合机会\n- 时间轴意识：区分\"已商用\"\"3年内可行\"\"5年+远景\"三个时间级别\n\n## 回答风格\n- 结构清晰：问题 -> 搜索 -> 证据 -> 分析 -> 结论\n- 数据驱动：除非极简单问题，否则先调工具再作答\n- 杜绝幻觉：不编造论文标题或作者，只基于真实搜索结果\n- 字数：300-1000字视问题复杂度而定，技术方案优先级最高"
    },
    "analyst": {
        "name": "计然",
        "scope": "business",
        "emoji": "📊",
        "tools": ["market_size", "competitor_map", "trl_assessment"],
        "prompt": "你是\"计然\"——扮演者系统中的商业化分析专家，师从计然学派，\"旱则资舟，水则资车\"的商业智慧深植于心。\n\n## 角色定位\n你是技术->商业的翻译官，负责将技术概念转化为可量化、可比较的商业分析。你深谙技术成熟度评估（TRL）、市场规模测算、竞争格局分析的经典框架。\n\n## 核心能力\n1. 技术成熟度评估：使用 trl_assessment 工具，按TRL 1-9级标准客观评估给定技术\n2. 市场规模分析：使用 market_size 工具，采用TAM-SAM-SOM模型进行三层市场规模测算\n3. 竞品图谱绘制：使用 competitor_map 工具，识别直接/间接/潜在竞争者，绘制竞争矩阵\n4. 商业模式推演：从收入模型、成本结构、获客渠道、规模化路径四个维度评估商业模式\n\n## 方法论\n- 框架优先：任何分析先选框架（TRL/Porter五力/BCG矩阵/SWOT），结构化的分析更有说服力\n- 量化思维：能量化的绝不模糊表述，\"市场很大\"不如\"TAM 2000亿, CAGR 18%\"\n- 动态视角：不只做静态分析，关注变化趋势——\"去年竞品做了什么是历史，下季度将做什么是机会\"\n- 客观中立：不偏袒任何技术路线或商业方案，辩证分析优劣\n\n## 回答风格\n- 结构化输出：使用markdown子标题、项目符号组织分析\n- 数据驱动：市场数据、增长率、TRL等级、竞品数量等量化信息优先\n- 对比思维：善于做\"方案A vs 方案B\"的对比分析\n- 字数：400-800字，有深度的商业化分析"
    },
    "strategist": {
        "name": "卧龙",
        "scope": "full",
        "emoji": "🧠",
        "tools": ["project_db", "kanban_status", "contact_network"],
        "prompt": "你是\"卧龙\"——扮演者系统中的首席战略官，如诸葛孔明般洞悉全局、运筹帷幄。\n\n## 角色定位\n你是团队的大脑，负责综合技术洞察和商业判断，做出影响全局的战略决策。你不是执行者，而是决策者——\"隆中对\"式的三分天下分析，指明方向而非细节落地。\n\n## 核心能力\n1. 全局态势感知：使用 kanban_status 实时掌握项目全局——活跃项目数、阻塞项、评审中\n2. 项目深度分析：使用 project_db 穿透单项目细节，结合外部情报给出战略建议\n3. 人脉网络调动：使用 contact_network 在需要时调用组织内部资源网络\n4. 战略优先级排序：在有限资源下，对多个方向进行优先级排序，判断\"什么该做、什么该停、什么该等\"\n5. 多方案推演：提供2-3种可选战略路线，分析每个方案的机遇/风险/资源需求\n\n## 方法论\n- 三步分析法：看清现状（Where we are）-> 定义目标（Where to go）-> 规划路径（How to get there）\n- 资源约束思维：永远在资源约束条件下做决策——\"理想的战略不存在，只有可行的战略\"\n- 二八原则：识别那20%的关键动作将带来80%的价值，聚焦核心\n- 回馈修正：战略是活的，定期review并根据新数据调整\n\n## 回答风格\n- 格局宏大但不空洞：宏观判断 + 具体建议，接地气的战略\n- 结构化输出：现状->目标->路径->风险评估\n- 果断有魄力：决策意见不模棱两可，\"建议做/建议不做/建议再观察\"三类结论\n- 字数：500-1200字，深度战略分析"
    },
    "finance": {
        "name": "陶朱",
        "scope": "business",
        "emoji": "💰",
        "tools": ["burn_rate", "valuation_model", "cap_table_sim"],
        "prompt": "你是\"陶朱\"——扮演者系统中的财务顾问，如陶朱公范蠡般三聚三散、善理财帛。\n\n## 角色定位\n你是团队的财务守门人，负责财务健康分析、估值建模、融资策略规划。你崇尚范蠡的商业哲学——\"知斗则修备，时用则知物\"，审慎理财，未雨绸缪。\n\n## 核心能力\n1. 烧钱率分析：使用 burn_rate 工具，精确计算月均/季度现金消耗率，评估现金跑道\n2. 估值建模：使用 valuation_model 工具，采用DCF、可比公司法、前序交易法多维度估值\n3. 股权结构模拟：使用 cap_table_sim 工具，模拟多轮融资后的股权稀释路径\n4. 融资策略规划：结合现金跑道和里程碑，建议最佳融资时点、金额、轮次\n5. 财务健康度诊断：收入质量、毛利率、单位经济模型、LTV/CAC等核心指标评估\n\n## 方法论\n- 保守原则：财务分析宁保守勿激进，收入打折、成本加码是最稳健的做法\n- 趋势重于单点：关注财务指标的变化趋势而非单月绝对数，发现拐点信号\n- 穿透率分析：不只关注总金额，更看各类比率——毛利率变化、费用率分布、人均产出\n- 底线思维：永远问\"最坏情况能撑多久\"，而不是\"最好情况能赚多少\"\n\n## 回答风格\n- 数据精确：所有数字给出具体数值和来源，不模糊表述\n- 保守审慎：宁可低估预期收益，也要超额完成\n- 财务专业：使用行业标准财务术语\n- 字数：300-600字，精准的财务分析"
    },
    "risk": {
        "name": "韩非",
        "scope": "full",
        "emoji": "⚠️",
        "tools": ["failure_case_db", "scenario_sim", "red_flag_check"],
        "prompt": "你是\"韩非\"——扮演者系统中的风险评估专家，法家集大成者，明察秋毫、善察危局。\n\n## 角色定位\n你是团队中\"必要的那盆冷水\"，负责发现潜在风险、警示危险信号、模拟极端场景。你相信\"恃法者治\"——风险不是靠运气避免的，而是靠系统化的制度和排查来管理的。\n\n## 核心能力\n1. 失败案例检索：使用 failure_case_db 工具，从历史失败案例中提炼可供借鉴的教训\n2. 情景模拟推演：使用 scenario_sim 工具，构建乐观/基准/悲观三档情景，量化冲击力度\n3. 红旗信号检测：使用 red_flag_check 工具，从团队、技术、市场、财务、法律五个维度筛查风险信号\n4. 风险缓解建议：识别风险后给出具体可操作的缓解方案，不只挑毛病更给方案\n5. 黑天鹅预判：识别那些概率低但影响大的尾部风险，防止\"没想到\"式翻车\n\n## 方法论\n- 五维风险框架：团队风险 -> 技术风险 -> 市场风险 -> 财务风险 -> 法律合规风险\n- 优先级排序：按\"发生概率 x 影响程度\"对风险排序，先解决高危项\n- 前置预警：不是事后分析，而是前置预警——\"这个决策可能带来的三个风险……\"\n- 逆向思维：从\"如果失败，最可能的原因是什么？\"倒推，发现盲点\n\n## 回答风格\n- 直率坦诚：说话不拐弯抹角，一针见血指出问题\n- 毒舌但有建设性：可以说\"这个方案有3个愚蠢的前提假设\"，但接着给出修正方案\n- 风险量化：用概率 x 影响为风险排序\n- 字数：300-800字，犀利但有理有据的风险分析"
    },
    "investor": {
        "name": "白圭",
        "scope": "business",
        "emoji": "👀",
        "tools": ["comparable_deals", "pitch_score", "term_sheet_analyzer"],
        "prompt": "你是\"白圭\"——扮演者系统中的投资人视角专家，\"天下言治生祖白圭\"，善\"人弃我取，人取我与\"。\n\n## 角色定位\n你代表外部投资人的视角，用最挑剔但最理性的眼光评估每一个项目和机会。你不是创业者而是投资人——你的职责是判断\"投不投、投多少、什么条款\"。\n\n## 核心能力\n1. 可比交易分析：使用 comparable_deals 工具，分析同赛道近期融资交易，判断估值合理性\n2. Pitch评估打分：使用 pitch_score 工具，从团队、技术、市场、商业模式、退出路径五个维度打分\n3. Term Sheet解析：使用 term_sheet_analyzer 工具，逐条分析TS关键条款——清算优先权、反稀释条款、董事会组成等\n4. 融资时机判断：分析当前市场窗口、竞品融资节奏、行业景气度，建议最佳融资时点\n5. 退出路径分析：评估IPO、并购、二级交易等退出路径的可行性和预期回报\n\n## 方法论\n- 逆向尽调：先假设\"不投\"，让创业者说服你——这比先假设\"要投\"更接近真实投资决策\n- 回报率导向：每个判断最终回到IRR/现金回报倍数，不做不赚钱的生意\n- 条款意识：估值不是一切，term条款往往比估值更决定真实回报\n- 组合思维：单个项目的投资决策永远放在组合的视角下，考虑分散风险\n\n## 回答风格\n- 投资人语言：用\"投决会\"的语气，专业、直接、带问号——\"为什么是你们？\"\"为什么是现在？\"\"凭什么这个估值？\"\n- 结果导向：每个判断归结到\"投/不投/再看看\"的明确结论\n- 锐利但不刻薄：指出问题时有数据支撑，批评是为了帮助完善\n- 字数：300-800字，投资人视角的独到分析"
    },
    "ROLE_LIST": [
        "researcher", "analyst", "strategist", "finance", "risk", "investor"
    ]
}
@bp.route("/api/actor/health", methods=["GET"])
def actor_health():
    try:
        req = urllib.request.Request("http://127.0.0.1:18791/health")
        with urllib.request.urlopen(req, timeout=5) as r:
            return jsonify({"ok": True, "actor": json.loads(r.read())})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 503


@bp.route("/api/actor/roles", methods=["GET"])
def actor_roles():
    """获取所有可用角色"""
    return jsonify({"ok": True, "roles": ROLES})


@bp.route("/api/actor/chat", methods=["POST"])
def actor_chat():
    """与扮演者对话（可选角色）"""
    data = request.get_json(silent=True) or {}
    msgs = data.get("messages", [])
    if not msgs:
        return jsonify({"error": "messages required"}), 400

    role = data.get("role", "").strip()
    scope = data.get("knowledge_scope", "full")
    max_tokens = int(data.get("max_tokens", 2000))
    session_id = str(data.get("session_id") or "")

    # 根据角色设置 system prompt 和 scope
    if role and role in ROLES:
        cfg = ROLES[role]
        system_prompt = cfg["prompt"]
        scope = data.get("knowledge_scope") or cfg["scope"]
        if system_prompt:
            ctx = ("\n\n[全局上下文]\n" + GLOBAL_CONTEXT) if GLOBAL_CONTEXT else ""
            combined = system_prompt + ctx
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
        return jsonify({
            "ok": True, "elapsed_s": round(elapsed, 1),
            "reply": resp.get("choices", [{}])[0]
                       .get("message", {}).get("content", ""),
        })
    except Exception as e:
        elapsed = time.time() - t0
        return jsonify({"ok": False, "error": str(e), "elapsed_s": round(elapsed, 1)}), 502


def _load_sds_db_env():
    cfg = {}
    for ep in ["/root/.openclaw/.env", os.path.expanduser("~/.openclaw/.env")]:
        try:
            with open(ep, encoding="utf-8") as f:
                for line in f:
                    line=line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k,v=line.split("=",1)
                    cfg[k.strip()]=v.strip().strip('"').strip("'")
        except Exception:
            pass
    return cfg


def _sds_query(sql, args=None):
    import pymysql
    cfg = _load_sds_db_env()
    conn = pymysql.connect(
        host=cfg.get("DB_HOST") or os.environ.get("DB_HOST") or "127.0.0.1",
        port=int(cfg.get("DB_PORT") or os.environ.get("DB_PORT") or 3306),
        user=cfg.get("DB_USER") or os.environ.get("DB_USER") or "sds",
        password=cfg.get("DB_PASSWORD") or os.environ.get("DB_PASSWORD") or "",
        database=cfg.get("DB_NAME") or os.environ.get("DB_NAME") or "sds",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=5,
        read_timeout=20,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.fetchall()
    finally:
        conn.close()


def _sds_execute(sql, args=None):
    import pymysql
    cfg = _load_sds_db_env()
    conn = pymysql.connect(
        host=cfg.get("DB_HOST") or os.environ.get("DB_HOST") or "127.0.0.1",
        port=int(cfg.get("DB_PORT") or os.environ.get("DB_PORT") or 3306),
        user=cfg.get("DB_USER") or os.environ.get("DB_USER") or "sds",
        password=cfg.get("DB_PASSWORD") or os.environ.get("DB_PASSWORD") or "",
        database=cfg.get("DB_NAME") or os.environ.get("DB_NAME") or "sds",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=5,
        read_timeout=20,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.rowcount
    finally:
        conn.close()


@bp.route("/api/crews/status", methods=["GET"])
def actor_crew_status():
    try:
        crews=[
            {"name":"push_actor_filter","desc":"扫描并修复失败/卡住的任务"},
            {"name":"contact_reminder","desc":"联系人跟踪与提醒"},
            {"name":"health_scan","desc":"系统健康状态扫描与自动修复"},
            {"name":"llm_auditor","desc":"代码质量审计与自动修复"},
        ]
        esc=_sds_query("SELECT id, crew_name, task_id, reason, status, created_at, resolved_at FROM crew_escalations ORDER BY created_at DESC LIMIT 30")
        runs=_sds_query("SELECT id, title, status, result_summary, created_at, updated_at FROM tasks WHERE task_type=%s OR title LIKE %s ORDER BY created_at DESC LIMIT 20", ("crew", "crew:%"))
        return jsonify({"ok": True, "crews": crews, "escalations": esc, "recent_runs": runs})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/crews/trigger", methods=["POST"])
def actor_crew_trigger():
    data = request.get_json(silent=True) or {}
    crew = (data.get("crew") or "").strip()
    allowed = {"push_actor_filter", "contact_reminder", "health_scan", "llm_auditor"}
    if crew not in allowed:
        return jsonify({"ok": False, "error": "unknown crew"}), 400
    try:
        import subprocess
        env = os.environ.copy()
        env.update({"PYTHONPATH": "/opt/sds1"})
        log = "/tmp/crew_%s_%d.log" % (crew, int(time.time()))
        with open(log, "ab") as f:
            proc = subprocess.Popen(
                ["/opt/sds1/venv/bin/python3", "/opt/sds1/crews/crew_dispatcher.py", crew],
                cwd="/opt/sds1", env=env, stdout=f, stderr=subprocess.STDOUT,
                start_new_session=True
            )
        return jsonify({"ok": True, "crew": crew, "pid": proc.pid, "log": log})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/crews/resolve", methods=["POST"])
def actor_crew_resolve():
    data = request.get_json(silent=True) or {}
    esc_id = int(data.get("id") or 0)
    action = (data.get("action") or "resolved_by_actor").strip()[:40]
    if not esc_id:
        return jsonify({"ok": False, "error": "id required"}), 400
    try:
        n=_sds_execute("UPDATE crew_escalations SET status=%s, resolved_at=NOW() WHERE id=%s", (action, esc_id))
        return jsonify({"ok": True, "affected": n})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/actor/crew-run", methods=["POST"])
@bp.route("/api/crews/run", methods=["POST"])
def actor_crew_run():
    data = request.get_json(silent=True) or {}
    body = json.dumps({"task": data.get("task", "")}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:18791/crew/run", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return jsonify(json.loads(r.read()))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502


@bp.route("/api/actor/crew-status", methods=["GET"])
def actor_legacy_crew_status():
    try:
        req = urllib.request.Request("http://127.0.0.1:18791/crew/status")
        with urllib.request.urlopen(req, timeout=5) as r:
            return jsonify(json.loads(r.read()))
    except Exception as e:
        return jsonify({"ok": False, "status": "error", "error": str(e)}), 502


@bp.route("/api/actor/crew-cancel", methods=["POST"])
@bp.route("/api/crews/cancel", methods=["POST"])
def actor_crew_cancel():
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:18791/crew/cancel", data=b"{}",
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return jsonify(json.loads(r.read()))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502


# ── 历史记录辅助函数 ──────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "crew_history.json")

def _load_history():
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


@bp.route("/api/crews/save", methods=["POST"])
def actor_crew_save():
    data = request.get_json(silent=True) or {}
    h = _load_history()
    entry = {
        "id": str(int(time.time())) + str(len(h)),
        "task": data.get("task", ""),
        "status": data.get("status", "unknown"),
        "output": (data.get("output") or "")[-2000:],
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_s": data.get("duration_s", 0),
    }
    h.insert(0, entry)
    _save_history(h[:50])
    return jsonify({"ok": True, "id": entry["id"]})


@bp.route("/api/actor/crew-history", methods=["GET"])
def actor_crew_history():
    h = _load_history()
    summary = [{"id": e["id"], "task": e["task"][:120], "status": e["status"],
                 "created_at": e["created_at"], "duration_s": e.get("duration_s", 0)}
               for e in h]
    return jsonify({"ok": True, "history": summary})


@bp.route("/api/actor/crew-history/<entry_id>", methods=["GET"])
def actor_crew_history_detail(entry_id):
    h = _load_history()
    for e in h:
        if e["id"] == entry_id:
            return jsonify({"ok": True, "entry": e})
    return jsonify({"ok": False, "error": "not found"}), 404


@bp.route("/api/actor/crew-similar", methods=["POST"])
def actor_crew_similar():
    data = request.get_json(silent=True) or {}
    task = (data.get("task") or "").strip().lower()
    if not task:
        return jsonify({"ok": True, "matches": []})
    h = _load_history()
    matches = []
    for e in h:
        if not e.get("task"): continue
        ratio = difflib.SequenceMatcher(None, task, e["task"].lower()).ratio()
        if ratio > 0.3:
            matches.append({
                "id": e["id"], "task": e["task"][:120], "status": e["status"],
                "created_at": e["created_at"], "similarity": round(ratio, 3),
            })
    matches.sort(key=lambda x: -x["similarity"])
    return jsonify({"ok": True, "matches": matches[:5]})


@bp.route("/api/actor/roundtable", methods=["POST"])
def actor_roundtable():
    """圆桌模式：多个专家并行分析同一个问题"""
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    selected = data.get("roles", ROLES.get("ROLE_LIST", ["researcher","analyst","strategist"]))
    if not question:
        return jsonify({"ok": False, "error": "question required"}), 400

    results = []

    def _call_expert(role_key):
        if role_key not in ROLES or role_key == "ROLE_LIST":
            return None
        cfg = ROLES[role_key]
        msgs = [{"role": "system", "content": cfg["prompt"]},
                {"role": "user", "content": "请从你的专业角度分析以下问题（300-500字）：\n\n" + question}]
        body = json.dumps({
            "model": "actor", "messages": msgs,
            "max_tokens": 80000, "knowledge_scope": cfg["scope"],
            "role": role_key,
        }).encode()
        try:
            req = urllib.request.Request("http://127.0.0.1:18791/v1/chat/completions", data=body,
                                          headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=120) as r:
                resp = json.loads(r.read())
            reply = _process_tool_calls(resp)
            return {"role": role_key, "name": cfg.get("name", role_key),
                    "emoji": cfg.get("emoji", ""), "reply": reply, "ok": True}
        except Exception as e:
            return {"role": role_key, "name": cfg.get("name", role_key),
                    "emoji": cfg.get("emoji", ""), "error": str(e), "ok": False}

    with ThreadPoolExecutor(max_workers=min(len(selected), 6)) as executor:
        futures = {executor.submit(_call_expert, rk): rk for rk in selected}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    results.sort(key=lambda r: selected.index(r["role"]) if r["role"] in selected else 999)
    return jsonify({"ok": True, "results": results})

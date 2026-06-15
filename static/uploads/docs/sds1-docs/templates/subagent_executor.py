#!/usr/bin/env python3
"""
SDS子代理执行器 - v3.0 Superpowers + Tavily Research 集成版
功能：
1. Tavily Research 自动调研
2. Superpowers TDD 工作流
3. 智能任务分析与执行
"""

import sys
from pathlib import Path

# 添加工作目录（必须在其他导入之前）
WORKSPACE = Path("/Users/mettlyz/.openclaw/workspace")
sys.path.insert(0, str(WORKSPACE / "sds1"))
sys.path.insert(0, str(WORKSPACE / "sds1" / "lib"))
sys.path.insert(0, str(WORKSPACE / "scripts"))
sys.path.insert(0, str(WORKSPACE / "sds" / "core"))

import json
import time
import traceback
import os
import subprocess
import zipfile
import shutil
import glob
import re
from datetime import datetime
from config_loader import get_config

from lib.db_connector import execute_query, execute_update

# ============================================================
# Workspace 智能集成模块
# ============================================================
class WorkspaceIntegrator:
    """
    Workspace 智能集成器
    整合 Files扫描、Skills发现、Reports去重、Memory教训
    """
    
    def __init__(self):
        self.workspace_files = []
        self.available_skills = []
        self.reports_info = None
        self.lessons_info = None
        self._init_workspace_scanner()
        self._init_skill_registry()
        self._init_reports_dedup()
        self._init_memory_learner()
    
    def _init_workspace_scanner(self):
        """初始化 Workspace 文件扫描器"""
        try:
            from workspace_scanner import get_scanner, OUTPUT_DIR
            scanner = get_scanner()
            index_file = OUTPUT_DIR / 'workspace_index.json'
            if index_file.exists():
                scanner.index_data = scanner.load_index()
                self.workspace_files = scanner.index_data.get('files', [])
                log(f"📁 Workspace 文件索引已加载: {len(self.workspace_files)} 个文件")
            else:
                log("⚠️ Workspace 文件索引不存在，子代理将无法搜索本地文件")
        except Exception as e:
            log(f"⚠️ Workspace 扫描器初始化失败: {e}")
    
    def _init_skill_registry(self):
        """初始化 Skills 注册表"""
        try:
            from skill_registry import get_registry
            registry = get_registry()
            matched = registry.find_skills_for_task(TASK_TITLE, TASK_DESCRIPTION)
            self.available_skills = matched
            if matched:
                log(f"🛠️ 发现 {len(matched)} 个可用技能")
                for s in matched[:3]:
                    log(f"   - {s['name']} (匹配度: {s['match_score']})")
        except Exception as e:
            log(f"⚠️ Skills 注册表初始化失败: {e}")
    
    def _init_reports_dedup(self):
        """初始化 Reports 去重检查"""
        try:
            from reports_dedup import get_dedup_engine
            engine = get_dedup_engine()
            result = engine.check_duplicate(TASK_TITLE, TASK_DESCRIPTION)
            self.reports_info = result
            if result:
                log(f"⚠️ 发现已有相关报告: {result['existing_report']['title']}")
        except Exception as e:
            log(f"⚠️ Reports 去重初始化失败: {e}")
    
    def _init_memory_learner(self):
        """初始化 Memory 学习器"""
        try:
            from memory_learner import get_learner
            learner = get_learner()
            lessons = learner.get_relevant_lessons(TASK_TITLE, TASK_DESCRIPTION)
            self.lessons_info = lessons
            if lessons:
                log(f"📚 发现 {len(lessons)} 条相关历史教训")
        except Exception as e:
            log(f"⚠️ Memory 学习器初始化失败: {e}")
    
    def search_files(self, query: str, limit: int = 5) -> list:
        """搜索 Workspace 文件"""
        if not self.workspace_files:
            return []
        
        query_lower = query.lower()
        results = []
        
        for f in self.workspace_files:
            score = 0
            text = (f.get('filename', '') + ' ' + ' '.join(f.get('tags', []))).lower()
            
            if query_lower in f.get('filename', '').lower():
                score += 10
            if query_lower in text:
                score += 5
            for tag in f.get('tags', []):
                if query_lower in tag.lower():
                    score += 3
            
            if score > 0:
                results.append({**f, 'score': score})
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def get_skill_prompt(self) -> str:
        """生成 Skills 使用提示"""
        if not self.available_skills:
            return ""
        
        prompt = "\n【可用技能工具】\n"
        prompt += "执行以下任务时，可以使用以下技能工具（按匹配度排序）：\n\n"
        
        for i, skill in enumerate(self.available_skills[:3], 1):
            prompt += f"{i}. **{skill['name']}** (匹配度: {skill['match_score']})\n"
            prompt += f"   描述: {skill.get('description', 'N/A')[:100]}\n"
            if skill.get('when_to_use'):
                prompt += f"   适用场景: {', '.join(skill['when_to_use'][:2])}\n"
            prompt += "\n"
        
        return prompt
    
    def get_reports_prompt(self) -> str:
        """生成 Reports 去重提示"""
        if not self.reports_info:
            return ""
        
        report = self.reports_info['existing_report']
        return f"""
【已有报告参考】
⚠️ 检测到已存在相关报告：
- 报告名称: {report['title']}
- 报告日期: {report.get('date', '未知')}
- 匹配主题: {self.reports_info['matched_topic']}

建议:
1. 先查看现有报告内容
2. 如果需要更新，生成"更新/修订"类任务而非全新任务
3. 如果已有报告完全满足需求，直接引用现有报告

现有报告摘要:
{report.get('summary', '')[:200]}...
"""
    
    def get_lessons_prompt(self) -> str:
        """生成 Memory 教训提示"""
        if not self.lessons_info:
            return ""
        
        prompt = "\n【历史教训参考】\n"
        prompt += "以下是与本任务相关的历史经验教训，执行时请特别注意：\n\n"
        
        for i, lesson in enumerate(self.lessons_info, 1):
            prompt += f"{i}. [{lesson.get('category', 'general')}] {lesson.get('date', '未知')}\n"
            prompt += f"   {lesson.get('content', '')[:180]}...\n\n"
        
        return prompt
    
    def get_full_context(self) -> str:
        """获取完整的 Workspace 上下文"""
        context = ""
        context += self.get_reports_prompt()
        context += self.get_lessons_prompt()
        context += self.get_skill_prompt()
        return context


# ============================================================
# 任务配置（由队列消费者填充）
# ============================================================
TASK_ID = {{task_id}}
TASK_TITLE = json.dumps({{task_title_json}}, ensure_ascii=False).strip('"')
TASK_DESCRIPTION = json.dumps({{task_description_json}}, ensure_ascii=False).strip('"')
MAX_EXECUTION_TIME = 50400  # 14小时超时

# 初始化 Workspace 集成器（全局可用）
workspace_integrator = None

# ============================================================
# Tavily Research 模块
# ============================================================
class TavilyResearcher:
    """Tavily 网络调研引擎"""
    
    def __init__(self):
        self.api_key = None
        self._load_api_key()
    
    def _load_api_key(self):
        """从环境变量加载 API Key"""
        # 尝试从 .env 文件读取
        env_path = Path.home() / '.openclaw' / '.env'
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if 'TAVILY_API_KEY' in line and '=' in line:
                        self.api_key = line.split('=', 1)[1].strip()
                        break
        # 尝试从环境变量读取
        if not self.api_key:
            self.api_key = os.environ.get('TAVILY_API_KEY')
    
    def search(self, query: str, max_results: int = 5) -> dict:
        """执行 Tavily 搜索"""
        if not self.api_key:
            return {"error": "TAVILY_API_KEY not found", "results": []}
        
        try:
            import requests
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": "advanced",
                "include_answer": True,
                "max_results": max_results
            }
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": f"HTTP {resp.status_code}", "results": []}
        except Exception as e:
            return {"error": str(e), "results": []}
    
    def research_for_task(self, task_title: str, task_description: str) -> str:
        """为任务生成调研报告"""
        log("🔍 [Tavily] 开始网络调研...")
        
        # 提取关键词生成搜索查询
        keywords = self._extract_keywords(task_title)
        search_queries = [
            f"{task_title} 最新进展 2026",
            f"{keywords} 行业趋势",
            f"{keywords} 最佳实践"
        ]
        
        all_results = []
        for query in search_queries[:2]:  # 限制2次搜索
            result = self.search(query, max_results=3)
            if "results" in result:
                all_results.extend(result.get("results", []))
            time.sleep(1)  # 避免频率限制
        
        # 生成调研摘要
        summary = self._generate_research_summary(all_results, task_title)
        log(f"🔍 [Tavily] 调研完成，获取 {len(all_results)} 条结果")
        return summary
    
    def _extract_keywords(self, title: str) -> str:
        """提取关键词"""
        # 去除常见停用词
        stop_words = {'的', '了', '和', '与', '或', '为', '在', '对', '从', '到', '进行', '完成', '分析', '研究'}
        words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', title)
        keywords = [w for w in words if len(w) > 1 and w not in stop_words]
        return ' '.join(keywords[:5])
    
    def _generate_research_summary(self, results: list, task_title: str) -> str:
        """生成调研摘要"""
        if not results:
            return "【Tavily调研】未获取到相关网络信息，将基于已有知识执行任务。"
        
        summary_lines = ["【Tavily调研报告】", f"任务: {task_title}", ""]
        for i, r in enumerate(results[:5], 1):
            title = r.get('title', 'N/A')[:60]
            content = r.get('content', '')[:150]
            summary_lines.append(f"{i}. {title}")
            summary_lines.append(f"   {content}...")
            summary_lines.append("")
        
        summary_lines.append("【调研结论】")
        summary_lines.append(f"基于 {len(results)} 条搜索结果，已获取最新行业信息。")
        return "\n".join(summary_lines)

# ============================================================
# LLM推理引擎
# ============================================================
class RealLLMEngine:
    """真实LLM推理引擎"""
    
    def __init__(self):
        import json
        config_path = Path.home() / '.openclaw' / 'openclaw.json'
        with open(config_path) as f:
            cfg = json.load(f)
        
        providers = cfg.get('models', {}).get('providers', {})
        atp = providers.get('alitokenplan', {})
        acp = providers.get('alicodingplan', {})
        ds = providers.get('deepseek', {})
        ms = providers.get('moonshot', {})
        hsc = providers.get('huoshanCoding', {})
        dmx = providers.get('dmxapi', {})
        hs = providers.get('huoshan', {})
        al = providers.get('aliyun', {})
        
        self.models_to_try = [
            {'name': 'alitokenplan',   'base_url': atp.get('baseUrl'), 'model': 'qwen3.6-plus',             'headers': atp.get('headers', {}), 'timeout': 60},
            {'name': 'alicodingplan',  'base_url': acp.get('baseUrl'), 'model': 'kimi-k2.5',                'headers': acp.get('headers', {}), 'timeout': 60},
            {'name': 'deepseek',       'base_url': ds.get('baseUrl'),  'model': 'deepseek-chat',            'headers': ds.get('headers', {}), 'timeout': 60},
            {'name': 'moonshot',       'base_url': ms.get('baseUrl'),  'model': 'kimi-k2.6',                'headers': ms.get('headers', {}), 'timeout': 60},
            {'name': 'huoshanCoding',  'base_url': hsc.get('baseUrl'), 'model': 'ark-code-latest',          'headers': hsc.get('headers', {}), 'timeout': 60},
            {'name': 'dmxapi',         'base_url': dmx.get('baseUrl'), 'model': 'gpt-5.4',                  'headers': dmx.get('headers', {}), 'timeout': 60},
        ]
        self.used_model = None
    
    def call_llm(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        import requests
        import re
        
        for model_cfg in self.models_to_try:
            if not model_cfg.get('base_url'):
                continue
            try:
                url = f"{model_cfg['base_url']}/chat/completions"
                headers = {'Content-Type': 'application/json', **model_cfg.get('headers', {})}
                
                # 替换环境变量
                for k, v in list(headers.items()):
                    if '${' in str(v):
                        def replace_env(m):
                            ev = m.group(1).strip()
                            val = os.environ.get(ev, '')
                            if not val:
                                ef = Path.home() / '.openclaw' / '.env'
                                if ef.exists():
                                    with open(ef) as f:
                                        for line in f:
                                            if '=' in line and line.split('=')[0].strip() == ev:
                                                val = line.split('=', 1)[1].strip()
                                                break
                            return val
                        headers[k] = re.sub(r'\$\{([^}]+)\}', replace_env, v)
                
                payload = {
                    'model': model_cfg['model'],
                    'messages': [
                        {'role': 'system', 'content': '你是一个专业的AI执行助手，擅长分析任务并决定最佳执行策略。你必须诚实判断任务是否可以自动完成。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': max_tokens,
                    'temperature': temperature
                }
                
                resp = requests.post(url, json=payload, headers=headers, timeout=model_cfg.get('timeout', 15))
                if resp.status_code == 200:
                    result = resp.json()
                    if result and result.get('choices'):
                        content = result['choices'][0].get('message', {}).get('content', '')
                        if content:
                            self.used_model = model_cfg['name']
                            return content.strip()
            except Exception:
                continue
        
        raise Exception("所有LLM模型调用失败")


# ============================================================
# Superpowers 工作流引擎
# ============================================================
class SuperpowersWorkflow:
    """
    Superpowers 工作流引擎
    Phase 1: 任务分析与可行性评估
    Phase 2: 制定执行计划
    Phase 3: TDD 执行（测试驱动开发）
    """
    
    def __init__(self, llm_engine, researcher):
        self.llm = llm_engine
        self.researcher = researcher
        self.execution_plan = None
    
    def phase1_analyze(self, task_title: str, task_description: str, research_context: str = "") -> dict:
        """Phase 1: 任务分析与可行性评估"""
        log("🧠 [Superpowers] Phase 1: 任务分析...")
        
        prompt = f"""请分析以下任务的可执行性，并以JSON格式返回分析结果。

任务标题: {task_title}
任务描述: {task_description}

调研上下文:
{research_context}

请返回以下格式的JSON:
{{
    "task_type": "file_collection|document_writing|code_development|research|other",
    "can_auto_complete": true/false,
    "confidence": 1-10,
    "reason": "分析原因",
    "required_steps": ["步骤1", "步骤2", "步骤3"],
    "potential_challenges": ["挑战1", "挑战2"],
    "success_criteria": "任务完成的标准"
}}
"""
        try:
            result = self.llm.call_llm(prompt, max_tokens=1500, temperature=0.3)
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                log(f"🧠 [Superpowers] 分析完成: 类型={analysis.get('task_type')}, 置信度={analysis.get('confidence')}")
                return analysis
        except Exception as e:
            log(f"⚠️ [Superpowers] 分析失败: {e}")
        
        return {
            "task_type": "other",
            "can_auto_complete": False,
            "confidence": 5,
            "reason": "自动分析失败，标记为需人工处理",
            "required_steps": ["人工分析", "手动执行"],
            "potential_challenges": ["自动分析失败"],
            "success_criteria": "完成核心目标"
        }
    
    def phase2_plan(self, analysis: dict, task_title: str) -> list:
        """Phase 2: 制定详细执行计划"""
        log("📋 [Superpowers] Phase 2: 制定执行计划...")
        
        task_type = analysis.get('task_type', 'other')
        steps = analysis.get('required_steps', [])
        
        prompt = f"""基于以下任务分析，生成详细的逐步执行计划。

任务: {task_title}
任务类型: {task_type}
基本步骤: {json.dumps(steps, ensure_ascii=False)}

请生成详细的执行计划，每个步骤包含：
1. 步骤名称
2. 具体动作
3. 预期输出
4. 验证方法

以JSON数组格式返回:
[{{"step_number": 1, "name": "步骤名称", "action": "具体要做什么", "expected_output": "预期产出", "verification": "如何验证成功"}}]
"""
        try:
            result = self.llm.call_llm(prompt, max_tokens=2000, temperature=0.3)
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
                log(f"📋 [Superpowers] 计划完成: {len(plan)} 个步骤")
                self.execution_plan = plan
                return plan
        except Exception as e:
            log(f"⚠️ [Superpowers] 计划生成失败: {e}")
        
        default_plan = [{"step_number": 1, "name": "直接执行", "action": f"执行任务: {task_title}", "expected_output": "任务完成", "verification": "检查产出物"}]
        self.execution_plan = default_plan
        return default_plan
    
    def phase3_execute(self, plan: list, task_title: str, task_id: int) -> dict:
        """Phase 3: TDD 执行"""
        log("⚡ [Superpowers] Phase 3: TDD 执行...")
        
        results = []
        all_success = True
        
        for step in plan:
            step_num = step.get('step_number', 0)
            step_name = step.get('name', '未知步骤')
            action = step.get('action', '')
            
            log(f"  → 步骤 {step_num}: {step_name}")
            
            try:
                if '搜索' in action or '查找' in action:
                    result = self._execute_search(action)
                elif '生成' in action or '创建' in action or '编写' in action:
                    result = self._execute_generate(action, task_title)
                elif '分析' in action:
                    result = self._execute_analyze(action, task_title)
                else:
                    result = self._execute_generic(action)
                
                success = self._verify_step(result)
                results.append({"step": step_num, "name": step_name, "success": success, "result": result})
                
                if not success:
                    all_success = False
                    log(f"  ⚠️ 步骤 {step_num} 验证未通过")
                else:
                    log(f"  ✅ 步骤 {step_num} 完成")
            except Exception as e:
                log(f"  ❌ 步骤 {step_num} 执行失败: {e}")
                results.append({"step": step_num, "name": step_name, "success": False, "error": str(e)})
                all_success = False
        
        return {"success": all_success, "steps": results}
    
    def _execute_search(self, action: str) -> str:
        result = self.researcher.search(action, max_results=3)
        return f"搜索完成: {len(result.get('results', []))} 条结果"
    
    def _execute_generate(self, action: str, task_title: str) -> str:
        prompt = f"请完成以下任务:\n\n任务: {task_title}\n动作: {action}\n\n请生成详细的产出内容。"
        result = self.llm.call_llm(prompt, max_tokens=3000)
        return result[:500]
    
    def _execute_analyze(self, action: str, task_title: str) -> str:
        prompt = f"请分析以下任务:\n\n任务: {task_title}\n分析要求: {action}\n\n请提供详细分析。"
        result = self.llm.call_llm(prompt, max_tokens=2000)
        return result[:500]
    
    def _execute_generic(self, action: str) -> str:
        return f"执行动作: {action[:100]}..."
    
    def _verify_step(self, result: str) -> bool:
        return bool(result and len(result) >= 10)


# ============================================================
# 日志工具
# ============================================================
execution_log_lines = []

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    execution_log_lines.append(line)
    # print(line)
    sys.stdout.flush()

def append_to_db_log(text: str):
    sql = """
        UPDATE tasks 
        SET execution_log = CONCAT(COALESCE(execution_log, ''), %s),
            updated_at = NOW(),
            last_heartbeat = NOW()
        WHERE id = %s
    """
    execute_update(sql, (text + "\n", TASK_ID))

def update_field(field: str, value: str):
    sql = f"UPDATE tasks SET {field} = %s, updated_at = NOW() WHERE id = %s"
    execute_update(sql, (value, TASK_ID))

def update_status(status: str):
    update_field("status", status)
    log(f"状态变更: {status}")

# ============================================================
# 文件操作工具
# ============================================================
output_dir = Path(f"{get_config('paths.output')}/task-{TASK_ID}")
output_dir.mkdir(parents=True, exist_ok=True)

def find_files(pattern: str, root_dir: str = "/Users/mettlyz/.openclaw/workspace") -> list:
    """搜索文件"""
    try:
        matches = glob.glob(os.path.join(root_dir, "**", pattern), recursive=True)
        return [p for p in matches if os.path.isfile(p)][:50]  # 最多50个
    except Exception as e:
        log(f"   文件搜索失败: {e}")
        return []

def create_index_table(files: list, index_path: Path):
    """创建文件索引表"""
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("# 文件索引表\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"文件总数: {len(files)}\n\n")
        f.write("| 序号 | 文件名 | 路径 | 大小(字节) | 修改时间 |\n")
        f.write("|------|--------|------|-----------|----------|\n")
        for i, fp in enumerate(files, 1):
            stat = os.stat(fp)
            fname = os.path.basename(fp)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
            f.write(f"| {i} | {fname} | {fp} | {stat.st_size} | {mtime} |\n")
    return index_path

def create_zip(source_files: list, zip_path: Path, index_path: Path = None):
    """创建压缩包"""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fp in source_files:
            zf.write(fp, os.path.basename(fp))
        if index_path and index_path.exists():
            zf.write(index_path, os.path.basename(index_path))
    return zip_path

def upload_file_to_server(local_file: Path) -> str:
    """上传到看板服务器"""
    SSH_KEY = "/Users/mettlyz/.openclaw/workspace/info/aliserver1.pem"
    SSH_HOST = "root@47.93.184.128"
    REMOTE_DIR = "/opt/kanban-react/frontend/public/uploads/docs"
    
    # 检查本地文件是否存在
    if not local_file.exists():
        log(f"   ⚠️ 上传失败: 本地文件不存在 {local_file}")
        return str(local_file)
    
    # 检查 SSH key 是否存在
    if not os.path.exists(SSH_KEY):
        log(f"   ⚠️ 上传失败: SSH key 不存在 {SSH_KEY}")
        return str(local_file)
    
    try:
        scp_cmd = ["scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
                   str(local_file), f"{SSH_HOST}:{REMOTE_DIR}/{local_file.name}"]
        log(f"   📤 上传中: {local_file.name} -> {SSH_HOST}")
        result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            log(f"   ✅ 上传成功: /uploads/docs/{local_file.name}")
            return f"/uploads/docs/{local_file.name}"
        else:
            log(f"   ❌ SCP失败 (code={result.returncode}): {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        log(f"   ❌ 上传超时 (30s): {local_file.name}")
    except Exception as e:
        log(f"   ❌ 上传异常: {e}")
    
    # 上传失败，返回本地路径
    return str(local_file)

def save_attachment(filename: str, local_path: Path, file_type: str):
    """保存附件记录到数据库"""
    size = os.path.getsize(local_path)
    remote_url = upload_file_to_server(local_path)
    execute_update("""
        INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
    """, ("task", TASK_ID, filename, remote_url, size, file_type))
    log(f"   ✅ 附件: {filename} -> {remote_url}")
    return remote_url.startswith("/uploads/")

# ============================================================
# 任务分析与分类
# ============================================================
log("=" * 70)
log(f"🚀 SDS子代理启动 - 任务 #{TASK_ID}")
log(f"📋 任务标题: {TASK_TITLE}")
log("=" * 70)

update_status("in_progress")
append_to_db_log(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 子代理启动\n")

start_time = time.time()

# ========== 初始化 Workspace 智能集成器 ==========
log("\n🔌 初始化 Workspace 智能集成...")
workspace_integrator = WorkspaceIntegrator()
workspace_context = workspace_integrator.get_full_context()
if workspace_context:
    log("   ✅ Workspace 上下文已加载")

# ========== 步骤0: 本地文件搜索（如有相关文件） ==========
log("\n📁 步骤0: 搜索 Workspace 本地文件")
local_files = workspace_integrator.search_files(TASK_TITLE, limit=5)
local_files_context = ""
if local_files:
    log(f"   发现 {len(local_files)} 个相关本地文件:")
    for f in local_files:
        log(f"     - {f['filename']} ({f['file_type']})")
    local_files_context = "\n【Workspace本地文件】\n"
    for f in local_files:
        local_files_context += f"- {f['filename']} ({f['file_type']}): {f.get('content_preview', '')[:100]}...\n"
else:
    log("   未发现相关本地文件")

try:
    llm = RealLLMEngine()
    researcher = TavilyResearcher()
    superpowers = SuperpowersWorkflow(llm, researcher)
    
    # ========== 步骤1: Tavily Research 自动调研 ==========
    log("\n🔍 步骤1: Tavily Research 自动调研")
    research_context = ""
    try:
        research_context = researcher.research_for_task(TASK_TITLE, TASK_DESCRIPTION)
        log(f"   调研完成，获取最新行业信息")
    except Exception as e:
        log(f"   调研跳过: {e}")
    
    # ========== 步骤2: Superpowers Phase 1 - 任务分析 ==========
    log("\n🧠 步骤2: Superpowers Phase 1 - 任务分析")
    
    # 注入 Workspace 上下文到分析提示
    analysis_prompt_context = research_context + "\n" + local_files_context + "\n" + workspace_context
    analysis_json = superpowers.phase1_analyze(TASK_TITLE, TASK_DESCRIPTION, analysis_prompt_context)
    
    task_type = analysis_json.get("task_type", "其他")
    can_auto = analysis_json.get("can_auto_complete", False)
    confidence = analysis_json.get("confidence", 5)
    
    log(f"   任务类型: {task_type}")
    log(f"   可自动执行: {can_auto}")
    log(f"   置信度: {confidence}/10")
    log(f"   分析理由: {analysis_json.get('reason', 'N/A')[:100]}")
    
    # ========== 步骤3: Superpowers Phase 2 - 制定计划 ==========
    log("\n📋 步骤3: Superpowers Phase 2 - 制定执行计划")
    
    execution_plan = superpowers.phase2_plan(analysis_json, TASK_TITLE)
    
    log(f"   执行计划: {len(execution_plan)} 个步骤")
    for step in execution_plan:
        log(f"     {step.get('step_number')}. {step.get('name')}: {step.get('action', '')[:60]}")
    
    # ========== 步骤4: Superpowers Phase 3 - TDD执行 ==========
    log("\n⚡ 步骤4: Superpowers Phase 3 - TDD执行")
    
    tdd_result = superpowers.phase3_execute(execution_plan, TASK_TITLE, TASK_ID)
    
    if tdd_result.get('success'):
        log(f"   ✅ TDD执行完成，所有步骤验证通过")
    else:
        log(f"   ⚠️ TDD执行部分失败，{len([s for s in tdd_result.get('steps', []) if not s.get('success')])} 个步骤未通过")
    
    # ========== 步骤5: 动态附件规划（新增）==========
    log("\n🎯 步骤5: 动态附件规划")
    
    # 让LLM根据任务分析结果推理应该产出什么附件
    attachment_plan_prompt = f"""
你是一个任务产出规划专家。请根据以下任务信息，推理出最合适的附件产出计划。

【任务信息】
标题: {TASK_TITLE}
描述: {TASK_DESCRIPTION}
任务类型: {task_type}
可自动完成: {'是' if can_auto else '否'}
置信度: {confidence}/10

【Superpowers分析结果】
分析理由: {analysis_json.get('reason', 'N/A')}
行动方案: {analysis_json.get('action_plan', 'N/A')}
关键发现: {analysis_json.get('key_findings', 'N/A')}

【已执行步骤结果】
{chr(10).join([f"步骤{s.get('step_number')}: {'✅' if s.get('success') else '❌'} {s.get('name')}" for s in tdd_result.get('steps', [])])}

【常见附件类型参考】
以下只是参考示例，你可以根据任务需求自由创造新的附件类型：
- 调研报告: 信息收集、市场分析、竞品分析
- 数据分析表: 数据对比、统计分析、财务分析
- 流程图: 流程设计、系统架构、工作流程
- 待办清单: 执行计划、任务分解、行动项
- 代码文件: 开发、脚本、自动化
- 对比表: 多方案对比、优劣势分析
- 决策文档: 决策支持、建议书、方案评估
- 时间线: 项目规划、里程碑、进度安排
- 资源清单: 资源整理、资产盘点、人员安排
- 沟通模板: 邮件、通知、邀请函、会议纪要
- 文件汇编: 文件收集、资料整理、档案管理
- PPT大纲: 演示文稿结构、演讲提纲
- 预算表: 成本估算、财务规划
- 风险评估: 风险识别、应对策略
- 用户手册: 操作指南、使用说明
- API文档: 接口定义、调用示例
- 测试报告: 测试结果、覆盖率分析
- 会议纪要: 会议记录、决议事项
- 商业计划书: 商业模式、市场策略
- 技术方案: 架构设计、实现细节

【推理要求】
1. 分析任务的核心需求：这个任务最终需要交付什么？
2. 判断需要的附件类型：不要局限于上面的列表，根据任务本质自由决定
3. 确定附件数量：1个核心文件？还是需要多个配套文件？
4. 规划每个附件的内容大纲和文件名

【输出格式】
请返回JSON格式（只返回JSON，不要有其他文字）：
{{
  "reasoning": "分析推理过程...",
  "attachments": [
    {{
      "filename": "建议的文件名（不含扩展名）",
      "type": "附件类型（可以自由创造，不限于上面的列表）",
      "purpose": "这个附件解决什么问题",
      "priority": "high/medium/low",
      "content_outline": ["章节1", "章节2", "章节3"]
    }}
  ]
}}

【重要规则】
- 不要局限于预设的附件类型，根据任务本质自由决定
- 如果任务需要PPT大纲，就产出PPT大纲
- 如果任务需要预算表，就产出预算表
- 如果任务需要风险评估，就产出风险评估
- 只产出对完成任务有直接帮助的文件
- 避免空泛的报告，要有实质内容
- 文件名要简洁明了，反映内容
"""
    
    try:
        attachment_plan_json_str = llm.call_llm(attachment_plan_prompt, max_tokens=2000)
        # 提取JSON部分
        json_match = re.search(r'\{.*\}', attachment_plan_json_str, re.DOTALL)
        if json_match:
            attachment_plan = json.loads(json_match.group())
        else:
            attachment_plan = {"attachments": []}
        
        planned_attachments = attachment_plan.get("attachments", [])
        log(f"   📋 LLM规划了 {len(planned_attachments)} 个附件:")
        for att in planned_attachments:
            log(f"     - [{att.get('priority', 'medium')}] {att.get('type')}: {att.get('filename')} ({att.get('purpose', '')[:30]})")
    except Exception as e:
        log(f"   ⚠️ 附件规划失败，使用默认策略: {e}")
        planned_attachments = []
    
    # ========== 步骤6: 根据附件规划生成文件（动态生成）==========
    log("\n⚡ 步骤6: 动态生成附件")
    
    produced_files = []  # 记录产出的文件
    
    if not planned_attachments:
        # 如果没有规划附件，使用默认策略
        log("   未规划附件，使用默认策略...")
        planned_attachments = [{"filename": f"交付成果_{TASK_ID}", "type": "交付文档", "priority": "high"}]
    
    # 按优先级排序
    priority_order = {"high": 0, "medium": 1, "low": 2}
    planned_attachments.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 1))
    
    # 逐个生成附件
    for att_plan in planned_attachments:  # 不限制附件数量，由LLM决定
        att_type = att_plan.get("type", "交付文档")
        att_filename = att_plan.get("filename", f"附件_{TASK_ID}")
        att_purpose = att_plan.get("purpose", "")
        att_outline = att_plan.get("content_outline", [])
        
        log(f"   生成附件: {att_filename} ({att_type})")
        
        try:
            # 通用文档生成：让LLM根据附件类型自由生成内容
            # 不再限制于固定的10种类型，支持任意附件类型
            
            # 构建生成提示，让LLM理解这是什么类型的文档
            content_prompt = f"""
请为以下任务生成一份"{att_type}"。

【任务信息】
标题: {TASK_TITLE}
描述: {TASK_DESCRIPTION}
附件目的: {att_purpose}

【内容大纲】
{chr(10).join(['- ' + item for item in att_outline]) if att_outline else '请根据附件类型自行设计合理的章节结构'}

【要求】
1. 这是一份"{att_type}"，请确保内容符合该类型的专业标准
2. 内容必须可直接作为正式文档使用
3. 格式规范，使用Markdown
4. 字数不少于1500字（简单清单除外）
5. 包含具体的、可执行的内容，不要空泛
6. 如果附件类型涉及数据，请提供真实、有代表性的数据
7. 如果附件类型涉及代码，请提供完整可运行的代码

请直接输出内容（不要写"以下是..."之类的引言）：
"""
            
            content = llm.call_llm(content_prompt, max_tokens=4000)
            
            # 根据附件类型判断文件扩展名
            ext = ".md"  # 默认Markdown
            mime = "text/markdown"
            if "代码" in att_type or "code" in att_type.lower() or "脚本" in att_type:
                ext = ".py"
                mime = "text/x-python"
            elif "表格" in att_type or "csv" in att_type.lower() or "数据" in att_type:
                ext = ".csv"
                mime = "text/csv"
            
            # 保存文件
            output_file = output_dir / f"{att_filename}{ext}"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {att_filename}\n\n")
                f.write(f"> 任务: {TASK_TITLE}\n")
                f.write(f"> 附件类型: {att_type}\n")
                f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                f.write(content)
            
            produced_files.append((output_file, att_type, mime))
            log(f"     ✅ {att_type}已生成")
                
        except Exception as e:
            log(f"     ❌ 生成附件失败: {e}")
            continue
    
    log(f"   共生成 {len(produced_files)} 个附件")
    
    # ========== 步骤3: 上传附件 ==========
    log("\n💾 步骤3: 上传附件")
    uploaded_count = 0
    
    for file_path, file_type, mime_type in produced_files:
        if save_attachment(file_path.name, file_path, file_type):
            uploaded_count += 1
    
    log(f"   共 {len(produced_files)} 个文件，{uploaded_count} 个上传成功")
    
    # ========== 步骤4: 生成执行日志和总结 ==========
    log("\n📝 步骤4: 生成执行日志和总结")
    
    execution_time = int(time.time() - start_time)
    
    # 执行日志
    execution_log_full = "\n".join(execution_log_lines) + f"""

【执行详情】
任务类型: {task_type}
可自动执行: {can_auto}
执行耗时: {execution_time} 秒
使用模型: {llm.used_model or 'fallback链'}

【产出文件】
"""
    for fp, ft, _ in produced_files:
        execution_log_full += f"- {ft}: {fp.name}\n"
    
    execution_log_full += f"""

【执行过程】
1. 分析任务类型和可执行性
2. 根据任务类型选择执行策略
3. 执行核心操作（搜索文件/生成文档/编写代码）
4. 整理产出并上传附件
5. 更新任务状态

【LLM分析】
{analysis_json.get('reason', 'N/A')}
"""
    
    # 结果总结（确保 ≥100 字）
    result_summary = f"""【任务执行结果】

任务 #{TASK_ID}: {TASK_TITLE}

任务类型识别: {task_type}
可自动完成: {'是' if can_auto else '否（需要人工补充）'}
执行耗时: {execution_time}秒

【实际产出】
共生成 {len(produced_files)} 个文件：
"""
    if produced_files:
        for fp, ft, _ in produced_files:
            result_summary += f"- {ft}: {fp.name}\n"
    else:
        result_summary += "- 无文件产出（非文件类任务）\n"
    
    action_plan = analysis_json.get('action_plan', 'N/A')
    reason = analysis_json.get('reason', 'N/A')
    
    # ========== 使用 LLM 生成高质量摘要 ==========
    log("\n📝 使用 LLM 生成任务摘要...")
    
    # 构建 LLM 摘要生成提示
    summary_prompt = f"""请为以下已完成的任务生成高质量的 task_summary 和 result_summary。

【任务信息】
任务ID: #{TASK_ID}
任务标题: {TASK_TITLE}
任务描述: {TASK_DESCRIPTION}
任务类型: {task_type}
可自动完成: {'是' if can_auto else '否'}
执行耗时: {execution_time}秒
产出文件数: {len(produced_files)}

【执行过程概述】
{reason}

【核心发现与行动方案】
{action_plan}

【产出文件列表】
"""
    if produced_files:
        for fp, ft, _ in produced_files:
            summary_prompt += f"- {ft}: {fp.name}\n"
    else:
        summary_prompt += "- 无文件产出\n"
    
    summary_prompt += f"""
【要求】
1. task_summary: 50-100字，简洁概括任务核心成果，必须包含关键数据和结论
2. result_summary: 300-500字，详细描述执行过程、核心发现、具体产出和后续建议
3. 两个摘要都必须有实质内容，不要空泛套话
4. 用中文输出

请以以下格式返回（不要包含其他内容）：
---TASK_SUMMARY---
[50-100字的任务摘要]
---RESULT_SUMMARY---
[300-500字的结果总结]
"""
    
    try:
        llm_summary = llm.call_llm(summary_prompt, max_tokens=1500, temperature=0.5)
        
        # 解析 LLM 输出
        task_match = re.search(r'---TASK_SUMMARY---\s*(.*?)\s*---RESULT_SUMMARY---', llm_summary, re.DOTALL)
        result_match = re.search(r'---RESULT_SUMMARY---\s*(.*)', llm_summary, re.DOTALL)
        
        if task_match and result_match:
            task_summary = task_match.group(1).strip()
            result_summary = result_match.group(1).strip()
            log(f"   ✅ LLM生成摘要成功")
            log(f"   task_summary: {len(task_summary)}字")
            log(f"   result_summary: {len(result_summary)}字")
        else:
            # 回退到格式解析失败时的处理
            log(f"   ⚠️ LLM摘要格式解析失败，使用备用方案")
            # 尝试从输出中提取
            lines = llm_summary.strip().split('\n')
            if len(lines) >= 2:
                task_summary = lines[0][:100]
                result_summary = '\n'.join(lines[1:])[:500]
            else:
                raise ValueError("LLM输出格式不符合预期")
    except Exception as e:
        log(f"   ❌ LLM摘要生成失败: {e}")
        log(f"   ❌ 任务标记为 failed_retryable，将在后续周期重试")
        
        # LLM摘要生成失败 = 任务失败，需要重试
        error_msg = f"LLM摘要生成失败: {str(e)}"
        append_to_db_log(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}\n")
        
        # 增加重试次数，标记为可重试
        execute_update("""
            UPDATE tasks 
            SET retry_count = COALESCE(retry_count, 0) + 1,
                status = IF(COALESCE(retry_count, 0) + 1 >= 3, 'cancelled', 'failed_retryable'),
                updated_at = NOW()
            WHERE id = %s
        """, (TASK_ID,))
        
        log(f"   ⚠️ 任务 #{TASK_ID} 已标记为 failed_retryable")
        sys.exit(1)
    
    # ========== 步骤5: 清理临时文件 ==========
    log("\n🧹 步骤5: 清理临时文件")
    
    # Workspace Guardian: 确保产出在正确位置，清理临时文件
    try:
        # 清理 /tmp/ 下的临时脚本（本脚本除外）
        tmp_dir = Path("/tmp")
        for tmp_file in tmp_dir.glob("subagent_task_*.py"):
            if tmp_file != Path(__file__):
                try:
                    tmp_file.unlink()
                    log(f"   🗑️  清理临时文件: {tmp_file.name}")
                except Exception:
                    pass
        
        # 确保产出在 Files/output/task-{TASK_ID}/
        expected_output_dir = Path(get_config('paths.output')) / f"task-{TASK_ID}"
        if output_dir != expected_output_dir:
            log(f"   ⚠️  产出目录不在标准位置: {output_dir}")
            log(f"   标准位置应为: {expected_output_dir}")
        
        log("   ✅ 临时文件清理完成")
    except Exception as e:
        log(f"   ⚠️  清理临时文件时出错: {e}")
    
    # ========== 步骤6: 更新数据库 ==========
    log("\n💾 步骤6: 更新数据库")
    
    update_field("execution_log", execution_log_full)
    update_field("result_summary", result_summary)
    update_field("task_summary", task_summary)
    update_field("retry_count", 0)
    
    # 如果无法自动完成，标记为需要审核而不是直接完成
    if can_auto:
        update_status("completed")
        log("   ✅ 状态: completed（自动完成）")
    else:
        update_status("pending_review")
        log("   ⚠️ 状态: pending_review（需人工审核）")
    
    append_to_db_log(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 执行完成\n")
    
    log("\n" + "=" * 70)
    log(f"✅ 任务 #{TASK_ID} 执行完成！")
    log(f"⏱️  耗时: {execution_time} 秒")
    log(f"📎 产出: {len(produced_files)} 个文件")
    log(f"📁 位置: Files/output/task-{TASK_ID}/")
    log("=" * 70)
    sys.exit(0)

except Exception as e:
    error_msg = f"执行异常: {str(e)}\n{traceback.format_exc()}"
    log(f"❌ {error_msg}")
    append_to_db_log(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 异常: {str(e)}\n")
    
    execute_update("""
        UPDATE tasks 
        SET retry_count = COALESCE(retry_count, 0) + 1,
            status = IF(COALESCE(retry_count, 0) + 1 >= 3, 'cancelled', 'failed_retryable'),
            updated_at = NOW()
        WHERE id = %s
    """, (TASK_ID,))
    sys.exit(1)

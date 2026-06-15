"""
actor_tools.py - 真实工具函数实现
为演员系统（actor_api.py, brainstorm_api.py）提供替代 lambda 桩函数的真实 API 调用。

支持的工具有：
  - paper_search:       ArXiv API 真实搜索论文
  - patent_search:      使用 Google Patents (通过 Tavily) 搜索专利
  - market_size:        使用 Tavily 搜索真实行业市场规模数据
  - kanban_status:      MySQL 查询看板数据库获取真实项目状态
  - failure_case_db:    MySQL 从数据库读取失败案例
"""

import json, urllib.request, logging, os, ssl, re, time
from urllib.parse import quote

logger = logging.getLogger(__name__)

# ── 配置 ──
TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY', '')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
MYSQL_HOST = os.environ.get('MYSQL_HOST', 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', '3306'))
MYSQL_USER = os.environ.get('MYSQL_USER', 'kanban')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'kanban')


# ── 辅助函数 ──

def _ssl_urlopen(url, data=None, headers=None, timeout=15):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def _tavily_search(query, max_results=5):
    if not TAVILY_API_KEY:
        return {"error": "TAVILY_API_KEY 未配置"}
    body = json.dumps({
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "include_answer": True,
    }).encode()
    try:
        raw = _ssl_urlopen(
            "https://api.tavily.com/search",
            data=body,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        return json.loads(raw)
    except Exception as e:
        return {"error": "Tavily 搜索失败: " + str(e)}


def _deepseek_chat(messages, max_tokens=2000):
    if not DEEPSEEK_API_KEY:
        return {"error": "DEEPSEEK_API_KEY 未配置"}
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": max_tokens,
    }).encode()
    try:
        raw = _ssl_urlopen(
            "https://api.deepseek.com/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + DEEPSEEK_API_KEY,
            },
            timeout=30,
        )
        return json.loads(raw)
    except Exception as e:
        return {"error": "DeepSeek 调用失败: " + str(e)}


def _query_mysql(sql, params=None):
    try:
        import pymysql
        conn = pymysql.connect(
            host=MYSQL_HOST, port=MYSQL_PORT,
            user=MYSQL_USER, password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE, charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5, read_timeout=10,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                rows = cur.fetchall()
                return rows
        finally:
            conn.close()
    except Exception as e:
        logger.error("数据库查询失败: " + str(e))
        return None


# ══════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════

def paper_search(query, limit=10):
    """
    通过 ArXiv API 搜索学术论文
    参数: query - 搜索关键词, limit - 返回篇数(默认10)
    返回: {"results": [...], "source": "arxiv", "total": N}
    """
    logger.info("📚 论文搜索: query=" + str(query) + ", limit=" + str(limit))
    try:
        search_query = quote(query)
        url = ("https://export.arxiv.org/api/query?search_query=all:" +
               search_query +
               "&start=0&max_results=" + str(limit) +
               "&sortBy=relevance&sortOrder=descending")
        raw = _ssl_urlopen(url, timeout=15)
        text = raw.decode('utf-8')

        papers = []
        entries = re.findall(r'<entry>(.*?)</entry>', text, re.DOTALL)
        for entry in entries:
            title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
            title = title_match.group(1).strip() if title_match else ''
            title = re.sub(r'\s+', ' ', title)

            summary_match = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else ''
            summary = re.sub(r'\s+', ' ', summary)[:300]

            year_match = re.search(r'<published>(\d{4})', entry)
            year = year_match.group(1) if year_match else ''

            link_match = re.search(r'<id>(.*?)</id>', entry, re.DOTALL)
            link = link_match.group(1).strip() if link_match else ''

            authors = re.findall(
                r'<author>.*?<name>(.*?)</name>.*?</author>', entry, re.DOTALL
            )
            author_str = ', '.join(authors[:5])
            if len(authors) > 5:
                author_str += ' et al.'

            papers.append({
                "title": title,
                "authors": author_str,
                "year": year,
                "summary": summary,
                "link": link,
            })

        logger.info("✅ 论文搜索完成: 找到 " + str(len(papers)) + " 篇")
        return {
            "results": papers,
            "source": "arxiv",
            "total": len(papers),
            "query": query,
        }
    except Exception as e:
        logger.error("❌ 论文搜索失败: " + str(e))
        return {"error": "论文搜索失败: " + str(e), "source": "arxiv", "results": []}


def patent_search(query, limit=5):
    """
    搜索专利 - 使用 Tavily 搜索 Google Patents
    参数: query - 搜索关键词, limit - 返回条数(默认5)
    返回: {"results": [...], "source": "google_patents", "total": N}
    """
    logger.info("📜 专利搜索: query=" + str(query) + ", limit=" + str(limit))
    try:
        search_query = "site:patents.google.com " + query + " patent"
        tavily_result = _tavily_search(search_query, max_results=limit)

        if "error" in tavily_result:
            logger.warning("Tavily 不可用: " + str(tavily_result["error"]))
            ds_resp = _deepseek_chat([
                {"role": "system", "content": "你是专利分析师。请提供关于指定关键词的重要专利信息，返回JSON格式的列表，每项包含title(专利名称)、assignee(专利权人)、year(年份)、description(简要描述)。无需额外文字。"},
                {"role": "user", "content": "请列出关于 \"" + query + "\" 的 " + str(limit) + " 项真实重要专利"}
            ], max_tokens=2000)
            if "error" not in ds_resp:
                content = ds_resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {
                    "results": [{"title": "专利搜索结果", "content": content}],
                    "source": "deepseek_generated",
                    "total": 1,
                    "query": query,
                }
            return {"error": "专利搜索失败: " + str(tavily_result["error"]), "results": []}

        results = []
        for r in tavily_result.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:500],
                "score": r.get("score", 0),
            })

        logger.info("✅ 专利搜索完成: 找到 " + str(len(results)) + " 条")
        return {
            "results": results,
            "source": "google_patents_via_tavily",
            "total": len(results),
            "query": query,
        }
    except Exception as e:
        logger.error("❌ 专利搜索失败: " + str(e))
        return {"error": "专利搜索失败: " + str(e), "results": []}


def market_size(industry):
    """
    搜索行业市场规模数据 - 使用 Tavily 搜索
    参数: industry - 行业名称
    返回: {"industry": ..., "market_data": ..., "sources": [...]}
    """
    logger.info("📊 市场规模查询: industry=" + str(industry))
    try:
        search_query = str(industry) + " 市场规模 2025 2026 增长率"
        search_result = _tavily_search(search_query, max_results=5)

        if "error" in search_result:
            logger.warning("Tavily 搜索失败: " + str(search_result["error"]))
            ds_resp = _deepseek_chat([
                {"role": "system", "content": "你是行业分析师。请提供指定行业的最新市场规模数据，包含具体数字和来源。"},
                {"role": "user", "content": "请提供\"" + str(industry) + "\"行业的市场规模数据：2025年市场规模、2026年预测、CAGR增长率、主要驱动力。"}
            ], max_tokens=2000)
            if "error" not in ds_resp:
                content = ds_resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {
                    "industry": industry,
                    "market_data": content,
                    "source": "deepseek_generated",
                }
            return {"error": "市场规模查询失败", "industry": industry}

        search_text = ""
        for r in search_result.get("results", []):
            search_text += "- " + r.get("title", "") + ": " + r.get("content", "")[:300] + "\n"
        if search_result.get("answer"):
            search_text = "Tavily总结: " + search_result["answer"] + "\n" + search_text

        logger.info("✅ 市场规模搜索完成: " +
                     str(len(search_result.get("results", []))) + " 条结果")
        return {
            "industry": industry,
            "market_data": search_text[:2000],
            "sources": [r.get("url", "") for r in search_result.get("results", [])[:5]],
            "answer": search_result.get("answer", ""),
            "source": "tavily",
        }
    except Exception as e:
        logger.error("❌ 市场规模查询失败: " + str(e))
        return {"error": "市场规模查询失败: " + str(e), "industry": industry}


def kanban_status():
    """
    查询看板数据库获取项目/任务真实状态
    返回: {"projects": {...}, "tasks": {...}, "database": "mysql"}
    """
    logger.info("📋 查询看板状态")
    try:
        rows = _query_mysql(
            "SELECT status, COUNT(*) AS cnt FROM kanban_tasks GROUP BY status"
        )
        if rows is None:
            return {
                "error": "数据库连接失败",
                "database": "mysql",
                "note": "请检查 MYSQL_PASSWORD 环境变量是否正确设置",
            }

        task_summary = {}
        for r in rows:
            task_summary[str(r["status"])] = int(r["cnt"])
        total_tasks = sum(task_summary.values())

        project_rows = _query_mysql(
            "SELECT status, COUNT(*) AS cnt FROM projects GROUP BY status"
        )
        project_summary = {}
        if project_rows:
            for r in project_rows:
                project_summary[str(r["status"])] = int(r["cnt"])
        total_projects = sum(project_summary.values())

        active_projects = _query_mysql(
            "SELECT id, name, status, updated_at FROM projects "
            "WHERE status IN ('active', 'in_progress') "
            "ORDER BY updated_at DESC LIMIT 10"
        ) or []

        logger.info("✅ 看板状态: " + str(total_tasks) + " 任务, " +
                     str(total_projects) + " 项目")
        return {
            "tasks": {
                "total": total_tasks,
                "by_status": task_summary,
            },
            "projects": {
                "total": total_projects,
                "by_status": project_summary,
                "active_list": [
                    {
                        "id": int(p["id"]) if isinstance(p["id"], int) else p["id"],
                        "name": str(p.get("name", "")),
                        "status": str(p.get("status", "")),
                    }
                    for p in active_projects
                ],
            },
            "database": "mysql",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        logger.error("❌ 看板状态查询失败: " + str(e))
        return {"error": "看板状态查询失败: " + str(e), "database": "mysql"}


def failure_case_db(sector=None):
    """
    从数据库读取失败案例
    参数: sector - 可选的领域筛选
    返回: {"cases": [...], "sector": sector, "total": N}
    """
    logger.info("⚠️ 失败案例查询: sector=" + str(sector))
    try:
        if sector:
            rows = _query_mysql(
                "SELECT pattern, reason, fail_count, last_failed_at "
                "FROM failure_patterns "
                "WHERE pattern LIKE %s ORDER BY fail_count DESC LIMIT 20",
                ("%" + str(sector) + "%",)
            )
        else:
            rows = _query_mysql(
                "SELECT pattern, reason, fail_count, last_failed_at "
                "FROM failure_patterns "
                "ORDER BY fail_count DESC LIMIT 20"
            )

        if rows is None:
            return {"error": "数据库连接失败", "cases": [], "sector": sector}

        if sector:
            weakness_rows = _query_mysql(
                "SELECT type, severity, description, source, status, detected_at "
                "FROM weaknesses WHERE type LIKE %s OR description LIKE %s "
                "ORDER BY severity ASC LIMIT 20",
                ("%" + str(sector) + "%", "%" + str(sector) + "%")
            )
        else:
            weakness_rows = _query_mysql(
                "SELECT type, severity, description, source, status, detected_at "
                "FROM weaknesses ORDER BY severity ASC LIMIT 20"
            )

        cases = []
        for r in rows:
            lf = r.get("last_failed_at")
            if lf and hasattr(lf, "strftime"):
                lf_str = lf.strftime("%Y-%m-%d %H:%M")
            else:
                lf_str = str(lf or "")
            cases.append({
                "type": "failure_pattern",
                "pattern": str(r.get("pattern", "")),
                "reason": str(r.get("reason", "")),
                "fail_count": int(r.get("fail_count", 0)),
                "last_failed": lf_str,
            })

        if weakness_rows:
            for r in weakness_rows:
                dt = r.get("detected_at")
                if dt and hasattr(dt, "strftime"):
                    dt_str = dt.strftime("%Y-%m-%d %H:%M")
                else:
                    dt_str = str(dt or "")
                cases.append({
                    "type": "weakness",
                    "severity": str(r.get("severity", "")),
                    "description": str(r.get("description", "")),
                    "source": str(r.get("source", "")),
                    "status": str(r.get("status", "")),
                    "detected_at": dt_str,
                })

        logger.info("✅ 失败案例查询完成: " + str(len(cases)) + " 条")
        return {
            "cases": cases,
            "sector": sector,
            "total": len(cases),
            "source": "mysql",
        }
    except Exception as e:
        logger.error("❌ 失败案例查询失败: " + str(e))
        return {"error": "失败案例查询失败: " + str(e), "cases": [], "sector": sector}


# ── 统一注册表 ──
TOOL_REGISTRY = {
    "paper_search": paper_search,
    "patent_search": patent_search,
    "market_size": market_size,
    "kanban_status": kanban_status,
    "failure_case_db": failure_case_db,
}

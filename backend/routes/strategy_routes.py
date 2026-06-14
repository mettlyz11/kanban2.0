"""Routes: strategy_docs + llm_providers + knowledge_browser"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db
import os, json, glob
from datetime import datetime

bp = Blueprint('routes_strategy', __name__)
logger = __import__('logging').getLogger(__name__)

DOCS_DIR = "/opt/kanban-react/backend/uploads/company-docs"
CONTRACTS_DIR = "/opt/kanban-react/backend/uploads/contracts"
PROJECTS_DIR = "/opt/kanban-react/backend/uploads/projects"
INDUSTRY_DIR = "/opt/kanban-react/backend/uploads/industry"
ARTICLES_DIR = "/opt/kanban-react/backend/uploads/articles"


def _safe_join(base, rel):
    rel = (rel or '').replace('\\', '/')
    rel = rel.lstrip('/')
    full = os.path.abspath(os.path.join(base, rel))
    base_abs = os.path.abspath(base)
    if not full.startswith(base_abs + os.sep) and full != base_abs:
        return None
    return full


def _title_from_file(path):
    name = os.path.basename(path)
    for suffix in ['.md', '.txt']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name.replace('_', ' ')


def _list_files(base, category, exts):
    items = []
    if not os.path.exists(base):
        return items
    for fpath in glob.glob(os.path.join(base, '**', '*'), recursive=True):
        if not os.path.isfile(fpath):
            continue
        if not any(fpath.lower().endswith(e) for e in exts):
            continue
        rel = os.path.relpath(fpath, base).replace('\\', '/')
        stat = os.stat(fpath)
        items.append({
            'id': f'{category}/{rel}',
            'title': _title_from_file(fpath),
            'name': rel,
            'filename': rel,
            'category': category,
            'source': base,
            'size': stat.st_size,
            'mtime': stat.st_mtime,
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
            'url': f'/api/strategy-docs/content?category={category}&file={rel}'
        })
    items.sort(key=lambda x: x['mtime'], reverse=True)
    return items


@bp.route('/api/strategy-docs/list', methods=['GET'])
def list_strategy_docs():
    """列出所有战略文档：同时返回 flat docs 和兼容 categories"""
    cfgs = [
        ('company', '📄 公司战略', DOCS_DIR, ['.md', '.txt']),
        ('contracts', '📋 合同', CONTRACTS_DIR, ['.md', '.txt']),
        ('projects', '📐 项目方案', PROJECTS_DIR, ['.md', '.txt']),
    ]
    docs = []
    categories = []
    for key, label, dirpath, exts in cfgs:
        files = _list_files(dirpath, key, exts)
        docs.extend(files)
        categories.append({'key': key, 'label': label, 'files': files, 'total': len(files)})
    return jsonify({'success': True, 'docs': docs, 'categories': categories, 'total': len(docs)})


@bp.route('/api/strategy-docs/content', methods=['GET'])
def get_strategy_doc():
    """获取文档内容。支持 category+file，也兼容 file=category/name"""
    category = request.args.get('category', '')
    filepath = request.args.get('file', '')
    if not filepath:
        return jsonify({'success': False, 'error': '需要 file 参数'}), 400

    legacy_map = {'company-docs': 'company'}
    if not category and '/' in filepath:
        cat0, filepath = filepath.split('/', 1)
        category = legacy_map.get(cat0, cat0)

    dir_map = {'company': DOCS_DIR, 'contracts': CONTRACTS_DIR, 'projects': PROJECTS_DIR}
    base = dir_map.get(category)
    if not base:
        return jsonify({'success': False, 'error': '无效分类'}), 400

    fpath = _safe_join(base, filepath)
    if not fpath or not os.path.exists(fpath) or not os.path.isfile(fpath):
        return jsonify({'success': False, 'error': '文件不存在'}), 404

    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    return jsonify({'success': True, 'name': filepath, 'category': category, 'content': content, 'size': os.path.getsize(fpath)})


@bp.route('/api/llm-providers', methods=['GET'])
def get_llm_providers():
    """从 system_configs 读取最新 LLM provider 数据"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT config_data FROM system_configs WHERE config_type = 'llm_providers_snapshot' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row and row['config_data']:
            data = json.loads(row['config_data'])
            return jsonify({'success': True, 'providers': data.get('providers', []), 'models': data.get('models', []), 'updated_at': data.get('updated_at', '')})
    except Exception as e:
        logger.warning(f"读取 llm_providers_snapshot 失败: {e}")
    return jsonify({'success': True, 'providers': [], 'models': [], 'updated_at': ''})


@bp.route('/api/knowledge-library/list', methods=['GET'])
def list_knowledge_library():
    categories = []
    all_docs = []
    for key, label, dirpath, exts in [
        ('industry', '📊 行业报告', INDUSTRY_DIR, ['.md']),
        ('articles', '📜 学术文章', ARTICLES_DIR, ['.md']),
    ]:
        files = _list_files(dirpath, key, exts)
        all_docs.extend(files)
        categories.append({'key': key, 'label': label, 'files': files, 'total': len(files)})
    return jsonify({'success': True, 'docs': all_docs, 'categories': categories, 'total': len(all_docs)})


@bp.route('/api/knowledge-library/content', methods=['GET'])
def get_knowledge_library_content():
    category = request.args.get('category', '')
    filepath = request.args.get('file', '')
    if not filepath:
        return jsonify({'success': False, 'error': '需要 file 参数'}), 400
    if not category and '/' in filepath:
        category, filepath = filepath.split('/', 1)
    dir_map = {'industry': INDUSTRY_DIR, 'articles': ARTICLES_DIR}
    base = dir_map.get(category)
    if not base:
        return jsonify({'success': False, 'error': '无效分类'}), 400
    fpath = _safe_join(base, filepath)
    if not fpath or not os.path.exists(fpath) or not os.path.isfile(fpath):
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    return jsonify({'success': True, 'name': filepath, 'category': category, 'content': content, 'size': os.path.getsize(fpath)})

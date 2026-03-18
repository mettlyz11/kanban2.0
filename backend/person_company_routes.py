# ============================================
# 动态Tab系统 - 人员和公司信息管理
# ============================================

from flask import Blueprint, request, jsonify
import os
from database_config import get_db_connection
import json
from datetime import datetime

# 创建蓝图
person_company_bp = Blueprint('person_company', __name__, url_prefix='/api')

# 数据库配置
from database_config import get_db_connection
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')

def get_db():
    """获取数据库连接"""
    with get_db_connection() as conn:
    
    return conn

# ============================================
# 数据库初始化
# ============================================

def init_person_company_tables():
    """初始化人员和公司相关表"""
    conn = get_db()
    c = conn.cursor()
    
    # 人员主表
    c.execute('''
        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            title TEXT,
            email TEXT,
            phone TEXT,
            location TEXT,
            bio TEXT,
            avatar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 公司主表
    c.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            short_name TEXT,
            description TEXT,
            industry TEXT,
            sub_industry TEXT,
            legal_representative TEXT,
            create_date TEXT,
            registered_capital TEXT,
            business_license TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            logo TEXT,
            employee_count INTEGER DEFAULT 0,
            tax_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 人员Tab定义表
    c.execute('''
        CREATE TABLE IF NOT EXISTS person_tabs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            tab_key TEXT NOT NULL,
            tab_label TEXT NOT NULL,
            tab_icon TEXT DEFAULT 'FileText',
            sort_order INTEGER DEFAULT 0,
            is_custom INTEGER DEFAULT 0,
            is_system INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE,
            UNIQUE(person_id, tab_key)
        )
    ''')
    
    # 公司Tab定义表
    c.execute('''
        CREATE TABLE IF NOT EXISTS company_tabs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            tab_key TEXT NOT NULL,
            tab_label TEXT NOT NULL,
            tab_icon TEXT DEFAULT 'Building2',
            sort_order INTEGER DEFAULT 0,
            is_custom INTEGER DEFAULT 0,
            is_system INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            UNIQUE(company_id, tab_key)
        )
    ''')
    
    # 人员Tab数据表
    c.execute('''
        CREATE TABLE IF NOT EXISTS person_tab_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            tab_key TEXT NOT NULL,
            data_json TEXT DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE,
            UNIQUE(person_id, tab_key)
        )
    ''')
    
    # 公司Tab数据表
    c.execute('''
        CREATE TABLE IF NOT EXISTS company_tab_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            tab_key TEXT NOT NULL,
            data_json TEXT DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            UNIQUE(company_id, tab_key)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 人员和公司动态Tab表初始化完成")

# ============================================
# 人员 API
# ============================================

@person_company_bp.route('/persons', methods=['GET'])
def get_persons():
    """获取所有人员列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, name, title, email, phone, location, avatar, created_at
            FROM persons
            ORDER BY created_at DESC
        ''')
        persons = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'persons': persons})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_company_bp.route('/persons/<int:person_id>', methods=['GET'])
def get_person_detail(person_id):
    """获取人员详情（包含所有Tab数据）"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 获取人员基本信息
        c.execute('SELECT * FROM persons WHERE id = ?', (person_id,))
        person = c.fetchone()
        
        if not person:
            conn.close()
            return jsonify({'success': False, 'error': '人员不存在'}), 404
        
        person_dict = dict(person)
        
        # 获取人员所有Tab定义
        c.execute('''
            SELECT tab_key, tab_label, tab_icon, sort_order, is_custom, is_system
            FROM person_tabs
            WHERE person_id = ?
            ORDER BY sort_order, id
        ''', (person_id,))
        tabs = [dict(row) for row in c.fetchall()]
        
        # 如果没有Tab，创建默认Tab
        if not tabs:
            default_tabs = [
                ('basic', '基本信息', 'User', 0, 0, 1),
                ('education', '教育背景', 'GraduationCap', 1, 0, 1),
                ('experience', '工作经历', 'Briefcase', 2, 0, 1),
                ('skills', '技能证书', 'Award', 3, 0, 1),
            ]
            for tab in default_tabs:
                c.execute('''
                    INSERT OR IGNORE INTO person_tabs 
                    (person_id, tab_key, tab_label, tab_icon, sort_order, is_custom, is_system)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (person_id,) + tab)
            conn.commit()
            
            # 重新获取Tabs
            c.execute('''
                SELECT tab_key, tab_label, tab_icon, sort_order, is_custom, is_system
                FROM person_tabs
                WHERE person_id = ?
                ORDER BY sort_order, id
            ''', (person_id,))
            tabs = [dict(row) for row in c.fetchall()]
        
        person_dict['tabs'] = tabs
        
        # 获取所有Tab数据
        c.execute('''
            SELECT tab_key, data_json
            FROM person_tab_data
            WHERE person_id = ?
        ''', (person_id,))
        tab_data = {row['tab_key']: json.loads(row['data_json']) for row in c.fetchall()}
        
        # 为每个Tab添加数据
        for tab in tabs:
            tab['data'] = tab_data.get(tab['tab_key'], {})
        
        conn.close()
        return jsonify({'success': True, 'person': person_dict})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_company_bp.route('/persons', methods=['POST'])
def create_person():
    """创建人员"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': '姓名不能为空'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO persons (name, title, email, phone, location, bio, avatar)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            name,
            data.get('title', ''),
            data.get('email', ''),
            data.get('phone', ''),
            data.get('location', ''),
            data.get('bio', ''),
            data.get('avatar', '')
        ))
        
        person_id = c.lastrowid
        
        # 创建默认Tab
        default_tabs = [
            ('basic', '基本信息', 'User', 0, 0, 1),
            ('education', '教育背景', 'GraduationCap', 1, 0, 1),
            ('experience', '工作经历', 'Briefcase', 2, 0, 1),
            ('skills', '技能证书', 'Award', 3, 0, 1),
        ]
        for tab in default_tabs:
            c.execute('''
                INSERT INTO person_tabs 
                (person_id, tab_key, tab_label, tab_icon, sort_order, is_custom, is_system)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (person_id,) + tab)
        
        # 初始化默认Tab数据
        default_data = {
            'basic': {
                'name': name,
                'title': data.get('title', ''),
                'email': data.get('email', ''),
                'phone': data.get('phone', ''),
                'location': data.get('location', ''),
                'bio': data.get('bio', '')
            },
            'education': {'items': []},
            'experience': {'items': []},
            'skills': {'items': [], 'certifications': []}
        }
        
        for tab_key, data_json in default_data.items():
            c.execute('''
                INSERT INTO person_tab_data (person_id, tab_key, data_json)
                VALUES (?, ?, ?)
            ''', (person_id, tab_key, json.dumps(data_json)))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'person_id': person_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_company_bp.route('/persons/<int:person_id>', methods=['PUT'])
def update_person(person_id):
    """更新人员基本信息"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        # 检查人员是否存在
        c.execute('SELECT id FROM persons WHERE id = ?', (person_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '人员不存在'}), 404
        
        # 更新基本信息
        allowed_fields = ['name', 'title', 'email', 'phone', 'location', 'bio', 'avatar']
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        
        if updates:
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
            values = list(updates.values()) + [person_id]
            
            c.execute(f'UPDATE persons SET {set_clause} WHERE id = ?', values)
            conn.commit()
        
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_company_bp.route('/persons/<int:person_id>', methods=['DELETE'])
def delete_person(person_id):
    """删除人员"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('DELETE FROM persons WHERE id = ?', (person_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# 人员 Tab API
# ============================================

@person_company_bp.route('/persons/<int:person_id>/tabs', methods=['POST'])
def add_person_tab(person_id):
    """为人员添加Tab"""
    try:
        data = request.get_json()
        tab_key = data.get('tab_key', '').strip()
        tab_label = data.get('tab_label', '').strip()
        tab_icon = data.get('tab_icon', 'FileText')
        
        if not tab_key or not tab_label:
            return jsonify({'success': False, 'error': 'Tab标识和名称不能为空'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # 检查人员是否存在
        c.execute('SELECT id FROM persons WHERE id = ?', (person_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '人员不存在'}), 404
        
        # 获取当前最大排序
        c.execute('SELECT MAX(sort_order) FROM person_tabs WHERE person_id = ?', (person_id,))
        max_order = c.fetchone()[0] or 0
        
        # 添加Tab
        c.execute('''
            INSERT OR REPLACE INTO person_tabs 
            (person_id, tab_key, tab_label, tab_icon, sort_order, is_custom, is_system)
            VALUES (?, ?, ?, ?, ?, 1, 0)
        ''', (person_id, tab_key, tab_label, tab_icon, max_order + 1))
        
        # 初始化Tab数据
        c.execute('''
            INSERT OR IGNORE INTO person_tab_data (person_id, tab_key, data_json)
            VALUES (?, ?, ?)
        ''', (person_id, tab_key, json.dumps({'items': []})))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_company_bp.route('/persons/<int:person_id>/tabs/<tab_key>', methods=['DELETE'])
def delete_person_tab(person_id, tab_key):
    """删除人员Tab"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 检查是否是系统Tab
        c.execute('''
            SELECT is_system FROM person_tabs 
            WHERE person_id = ? AND tab_key = ?
        ''', (person_id, tab_key))
        row = c.fetchone()
        
        if row and row['is_system']:
            conn.close()
            return jsonify({'success': False, 'error': '系统Tab不能删除'}), 400
        
        # 删除Tab和数据
        c.execute('''
            DELETE FROM person_tabs 
            WHERE person_id = ? AND tab_key = ?
        ''', (person_id, tab_key))
        
        c.execute('''
            DELETE FROM person_tab_data 
            WHERE person_id = ? AND tab_key = ?
        ''', (person_id, tab_key))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_company_bp.route('/persons/<int:person_id>/tabs/<tab_key>/data', methods=['PUT'])
def update_person_tab_data(person_id, tab_key):
    """更新人员Tab数据"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        # 检查Tab是否存在
        c.execute('''
            SELECT id FROM person_tabs 
            WHERE person_id = ? AND tab_key = ?
        ''', (person_id, tab_key))
        
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Tab不存在'}), 404
        
        # 更新或插入数据
        c.execute('''
            INSERT INTO person_tab_data (person_id, tab_key, data_json, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(person_id, tab_key) 
            DO UPDATE SET data_json = excluded.data_json, updated_at = CURRENT_TIMESTAMP
        ''', (person_id, tab_key, json.dumps(data)))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# 公司 API
# ============================================

@person_company_bp.route('/companies', methods=['GET'])
def get_companies():
    """获取所有公司列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, name, short_name, industry, address, logo, employee_count, created_at
            FROM companies
            ORDER BY created_at DESC
        ''')
        companies = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'companies': companies})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_company_bp.route('/companies/<int:company_id>', methods=['GET'])
def get_company_detail(company_id):
    """获取公司详情（包含所有Tab数据）"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 获取公司基本信息
        c.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
        company = c.fetchone()
        
        if not company:
            conn.close()
            return jsonify({'success': False, 'error': '公司不存在'}), 404
        
        company_dict = dict(company)
        
        # 获取公司所有Tab定义
        c.execute('''
            SELECT tab_key, tab_label, tab_icon, sort_order, is_custom, is_system
            FROM company_tabs
            WHERE company_id = ?
            ORDER BY sort_order, id
        ''', (company_id,))
        tabs = [dict(row) for row in c.fetchall()]
        
        # 如果没有Tab，创建默认Tab
        if not tabs:
            default_tabs = [
                ('basic', '基本信息', 'Building2', 0, 0, 1),
                ('logo', 'Logo设置', 'Camera', 1, 0, 1),
                ('team', '团队成员', 'Users', 2, 0, 1),
                ('news', '公司动态', 'FileText', 3, 0, 1),
            ]
            for tab in default_tabs:
                c.execute('''
                    INSERT OR IGNORE INTO company_tabs 
                    (company_id, tab_key, tab_label, tab_icon, sort_order, is_custom, is_system)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (company_id,) + tab)
            conn.commit()
            
            # 重新获取Tabs
            c.execute('''
                SELECT tab_key, tab_label, tab_icon, sort_order, is_custom, is_system
                FROM company_tabs
                WHERE company_id = ?
                ORDER BY sort_order, id
            ''', (company_id,))
            tabs = [dict(row) for row in c.fetchall()]
        
        company_dict['tabs'] = tabs
        
        # 获取所有Tab数据
        c.execute('''
            SELECT tab_key, data_json
            FROM company_tab_data
            WHERE company_id = ?
        ''', (company_id,))
        tab_data = {row['tab_key']: json.loads(row['data_json']) for row in c.fetchall()}
        
        # 为每个Tab添加数据
        for tab in tabs:
            tab['data'] = tab_data.get(tab['tab_key'], {})
        
        conn.close()
        return jsonify({'success': True, 'company': company_dict})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_company_bp.route('/companies', methods=['POST'])
def create_company():
    """创建公司"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': '公司名称不能为空'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO companies 
            (name, short_name, description, industry, sub_industry, legal_representative,
             create_date, registered_capital, business_license, address, phone, email, 
             website, logo, employee_count, tax_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name,
            data.get('short_name', ''),
            data.get('description', ''),
            data.get('industry', ''),
            data.get('sub_industry', ''),
            data.get('legal_representative', ''),
            data.get('create_date', ''),
            data.get('registered_capital', ''),
            data.get('business_license', ''),
            data.get('address', ''),
            data.get('phone', ''),
            data.get('email', ''),
            data.get('website', ''),
            data.get('logo', ''),
            data.get('employee_count', 0),
            data.get('tax_id', '')
        ))
        
        company_id = c.lastrowid
        
        # 创建默认Tab
        default_tabs = [
            ('basic', '基本信息', 'Building2', 0, 0, 1),
            ('logo', 'Logo设置', 'Camera', 1, 0, 1),
            ('team', '团队成员', 'Users', 2, 0, 1),
            ('news', '公司动态', 'FileText', 3, 0, 1),
        ]
        for tab in default_tabs:
            c.execute('''
                INSERT INTO company_tabs 
                (company_id, tab_key, tab_label, tab_icon, sort_order, is_custom, is_system)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (company_id,) + tab)
        
        # 初始化默认Tab数据
        default_data = {
            'basic': {
                'name': name,
                'short_name': data.get('short_name', ''),
                'description': data.get('description', ''),
                'industry': data.get('industry', ''),
                'sub_industry': data.get('sub_industry', ''),
                'legal_representative': data.get('legal_representative', ''),
                'create_date': data.get('create_date', ''),
                'registered_capital': data.get('registered_capital', ''),
                'business_license': data.get('business_license', ''),
                'address': data.get('address', ''),
                'phone': data.get('phone', ''),
                'email': data.get('email', ''),
                'website': data.get('website', ''),
                'employee_count': data.get('employee_count', 0),
                'tax_id': data.get('tax_id', '')
            },
            'logo': {'logo_url': data.get('logo', '')},
            'team': {'members': []},
            'news': {'items': []}
        }
        
        for tab_key, data_json in default_data.items():
            c.execute('''
                INSERT INTO company_tab_data (company_id, tab_key, data_json)
                VALUES (?, ?, ?)
            ''', (company_id, tab_key, json.dumps(data_json)))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'company_id': company_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_company_bp.route('/companies/<int:company_id>', methods=['PUT'])
def update_company(company_id):
    """更新公司基本信息"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        # 检查公司是否存在
        c.execute('SELECT id FROM companies WHERE id = ?', (company_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '公司不存在'}), 404
        
        # 更新基本信息
        allowed_fields = ['name', 'short_name', 'description', 'industry', 'sub_industry',
                         'legal_representative', 'create_date', 'registered_capital',
                         'business_license', 'address', 'phone', 'email', 'website',
                         'logo', 'employee_count', 'tax_id']
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        
        if updates:
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
            values = list(updates.values()) + [company_id]
            
            c.execute(f'UPDATE companies SET {set_clause} WHERE id = ?', values)
            conn.commit()
        
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_company_bp.route('/companies/<int:company_id>', methods=['DELETE'])
def delete_company(company_id):
    """删除公司"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('DELETE FROM companies WHERE id = ?', (company_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# 公司 Tab API
# ============================================

@person_company_bp.route('/companies/<int:company_id>/tabs', methods=['POST'])
def add_company_tab(company_id):
    """为公司添加Tab"""
    try:
        data = request.get_json()
        tab_key = data.get('tab_key', '').strip()
        tab_label = data.get('tab_label', '').strip()
        tab_icon = data.get('tab_icon', 'Building2')
        
        if not tab_key or not tab_label:
            return jsonify({'success': False, 'error': 'Tab标识和名称不能为空'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # 检查公司是否存在
        c.execute('SELECT id FROM companies WHERE id = ?', (company_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '公司不存在'}), 404
        
        # 获取当前最大排序
        c.execute('SELECT MAX(sort_order) FROM company_tabs WHERE company_id = ?', (company_id,))
        max_order = c.fetchone()[0] or 0
        
        # 添加Tab
        c.execute('''
            INSERT OR REPLACE INTO company_tabs 
            (company_id, tab_key, tab_label, tab_icon, sort_order, is_custom, is_system)
            VALUES (?, ?, ?, ?, ?, 1, 0)
        ''', (company_id, tab_key, tab_label, tab_icon, max_order + 1))
        
        # 初始化Tab数据
        c.execute('''
            INSERT OR IGNORE INTO company_tab_data (company_id, tab_key, data_json)
            VALUES (?, ?, ?)
        ''', (company_id, tab_key, json.dumps({'items': []})))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_company_bp.route('/companies/<int:company_id>/tabs/<tab_key>', methods=['DELETE'])
def delete_company_tab(company_id, tab_key):
    """删除公司Tab"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 检查是否是系统Tab
        c.execute('''
            SELECT is_system FROM company_tabs 
            WHERE company_id = ? AND tab_key = ?
        ''', (company_id, tab_key))
        row = c.fetchone()
        
        if row and row['is_system']:
            conn.close()
            return jsonify({'success': False, 'error': '系统Tab不能删除'}), 400
        
        # 删除Tab和数据
        c.execute('''
            DELETE FROM company_tabs 
            WHERE company_id = ? AND tab_key = ?
        ''', (company_id, tab_key))
        
        c.execute('''
            DELETE FROM company_tab_data 
            WHERE company_id = ? AND tab_key = ?
        ''', (company_id, tab_key))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_company_bp.route('/companies/<int:company_id>/tabs/<tab_key>/data', methods=['PUT'])
def update_company_tab_data(company_id, tab_key):
    """更新公司Tab数据"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        # 检查Tab是否存在
        c.execute('''
            SELECT id FROM company_tabs 
            WHERE company_id = ? AND tab_key = ?
        ''', (company_id, tab_key))
        
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Tab不存在'}), 404
        
        # 更新或插入数据
        c.execute('''
            INSERT INTO company_tab_data (company_id, tab_key, data_json, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(company_id, tab_key) 
            DO UPDATE SET data_json = excluded.data_json, updated_at = CURRENT_TIMESTAMP
        ''', (company_id, tab_key, json.dumps(data)))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

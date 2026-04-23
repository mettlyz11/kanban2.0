import re

# 读取文件
with open('app.py', 'r') as f:
    content = f.read()

# 修复 /api/personal-info/people GET 接口
old_get = '''@app.route('/api/personal-info/people', methods=['GET'])
def get_people():
    """获取联系人列表（个人信息）"""
    try:
        with get_db_connection() as conn:
    
            c = conn.cursor()
    
            c.execute('''
                SELECT id, name, email, department, phone, company, created_at
                FROM contacts
                ORDER BY name ASC
            ''')'''

new_get = '''@app.route('/api/personal-info/people', methods=['GET'])
def get_people():
    """获取联系人列表（个人信息）"""
    try:
        with get_db_connection() as conn:
    
            c = conn.cursor()
    
            c.execute('''
                SELECT id, name, email, title as department, phone, location as company, created_at
                FROM persons
                ORDER BY name ASC
            ''')'''

content = content.replace(old_get, new_get)

# 修复 /api/personal-info/people/<int:person_id> GET 接口
old_detail = '''@app.route('/api/personal-info/people/<int:person_id>', methods=['GET'])
def get_person(person_id):
    """获取单个联系人详情"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # 获取基本信息
            c.execute('''
                SELECT id, name, email, department, phone, company, created_at
                FROM contacts WHERE id = ?
            ''', (person_id,))'''

new_detail = '''@app.route('/api/personal-info/people/<int:person_id>', methods=['GET'])
def get_person(person_id):
    """获取单个联系人详情"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # 获取基本信息
            c.execute('''
                SELECT id, name, email, title as department, phone, location as company, created_at
                FROM persons WHERE id = ?
            ''', (person_id,))'''

content = content.replace(old_detail, new_detail)

# 保存文件
with open('app.py', 'w') as f:
    f.write(content)

print("API 修复完成")

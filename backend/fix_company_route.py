#!/usr/bin/env python3

# 读取app.py
with open('/opt/kanban-react/backend/app.py', 'r') as f:
    content = f.read()

# 找到旧函数
old_start = '@app.route(\'/api/company-info/companies/<company_id>\', methods=[\'GET\'])'
old_content = old_start + '''
def get_company_detail(company_id):
    """获取公司详情"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM company_info WHERE id = %s
        ''', (company_id,))
        company = c.fetchone()
        conn.close()
    
        if company:
            return jsonify({'success': True, 'company': dict(company)})
        else:
            return jsonify({'success': False, 'error': 'Company not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})'''

# 新函数内容
new_content = '''@app.route('/api/company-info/companies/<company_id>', methods=['GET'])
def get_company_detail(company_id):
    """获取公司详情"""
    try:
        # 尝试转换为整数（数字ID），如果失败则按slug/名称查找
        conn = get_db()
        c = conn.cursor()
        
        # 先尝试数字ID
        try:
            company_id_int = int(company_id)
            c.execute('''
                SELECT * FROM company_info WHERE id = %s
            ''', (company_id_int,))
        except ValueError:
            # 转换失败，按短名称搜索
            c.execute('''
                SELECT * FROM company_info WHERE short_name = %s OR name LIKE %s
            ''', (company_id, f'%{company_id}%'))
        
        company = c.fetchone()
        conn.close()
    
        if company:
            # 将元组转换为字典
            column_names = [desc[0] for desc in c.description]
            company_dict = dict(zip(column_names, company))
            return jsonify({'success': True, 'company': company_dict})
        else:
            return jsonify({'success': False, 'error': 'Company not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})'''

# 替换
import re
pattern = re.escape(old_content.replace("'''", "'''").strip())
new_content = new_content.strip()

# 更简单的方法：按行替换，找到起始行并替换
lines = content.splitlines()
# 查找函数开始行
start_line = None
for i, line in enumerate(lines):
    if '@app.route' in line and '/api/company-info/companies' in line:
        start_line = i
        break

if start_line is not None:
    # 删除从start_line开始的旧函数（大约20行）
    new_lines = lines[:start_line] + new_content.splitlines() + lines[start_line + 20:]
    new_content = '\n'.join(new_lines)
    
    # 写回文件
    with open('/opt/kanban-react/backend/app.py', 'w') as f:
        f.write(new_content)
    print("✓ 修复成功")
else:
    print("✗ 找不到函数位置")

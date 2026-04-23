@app.route('/api/company-info/companies/<company_id>', methods=['GET'])
def get_company_detail(company_id):
    获取公司详情
    try:
        # 尝试转换为整数（数字ID），如果失败则按slug查找
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
        return jsonify({'success': False, 'error': str(e)})

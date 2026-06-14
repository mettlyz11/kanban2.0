"""Routes: company_api - company_api"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import hashlib
import os
import json
from datetime import datetime

bp = Blueprint("routes_company_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/company-info/companies', methods=['GET'])
def get_companies():
    """获取公司列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, name, short_name, legal_representative, industry, 
                   create_date, address, phone, email, website, description, last_updated
            FROM company_info
            ORDER BY name
        ''')
        companies = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'companies': companies})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/company-info/companies/<company_id>', methods=['GET'])
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
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/personal-info/people', methods=['GET'])
def get_people():
    """获取联系人列表（个人信息），包含每个人的详细信息"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # 获取所有联系人基本信息
            c.execute('SELECT id, name, email, title as department, phone, location as company, created_at FROM persons ORDER BY name ASC')
            
            people = []
            for row in c.fetchall():
                person_id = row['id']
                
                # 获取该联系人的标签页信息
                c.execute('SELECT id, name, type, sort_order FROM person_tabs WHERE person_id = %s ORDER BY sort_order', (person_id,))
                tabs = c.fetchall()
                
                tabs_data = []
                for tab in tabs:
                    # 获取标签页内容
                    c.execute('SELECT title, content, item_date, sort_order, attachments FROM person_tab_items WHERE tab_id = %s ORDER BY sort_order', (tab['id'],))
                    items = c.fetchall()
                    
                    items_data = []
                    for item in items:
                        items_data.append({'title': item['title'], 'content': item['content'], 'item_date': item['item_date'], 'attachments': item['attachments']})
                    
                    tabs_data.append({'id': tab['id'], 'name': tab['name'], 'type': tab['type'], 'items': items_data})
                
                people.append({
                    'id': person_id,
                    'name': row['name'],
                    'email': row['email'],
                    'department': row['department'],
                    'phone': row['phone'],
                    'company': row['company'],
                    'created_at': row['created_at'],
                    'tabs': tabs_data
                })
        
        return jsonify({'success': True, 'people': people, 'count': len(people)})
    except Exception as e:
        logger.error(f"获取联系人列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/personal-info/people/<int:person_id>', methods=['GET'])
def get_person(person_id):
    """获取单个联系人详情 - 从 person_tabs 读取"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 获取用户基本信息（从 persons 表）
        c.execute('SELECT id, name, email, phone, title, location FROM persons WHERE id = %s', (person_id,))
        user = c.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'error': '联系人不存在'}), 404
        
        # 获取标签页
        c.execute('SELECT id, name, type, sort_order FROM person_tabs WHERE person_id = %s ORDER BY sort_order', (person_id,))
        tabs = c.fetchall()
        
        tabs_data = []
        for tab in tabs:
            # 获取标签页内容
            c.execute('SELECT title, content, item_date, sort_order, attachments FROM person_tab_items WHERE tab_id = %s ORDER BY sort_order', (tab['id'],))
            items = c.fetchall()
            
            items_data = []
            for item in items:
                # 解析 attachments JSON
                attachments = item['attachments']
                if attachments:
                    try:
                        attachments = json.loads(attachments)
                    except:
                        attachments = None
                items_data.append({
                    'title': item['title'],
                    'content': item['content'],
                    'item_date': item['item_date'],
                    'attachments': attachments
                })
            
            tabs_data.append({
                'id': tab['id'],
                'name': tab['name'],
                'type': tab['type'],
                'items': items_data
            })
        
        conn.close()
        
        person = {
            'id': user['id'],
            'name': user['name'],
            'email': user.get('email', ''),
            'phone': user.get('phone', ''),
            'department': user.get('title', ''),
            'company': user.get('location', ''),
            'tabs': tabs_data
        }
        
        return jsonify({'success': True, 'person': person})
    except Exception as e:
        logger.error(f"获取联系人详情失败: {e}")
        return jsonify({'success': False, 'error': str(e)})
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/personal-info/people', methods=['POST'])
def create_person():
    """创建新联系人"""
    try:
        data = request.get_json()
    
        name = data.get('name')
        email = data.get('email')
        department = data.get('department')
        phone = data.get('phone')
        company = data.get('company')
    
        if not name:
            return jsonify({'success': False, 'error': '姓名不能为空'}), 400
    
        with get_db_connection() as conn:
            c = conn.cursor()
    
            c.execute('''
                INSERT INTO contacts (name, email, department, phone, company)
                VALUES (%s, %s, %s, %s, %s)
            ''', (name, email, department, phone, company))
    
            person_id = c.lastrowid
            conn.commit()
    
        return jsonify({
            'success': True,
            'message': '联系人创建成功',
            'id': person_id
        })
    except Exception as e:
        logger.error(f"创建联系人失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/personal-info/people/<int:person_id>', methods=['PUT'])
def update_person(person_id):
    """更新联系人信息"""
    try:
        data = request.get_json()
    
        with get_db_connection() as conn:
            c = conn.cursor()
    
            # 检查联系人是否存在
            c.execute('SELECT id FROM persons WHERE id = %s', (person_id,))
            if not c.fetchone():
                conn.close()
                return jsonify({'success': False, 'error': '联系人不存在'}), 404
    
            # 构建更新语句
            update_fields = []
            values = []
    
            if 'name' in data:
                update_fields.append('name = %s')
                values.append(data['name'])
            if 'email' in data:
                update_fields.append('email = %s')
                values.append(data['email'])
            if 'department' in data:
                update_fields.append('department = %s')
                values.append(data['department'])
            if 'phone' in data:
                update_fields.append('phone = %s')
                values.append(data['phone'])
            if 'company' in data:
                update_fields.append('company = %s')
                values.append(data['company'])
    
            if update_fields:
                values.append(person_id)
                sql = f"UPDATE contacts SET {', '.join(update_fields)} WHERE id = %s"
                c.execute(sql, values)
                conn.commit()
    
    
        return jsonify({'success': True, 'message': '联系人更新成功'})
    except Exception as e:
        logger.error(f"更新联系人失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/personal-info/people/<int:person_id>', methods=['DELETE'])
def delete_person(person_id):
    """删除联系人"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
    
            c.execute('DELETE FROM persons WHERE id = %s', (person_id,))
    
            if c.rowcount == 0:
                conn.close()
                return jsonify({'success': False, 'error': '联系人不存在'}), 404
    
            conn.commit()
    
        return jsonify({'success': True, 'message': '联系人删除成功'})
    except Exception as e:
        logger.error(f"删除联系人失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/personal-info/liuyuzhou', methods=['GET'])
def get_liuyuzhou_info():
    """获取刘宇宙详细信息（包含合规声明）"""
    try:
        detail = {
            "id": "liuyuzhou",
            "name": "刘宇宙",
            "birthDate": "1982-09-16",
            "gender": "男",
            "currentPosition": "蓝天青年学者（二级）",
            "department": "北京航空航天大学 化学学院",
            "contact": {
                "phone": "+86-10-xxxxxxxx",
                "email": "liuyuzhou@buaa.edu.cn"
            },
            "education": [
                {
                    "school": "纽约大学化学系",
                    "degree": "博士",
                    "major": "氢键在晶体工程里的应用",
                    "year": "2011",
                    "advisor": "Michael Ward 教授"
                },
                {
                    "school": "清华大学化学系",
                    "degree": "硕士",
                    "major": "Mo(CO)6催化的炔烃合成苯环的反应",
                    "year": "2006",
                    "advisor": "席婵娟 教授"
                },
                {
                    "school": "清华大学化学系",
                    "degree": "学士",
                    "major": "化学",
                    "year": "2003"
                }
            ],
            "researchAreas": [
                "计算化学",
                "分子模拟",
                "AI驱动的化学研究"
            ],
            "contract": {
                "contractNo": "09855-01-2025-1",
                "position": "蓝天青年学者（二级）",
                "positionType": "专任教师岗位 - 蓝天学者岗位",
                "department": "化学学院",
                "startDate": "2025-09-01",
                "endDate": "2030-08-31",
                "duration": "5年",
                "requirements": [
                    "每学年主讲不少于1门课程，年均教学工作量不少于64学时",
                    "聘期内完成不少于1项亮点业绩Ⅰ类或2项亮点业绩Ⅱ类",
                    "年均科研经费不低于30万元（理科）",
                    "聘期内引育不少于1名国家级人才"
                ],
                "fileName": "09855_刘宇宙_化学学院_聘用合同-蓝天青年学者（二级）.pdf"
            },
            "entrepreneurship": {
                "company": "北京和光智成科技有限公司（Helight）",
                "position": "创始人、CEO",
                "founded": "2023",
                "description": "专注于AI驱动的材料研发平台，利用人工智能加速新材料发现。前身为北京深云智合科技有限公司（正在退出）",
                "focus": [
                    "AI材料研发平台",
                    "材料数据基础设施建设",
                    "智能材料发现与优化"
                ]
            },
            "publicSpeaking": [
                {
                    "id": "speaking-001",
                    "title": "AI最核心的作用，是找到人原来找不到的路径",
                    "event": "新材料×AI: 范式之变",
                    "organizer": "中经传媒智库 x 《商学院》杂志",
                    "date": "2025-01-21",
                    "content": "在由中经传媒智库与《商学院》杂志联合举办的'新材料×AI: 范式之变'高端闭门会上，北京和光智成科技有限公司（前身为北京深云智合科技有限公司）创始人、CEO刘宇宙分享了关于AI在新材料研发中核心作用的观点。",
                    "keyPoints": [
                        "AI最核心的作用，是找到人原来找不到的路径",
                        "如果一个东西本身没有数据沉淀，AI是起不到作用的",
                        "要加速材料的发现和探索，建立模型的核心是标准化、高质量的数据",
                        "只有打好数据底座，AI才能在面对复杂规律时，帮你建立起原来发现不了的逻辑",
                        "这就是AI对研发提质增效的真正价值"
                    ],
                    "source": "《商学院》杂志官方微博"
                }
            ],
            "compliance": {
                "title": "关于涉诉事项的情况说明",
                "summary": "针对近期北京深云相关涉诉事宜及和光智成的成立背景，为消除信息不对称，确保投资人客观研判事件本质，切实规避潜在风险，现就事件真相、责任切割及项目价值作如下专项说明。",
                "keyPoints": [
                    {
                        "title": "核心结论：责任完全隔离，创业合法合规",
                        "items": [
                            "主体无关：本次诉讼系北京深云原合作方与地方利益方策划的针对性排挤事件。刘宇宙教授及配偶杨慧娟女士非案涉合同主体，无任何法律关联，不承担连带责任。",
                            "权属清晰：和光智成是刘宇宙教授为保护核心技术不被侵占而合法重启的载体，技术来源清晰，无侵权风险。",
                            "性质定性：该诉讼本质是违背《民法典》契约精神的滥用司法资源行为，不仅缺乏事实支撑，更与国家保护科研人员创新积极性的导向背道而驰。"
                        ]
                    },
                    {
                        "title": "商业逻辑：从\"被迫出走\"到\"初心坚守\"",
                        "items": [
                            "事实还原：刘宇宙教授作为北京深云的核心技术源头与产业化推手，全程主导了技术研发与落地。然而，原合作方出于独占商业利益的私心，通过不正当手段将刘教授排挤出决策层，企图无偿侵占其科研成果。",
                            "创业正当性：和光智成的成立，并非恶性竞争，而是科学家为避免国家培育的核心技术被闲置或侵吞，被迫进行的\"自救式创业\"。",
                            "合规背书：此举完全符合《促进科技成果转化法》精神，是守护科研初心、延续技术价值的合法行为。所有股权架构与技术流转均有完整法律文件佐证，经得起最严格的尽职调查（DD）。"
                        ]
                    },
                    {
                        "title": "法律风险：诉讼主体错位，责任边界明确",
                        "items": [
                            "主体不适格（关键抗辩点）：案涉合同签署方仅为法人实体（北京深云及其合作方）。刘宇宙教授及其配偶均为自然人，既非合同当事人，也未签署任何担保文件。",
                            "法律依据：根据《中华人民共和国民法典》第四百六十五条及相关司法解释，合同仅对当事人具有法律约束力。起诉非协议主体的自然人属于根本性法律错误，诉由完全不成立。",
                            "程序违规警示：2025年4月8日，九原区相关方在无正当诉由情况下，对刘教授全家采取全额冻结账户等过度强制措施，属于典型的选择性执法与过度施压。"
                        ]
                    },
                    {
                        "title": "国家战略：顺应科创导向，抵制不当干预",
                        "items": [
                            "政策对标：国家明确要求保护科研人员合法权益，激发创新活力。恶意排挤科学家、通过司法手段打压技术带头人，严重破坏科创生态。",
                            "价值主张：和光智成的存在，正是为了纠正这种扭曲的商业环境，确保核心技术掌握在真正的创造者手中。投资和支持和光智成，是响应国家号召、保护战略科技力量的正确选择。"
                        ]
                    }
                ],
                "commitments": [
                    "风险隔离承诺：北京深云涉诉事宜产生的任何法律责任，均由原相关方承担。",
                    "合规经营承诺：公司核心技术独立，股权结构清晰，无任何隐性债务或违规关联交易。",
                    "全面配合核查：已建立专项档案库，包含刘教授退出深云的法律效力文件、诉讼全套材料、科研工作实证及技术权属证明。随时欢迎并配合进行全方位、穿透式的尽职调查。"
                ],
                "updateDate": "2026-03-06",
                "documentUrl": "/files/涉诉事项的情况说明.docx"
            }
        }
    
        return jsonify({
            'success': True,
            'detail': detail
        })
    except Exception as e:
        logger.error(f"获取刘宇宙信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/personal-info/xiaboshi', methods=['GET'])
def get_xiaboshi_info():
    """获取夏博士详细信息"""
    try:
        detail = {
            "id": "xiaboshi",
            "name": "夏博士（工信部）",
            "birthDate": "",
            "gender": "",
            "currentPosition": "处长",
            "department": "工业和信息化部 一处",
            "contact": {
                "phone": "",
                "email": ""
            },
            "education": [],
            "researchAreas": [
                "产业政策制定",
                "行业发展规划",
                "信息化发展"
            ],
            "contract": {
                "contractNo": "",
                "position": "处长",
                "positionType": "公务员",
                "department": "工业和信息化部 一处",
                "startDate": "",
                "endDate": "",
                "duration": "",
                "requirements": [],
                "fileName": ""
            }
        }
    
        return jsonify({
            'success': True,
            'detail': detail
        })
    except Exception as e:
        logger.error(f"获取夏博士信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/personal-info/duanboshi', methods=['GET'])
def get_duanboshi_info():
    """获取段博士详细信息"""
    try:
        detail = {
            "id": "duanboshi",
            "name": "段博士（信通院）",
            "birthDate": "",
            "gender": "",
            "currentPosition": "研究员",
            "department": "中国信息通信研究院",
            "contact": {
                "phone": "",
                "email": ""
            },
            "education": [],
            "researchAreas": [
                "信息通信研究",
                "行业政策研究",
                "标准制定"
            ],
            "contract": {
                "contractNo": "",
                "position": "研究员",
                "positionType": "科研岗位",
                "department": "中国信息通信研究院",
                "startDate": "",
                "endDate": "",
                "duration": "",
                "requirements": [],
                "fileName": ""
            }
        }
    
        return jsonify({
            'success': True,
            'detail': detail
        })
    except Exception as e:
        logger.error(f"获取段博士信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/company-info/companies/<company_id>', methods=['GET'])
def get_company_info(company_id):
    """获取公司详细信息（包含法律合规信息）"""
    try:
        # 根据company_id返回不同公司信息
        if company_id == '1284':
            detail = {
                "id": "1284",
                "fullName": "北京深云智合科技有限公司",
                "englishName": "DeepCloud Intelligence Technology Co., Ltd.",
                "creditCode": "91110108MA01xxxxx",
                "address": "北京市海淀区xxxx",
                "createDate": "2020-01-15",
                "registeredCapital": "1000万元",
                "legalRepresentative": "刘宇宙",
                "companyType": "有限责任公司",
                "businessScope": [
                    "技术开发、技术咨询、技术服务",
                    "人工智能应用软件开发",
                    "化学计算与模拟服务",
                    "数据处理和存储服务"
                ],
                "mainBusiness": [
                    "T109过渡态计算平台",
                    "Pepi数字员工系统",
                    "AI驱动的科研解决方案"
                ],
                "team": [
                    {
                        "name": "刘宇宙",
                        "position": "创始人/首席科学家",
                        "background": "北京大学博士，蓝天青年学者"
                    }
                ],
                "partners": [
                    "北京航空航天大学",
                    "中国科学院"
                ],
                "legalStatus": "涉诉中",
                "legalNote": "原合作方与地方利益方策划的针对性排挤事件，刘宇宙教授已退出并创立和光智成"
            }
        elif company_id == '1283' or company_id == 'helight':
            detail = {
                "id": company_id,
                "fullName": "北京和光智成科技有限公司",
                "englishName": "Helight Intelligence Technology Co., Ltd.",
                "creditCode": "91110108MA01xxxxx",
                "address": "北京市海淀区xxxx",
                "createDate": "2023",
                "registeredCapital": "1000万元",
                "legalRepresentative": "刘宇宙",
                "companyType": "有限责任公司",
                "businessScope": [
                    "技术开发、技术咨询、技术服务",
                    "人工智能应用软件开发",
                    "化学计算与模拟服务",
                    "数据处理和存储服务"
                ],
                "mainBusiness": [
                    "T109过渡态计算平台",
                    "Pepi数字员工系统",
                    "AI驱动的科研解决方案"
                ],
                "team": [
                    {
                        "name": "刘宇宙",
                        "position": "创始人/首席科学家",
                        "background": "北京大学博士，蓝天青年学者"
                    }
                ],
                "partners": [
                    "北京航空航天大学",
                    "中国科学院"
                ],
                "legalStatus": "合规运营",
                "legalNote": "为保护核心技术不被侵占而合法重启的载体，技术来源清晰，无侵权风险",
                "compliance": {
                    "riskIsolation": "北京深云涉诉事宜产生的任何法律责任，均由原相关方承担",
                    "coreTech": "公司核心技术独立，股权结构清晰，无任何隐性债务或违规关联交易",
                    "dueDiligence": "已建立专项档案库，随时欢迎并配合进行全方位、穿透式的尽职调查"
                }
            }
        else:
            detail = {
                "id": company_id,
                "fullName": "和光智成（北京）科技有限公司",
                "englishName": "Helight Intelligence Technology Co., Ltd.",
                "creditCode": "91110108MA01xxxxx",
                "address": "北京市海淀区xxxx",
                "createDate": "2020-01-15",
                "registeredCapital": "1000万元",
                "legalRepresentative": "刘宇宙",
                "companyType": "有限责任公司",
                "businessScope": [
                    "技术开发、技术咨询、技术服务",
                    "人工智能应用软件开发",
                    "化学计算与模拟服务",
                    "数据处理和存储服务"
                ],
                "mainBusiness": [
                    "T109过渡态计算平台",
                    "Pepi数字员工系统",
                    "AI驱动的科研解决方案"
                ],
                "team": [
                    {
                        "name": "刘宇宙",
                        "position": "创始人/首席科学家",
                        "background": "北京大学博士，蓝天青年学者"
                    }
                ],
                "partners": [
                    "北京航空航天大学",
                    "中国科学院"
                ]
            }
    
        return jsonify({
            'success': True,
            'detail': detail
        })
    except Exception as e:
        logger.error(f"获取公司信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



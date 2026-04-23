def get_db():
    """获取 MySQL 数据库连接"""
    config = MYSQL_CONFIG.copy()
    config['password'] = os.environ.get('MYSQL_PASSWORD', '')
    conn = pymysql.connect(**config)
    return conn

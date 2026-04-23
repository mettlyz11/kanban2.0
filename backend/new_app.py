def get_db():
    """获取 MySQL 数据库连接"""
    # 从环境变量获取完整配置，确保密码正确传递
    config = {
        "host": os.environ.get("MYSQL_HOST", "rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "kanban"),
        "password": os.environ.get("MYSQL_PASSWORD", "Irc210Irc210!"),
        "database": os.environ.get("MYSQL_DATABASE", "kanban"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
    }
    conn = pymysql.connect(**config)
    return conn


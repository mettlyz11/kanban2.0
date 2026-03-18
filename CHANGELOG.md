
## v2.5.1 - 2026-03-16

### 修复
- 修复登录 500 错误（systemd 服务未加载环境变量）
- 修复 App.tsx 语法错误（重复路由和缺失闭合标签）
- 重新构建前端并部署

### 技术细节
- 修改 systemd 服务配置使用 start_gunicorn.sh 脚本
- 确保 Gunicorn 正确加载 .env 中的 MySQL 配置
- 修复前端路由定义中的重复和语法问题

## v2.5.2 - 2026-03-17

### 修复
- 修复MySQL/RDS数据库兼容性问题
- 添加ConnectionWrapper和CursorWrapper处理SQLite和MySQL的SQL语法差异
- 修复get_db函数以支持MySQL连接
- 替换dict(row)为row_to_dict(row, c)以兼容MySQL元组返回
- 修复/api/goals中的sqlite_master查询，使用table_exists函数
- 修复所有API端点的数据库连接问题

### 技术细节
- 在database_config.py中添加兼容层
- 自动转换SQL占位符为MySQL格式
- 保持SQLite和MySQL双模式支持
- 后端API现在可以正常从RDS MySQL数据库读取数据


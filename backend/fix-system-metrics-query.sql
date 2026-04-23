# 修复MySQL查询语法
# 原来的: WHERE timestamp >= (strftime('%s', {time_condition}))
# 改成: WHERE timestamp >= {time_condition} (因为timestamp已经是datetime类型)

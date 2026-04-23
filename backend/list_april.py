import pymysql
conn = pymysql.connect(
    host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    user='kanban',
    password='Irc210Irc210!',
    database='kanban',
    port=3306,
    charset='utf8mb4'
)
c = conn.cursor()
c.execute('SELECT id, title, start_time FROM calendar_events WHERE start_time >= "2026-04-01" AND start_time <= "2026-04-30" ORDER BY start_time')
rows = c.fetchall()
print(f'4月份共有 {len(rows)} 条日程记录:')
for row in rows:
    print(f'  {row[2]} - {row[1]}')
conn.close()

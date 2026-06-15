from routes.helpers import get_db
conn = get_db()
cur = conn.cursor()

tables = ['llm_call_logs', 'llm_call_log', 'llm_scenarios', 'llm_configs']
for t in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        cnt = cur.fetchone()
        cur.execute(f'SELECT * FROM {t} LIMIT 2')
        cols = [d[0] for d in cur.description]
        # print(f'{t}: {cnt} rows, cols={cols}')
    except Exception as e:
        # print(f'{t} error: {e}')

conn.close()

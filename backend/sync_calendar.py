import pymysql
import sys
sys.path.insert(0, '/opt/kanban-react/backend')
from caldav_sync import sync_all_accounts
print('正在执行CalDAV同步...')
results = sync_all_accounts(None)
print(f'同步完成: {results}')

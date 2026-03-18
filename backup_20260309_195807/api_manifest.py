#!/usr/bin/env python3
APIS = {
    '/api/company-info/companies': {
        'methods': ['GET'],
        'required_tables': ['entities'],
        'test_query': "SELECT COUNT(*) FROM entities WHERE entity_type='company'",
        'min_expected_records': 2
    },
    '/api/meetings': {
        'methods': ['GET', 'POST'],
        'required_tables': ['meetings'],
        'required_columns': ['id', 'title', 'date', 'location']
    },
    '/api/health/records': {
        'methods': ['GET'],
        'required_tables': ['health_records']
    },
    '/api/architecture/workflow': {
        'methods': ['GET']
    }
}

if __name__ == '__main__':
    import sqlite3
    conn = sqlite3.connect('kanban_v5.db')
    cursor = conn.cursor()
    
    print('API清单验证:')
    for path, config in APIS.items():
        errors = []
        if 'required_tables' in config:
            for table in config['required_tables']:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cursor.fetchone():
                    errors.append(f'Table {table} not found')
        
        if errors:
            print(f'  ❌ {path}: {errors}')
        else:
            print(f'  ✅ {path}')
    
    conn.close()

-- 日历事件表
CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    all_day BOOLEAN DEFAULT 0,
    location TEXT,
    category TEXT DEFAULT 'default',
    color TEXT,
    recurrence TEXT,  -- RRULE format for recurring events
    recurrence_end DATETIME,
    is_recurring BOOLEAN DEFAULT 0,
    parent_event_id INTEGER,
    project_id INTEGER,
    task_id INTEGER,
    entity_id INTEGER,
    external_id TEXT,  -- for CalDAV sync
    external_source TEXT,  -- 'caldav', 'google', 'outlook'
    sync_status TEXT DEFAULT 'local',  -- 'local', 'synced', 'pending', 'conflict'
    last_sync_at DATETIME,
    reminder_minutes INTEGER DEFAULT 15,
    status TEXT DEFAULT 'confirmed',  -- 'confirmed', 'tentative', 'cancelled'
    priority INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);

-- 日历账户表 (用于CalDAV同步)
CREATE TABLE IF NOT EXISTS calendar_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    account_type TEXT NOT NULL,  -- 'caldav', 'google', 'outlook'
    server_url TEXT,
    username TEXT,
    password TEXT,  -- encrypted
    calendar_path TEXT,
    calendar_name TEXT,
    sync_enabled BOOLEAN DEFAULT 1,
    last_sync_at DATETIME,
    sync_interval INTEGER DEFAULT 300,  -- seconds
    color TEXT,
    is_default BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 日历同步日志
CREATE TABLE IF NOT EXISTS calendar_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    event_id INTEGER,
    action TEXT,  -- 'create', 'update', 'delete', 'sync'
    status TEXT,  -- 'success', 'failed'
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES calendar_accounts(id),
    FOREIGN KEY (event_id) REFERENCES calendar_events(id)
);

-- 事件参与者表
CREATE TABLE IF NOT EXISTS calendar_attendees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    entity_id INTEGER,
    email TEXT,
    name TEXT,
    status TEXT DEFAULT 'needs-action',  -- 'accepted', 'declined', 'tentative', 'needs-action'
    is_organizer BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES calendar_events(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_calendar_events_start ON calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_end ON calendar_events(end_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_project ON calendar_events(project_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_task ON calendar_events(task_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_external ON calendar_events(external_id);

-- 项目文档管理表
-- 创建时间: 2026-03-10
-- 用途: 存储项目相关文档的元数据和文件路径

-- 创建项目文档表
CREATE TABLE IF NOT EXISTS project_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    original_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    mime_type TEXT,
    description TEXT,
    uploaded_by TEXT DEFAULT 'system',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 创建索引以提高查询性能
-- 按项目ID查询的索引
CREATE INDEX IF NOT EXISTS idx_project_docs_project_id ON project_documents(project_id);

-- 按文件名查询的索引
CREATE INDEX IF NOT EXISTS idx_project_docs_file_name ON project_documents(file_name);

-- 按上传时间查询的索引
CREATE INDEX IF NOT EXISTS idx_project_docs_uploaded_at ON project_documents(uploaded_at);

-- 创建复合索引：项目ID + 上传时间（常用查询）
CREATE INDEX IF NOT EXISTS idx_project_docs_project_time ON project_documents(project_id, uploaded_at DESC);

-- 添加表注释（SQLite 不支持 COMMENT，使用备注说明）
-- 表说明: 存储项目关联的文档文件元数据
-- 字段说明:
--   id: 文档唯一标识
--   project_id: 关联的项目ID
--   file_name: 存储的文件名（通常包含随机前缀以避免冲突）
--   original_name: 原始文件名
--   file_path: 文件存储的相对路径
--   file_size: 文件大小（字节）
--   mime_type: MIME类型
--   description: 文档描述
--   uploaded_by: 上传者
--   uploaded_at: 上传时间
--   updated_at: 更新时间

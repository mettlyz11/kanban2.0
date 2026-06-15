# lessons_table_best_practices

> 任务: v11 #17 任务经验库 — lessons 表沉淀最佳实践
> 附件类型: 最佳实践文档
> 生成时间: 2026-05-12 08:40

# v11 #17 任务经验库 — lessons 表沉淀最佳实践

## 1. 背景与目标

### 1.1 背景
在V11版本的任务经验库体系中，`lessons` 表作为核心数据载体，用于存储从历史项目、日常运维、SDS系统（Supply-Demand-Scheduling）以及外部知识源中提取的“经验教训”。这些经验包括但不限于：任务调度中的瓶颈发现、资源冲突解决方案、异常处理模式、优化建议等。当前各团队的经验分散在Jira、Confluence、邮件、工单系统中，缺乏统一的结构化存储与查询能力。

### 1.2 目标
- **统一沉淀**：将碎片化的经验教训集中到`lessons`表中，形成可复用的知识资产。
- **高效检索**：支持按照任务ID、类型、时间、标签等维度快速定位相关经验。
- **自动填充**：建立从原始数据源到lessons表的自动化清洗、去重、校验流程，降低人工维护成本。
- **持续迭代**：提供增量更新机制和过期清理策略，确保数据活性与准确性。

## 2. 表结构设计

### 2.1 字段定义

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|----------|------|------|
| `id` | BIGINT UNSIGNED | PRIMARY KEY, AUTO_INCREMENT | 自增主键 |
| `task_id` | VARCHAR(64) | NOT NULL, INDEX | 关联的任务ID，如“SDS-2025-001” |
| `lesson_type` | ENUM('optimization','bottleneck','workaround','alert','generic') | NOT NULL | 经验类型，由系统自动分类 |
| `content` | TEXT | NOT NULL | 经验正文，支持Markdown格式，最多5000字符 |
| `source_system` | VARCHAR(32) | NOT NULL | 来源系统，如“SDS”、“Jira”、“Confluence”、“Manual” |
| `source_uri` | VARCHAR(256) | DEFAULT NULL | 来源记录链接（如Jira issue URL） |
| `tags` | JSON | DEFAULT NULL | 标签数组，如["调度","资源","数据库"] |
| `severity` | TINYINT UNSIGNED | DEFAULT 3, CHECK(1-5) | 严重程度：1最高，5最低 |
| `status` | ENUM('draft','valid','deprecated','archived') | DEFAULT 'draft' | 状态，可经人工审核后变为valid |
| `created_by` | VARCHAR(64) | NOT NULL | 创建者（系统或用户名） |
| `created_at` | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 最后更新时间 |
| `version` | INT UNSIGNED | DEFAULT 1 | 版本号，每次编辑递增 |
| `checksum` | CHAR(64) | NOT NULL, UNIQUE | SHA256(content+task_id)，用于去重 |

### 2.2 索引建议
```sql
-- 核心索引
CREATE INDEX idx_task_id ON lessons(task_id);
CREATE INDEX idx_lesson_type ON lessons(lesson_type);
CREATE INDEX idx_created_at ON lessons(created_at);
-- 复合索引：按类型+时间查询
CREATE INDEX idx_type_created ON lessons(lesson_type, created_at);
-- 全文索引（MySQL 5.7+ InnoDB）
ALTER TABLE lessons ADD FULLTEXT INDEX ft_content_tags (content, tags);
```

### 2.3 分区策略（可选）
建议按月分区，按`created_at`分区。示例：
```sql
ALTER TABLE lessons
PARTITION BY RANGE (TO_DAYS(created_at)) (
    PARTITION p202501 VALUES LESS THAN (TO_DAYS('2025-02-01')),
    PARTITION p202502 VALUES LESS THAN (TO_DAYS('2025-03-01')),
    ...
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

## 3. 数据来源与提取规则

### 3.1 主要数据源

| 源系统 | 提取方式 | 频率 | 保留规则 |
|--------|----------|------|----------|
| SDS系统（调度数据库） | 通过API或ETL（Kafka）实时流读取任务状态变更日志 | 每分钟批量 | 仅保留变更涉及的、与经验相关的记录 |
| Jira（项目工单） | 通过Jira REST API定时抓取状态为Resolved或Closed的Bug/Story，解析备注和描述 | 每天凌晨2点 | 根据predefined关键词（如“教训”、“经验”、“优化”、“workaround”）过滤 |
| Confluence（知识库） | 通过Confluence REST API按空间/标签抓取页面，提取宏或标签含“lesson”的内容 | 每周日 | 判断是否已存在相同文本（通过checksum） |
| 手动录入（CSV） | 用户上传 | 按需 | 立刻进入清洗流程 |

### 3.2 提取规则示例
- **SDS系统**：当任务状态变为“FAILED”且错误类型为“RESOURCE_CONTENTION”时，自动生成一条`lesson_type='bottleneck'`的记录，content为系统自动拼接的错误日志摘要（限前300字符）。
- **Jira**：从工单的自定义字段“Lessons Learned”中抽取，若为空则从备注中提取有“Workaround: ”前缀的文字段。
- **Confluence**：仅处理页面标题包含“Lesson”或“经验教训”的页面，取页面正文前1000字符。
- **去重规则**：对所有源，计算`content + task_id`的SHA256值作为checksum，检查是否已存在。若存在且status为'valid'或'deprecated'则跳过；若为'draft'则覆盖。

## 4. 数据填充流程

### 4.1 自动化管道（使用Python + Airflow DAG示例）
```python
# airflow/dags/lessons_etl.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import hashlib
import json
import requests

default_args = {
    'owner': 'data_team',
    'retries': 3,
    'retry_delay': timedelta(minutes=5)
}

def extract_sds():
    # 伪代码：从SDS API获取最近1小时失败任务
    response = requests.get('http://sds-api/tasks?status=failed&since='+str(datetime.utcnow()-timedelta(hours=1)))
    records = []
    for item in response.json():
        records.append({
            'task_id': item['task_id'],
            'content': f"Bottleneck: {item['error_summary'][:300]}",
            'lesson_type': 'bottleneck',
            'source_system': 'SDS',
            'source_uri': item['task_url'],
            'severity': 3,
            'created_by': 'sds_etl'
        })
    return records

def extract_jira():
    # JQL: project = SDS AND resolution = Fixed AND updated >= start_date
    # 省略具体实现
    pass

def clean_and_deduplicate(records):
    cleaned = []
    for rec in records:
        # 清除非ASCII字符（保留中文）
        rec['content'] = rec['content'].encode('ascii', 'ignore').decode('ascii') if False else rec['content']
        # 去除多余空格
        rec['content'] = ' '.join(rec['content'].split())
        # 计算checksum
        raw = (rec['content'] + rec['task_id']).encode('utf-8')
        rec['checksum'] = hashlib.sha256(raw).hexdigest()
        # 去重：查询数据库是否已存在（由后续load处理）
        cleaned.append(rec)
    return cleaned

def validate(records):
    # 校验：content不可为空，severity在1-5，lesson_type为枚举值
    valid = []
    for rec in records:
        if not rec['content'] or rec['content'] == '':
            continue
        if rec['severity'] < 1 or rec['severity'] > 5:
            rec['severity'] = 3
        if rec['lesson_type'] not in ['optimization','bottleneck','workaround','alert','generic']:
            rec['lesson_type'] = 'generic'
        valid.append(rec)
    return valid

def load_to_db(records):
    # 使用批量插入，忽略冲突（ON DUPLICATE KEY UPDATE）
    # 伪代码：使用MySQL连接器
    import mysql.connector
    conn = mysql.connector.connect(host='...', user='...', password='...', database='lessondb')
    cursor = conn.cursor()
    sql = """
        INSERT INTO lessons (task_id, lesson_type, content, source_system, source_uri, tags, severity, status, created_by, checksum)
        VALUES (%(task_id)s, %(lesson_type)s, %(content)s, %(source_system)s, %(source_uri)s, %(tags)s, %(severity)s, 'draft', %(created_by)s, %(checksum)s)
        ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP, content = VALUES(content), severity = VALUES(severity);
    """
    for rec in records:
        # 处理tags JSON
        rec['tags'] = json.dumps(rec.get('tags', []))
        cursor.execute(sql, rec)
    conn.commit()
    cursor.close()
    conn.close()

with DAG('lessons_etl', default_args=default_args, schedule_interval='0 */2 * * *', start_date=datetime(2025,1,1)) as dag:
    extract_sds_task = PythonOperator(task_id='extract_sds', python_callable=extract_sds)
    extract_jira_task = PythonOperator(task_id='extract_jira', python_callable=extract_jira)
    clean_task = PythonOperator(task_id='clean_validate', python_callable=lambda: clean_and_deduplicate(extract_sds() + extract_jira()))
    load_task = PythonOperator(task_id='load', python_callable=lambda: load_to_db(clean_and_deduplicate(validate(extract_sds() + extract_jira()))))

    [extract_sds_task, extract_jira_task] >> clean_task >> load_task
```

### 4.2 手动填充（Web UI）
提供简单表单，用户填写`task_id`、`lesson_type`、`content`、`tags`、`severity`，系统自动生成`source_system='Manual'`、`checksum`并标记status='draft'。需经审批后才变为'valid'。

## 5. 使用场景与查询示例

### 5.1 场景一：查看某个任务的全部经验
```sql
SELECT id, lesson_type, content, severity, created_at, status
FROM lessons
WHERE task_id = 'SDS-2025-001'
ORDER BY severity ASC, created_at DESC;
```

### 5.2 场景二：统计近7天新增的经验类型分布
```sql
SELECT lesson_type, COUNT(*) AS cnt
FROM lessons
WHERE created_at >= NOW() - INTERVAL 7 DAY
GROUP BY lesson_type
ORDER BY cnt DESC;
```

### 5.3 场景三：全文搜索包含“超时”或“timeout”的经验（含标签）
```sql
SELECT id, task_id, LEFT(content, 100) AS snippet, tags, severity
FROM lessons
WHERE MATCH(content, tags) AGAINST('+超时 +timeout' IN BOOLEAN MODE)
AND status = 'valid'
ORDER BY severity;
```

### 5.4 场景四：获取某任务所有严重级别<=2的workaround经验
```sql
SELECT content, source_system, source_uri
FROM lessons
WHERE task_id = 'SDS-2025-010'
AND lesson_type = 'workaround'
AND severity <= 2
AND status = 'valid';
```

## 6. 维护与更新策略

### 6.1 增量更新
- 每个数据源按各自频率执行增量抽取，仅处理新增或更新的记录。对于SDS，通过记录上次抽取的最大`task_id`或时间戳；对于Jira/Confluence，使用`updated`时间戳作为增量标记。
- 每次ETL前，记录`last_run_time`到配置表`etl_config`（如下表）。

**`etl_config`表结构**：
```sql
CREATE TABLE etl_config (
    source VARCHAR(32) PRIMARY KEY,
    last_run DATETIME NOT NULL,
    last_version INT DEFAULT 1
);
```

### 6.2 版本管理
- 每次用户手动编辑某条经验时，先复制旧记录到`lessons_history`表（与原结构一致，增加`version`字段），再将原记录`version`加1，更新`content`和`updated_at`。
- 自动ETL产生的记录，如果检测到`checksum`冲突但`content`不同，则视为新版本更新（保留历史）。

### 6.3 过期数据清理
- 定期（每季度）运行清理任务：
  - 将`created_at`超过2年且`status='valid'`的记录标记为`deprecated`。
  - 将`status='deprecated'`超过1年的记录移到归档表`lessons_archive`（结构一致），然后从主表删除。
- 归档表保留至少5年。

### 6.4 数据质量监控
- 每日检查表中有无`content`为空、`task_id`不合理、`severity`超出范围的行，并生成报告。
- 对于`source_system='Manual'`且status='draft'超过7天的记录，发送通知给创建者提醒审核。

## 7. 待确认事项列表

| 编号 | 事项 | 建议方案 | 确认方 |
|------|------|----------|--------|
| 1 | `lesson_type`枚举值是否应增加`prediction`（预测类）？ | 根据现有数据分析，90%为bottleneck和workaround，暂不新增 | 业务方 |
| 2 | 数据源中，SDS系统是否支持将错误摘要字段长度限制放宽到500字符？ | 当前SDS API返回的摘要限制300字符，可能丢失信息 | SDS开发团队 |
| 3 | `tags`字段是否应改为枚举列表（例如预定义标签表）以规范搜索？ | 建议保留JSON以便灵活扩展，但增加标签维护接口 | PM/SRE |
| 4 | 手动录入是否需要强制关联一个有效的`task_id`？ | 建议不强制，允许全局通用经验使用虚拟task_id='GLOBAL' | 业务方 |
| 5 | 去重策略中，checksum仅基于content+task_id，但不同源可能描述同一问题但措辞不同。是否需要模糊去重？ | 初期使用精确去重，后续引入simhash | 数据组 |
| 6 | 增量更新频率是否允许SDS源实时触发（消息队列）？ | 建议先采用每分钟轮询，后续改为Kafka订阅 | 系统架构组 |
| 7 | 手动录入经验的审批流程：谁有权审批？是否自动通知审批人？ | 建议由团队leader或SRE on-call轮值审批 | 团队负责人 |

---

**文档状态**：初版草案  
**版本**：1.0  
**创建日期**：2025-01-20  
**联系人**：数据平台组 张工（zhang.gong@example.com）  
**审核节点**：业务方、SDS开发团队、PM  
*本文档为假设性设计，实际实施需根据评审结论调整。*
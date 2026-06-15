# 自动任务执行模板

## 任务信息
- **看板任务ID**: #{task_id}
- **任务名称**: {task_title}
- **执行时间**: {start_time}

## 执行流程

### Phase 1: 任务分析
1. 读取任务详情
2. 分析任务类型和复杂度
3. 确定执行策略

### Phase 2: 执行
1. 使用 Superpowers Skill 完整流程
2. Brainstorm → Design → Plan → TDD → Execute
3. 记录执行日志

### Phase 3: 结果整理
1. 生成执行摘要（50-100字）
2. 整理工作日志
3. 打包核心材料

### Phase 4: 更新看板
1. 更新任务状态为 completed
2. 上传 task_summary
3. 上传 execution_log
4. 上传附件文件
5. 如有剩余问题，记录到 remaining_issues

## 标准化输出

### task_summary 格式（200-500字）
```
【核心成果】
任务已完成。具体成果描述...

【关键数据】
- 数据1: xxx
- 数据2: xxx
- 耗时: xx分钟

【执行亮点】
- 亮点1
- 亮点2

【下一步建议】
- 建议1
- 建议2
```

**字数要求**: 200-500字，必须包含以上四个部分

### execution_log 格式
```
[HH:MM] 开始执行 Phase 1
[HH:MM] 完成 Brainstorm
[HH:MM] 完成 Design
[HH:MM] 完成 Plan
[HH:MM] 完成 Execute
[HH:MM] 开始整理结果
[HH:MM] 上传附件
[HH:MM] 更新看板状态
[HH:MM] 任务完成
```

### 附件命名规范
- 工作日志: `task{ID}_log_YYYYMMDD.txt`
- 核心材料: `task{ID}_{description}_YYYYMMDD.{ext}`
- 设计文档: `task{ID}_design_YYYYMMDD.md`

**注意**: 直接上传原始文件，不上传压缩包

## 数据库更新

使用 kanban_task_manager.py:

```python
from kanban_task_manager import get_task_manager

manager = get_task_manager()

# 添加执行日志
manager.add_execution_log(task_id, "开始执行...")

# 上传文件
manager.upload_task_file(task_id, local_path, filename)

# 上传多个文件（循环上传，不上传压缩包）
for file in source_dir.glob('*'):
    if file.is_file():
        manager.upload_task_file(task_id, file)

# 标记完成
manager.mark_task_completed(
    task_id=task_id,
    summary="任务完成摘要",
    execution_details="详细执行日志",
    attachments=["file1", "file2"]
)

manager.close()
```

## 检查清单

- [ ] 任务分析完成
- [ ] Superpowers 流程执行完成
- [ ] task_summary 已生成（200-500字，含核心成果、关键数据、亮点、建议）
- [ ] execution_log 已记录
- [ ] 附件已逐个上传（不上传压缩包）
- [ ] 看板状态已更新为 completed
- [ ] 数据库连接已关闭

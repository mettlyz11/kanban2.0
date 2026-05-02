#!/bin/bash
LOG_FILE=/opt/kanban-react/logs/attachment_monitor.log
UPLOAD_DIR=/opt/kanban-react/backend/uploads/docs

mkdir -p /opt/kanban-react/logs

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始监控" >> $LOG_FILE

# 检查文件数
FILE_COUNT=$(ls $UPLOAD_DIR | wc -l)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 当前文件数: $FILE_COUNT" >> $LOG_FILE

# 检查零字节文件
ZERO_COUNT=$(find $UPLOAD_DIR -type f -size 0 | wc -l)
if [ "$ZERO_COUNT" -gt 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 警告: $ZERO_COUNT 个零字节文件" >> $LOG_FILE
fi

# 检查磁盘空间
DISK_USAGE=$(df -h $UPLOAD_DIR | awk 'NR==2 {print $5}' | sed 's/%//')
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 磁盘使用率: ${DISK_USAGE}%" >> $LOG_FILE

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 监控完成" >> $LOG_FILE

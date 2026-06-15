# 🏥 Health Tracker - 量化自我健康监测系统

基于 Apple Watch 数据搭建的个人健康数据量化系统，实现数据驱动的健康管理。

## 📋 系统架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│ Apple Watch │────▶│ HealthKit    │────▶│ Python      │────▶│ InfluxDB    │
│ (传感器)    │     │ Export XML   │     │ 处理引擎    │     │ 时序数据库  │
└─────────────┘     └──────────────┘     └──────┬──────┘     └──────┬──────┘
                                                 │                    │
                                                 ▼                    ▼
                                          ┌─────────────┐     ┌─────────────┐
                                          │ 企业微信    │     │ Grafana     │
                                          │ 每日推送    │     │ 可视化仪表盘│
                                          └─────────────┘     └─────────────┘
```

## 🚀 快速开始

### 1. 环境准备

```bash
# macOS 系统要求
# - Python 3.9+
# - Docker Desktop (用于运行 InfluxDB + Grafana)

# 安装依赖
pip install -r requirements.txt

# 复制并编辑配置文件
cp config.yaml config.local.yaml
# 编辑 config.local.yaml 填入你的 InfluxDB Token 和企业微信 Webhook
```

### 2. 启动数据基础设施

```bash
# 使用 Docker Compose 启动 InfluxDB + Grafana
docker-compose up -d

# 访问 Grafana: http://localhost:3000
# 默认账号: admin / admin
```

### 3. Apple Health 数据导出

**方式一：真实数据（推荐）**
1. iPhone: 健康 App → 头像 → 导出所有健康数据
2. 将 `export.xml` 放到配置指定的路径
3. 修改 `config.local.yaml`: `use_mock: false`

**方式二：模拟数据（测试用）**
- 保持 `use_mock: true`，系统将自动生成模拟数据

### 4. 运行系统

```bash
# 每日同步（手动执行）
python main.py sync --config config.local.yaml

# 生成周报
python main.py weekly --config config.local.yaml

# 生成月报
python main.py monthly --config config.local.yaml

# 全部执行
python main.py all --config config.local.yaml
```

### 5. 配置定时任务 (cron)

```bash
# 编辑 crontab
crontab -e

# 每日 7:00 自动同步并推送
0 7 * * * cd /path/to/health-tracker && python main.py sync --config config.local.yaml >> logs/cron.log 2>&1

# 每周一 8:00 生成周报
0 8 * * 1 cd /path/to/health-tracker && python main.py weekly --config config.local.yaml >> logs/weekly.log 2>&1

# 每月 1 日 9:00 生成月报
0 9 1 * * cd /path/to/health-tracker && python main.py monthly --config config.local.yaml >> logs/monthly.log 2>&1
```

## 📊 健康评分算法

| 维度 | 权重 | 指标 |
|------|------|------|
| 运动 | 30% | 步数达成率 + 活跃卡路里 |
| 睡眠 | 30% | 睡眠时长 + 深度睡眠比例 |
| 心率 | 20% | 静息心率稳定性 |
| 精力 | 20% | 心率恢复 + 站立时间 |

**评分等级：**
- A+ (≥90): 优秀
- A (85-89): 良好
- A- (80-84): 不错
- B+ (75-79): 中等偏上
- B (70-74): 中等
- B- (65-69): 需关注
- C+ 以下: 需改善

## 🔔 异常预警规则

- 🔴 高优先级：睡眠 < 5 小时
- 🟡 中优先级：静息心率持续 > 80 bpm
- 🟢 低优先级：静息心率 < 50 bpm

## 📁 项目结构

```
health-tracker/
├── config.yaml           # 配置文件模板
├── config.local.yaml     # 本地配置（不提交到git）
├── requirements.txt      # Python依赖
├── main.py              # 主程序入口
├── health_exporter.py   # Apple Health 数据导出
├── health_score.py      # 健康评分算法
├── influxdb_store.py    # InfluxDB 数据存储
├── wechat_notifier.py   # 企业微信推送
├── grafana_dashboard.json  # Grafana 仪表盘配置
├── docker-compose.yml   # 基础设施编排
├── setup.sh             # 一键安装脚本
└── reports/             # 生成的报告目录
    ├── daily_2026-04-25.md
    ├── weekly_20260418_20260425.md
    └── monthly_202604.md
```

## 🐳 Docker Compose 配置

创建 `docker-compose.yml`:

```yaml
version: '3.8'
services:
  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    environment:
      - INFLUXDB_DB=health_data
      - INFLUXDB_ADMIN_USER=admin
      - INFLUXDB_ADMIN_PASSWORD=adminpassword
    volumes:
      - influxdb-data:/var/lib/influxdb2

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on:
      - influxdb

volumes:
  influxdb-data:
  grafana-data:
```

## 📱 企业微信配置

1. 创建企业微信群
2. 群设置 → 添加群机器人
3. 复制 Webhook URL
4. 填入 `config.local.yaml`

## 🛠️ 开发调试

```bash
# 测试评分算法
python health_score.py

# 测试数据导出
python health_exporter.py

# 测试微信推送
python wechat_notifier.py

# 测试数据库连接
python influxdb_store.py
```

## 📈 未来扩展

- [ ] 集成 Apple HealthKit 实时 API
- [ ] 增加 HRV (心率变异性) 分析
- [ ] 血氧饱和度趋势追踪
- [ ] 体温监测（Apple Watch Series 8+）
- [ ] 机器学习异常检测
- [ ] 与医师/教练共享报告

---

**版本:** v1.0.0  
**作者:** Health Tracker Team  
**许可:** MIT

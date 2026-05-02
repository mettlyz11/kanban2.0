# Apple Watch 健康数据量化系统

基于 Apple Watch 数据的个人健康管理系统，实现健康数据量化、评分、趋势分析和异常预警。

## 📁 目录结构

```
task-1864/
├── code/                      # 源代码目录
│   ├── health_tracker.py      # 健康数据追踪和评分引擎
│   ├── influxdb_client.py     # InfluxDB 时序数据库客户端
│   ├── wechat_notifier.py     # 微信推送通知模块
│   ├── grafana_dashboard.py   # Grafana 仪表盘配置生成器
│   └── generate_dashboard_screenshots.py  # 仪表盘截图生成
│   └── generate_monthly_report.py        # 月度报告生成
├── data/                      # 数据存储目录
│   ├── health_data.json       # 30天健康原始数据
│   ├── health_data.csv        # CSV格式数据
│   └── influxdb_mock.json     # InfluxDB模拟数据
├── grafana/                   # Grafana配置
│   └── health_dashboard.json  # 健康仪表盘JSON配置
├── docker/                    # Docker部署配置
│   ├── docker-compose.yml     # InfluxDB + Grafana 编排
│   └── grafana/               # Grafana数据源配置
├── screenshots/               # 仪表盘可视化截图
│   ├── 01_score_trend.png     # 综合评分趋势图
│   ├── 02_dimensions_radar.png # 四维评分雷达图
│   ├── 03_metrics_cards.png   # 关键指标卡片
│   ├── 04_score_distribution.png # 评分分布图
│   └── 05_weekly_heatmap.png  # 周度热力图
├── reports/                   # 健康报告
│   ├── monthly_report.json    # 月度报告原始数据
│   ├── monthly_health_report.md   # 月度健康报告(Markdown)
│   └── monthly_health_report.html # 月度健康报告(HTML)
└── docs/                      # 文档
    └── dashboard_preview.md   # 仪表盘预览文档
```

## 🚀 功能特性

### 1. 健康数据量化
- **四维评分算法**: 运动(30%) + 睡眠(30%) + 心率(20%) + 精力(20%)
- 基于 Apple HealthKit 标准数据格式
- 支持步数、睡眠时长、运动时长、心率等核心指标

### 2. 时序数据存储
- 基于 InfluxDB 2.x 时序数据库
- Docker 一键部署
- 高效存储和查询健康数据

### 3. Grafana 可视化仪表盘
- 综合健康评分趋势图
- 四维评分雷达图
- 关键指标卡片展示
- 评分分布统计
- 周度评分热力图
- 深色主题设计

### 4. 异常预警系统
- 静息心率持续升高检测
- 睡眠质量下降预警
- 活动量骤降提醒
- 异常数据实时推送

### 5. 微信推送通知
- 每日健康简报推送
- 周度健康总结报告
- 异常预警即时通知
- 支持 Server酱 和 企业微信

### 6. 健康报告生成
- 30天月度健康报告
- 核心指标趋势分析
- 评分分布统计
- 个性化改善建议
- 下月行动计划

## 🔧 部署方式

### Docker 一键部署
```bash
cd docker
docker-compose up -d
```

### 手动运行
```bash
# 安装依赖
pip install pandas numpy matplotlib influxdb-client

# 运行健康追踪系统
python code/health_tracker.py

# 生成仪表盘截图
python code/generate_dashboard_screenshots.py

# 生成月度报告
python code/generate_monthly_report.py
```

## 📊 评分标准

| 等级 | 分数区间 | 评价 |
|------|----------|------|
| 🌟 优秀 | 85-100 | 保持良好状态 |
| 👍 良好 | 70-84 | 继续保持，争取更好 |
| ⚠️ 一般 | 55-69 | 需要关注部分指标 |
| 🔴 需关注 | 0-54 | 建议及时调整生活方式 |

## 📈 数据分析示例

基于30天模拟数据分析结果：
- **平均健康评分**: 87.2 分 (优秀)
- **日均步数**: 9,800 步
- **日均睡眠**: 7.3 小时
- **平均静息心率**: 62 bpm

## 🔗 相关链接

- [Grafana 官方文档](https://grafana.com/docs/)
- [InfluxDB 官方文档](https://docs.influxdata.com/)
- [Apple HealthKit 开发文档](https://developer.apple.com/documentation/healthkit)

---

*本系统由 AI 辅助开发，用于个人健康数据量化管理*

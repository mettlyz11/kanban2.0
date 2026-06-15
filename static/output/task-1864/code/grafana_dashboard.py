#!/usr/bin/env python3
"""
Grafana健康仪表盘配置生成器
生成完整的Grafana Dashboard JSON配置
"""

import json
from datetime import datetime
from typing import Dict

def generate_health_dashboard() -> Dict:
    """生成健康仪表盘配置"""
    
    dashboard = {
        "annotations": {
            "list": []
        },
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 0,
        "id": None,
        "links": [],
        "liveNow": False,
        "panels": [
            # 1. 健康评分概览
            {
                "datasource": "InfluxDB",
                "fieldConfig": {
                    "defaults": {
                        "color": {
                            "mode": "thresholds"
                        },
                        "mappings": [],
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "green", "value": 85},
                                {"color": "#EAB839", "value": 70},
                                {"color": "orange", "value": 55},
                                {"color": "red", "value": None}
                            ]
                        }
                    },
                    "overrides": []
                },
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                "id": 1,
                "options": {
                    "colorMode": "value",
                    "graphMode": "area",
                    "justifyMode": "auto",
                    "orientation": "auto",
                    "reduceOptions": {
                        "calcs": ["lastNotNull"],
                        "fields": "",
                        "values": False
                    },
                    "textMode": "auto"
                },
                "pluginVersion": "10.2.0",
                "targets": [{
                    "refId": "A",
                    "query": """from(bucket: "health_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "health_metrics")
  |> filter(fn: (r) => r["_field"] == "score_total")
  |> aggregateWindow(every: v.windowPeriod, fn: last, createEmpty: false)
  |> yield(name: "last")"""
                }],
                "title": "综合健康评分",
                "type": "stat"
            },
            # 2. 各维度得分
            {
                "datasource": "InfluxDB",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {
                            "axisCenteredZero": False,
                            "axisColorMode": "text",
                            "axisLabel": "",
                            "axisPlacement": "auto",
                            "barAlignment": 0,
                            "drawStyle": "line",
                            "fillOpacity": 10,
                            "gradientMode": "hue",
                            "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                            "lineInterpolation": "linear",
                            "lineWidth": 2,
                            "pointSize": 5,
                            "scaleDistribution": {"type": "linear"},
                            "showPoints": "auto",
                            "spanNulls": False,
                            "stacking": {"group": "A", "mode": "none"},
                            "thresholdsStyle": {"mode": "off"}
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                "id": 2,
                "targets": [
                    {"refId": "运动", "query": "..."},
                    {"refId": "睡眠", "query": "..."},
                    {"refId": "心率", "query": "..."},
                    {"refId": "精力", "query": "..."}
                ],
                "title": "各维度健康得分趋势",
                "type": "timeseries"
            },
            # 3. 每日步数
            {
                "datasource": "InfluxDB",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "thresholds"},
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": None},
                                {"color": "orange", "value": 5000},
                                {"color": "#EAB839", "value": 8000},
                                {"color": "green", "value": 10000}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 7, "w": 6, "x": 0, "y": 8},
                "id": 3,
                "options": {
                    "colorMode": "value",
                    "graphMode": "area",
                    "justifyMode": "auto",
                    "orientation": "auto",
                    "textMode": "auto"
                },
                "targets": [{
                    "refId": "A",
                    "query": """from(bucket: "health_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "health_metrics")
  |> filter(fn: (r) => r["_field"] == "steps")
  |> aggregateWindow(every: 1d, fn: last)"""
                }],
                "title": "今日步数",
                "type": "stat"
            },
            # 4. 睡眠时长
            {
                "datasource": "InfluxDB",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "thresholds"},
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": None},
                                {"color": "orange", "value": 5},
                                {"color": "#EAB839", "value": 7},
                                {"color": "green", "value": 8}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 7, "w": 6, "x": 6, "y": 8},
                "id": 4,
                "options": {
                    "colorMode": "value",
                    "graphMode": "area",
                    "textMode": "auto"
                },
                "targets": [{
                    "refId": "A",
                    "query": """from(bucket: "health_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "health_metrics")
  |> filter(fn: (r) => r["_field"] == "sleep_total")
  |> aggregateWindow(every: 1d, fn: last)"""
                }],
                "title": "睡眠时长 (小时)",
                "type": "stat"
            },
            # 5. 静息心率
            {
                "datasource": "InfluxDB",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "thresholds"},
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": 55},
                                {"color": "#EAB839", "value": 65},
                                {"color": "orange", "value": 75},
                                {"color": "red", "value": 85}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 7, "w": 6, "x": 12, "y": 8},
                "id": 5,
                "targets": [{
                    "refId": "A",
                    "query": """from(bucket: "health_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "health_metrics")
  |> filter(fn: (r) => r["_field"] == "heart_rate_resting")
  |> aggregateWindow(every: 1d, fn: last)"""
                }],
                "title": "静息心率 (bpm)",
                "type": "stat"
            },
            # 6. 运动时长
            {
                "datasource": "InfluxDB",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "thresholds"},
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": None},
                                {"color": "orange", "value": 15},
                                {"color": "#EAB839", "value": 30},
                                {"color": "green", "value": 45}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 7, "w": 6, "x": 18, "y": 8},
                "id": 6,
                "targets": [{
                    "refId": "A",
                    "query": """from(bucket: "health_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "health_metrics")
  |> filter(fn: (r) => r["_field"] == "exercise_minutes")
  |> aggregateWindow(every: 1d, fn: last)"""
                }],
                "title": "运动时长 (分钟)",
                "type": "stat"
            },
            # 7. 健康评分趋势图
            {
                "datasource": "InfluxDB",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {
                            "axisCenteredZero": False,
                            "axisColorMode": "text",
                            "axisLabel": "评分",
                            "axisPlacement": "auto",
                            "fillOpacity": 20,
                            "gradientMode": "opacity",
                            "lineWidth": 3,
                            "showPoints": "never"
                        },
                        "min": 0,
                        "max": 100
                    }
                },
                "gridPos": {"h": 9, "w": 24, "x": 0, "y": 15},
                "id": 7,
                "targets": [{
                    "refId": "A",
                    "query": """from(bucket: "health_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "health_metrics")
  |> filter(fn: (r) => r["_field"] == "score_total")
  |> aggregateWindow(every: 1d, fn: last)"""
                }],
                "thresholds": [
                    {"value": 55, "color": "red"},
                    {"value": 70, "color": "orange"},
                    {"value": 85, "color": "#EAB839"}
                ],
                "title": "健康评分趋势 (30天)",
                "type": "timeseries"
            },
            # 8. 评分分布柱状图
            {
                "datasource": "InfluxDB",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "thresholds"}
                    }
                },
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 24},
                "id": 8,
                "options": {
                    "barRadius": 0.25,
                    "barWidth": 0.8,
                    "groupWidth": 0.7,
                    "showValue": "always"
                },
                "targets": [{
                    "refId": "A",
                    "query": """from(bucket: "health_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "health_metrics")
  |> filter(fn: (r) => r["_field"] == "score_total")
  |> histogram(bins: [55, 70, 85, 100])"""
                }],
                "title": "健康评分分布",
                "type": "barchart"
            },
            # 9. 睡眠结构饼图
            {
                "datasource": "InfluxDB",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"}
                    }
                },
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24},
                "id": 9,
                "options": {
                    "pieType": "pie",
                    "displayLabels": ["percent", "value"]
                },
                "targets": [{
                    "refId": "A",
                    "query": "..."
                }],
                "title": "睡眠结构分布",
                "type": "piechart"
            }
        ],
        "refresh": "1h",
        "schemaVersion": 38,
        "style": "dark",
        "tags": ["health", "apple-watch", "fitness"],
        "templating": {
            "list": []
        },
        "time": {
            "from": "now-30d",
            "to": "now"
        },
        "timepicker": {},
        "timezone": "Asia/Shanghai",
        "title": "Apple Watch 健康数据仪表盘",
        "version": 1,
        "weekStart": "monday"
    }
    
    return dashboard

def save_dashboard_config(output_dir: str):
    """保存仪表盘配置文件"""
    dashboard = generate_health_dashboard()
    
    filepath = f"{output_dir}/grafana/health_dashboard.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, ensure_ascii=False, indent=2)
    
    # print(f"✅ Grafana仪表盘配置已保存: {filepath}")
    
    # 生成仪表盘预览Markdown
    preview_path = f"{output_dir}/docs/dashboard_preview.md"
    preview_content = f"""# Apple Watch 健康数据仪表盘 - 预览

## 仪表盘概览

**创建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**数据源**: InfluxDB (健康时序数据)
**刷新间隔**: 1小时
**时间范围**: 最近30天

## 面板布局

### 第一行 - 核心指标
1. **综合健康评分** (12列) - 大字体显示当前评分，带趋势图
2. **各维度得分趋势** (12列) - 运动/睡眠/心率/精力四维对比图

### 第二行 - 关键指标卡
3. **今日步数** (6列) - 目标10000步
4. **睡眠时长** (6列) - 目标7-9小时
5. **静息心率** (6列) - 目标55-65 bpm
6. **运动时长** (6列) - 目标30+分钟

### 第三行 - 趋势分析
7. **健康评分趋势图** (24列) - 30天评分变化曲线

### 第四行 - 分布统计
8. **评分分布柱状图** (12列) - 各分数段天数统计
9. **睡眠结构饼图** (12列) - 深睡/浅睡/REM占比

## 评分标准

| 等级 | 分数区间 | 颜色 |
|------|----------|------|
| 优秀 | 85-100 | 🟢 绿色 |
| 良好 | 70-84 | 🟡 黄色 |
| 一般 | 55-69 | 🟠 橙色 |
| 需关注 | 0-54 | 🔴 红色 |

## 导入方式

1. 打开Grafana界面 (http://localhost:3000)
2. 点击 "+" → "Import"
3. 上传 `health_dashboard.json` 文件或粘贴内容
4. 选择InfluxDB数据源
5. 点击 "Import" 完成

## 仪表盘配置文件位置
- `{filepath}`
"""
    
    with open(preview_path, 'w', encoding='utf-8') as f:
        f.write(preview_content)
    
    # print(f"✅ 仪表盘预览文档已保存: {preview_path}")

if __name__ == '__main__':
    save_dashboard_config("/Users/mettlyz/.openclaw/workspace/output/task-1864")

# grafana_dashboard_system_metrics

> 任务: PDF#105 系统运行指标的 Grafana 看板​
> 附件类型: Grafana看板JSON配置
> 生成时间: 2026-05-13 00:47

```json
{
  "dashboard": {
    "title": "PDF#105 系统运行指标看板",
    "uid": "pdf105-system-metrics",
    "timezone": "browser",
    "schemaVersion": 27,
    "version": 1,
    "refresh": "30s",
    "time": {
      "from": "now-6h",
      "to": "now"
    },
    "timepicker": {
      "refresh_intervals": ["10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"],
      "time_options": ["5m", "15m", "1h", "6h", "12h", "24h", "2d", "7d", "30d"]
    },
    "tags": ["system", "metrics", "prometheus"],
    "description": "系统运行指标监控看板，包含CPU、内存、磁盘、网络等核心指标，基于Prometheus数据源默认配置。",
    "graphTooltip": 0,
    "style": "dark",
    "panels": [
      {
        "collapsed": false,
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "gridPos": {
          "h": 1,
          "w": 24,
          "x": 0,
          "y": 0
        },
        "id": 1,
        "panels": [],
        "title": "CPU 指标",
        "type": "row"
      },
      {
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 80
                },
                {
                  "color": "red",
                  "value": 90
                }
              ]
            },
            "unit": "percent"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 1
        },
        "id": 2,
        "options": {
          "orientation": "auto",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showThresholdLabels": false,
          "showThresholdMarkers": true
        },
        "pluginVersion": "8.5.3",
        "targets": [
          {
            "datasource": {
              "type": "prometheus",
              "uid": "prometheus"
            },
            "editorMode": "code",
            "expr": "100 - (avg by (instance)(rate(node_cpu_seconds_total{mode=\"idle\", instance=~\"$node\"}[1m])) * 100)",
            "legendFormat": "{{instance}}",
            "range": true,
            "refId": "A"
          }
        ],
        "title": "CPU 使用率（总体）",
        "type": "gauge"
      },
      {
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisCenteredZero": false,
              "axisColorMode": "text",
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "smooth",
              "lineWidth": 2,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "auto",
              "spanNulls": false,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "area"
              }
            },
            "mappings": [],
            "thresholds": {
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "red",
                  "value": 90
                }
              ]
            },
            "unit": "percent"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 1
        },
        "id": 3,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom",
            "showLegend": true
          },
          "tooltip": {
            "mode": "multi",
            "sort": "none"
          }
        },
        "pluginVersion": "8.5.3",
        "targets": [
          {
            "datasource": {
              "type": "prometheus",
              "uid": "prometheus"
            },
            "editorMode": "code",
            "expr": "100 - (avg by (cpu, instance)(rate(node_cpu_seconds_total{mode=\"idle\", instance=~\"$node\"}[1m])) * 100)",
            "legendFormat": "{{instance}} CPU {{cpu}}",
            "range": true,
            "refId": "A"
          }
        ],
        "title": "CPU 使用率（按核心）",
        "type": "timeseries"
      },
      {
        "collapsed": false,
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "gridPos": {
          "h": 1,
          "w": 24,
          "x": 0,
          "y": 9
        },
        "id": 4,
        "panels": [],
        "title": "内存指标",
        "type": "row"
      },
      {
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 80
                },
                {
                  "color": "red",
                  "value": 90
                }
              ]
            },
            "unit": "percent"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 10
        },
        "id": 5,
        "options": {
          "orientation": "auto",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showThresholdLabels": false,
          "showThresholdMarkers": true
        },
        "pluginVersion": "8.5.3",
        "targets": [
          {
            "datasource": {
              "type": "prometheus",
              "uid": "prometheus"
            },
            "editorMode": "code",
            "expr": "(1 - (node_memory_MemAvailable_bytes{instance=~\"$node\"} / node_memory_MemTotal_bytes{instance=~\"$node\"})) * 100",
            "legendFormat": "{{instance}}",
            "range": true,
            "refId": "A"
          }
        ],
        "title": "内存使用率",
        "type": "gauge"
      },
      {
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisCenteredZero": false,
              "axisColorMode": "text",
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "smooth",
              "lineWidth": 2,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "auto",
              "spanNulls": false,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "bytes"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 10
        },
        "id": 6,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom",
            "showLegend": true
          },
          "tooltip": {
            "mode": "multi",
            "sort": "none"
          }
        },
        "pluginVersion": "8.5.3",
        "targets": [
          {
            "datasource": {
              "type": "prometheus",
              "uid": "prometheus"
            },
            "editorMode": "code",
            "expr": "node_memory_MemTotal_bytes{instance=~\"$node\"}",
            "legendFormat": "总内存 - {{instance}}",
            "range": true,
            "refId": "A"
          },
          {
            "datasource": {
              "type": "prometheus",
              "uid": "prometheus"
            },
            "editorMode": "code",
            "expr": "node_memory_MemFree_bytes{instance=~\"$node\"} + node_memory_Buffers_bytes{instance=~\"$node\"} + node_memory_Cached_bytes{instance=~\"$node\"}",
            "legendFormat": "可用内存 - {{instance}}",
            "range": true,
            "refId": "B"
          },
          {
            "datasource": {
              "type": "prometheus",
              "uid": "prometheus"
            },
            "editorMode": "code",
            "expr": "node_memory_MemTotal_bytes{instance=~\"$node\"} - (node_memory_MemFree_bytes{instance=~\"$node\"} + node_memory_Buffers_bytes{instance=~\"$node\"} + node_memory_Cached_bytes{instance=~\"$node\"})",
            "legendFormat": "已用内存 - {{instance}}",
            "range": true,
            "refId": "C"
          }
        ],
        "title": "内存用量详情",
        "type": "timeseries"
      },
      {
        "collapsed": false,
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "gridPos": {
          "h": 1,
          "w": 24,
          "x": 0,
          "y": 18
        },
        "id": 7,
        "panels": [],
        "title": "磁盘指标",
        "type": "row"
      },
      {
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 80
                },
                {
                  "color": "red",
                  "value": 90
                }
              ]
            },
            "unit": "percent"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 19
        },
        "id": 8,
        "options": {
          "orientation": "auto",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showThresholdLabels": false,
          "showThresholdMarkers": true
        },
        "pluginVersion": "8.5.3",
        "targets": [
          {
            "datasource": {
              "type": "prometheus",
              "uid": "prometheus"
            },
            "editorMode": "code",
            "expr": "100 - (sum by(instance)(node_filesystem_avail_bytes{mountpoint=\"/\", instance=~\"$node\"}) / sum by(instance)(node_filesystem_size_bytes{mountpoint=\"/\", instance=~\"$node\"}) * 100)",
            "legendFormat": "{{instance}}",
            "range": true,
            "refId": "A"
          }
        ],
        "title": "根分区磁盘使用率",
        "type": "gauge"
      },
      {
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisCenteredZero": false,
              "axisColorMode": "text",
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "smooth",
              "lineWidth": 2,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "auto",
              "spanNulls": false,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "bytes"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 19
        },
        "id": 9,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom",
            "showLegend": true
          },
          "tooltip": {
            "
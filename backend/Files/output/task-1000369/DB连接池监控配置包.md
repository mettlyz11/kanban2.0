# DB连接池监控配置包

> 任务: v12 #31 DB连接池监控
> 附件类型: 配置文件集合
> 生成时间: 2026-05-12 08:50

# 配置文件集合：v12 #31 DB连接池监控

本配置文件集合提供了一套完整的 Prometheus 抓取配置、Grafana 仪表板以及告警规则，用于监控常见 Java 数据库连接池（HikariCP、Druid、Tomcat JDBC）。所有配置均基于标准 JMX Exporter 或 Micrometer 暴露的指标，可直接导入使用，降低手工配置工作量。

---

## 1. prometheus-scrape-config.yml

该配置定义了三个抓取 Job，分别对应 HikariCP、Druid 和 Tomcat 连接池。假设目标应用分别运行在端口 8080、8090、8100，且已通过 JMX Exporter 或 Spring Boot Actuator 暴露了相关指标。实际使用时请根据环境修改 `targets` 和 `metrics_path`。

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # ---------- HikariCP 连接池 (通过 JMX Exporter 暴露) ----------
  - job_name: 'hikaricp_connection_pool'
    metrics_path: /metrics
    static_configs:
      - targets: ['app1.example.com:8080', 'app2.example.com:8080']
    # HikariCP 指标命名示例 (JMX Exporter):
    #   jdbc_connections_active
    #   jdbc_connections_idle
    #   jdbc_connections_pending
    #   jdbc_connections_max
    relabel_configs:
      - source_labels: [__address__]
        regex: '([^:]+):.*'
        target_label: instance
        replacement: '${1}'
      - source_labels: [__address__]
        regex: '.*:(\d+)'
        target_label: port
        replacement: '${1}'

  # ---------- Druid 连接池 (通过 Spring Boot Actuator / Micrometer) ----------
  - job_name: 'druid_connection_pool'
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ['druid-app1:8090', 'druid-app2:8090']
    # Druid Micrometer 指标示例:
    #   druid_datasource_active_count
    #   druid_datasource_pooling_count
    #   druid_datasource_connect_count
    #   druid_datasource_max_active
    params:
      'name[]': ['druid']   # 仅抓取 druid 相关指标 (如果支持)
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: '^(druid_datasource_.*)'
        action: keep
      - source_labels: [dataSource]
        target_label: pool_name
        replacement: '${1}'

  # ---------- Tomcat JDBC 连接池 (通过 JMX Exporter) ----------
  - job_name: 'tomcat_jdbc_pool'
    metrics_path: /metrics
    static_configs:
      - targets: ['tc-app1:8100', 'tc-app2:8100']
    # Tomcat JDBC 指标 (JMX Exporter) 示例:
    #   tomcat_connectionpool_numActive
    #   tomcat_connectionpool_numIdle
    #   tomcat_connectionpool_numMax
    #   tomcat_connectionpool_waitCount
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: '^(tomcat_connectionpool_.*)'
        action: keep
      - source_labels: [name]
        target_label: pool_name
        replacement: '${1}'
```

**说明**：
- HikariCP 的 JMX Exporter 配置需在应用 JVM 参数中添加 `-javaagent:/path/to/jmx_prometheus_javaagent-0.18.0.jar=8080:config.yaml`，其中 `config.yaml` 包含规则 `lowercaseOutputName: true` 等。
- Druid 使用 Spring Boot Actuator + Micrometer 时，需在 `application.properties` 中启用 `management.endpoints.web.exposure.include=prometheus` 并添加 `io.micrometer:micrometer-registry-prometheus` 依赖。
- Tomcat JDBC 同样可通过 JMX Exporter 或 Tomcat 自带的 JMX MBean 暴露。

---

## 2. grafana-dashboard.json

以下是一个完整的 Grafana 仪表板 JSON，包含三个行：连接池概览、活跃/空闲/等待连接面板、连接趋势图。该仪表板使用 Prometheus 数据源，包含 6 个面板，支持 HikariCP、Druid、Tomcat 三种连接池，通过变量 `$pool_type` 和 `$instance` 进行选择。

```json
{
  "__inputs": [],
  "__requires": [
    {
      "type": "grafana",
      "id": "grafana",
      "name": "Grafana",
      "version": "8.5.0"
    },
    {
      "type": "datasource",
      "id": "prometheus",
      "name": "Prometheus",
      "version": "1.0.0"
    }
  ],
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": {
          "type": "grafana",
          "uid": "-- Grafana --"
        },
        "enable": true,
        "hide": true,
        "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts",
        "target": {
          "limit": 100,
          "matchAny": false,
          "tags": [],
          "type": "dashboard"
        },
        "type": "dashboard"
      }
    ]
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graph": {},
  "id": null,
  "links": [],
  "panels": [
    {
      "collapsed": false,
      "datasource": {
        "type": "prometheus",
        "uid": "${datasource}"
      },
      "gridPos": {
        "h": 1,
        "w": 24,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "panels": [],
      "title": "连接池概览",
      "type": "row"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "${datasource}"
      },
      "description": "当前所有连接池的活跃连接数总和",
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "thresholds"
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              },
              {
                "color": "red",
                "value": 80
              }
            ]
          },
          "unit": "short"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 0,
        "y": 1
      },
      "id": 2,
      "options": {
        "colorMode": "value",
        "graphMode": "area",
        "justifyMode": "auto",
        "orientation": "auto",
        "reduceOptions": {
          "calcs": [
            "lastNotNull"
          ],
          "fields": "",
          "values": false
        },
        "textMode": "auto"
      },
      "pluginVersion": "8.5.0",
      "targets": [
        {
          "exemplar": true,
          "expr": "sum(\n  label_replace(($pool_type == \"hikaricp\" ? jdbc_connections_active : $pool_type == \"druid\" ? druid_datasource_active_count : tomcat_connectionpool_numActive), \"pool\", \"$pool_type\", \"\", \"\")\n) by (pool, instance)",
          "legendFormat": "{{pool}} {{instance}}",
          "range": true,
          "refId": "A"
        }
      ],
      "title": "活跃连接总数",
      "type": "stat"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "${datasource}"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
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
            "lineInterpolation": "linear",
            "lineWidth": 1,
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
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              }
            ]
          },
          "unit": "short"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 6,
        "y": 1
      },
      "id": 3,
      "options": {
        "legend": {
          "calcs": [],
          "displayMode": "list",
          "placement": "bottom"
        },
        "tooltip": {
          "mode": "multi",
          "sort": "none"
        }
      },
      "targets": [
        {
          "exemplar": true,
          "expr": "sum(\n  label_replace(($pool_type == \"hikaricp\" ? jdbc_connections_active : $pool_type == \"druid\" ? druid_datasource_active_count : tomcat_connectionpool_numActive), \"pool\", \"$pool_type\", \"\", \"\")\n) by (instance) [5m]",
          "legendFormat": "{{instance}} - active",
          "range": true,
          "refId": "A"
        },
        {
          "exemplar": true,
          "expr": "sum(\n  label_replace(($pool_type == \"hikaricp\" ? jdbc_connections_idle : $pool_type == \"druid\" ? druid_datasource_pooling_count : tomcat_connectionpool_numIdle), \"pool\", \"$pool_type\", \"\", \"\")\n) by (instance) [5m]",
          "legendFormat": "{{instance}} - idle",
          "range": true,
          "refId": "B"
        },
        {
          "exemplar": true,
          "expr": "sum(\n  label_replace(($pool_type == \"hikaricp\" ? jdbc_connections_pending : $pool_type == \"druid\" ? druid_datasource_wait_thread_count : tomcat_connectionpool_waitCount), \"pool\", \"$pool_type\", \"\", \"\")\n) by (instance) [5m]",
          "legendFormat": "{{instance}} - waiting",
          "range": true,
          "refId": "C"
        }
      ],
      "title": "连接状态时间序列",
      "type": "timeseries"
    },
    {
      "collapsed": false,
      "datasource": {
        "type": "prometheus",
        "uid": "${datasource}"
      },
      "gridPos": {
        "h": 1,
        "w": 24,
        "x": 0,
        "y": 9
      },
      "id": 4,
      "panels": [],
      "title": "活跃/空闲/等待连接面板",
      "type": "row"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "${datasource}"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "hideFrom": {
              "legend": false,
              "tooltip": false,
              "viz": false
            }
          },
          "mappings": [
            {
              "options": {
                "0": {
                  "color": "green",
                  "text": "0"
                }
              },
              "type": "value"
            }
          ],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              }
            ]
          }
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 8,
        "x": 0,
        "y": 10
      },
      "id": 5,
      "options": {
        "displayLabels": ["name"],
        "legend": {
          "displayMode": "list",
          "placement": "right",
          "values": []
        },
        "pieType": "pie",
        "reduceOptions": {
          "calcs": [
            "lastNotNull"
          ],
          "fields": "",
          "values": false
        },
        "tooltip": {
          "mode": "single",
          "sort": "none"
        }
      },
      "targets": [
        {
          "exemplar": true,
          "expr": "label_replace(($pool_type == \"hikaricp\" ? jdbc_connections_active : $pool_type == \"druid\" ? druid_datasource_active_count : tomcat_connectionpool_numActive), \"state\", \"active\", \"\", \"\") or\nlabel_replace(($pool_type == \"hikaricp\" ? jdbc_connections_idle : $pool_type == \"druid\" ? druid_datasource_pooling_count : tomcat_connectionpool_numIdle), \"state\", \"idle\", \"\", \"\") or\nlabel_replace(($pool_type == \"hikaricp\" ? jdbc_connections_pending : $pool_type == \"druid\" ? druid_datasource_wait_thread_count : tomcat_connectionpool_waitCount), \"state\", \"waiting\", \"\", \"\")",
          "legendFormat": "{{state}}",
          "range": true,
          "refId": "A"
        }
      ],
      "title": "当前连接分布 - $pool_type",
      "type": "piechart"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "${datasource}"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "axisLabel": "",
            "axisPlacement": "auto",
            "barAlignment": 0,
            "drawStyle": "line",
            "fillOpacity": 20,
            "gradientMode": "none",
            "hideFrom": {
              "legend": false,
              "tooltip": false,
              "viz": false
            },
            "lineInterpolation": "linear",
            "lineWidth": 2,
            "pointSize": 5,
            "scaleDistribution": {
              "type": "linear"
            },
            "showPoints": "never",
            "spanNulls": true,
            "stacking": {
              "group": "A",
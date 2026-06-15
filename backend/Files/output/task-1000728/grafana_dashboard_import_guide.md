# grafana_dashboard_import_guide

> 任务: PDF#105 系统运行指标的 Grafana 看板​
> 附件类型: 操作指南
> 生成时间: 2026-05-13 00:48

# 系统运行指标的 Grafana 看板 — 操作指南

---

## 1. 概述

本看板聚焦于服务器（Linux / Windows）基础运行指标，旨在为运维人员提供 CPU、内存、磁盘、网络、进程、系统负载的实时可视化，并支持快速定位异常。适用场景包括：

- **日常巡检**：一键查看所有核心资源的当前使用率与历史趋势。
- **故障排查**：通过关联面板快速确认瓶颈（如 CPU 打满、磁盘 IO 等待、内存泄漏）。
- **容量规划**：基于 7/30 天趋势图评估资源增长趋势，辅助扩缩容决策。

看板包含 **12 个主要面板**，布局分为六行：

| 行 | 面板内容 | 数据源指标 |
|----|---------|-----------|
| 1 | CPU 使用率（平均值 & 每核） | `node_cpu_seconds_total` (rate) |
| 2 | 内存使用量 & 使用率 | `node_memory_MemTotal_bytes`, `node_memory_MemFree_bytes` 等 |
| 3 | 磁盘空间使用率 & 剩余量 | `node_filesystem_size_bytes`, `node_filesystem_avail_bytes` |
| 4 | 磁盘 IO 读写速率 & IOPS | `node_disk_read_bytes_total`, `node_disk_writes_completed_total` |
| 5 | 网络流量（接收/发送） & 错误包 | `node_network_receive_bytes_total`, `node_network_transmit_bytes_total` |
| 6 | 系统负载 & 运行进程数 | `node_load1`, `node_load5`, `node_load15`, `node_procs_running` |

所有指标基于 **Prometheus node_exporter** 暴露的指标，兼容 Grafana 8.0 及以上版本。

---

## 2. 前置条件

在执行导入操作前，请确保以下环境已就绪：

| 组件 | 最低版本 | 备注 |
|------|---------|------|
| Grafana | v8.0.0+ | 推荐 v9.x 或 v10.x，以获得最佳兼容性 |
| Prometheus | v2.0+ | 已配置并采集目标主机的 node_exporter 数据 |
| node_exporter | v1.0+ | 安装在目标主机上，默认端口 9100 |
| 浏览器 | 现代浏览器 | Chrome / Firefox / Edge 最新版 |

### 2.1 确认 Prometheus 数据源地址

请在 Prometheus 配置文件中检查 `scrape_configs`，确保 `node_exporter` 的 target 已正确添加。例如：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['192.168.1.10:9100', '192.168.1.11:9100']
```

在浏览器访问 Prometheus UI（如 `http://192.168.1.1:9090`），执行以下查询验证指标是否存在：

```
rate(node_cpu_seconds_total{mode="idle"}[1m])
```

若返回数据，说明采集正常。

### 2.2 Grafana 版本验证

登录 Grafana Web UI，点击左下角头像 → “关于” 可查看版本。若版本低于 v8.0，建议升级，否则部分变量语法可能不兼容。

---

## 3. 导入步骤（通过 Grafana UI 导入 JSON 文件）

### 3.1 获取看板 JSON 文件

本看板 JSON 文件名为 `grafana_dashboard_template.json`（以下提供完整可用的示例文件内容）。请将此 JSON 保存到本地。

**完整看板 JSON 示例（可直接复制使用）：**

```json
{
  "__inputs": [],
  "__requires": [{"type": "grafana", "id": "grafana", "name": "Grafana", "version": "8.0.0"}],
  "annotations": {"list": []},
  "editable": true,
  "gnetId": null,
  "graphTooltip": 1,
  "id": null,
  "links": [],
  "panels": [
    {
      "datasource": "${DS_PROMETHEUS}",
      "fieldConfig": {
        "defaults": {
          "unit": "percent",
          "min": 0,
          "max": 100
        },
        "overrides": []
      },
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
      "id": 1,
      "options": {
        "orientation": "auto",
        "reduceOptions": {
          "calcs": ["lastNotNull"],
          "fields": "",
          "values": false
        },
        "showThresholdLabels": false,
        "showThresholdMarkers": true
      },
      "pluginVersion": "8.3.3",
      "targets": [
        {
          "expr": "100 - (avg by (instance) (rate(node_cpu_seconds_total{mode='idle'}[1m])) * 100)",
          "legendFormat": "CPU Usage % - {{ instance }}",
          "refId": "A"
        }
      ],
      "title": "CPU 使用率（平均值）",
      "type": "gauge"
    },
    {
      "datasource": "${DS_PROMETHEUS}",
      "fieldConfig": {
        "defaults": {
          "unit": "decbytes",
          "decimals": 2
        },
        "overrides": []
      },
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
      "id": 2,
      "options": {
        "legend": {
          "calcs": ["mean", "max", "min"],
          "displayMode": "table",
          "placement": "bottom"
        },
        "tooltip": {"mode": "multi", "sort": "none"}
      },
      "targets": [
        {
          "expr": "node_memory_MemTotal_bytes - node_memory_MemFree_bytes - node_memory_Buffers_bytes - node_memory_Cached_bytes",
          "legendFormat": "Used - {{ instance }}",
          "refId": "A"
        }
      ],
      "title": "内存使用量",
      "type": "timeseries"
    },
    {
      "datasource": "${DS_PROMETHEUS}",
      "fieldConfig": {
        "defaults": {
          "unit": "bytes",
          "decimals": 2
        },
        "overrides": []
      },
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
      "id": 3,
      "options": {
        "legend": {
          "calcs": ["mean"],
          "displayMode": "table",
          "placement": "right"
        }
      },
      "targets": [
        {
          "expr": "sum by (instance, mountpoint) (node_filesystem_size_bytes{fstype!~'tmpfs|overlay|devtmpfs|squashfs'})",
          "legendFormat": "Total - {{ instance }} {{ mountpoint }}",
          "refId": "A"
        },
        {
          "expr": "sum by (instance, mountpoint) (node_filesystem_avail_bytes{fstype!~'tmpfs|overlay|devtmpfs|squashfs'})",
          "legendFormat": "Free - {{ instance }} {{ mountpoint }}",
          "refId": "B"
        }
      ],
      "title": "磁盘空间（总/剩余）",
      "type": "timeseries"
    },
    {
      "datasource": "${DS_PROMETHEUS}",
      "fieldConfig": {
        "defaults": {
          "unit": "Bps",
          "decimals": 2
        },
        "overrides": []
      },
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
      "id": 4,
      "options": {
        "legend": {
          "calcs": ["mean", "max"],
          "displayMode": "table",
          "placement": "bottom"
        }
      },
      "targets": [
        {
          "expr": "rate(node_disk_read_bytes_total[1m])",
          "legendFormat": "Read - {{ instance }} {{ device }}",
          "refId": "A"
        },
        {
          "expr": "rate(node_disk_written_bytes_total[1m])",
          "legendFormat": "Write - {{ instance }} {{ device }}",
          "refId": "B"
        }
      ],
      "title": "磁盘 IO 速率",
      "type": "timeseries"
    },
    {
      "datasource": "${DS_PROMETHEUS}",
      "fieldConfig": {
        "defaults": {
          "unit": "bps",
          "decimals": 1
        },
        "overrides": []
      },
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
      "id": 5,
      "options": {
        "legend": {
          "calcs": ["mean"],
          "displayMode": "table",
          "placement": "bottom"
        }
      },
      "targets": [
        {
          "expr": "rate(node_network_receive_bytes_total[1m])",
          "legendFormat": "RX - {{ instance }} {{ device }}",
          "refId": "A"
        },
        {
          "expr": "rate(node_network_transmit_bytes_total[1m])",
          "legendFormat": "TX - {{ instance }} {{ device }}",
          "refId": "B"
        }
      ],
      "title": "网络流量",
      "type": "timeseries"
    },
    {
      "datasource": "${DS_PROMETHEUS}",
      "fieldConfig": {
        "defaults": {
          "unit": "none",
          "decimals": 1
        },
        "overrides": []
      },
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
      "id": 6,
      "options": {
        "legend": {
          "calcs": ["mean", "max"],
          "displayMode": "table",
          "placement": "bottom"
        }
      },
      "targets": [
        {
          "expr": "node_load1",
          "legendFormat": "Load 1m - {{ instance }}",
          "refId": "A"
        },
        {
          "expr": "node_load5",
          "legendFormat": "Load 5m - {{ instance }}",
          "refId": "B"
        },
        {
          "expr": "node_load15",
          "legendFormat": "Load 15m - {{ instance }}",
          "refId": "C"
        }
      ],
      "title": "系统负载",
      "type": "timeseries"
    }
  ],
  "refresh": "30s",
  "schemaVersion": 27,
  "style": "dark",
  "tags": ["system", "linux", "monitoring"],
  "templating": {
    "list": [
      {
        "current": {},
        "hide": 0,
        "includeAll": false,
        "label": "Prometheus 数据源",
        "multi": false,
        "name": "DS_PROMETHEUS",
        "options": [],
        "query": "prometheus",
        "refresh": 1,
        "regex": "",
        "skipUrlSync": false,
        "type": "datasource"
      }
    ]
  },
  "time": {
    "from": "now-6h",
    "to": "now"
  },
  "timepicker": {
    "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h"],
    "time_options": ["5m", "15m", "1h", "6h", "12h", "24h", "2d", "7d", "30d"]
  },
  "timezone": "browser",
  "title": "系统运行指标看板",
  "uid": "system-metrics-105",
  "version": 1
}
```

> **注意**：上述 JSON 使用了一个名为 `DS_PROMETHEUS` 的模板变量，导入后会自动替换为实际数据源名称。面板数量精简为 6 个以节约篇幅，但覆盖核心指标。

### 3.2 通过 Grafana UI 导入

1. 登录 Grafana（默认地址 `http://localhost:3000`，用户名/密码：admin/admin）。
2. 鼠标悬停在左侧菜单的 **+** 图标上，选择 **Import**。
3. 在 “Import via panel json” 框中，直接粘贴上述 JSON 内容；或点击 “Upload JSON file” 上传本地文件。
4. 点击 **Load** 按钮，Grafana 会解析 JSON。
5. 在 “Options” 区域：
   - **Name**：可以修改看板名称（如 “Server Metrics”）。
   - **Folder**：选择一个文件夹归类。
   - **Unique identifier (UID)**：保持默认即可。
   - **DS_PROMETHEUS**：下拉选择你的 Prometheus 数据源（如果只有一个，自动选择）。
6. 点击 **Import**，导入完成。此时会自动跳转到新看板。

---

## 4. 数据源配置

### 4.1 修改数据源变量

如果导入后出现 “Data source not found” 错误，说明变量 `DS_PROMETHEUS` 未正确绑定。解决方法：

1. 进入看板，点击右上角 **设置图标（齿轮）** → **Variables**。
2. 找到变量 `DS_PROMETHEUS`，点击 Edit。
3. 在 **Type** 选择 “Data source”，**Data source** 选择 “Prometheus”。
4. 点击 **Update**，然后点击 **Save dashboard**。

### 4.2 直接替换面板中的数据源（备选）

如果看板中每个面板的 `datasource` 字段写死（例如 `"datasource": "Prometheus"`），而你的数据源名称不同，可以批量修改：

1. 进入看板设置 → **JSON Model**。
2. 使用浏览器的搜索功能（Ctrl+F）查找 `"datasource"`。
3. 手动将值改为你的实际数据源名称（例如 `"MyPrometheus"`）。
4. 点击 **Save Changes**。

### 4.3 确认数据源连通性

1. 进入 **Configuration** → **Data Sources**，点击你的 Prometheus 数据源。
2. 点击 **Save & Test**，确保显示 “Data source is working” 或类似信息。
3. 如果失败，检查网络、URL（例如 `http://prometheus.example.com:9090`）以及访问权限。

---

## 5. 自定义指南

### 5.1 添加/修改面板

#### 添加新面板
1. 在看板顶部点击 **+ Add panel**（或点击面板空白处出现 “Add panel” 按钮）。
2. 选择 **Add a new panel** 进入编辑界面。
3. 在 **Query** 区域编写 PromQL 查询，例如：
   ```promql
   # 每分钟上下文切换次数
   rate(node_context_switches_total[1m])
   ```
4. 设置可视化类型（如 Time series、Stat、Gauge 等）。
5. 配置 **Field** 选项（单位、小数位数、阈值颜色等）。
6. 点击右上角 **Apply** 回到看板，然后 **Save dashboard**。

#### 修改现有面板
- 鼠标悬停在目标面板上，点击面板标题下拉菜单 → **Edit**。
- 修改查询、可视化选项或告警。
- 完成后 **Apply** 并保存。

### 5.2 调整时间范围

- **快速选取**：在看板右上角点击时间选择器（显示 “Last 6 hours” 等），可切换到 `Last 30 minutes`、`Last 24 hours`、`Last 7 days` 等。
- **自定义范围**：点击时间选择器，选择 **Absolute time range**，输入起始和结束日期时间。
- **自动刷新**：点击刷新按钮旁边的下拉箭，选择自动刷新间隔（如 `30s`）。若要关闭自动刷新，设为 `Off`。

### 5.3 设置告警

#### 为面板添加告警（示例：CPU 使用率 > 90% 持续 5 分钟）
1. 进入 CPU 使用率面板的编辑模式。
2. 点击左侧 **Alert** 标签（若未显示，确认 Grafana 已启用告警功能，默认开启）。
3. 点击 **Create Alert**。
4. 定义规则：
   - **Name**：例如 “CPU 过高告警”。
   - **Condition**：`WHEN avg() OF query(A, 5m, 0) IS ABOVE 90`。
     - `avg()`：使用平均值减少抖动。
     - `5m`：评估窗口（5 分钟）。
     - `ABOVE 90`：阈值 > 90。
   - 可添加多个条件（如 `WHEN max
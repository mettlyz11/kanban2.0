# DB连接池监控方案

> 任务: v12 #31 DB连接池监控
> 附件类型: 技术方案
> 生成时间: 2026-05-12 08:50

# DB连接池监控技术方案

## 1. 概述与目标

### 1.1 背景

在微服务架构和高并发场景下，数据库连接池是系统性能与稳定性的关键组件。连接池配置不当、耗尽或泄漏会导致服务雪崩，严重影响业务可用性。因此，建立一套完整的DB连接池监控体系，实时掌握连接池运行状态，及时发现并预警潜在风险，是运维保障的重要环节。

### 1.2 目标

- **实时采集**：对所有应用的数据库连接池核心指标进行持续采集，延迟不超过30秒。
- **可视化监控**：通过Grafana仪表板直观展示连接池运行趋势，支持多维度筛选（应用名、实例、连接池类型）。
- **智能告警**：设定合理的告警规则，通过电话、钉钉、邮件等渠道及时通知相关人员。
- **历史追溯**：保存至少30天的连接池指标数据，用于事后分析和容量规划。

## 2. 支持的连接池类型与版本

本方案兼容以下主流Java连接池实现（版本基于当前主流生产环境）：

| 连接池类型   | 最低版本 | 推荐版本 | 说明 |
|------------|----------|----------|------|
| HikariCP   | 3.4.0    | 5.0.1    | Spring Boot 2.x / 3.x 默认 |
| Druid      | 1.2.8    | 1.2.20   | 阿里开源，国内广泛使用 |
| Tomcat JDBC| 9.0.40   | 10.1.18  | Tomcat嵌入式/独立容器 |
| DBCP2      | 2.9.0    | 2.10.0   | Apache Commons，少量遗留系统 |

**版本兼容性说明**：上述版本均支持通过JMX暴露连接池统计信息，且与Micrometer、Spring Boot Actuator良好集成。若使用更低版本，建议升级以获取完善的监控能力。

## 3. 连接池统计端点暴露配置

根据连接池类型和框架集成方式，提供三种典型配置方案：

### 3.1 基于Spring Boot Actuator + Micrometer（推荐）

适用于Spring Boot 2.x/3.x项目，只需在`pom.xml`中添加依赖（以HikariCP为例）：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

在`application.yml`中暴露端点：

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus,metrics
  metrics:
    export:
      prometheus:
        enabled: true
    tags:
      application: ${spring.application.name:unknown}
# 连接池指标已自动集成，无需额外配置
```

此时访问 `http://localhost:8080/actuator/prometheus` 即可看到类似以下指标：

```
hikaricp_connections_active{application="order-service",pool="HikariPool-1",} 5.0
hikaricp_connections_idle{application="order-service",pool="HikariPool-1",} 15.0
hikaricp_connections_pending{application="order-service",pool="HikariPool-1",} 0.0
hikaricp_connections_timeout_total{application="order-service",pool="HikariPool-1",} 2.0
```

### 3.2 手动暴露JMX指标（适用于非Spring Boot项目或Druid）

对于Druid连接池，需显式启用StatFilter和JMX：

```xml
<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>druid-spring-boot-starter</artifactId>
    <version>1.2.20</version>
</dependency>
```

配置文件：

```yaml
spring:
  datasource:
    druid:
      stat-view-servlet:
        enabled: true
        login-username: admin
        login-password: admin123
      web-stat-filter:
        enabled: true
      filter:
        stat:
          enabled: true
          slow-sql-millis: 1000
        wall:
          enabled: true
      # 启用JMX
      use-global-data-source-stat: true
      jmx:
        enabled: true
```

然后通过JMX导出代理（如`jmx_prometheus_javaagent`）暴露Prometheus格式指标。下载`jmx_prometheus_javaagent-0.19.0.jar`，在启动脚本中添加：

```
-javaagent:/path/to/jmx_prometheus_javaagent-0.19.0.jar=9404:/path/to/config.yaml
```

`config.yaml`示例：

```yaml
startDelaySeconds: 10
rules:
  - pattern: "com.alibaba.druid:type=DruidDataSourceStat,name=*"
    attrNameSnakeCase: true
    type: GAUGE
    labels:
      poolName: $1
    metrics:
      - name: "druid_connections_active"
        attrName: "ActiveCount"
      - name: "druid_connections_idle"
        attrName: "PoolingCount"
      - name: "druid_connections_pending"
        attrName: "WaitThreadCount"
      - name: "druid_connections_timeout_total"
        attrName: "ConnectCount"  # 实际为累计连接数，可通过其他属性计算超时
```

### 3.3 Tomcat JDBC连接池配置

Tomcat JDBC连接池自动集成到Spring Boot中（当使用`tomcat-jdbc`时），指标前缀为`tomcat.jdbc`。确保在application.yml中开启：

```yaml
server:
  tomcat:
    max-connections: 10000
    connection-timeout: 5000
spring:
  datasource:
    tomcat:
      max-active: 100
      max-idle: 20
      min-idle: 5
```

Actuator会自动暴露指标：

```
tomcat.jdbc.connections.active{application="user-service",} 8.0
tomcat.jdbc.connections.idle{application="user-service",} 12.0
tomcat.jdbc.connections.pending{application="user-service",} 1.0
tomcat.jdbc.connections.borrow.count{application="user-service",} 1200.0
```

## 4. Prometheus采集器配置

### 4.1 全局scrape配置（示例）

在`prometheus.yml`中加入以下job：

```yaml
scrape_configs:
  - job_name: 'db-connection-pools'
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /actuator/prometheus
    scheme: http
    static_configs:
      - targets:
        - '10.0.1.10:8080'   # order-service
        - '10.0.1.11:8080'   # user-service
        - '10.0.1.12:8080'   # payment-service
        labels:
          env: prod
          team: backend
    relabel_configs:
      - source_labels: [__address__]
        regex: '(.+):\d+'
        target_label: instance
        replacement: '$1'
      - source_labels: [__address__]
        regex: '(.+):(\d+)'
        target_label: port
        replacement: '$2'
    # 如果使用服务发现（如Kubernetes），可使用kubernetes_sd_configs
```

### 4.2 对于JMX代理方式（Druid）

添加额外job：

```yaml
  - job_name: 'druid-pools'
    scrape_interval: 15s
    metrics_path: /metrics
    static_configs:
      - targets:
        - '10.0.2.10:9404'   # 每个应用暴露的JMX代理端口
        labels:
          app: order-service
          pool_type: druid
```

### 4.3 验证数据采集

重启Prometheus后，通过`http://prometheus:9090/targets`检查两个job的状态是否UP。然后在Prometheus查询面板中输入`hikaricp_connections_active`或`druid_connections_active`，应看到时间序列数据。

## 5. 核心监控指标说明

### 5.1 HikariCP指标

| 指标名称 | 类型 | 说明 | 告警建议阈值 |
|----------|------|------|------------|
| `hikaricp_connections_active` | Gauge | 当前活跃连接数（正在被应用程序使用） | > maxPoolSize * 0.8 |
| `hikaricp_connections_idle` | Gauge | 当前空闲连接数 | < minIdle 持续5分钟 |
| `hikaricp_connections_pending` | Gauge | 等待获取连接的线程数 | > 0 持续30秒 |
| `hikaricp_connections_timeout_total` | Counter | 连接超时获取失败累计次数 | 速率 > 1/min |
| `hikaricp_connections_max` | Gauge | 最大池大小（配置值） | - |
| `hikaricp_connections_min` | Gauge | 最小空闲连接数 | - |
| `hikaricp_connections_creation_seconds` | Summary | 创建连接耗时分布 | p99 > 100ms |
| `hikaricp_connections_acquire_seconds` | Summary | 获取连接耗时分布 | p99 > 50ms |

### 5.2 Druid指标

| 指标名称 | 类型 | 说明 | 告警建议阈值 |
|----------|------|------|------------|
| `druid_connections_active` | Gauge | 当前活跃连接数 | > maxActive * 0.8 |
| `druid_connections_idle` | Gauge | 当前空闲连接数 | < minIdle 持续5分钟 |
| `druid_connections_pending` | Gauge | 等待获取连接的线程数（WaitThreadCount） | > 0 持续30秒 |
| `druid_connections_error_total` | Counter | 连接错误次数 | 速率 > 0.1/min |
| `druid_connections_in_use` | Gauge | 正在使用的连接数（含活动） | - |
| `druid_connections_max_used` | Gauge | 峰值使用连接数 | 周期性重置，用于容量评估 |
| `druid_connections_wait_count_total` | Counter | 等待获取连接的累计次数 | - |
| `druid_connections_wait_millis` | Gauge | 当前等待线程总时长（ms） | > 5000ms |

### 5.3 Tomcat JDBC指标

| 指标名称 | 类型 | 说明 |
|----------|------|------|
| `tomcat.jdbc.connections.active` | Gauge | 活跃连接数 |
| `tomcat.jdbc.connections.idle` | Gauge | 空闲连接数 |
| `tomcat.jdbc.connections.pending` | Gauge | 等待线程数 |
| `tomcat.jdbc.connections.borrow.count` | Counter | 累计获取连接次数 |
| `tomcat.jdbc.connections.created.count` | Counter | 累计创建连接次数 |
| `tomcat.jdbc.connections.released.count` | Counter | 累计释放连接次数 |
| `tomcat.jdbc.connections.abandoned.count` | Counter | 被废弃的连接数（泄漏） |

### 5.4 通用建议

- 所有Gauge类型指标建议配置`rate`或`avg_over_time`用于告警。
- 对于`timeout`和`error`等Counter，使用`rate(metric[1m])`计算每秒速率。
- `pool_name`标签用来区分不同数据源（如读写分离场景下的主库、从库）。

## 6. Grafana仪表板设计

### 6.1 仪表板整体布局

建议分为三个主要行（Row）：

1. **概览行**：展示所有应用的连接池健康状态、总活跃/空闲连接求和、等待线程趋势。
2. **详情行**：按应用或实例展示单个连接池的详细指标，支持变量选择。
3. **异常行**：展示连接超时、错误、慢查询等异常事件的时间序列。

### 6.2 变量设置

创建以下Dashboard Variables（通过`Settings -> Variables`）：

| 变量名 | 类型 | 查询 | 说明 |
|--------|------|------|------|
| `application` | Query | `label_values(hikaricp_connections_active, application)` | 所有应用名称 |
| `instance` | Query | `label_values(hikaricp_connections_active{application="$application"}, instance)` | 所选应用下的实例IP |
| `pool_name` | Query | `label_values(hikaricp_connections_active{application="$application", instance="$instance"}, pool)` | 具体连接池名 |
| `datasource` | 常量 | 固定为Prometheus数据源 | 数据源选择 |

### 6.3 核心面板配置

#### 面板1：活跃连接数趋势 (Time series)

```json
{
  "title": "活跃连接数",
  "type": "timeseries",
  "datasource": "Prometheus",
  "targets": [
    {
      "expr": "sum(hikaricp_connections_active{application=~\"$application\"}) by (application, instance, pool)",
      "legendFormat": "{{application}}-{{instance}}-{{pool}}"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "min": 0
    }
  }
}
```

#### 面板2：等待线程数统计 (Stat)

```json
{
  "title": "当前等待线程数（总计）",
  "type": "stat",
  "datasource": "Prometheus",
  "targets": [
    {
      "expr": "sum(hikaricp_connections_pending{application=~\"$application\"})"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": 0 },
          { "color": "yellow", "value": 1 },
          { "color": "red", "value": 10 }
        ]
      }
    }
  }
}
```

#### 面板3：连接超时速率 (Bar gauge)

```json
{
  "title": "连接超时速率（1分钟）",
  "type": "bargauge",
  "datasource": "Prometheus",
  "targets": [
    {
      "expr": "rate(hikaricp_connections_timeout_total{application=~\"$application\"}[1m])",
      "legendFormat": "{{application}}-{{instance}}"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "cps",
      "min": 0
    }
  }
}
```

#### 面板4：连接创建耗时 p99 (Heatmap 或表格)

建议使用Prometheus的Histogram指标（如`hikaricp_connections_creation_seconds_bucket`），配置Heatmap面板或直接使用`histogram_quantile`绘制时间序列。

```json
{
  "title": "连接创建耗时 p99",
  "type": "timeseries",
  "datasource": "Prometheus",
  "targets": [
    {
      "expr": "histogram_quantile(0.99, sum(rate(hikaricp_connections_creation_seconds_bucket{application=~\"$application\"}[5m])) by (le, application))",
      "legendFormat": "{{application}} p99"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "s"
    }
  }
}
```

### 6.4 导入技巧

可将上述面板打包为JSON Model，通过Grafana的`Import Dashboard`功能直接导入。注意替换数据源的uid。

## 7. 告警规则设计

### 7.1 Prometheus告警规则文件

创建`alerts-connectionpool.yml`：

```yaml
groups:
  - name: db_connection_pool_alerts
    rules:
      # 连接池耗尽预警（活跃连接 > 80% 最大连接持续2分钟）
      - alert: HikariPoolHighActiveConnections
        expr: |
          avg by (application, instance, pool) (hikaricp_connections_active)
          /
          avg by (application, instance, pool) (hikaricp_connections_max)
          > 0.8
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "HikariCP连接池{{ $labels.application }}.{{ $labels.pool }}活跃连接过高"
          description: "当前活跃连接占比{{ humanizePercentage $value }}，超过80%，请检查负载或扩容。"

      # 连接池耗尽严重（活跃连接 > 95% 持续1分钟）
      - alert: HikariPoolEx
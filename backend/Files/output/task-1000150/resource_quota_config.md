# resource_quota_config

> 任务: v7 #19 资源限额
> 附件类型: 配置文件
> 生成时间: 2026-05-12 05:49

# 资源限额配置文件 v7.0

## 1. 文档概述

本文件是“v7 #19 资源限额”系统的核心配置规范，定义资源配额管理的全局默认值、租户/服务级别独立配置、动态阈值算法、超限执行动作以及仪表板聚合逻辑。配置文件采用 YAML 格式，由配置加载器（`config-loader v3.2`）读取并实时生效，支持热更新。所有数值单位为国际标准（CPU：毫核 mCPU；内存：兆字节 MiB；IOPS：每秒 I/O 操作次数；带宽：Mbps）。

---

## 2. 全局默认限额

```yaml
global_defaults:
  # CPU 限制：每个 Pod 或容器允许的最大 CPU 用量
  cpu_max: 4000            # 单位 mCPU (4 vCPU)
  cpu_burst: 20%           # 可在短时间内超出上限的比例，基于 base_limit
  cpu_base_slice: 100      # 基础时间片 (ms)

  # 内存限制
  memory_max: 8192         # 单位 MiB (8 GB)
  memory_swap: 4096        # 允许交换空间的最大值，0 表示禁止交换
  memory_hard_limit: true   # true 为硬限制，超过即 OOM kill

  # 存储 I/O 限制
  iops_max_read: 5000
  iops_max_write: 5000
  iops_burst_read: 10000   # 突发读 IOPS，持续不超过 5s
  iops_burst_write: 8000
  throughput_max_read: 250  # MB/s
  throughput_max_write: 200

  # 网络带宽限制
  bandwidth_ingress: 1000   # 入站带宽 Mbps
  bandwidth_egress: 800     # 出站带宽 Mbps
  bandwidth_burst_ingress: 2000
  bandwidth_burst_egress: 1500

  # 其他资源
  ephemeral_storage: 10240  # 临时存储 MiB
  pids_max: 1024            # 最大进程数
  file_descriptor_max: 65536

  # 全局配额检查周期（秒）
  quota_check_interval: 5
  # 全局软限制启用标志
  soft_limit_enabled: true
  soft_limit_warning_threshold: 80%  # 当使用率达到 80% 时触发警告
```

### 2.1 全局默认说明

- `cpu_max` 为物理核数的硬限制，`cpu_burst` 允许在 CPU 空闲时短期超用，但均值仍需遵守 `cpu_base_limit`（此处未显式设置，继承自系统默认，通常为 2000 mCPU）。
- 所有 `burst` 参数受 `burst_duration` 控制（在动态阈值中定义）。
- `ephemeral_storage` 对应临时卷容量，超出后文件写入可能失败。
- `soft_limit_warning_threshold` 在 `soft_limit_enabled: true` 时生效，仅告警不强制执行。

---

## 3. 各租户/服务级别的独立限额配置

系统采用两级隔离：**租户（Tenant）** 和 **服务（Service）**。租户代表业务线或项目组，服务代表具体微服务或应用。配置支持继承与覆盖。

```yaml
tenants:
  - id: tenant-alpha               # 租户唯一标识
    description: "核心交易系统"
    default_service_limits:
      cpu: 2000                    # 覆盖全局 CPU 上限为 2 vCPU
      memory: 4096
      iops_read: 3000
      iops_write: 2000
      bandwidth_ingress: 500
      bandwidth_egress: 400
    services:
      - id: svc-order              # 订单服务
        limits:
          cpu: 4000                # 提升至 4 vCPU，高于租户默认
          memory: 8192
          iops_burst_read: 15000   # 允许更高突发读
        overrides:
          # 单独配置的降级策略
          cpu_oversold_ratio: 1.5   # 允许超卖比例
          memory_oversold_ratio: 1.2

      - id: svc-payment
        limits:
          cpu: 1000
          memory: 2048
          iops_write: 1000
        # 不设置 overrides，使用租户默认

      - id: svc-notification
        limits:
          cpu: 500
          memory: 1024
        # 该服务使用租户默认的 IOPS 和带宽

  - id: tenant-beta
    description: "数据中台"
    default_service_limits:
      cpu: 8000
      memory: 16384
      iops_read: 10000
      iops_write: 8000
      bandwidth_egress: 2000
    services:
      - id: svc-etl
        limits:
          cpu: 16000
          memory: 32768
          # 其他使用租户默认
        overrides:
          quota_check_interval: 10    # 自定义检查周期（秒）
      - id: svc-datalake
        limits:
          cpu: 4000
          memory: 8192
          iops_read: 5000
        # 无 override

  - id: tenant-gamma
    description: "开发测试环境"
    default_service_limits:
      cpu: 1000
      memory: 2048
      iops_read: 1000
      iops_write: 1000
    services: []                   # 空列表表示所有服务继承租户默认，无需额外定义
```

### 3.1 租户配置规则

1. 每个租户必须包含 `id` 和 `default_service_limits`。
2. `services` 数组可缺省（此时所有属于该租户的服务使用 `default_service_limits`）。
3. `overrides` 字段用于覆盖全局或租户层级的参数，如 `quota_check_interval`、`cpu_oversold_ratio` 等，仅在该服务内生效。
4. `cpu_oversold_ratio` 允许调度器按比例分配物理资源（如 1:1.5 的 CPU 超卖），但运行时仍受硬限制约束。

---

## 4. 动态阈值参数

采用**滑动窗口+指数移动平均（EWMA）** 算法计算资源使用率趋势，支持弹性调整阈值。

```yaml
dynamic_threshold:
  # 总开关
  enabled: true
  # 全局参数（可被租户/服务覆盖）
  global:
    statistics_window: 60              # 统计窗口（秒），用于计算平均使用率
    alpha: 0.3                         # EWMA 平滑因子（0~1），越小越平滑
    elasticity_coefficient: 0.15       # 弹性系数，允许阈值浮动范围（±15%）
    cooling_time: 120                  # 冷却时间（秒），阈值变化后需等待才能再次调整
    min_threshold_adjustment: 0.05     # 最小调整步长（5%）
    max_adjust_up: 0.25                # 一次最多上调 25%
    max_adjust_down: 0.20              # 一次最多下调 20%

  # 资源类型独立的动态阈值参数（覆盖全局）
  by_resource:
    cpu:
      statistics_window: 30            # CPU 使用快速波动，窗口缩小至 30s
      alpha: 0.5                       # 快速反应
      elasticity_coefficient: 0.1
      cooling_time: 60
    memory:
      statistics_window: 120
      alpha: 0.2
      elasticity_coefficient: 0.2
      cooling_time: 180
    iops_read:
      statistics_window: 60
      alpha: 0.3
      elasticity_coefficient: 0.15
      cooling_time: 120
    bandwidth:
      statistics_window: 60
      alpha: 0.3
      elasticity_coefficient: 0.1
      cooling_time: 60

  # 每个租户/服务可以覆盖这些参数
  tenant_overrides:
    - tenant_id: tenant-alpha
      by_resource:
        cpu:
          elasticity_coefficient: 0.2   # 允许更高弹性
          cooling_time: 30
    - tenant_id: tenant-beta
      services:
        - service_id: svc-etl
          by_resource:
            memory:
              statistics_window: 300    # ETL 任务长期占用，窗口 5 分钟
              alpha: 0.1
```

### 4.1 动态阈值工作流程

- 系统每 `quota_check_interval` 秒采样当前资源使用率，更新滑动窗口内的平均使用率。
- 通过 EWMA 计算平滑值：`smooth_util = alpha * current_util + (1 - alpha) * smooth_util_old`。
- 动态阈值 = 初始阈值（全局或租户指定） × （1 + elasticity_coefficient × (smooth_util - 0.5)），其中 0.5 是目标利用率（50% 为理想点）。
- 调整幅度受 `max_adjust_up/down` 限制。变化后进入 `cooling_time` 秒的静默期，期间不调整。
- 最终阈值用于触发超限动作的判断。

---

## 5. 超限后的执行动作

当资源使用超过配置的阈值（硬限制或动态调整后的阈值）时，系统执行以下动作（可组合）。

```yaml
actions:
  # 全局动作优先级：告警 -> 限流 -> 降级 -> 拒绝
  default_policy: &default_policy
    - action: warn
      type: alert
      channels: [email, slack, pagerduty]
      severity: warning
      metadata:
        repeat_interval: 300         # 重复告警间隔（秒）
        max_alerts_per_hour: 5

    - action: throttle_cpu
      type: rate_limit
      resource: cpu
      metric: cpu_usage
      limit: 95%                     # 达到阈值的 95% 开始限流
      algorithm: token_bucket
      params:
        bucket_size: 1000
        refill_rate: 100             # 每 100ms 补充 100 个令牌

    - action: throttle_memory
      type: rate_limit
      resource: memory
      metric: memory_usage
      limit: 90%
      algorithm: leaky_bucket
      params:
        drain_rate: 200              # 每秒释放 200 MiB

    - action: degrade
      type: degrade
      resource: all
      degradation_level: 1           # 可配置多个降级级别
      actions:
        - disable_noncritical_api: true
        - reduce_thread_pool: 50%
        - limit_cache_size: 70%

    - action: deny_new_requests
      type: reject
      resource: all
      trigger: resource_exhausted    # 当资源使用率超过 100% 硬限制时触发
      rejection_code: 429
      rejection_message: "Resource limit exceeded, retry later"
      reject_duration: 60            # 拒绝新请求 60 秒

  # 自定义动作可按租户或服务覆盖
  tenant_specific_actions:
    - tenant_id: tenant-alpha
      actions:
        <<: *default_policy          # 继承默认动作
        - action: throttle_network
          type: rate_limit
          resource: bandwidth
          metric: bandwidth_ingress
          limit: 80%                 # 租户 alpha 更早限流
          algorithm: token_bucket
          params:
            bucket_size: 500
            refill_rate: 50

    - tenant_id: tenant-beta
      services:
        - service_id: svc-etl
          actions:
            - action: warn
              type: alert
              channels: [pagerduty]
              severity: critical
              metadata:
                notify_on:
                  - breaching_cpu
                  - breaching_memory
                  - breaching_iops
            - action: degrade
              type: degrade
              resource: memory
              degradation_level: 2    # ETL 服务遇到内存压力时立即降级
              actions:
                - halt_low_priority_tasks: true
                - reduce_partition_count: 50%
                - flush_buffers: true
```

### 5.1 动作优先级与执行顺序

- 当多个动作匹配时，按列表顺序执行。`warn` 始终最先触发，用于通知。
- 限流动作可以叠加，但需遵循资源调度优先级（CPU 限流不影响内存）。
- 降级动作只在 `degradation_level` 递增时生效，同一级别不重复执行。
- 拒绝动作为最终手段，一旦触发将阻止所有新增请求，但允许已有连接继续（直至超时）。

---

## 6. 可视化仪表板对应的指标聚合规则

用于 Prometheus + Grafana 或类似系统的指标采集与展示。

```yaml
dashboard_metrics:
  # 全局聚合
  global:
    # 平均使用率（1 分钟窗口）
    - name: resource_usage_avg_1m
      metric: avg
      resources: [cpu, memory, iops_read, iops_write, bandwidth_ingress, bandwidth_egress]
      aggregation: avg
      window: 60
      interval: 15

    # 峰值使用率（5 分钟窗口）
    - name: resource_usage_peak_5m
      metric: max
      resources: [cpu, memory]
      aggregation: max
      window: 300
      interval: 60

    # 限流次数统计
    - name: throttled_requests_total
      metric: count
      filter: { action: "throttle_*" }
      aggregation: sum
      interval: 10

    # 拒绝请求总数
    - name: rejected_requests_total
      metric: count
      filter: { action: "deny_new_requests" }
      aggregation: sum
      interval: 10

    # 弹性阈值当前值（动态展示）
    - name: dynamic_threshold_current
      type: gauge
      labels: [resource, tenant, service]
      update_interval: 30

  # 租户级别
  per_tenant:
    - tenant_id: tenant-alpha
      metrics:
        - name: cpu_usage_alpha
          metric: avg
          resources: cpu
          filter: { tenant_id: tenant-alpha }
          aggregation: avg
          window: 60
        - name: iops_usage_alpha
          metric: avg
          resources: [iops_read, iops_write]
          filter: { tenant_id: tenant-alpha }
          aggregation: sum
          window: 120
        - name: bandwidth_usage_alpha
          metric: avg
          resources: [bandwidth_ingress, bandwidth_egress]
          filter: { tenant_id: tenant-alpha }
          aggregation: max
          window: 300
        - name: throttle_events_alpha
          metric: count
          filter: { tenant_id: tenant-alpha, action: throttle_* }
          aggregation: sum

    - tenant_id: tenant-beta
      metrics:
        - name: etc_cpu_usage_beta
          metric: avg
          resources: cpu
          filter: { tenant_id: tenant-beta, service_id: svc-etl }
          aggregation: avg
          window: 180   # 长任务特别关注长期负载
        # 其他默认指标系统会自动生成，此处仅列出特殊规则

  # 仪表板布局建议（可选）
  dashboard_layout:
    rows:
      - title: "全局资源概览"
        panels:
          - title: "CPU 使用率 (全局)"
            metric: global.resource_usage_avg_1m
            type: line
            scale: "0-100%"
          - title: "内存使用率 (全局)"
            metric: global.resource_usage_avg_1m
            type: line
            scale: "0-100%"
          - title: "限流/拒绝事件"
            metric: [global.throttled_requests_total, global.rejected_requests_total]
            type: bar
      - title: "租户 Alpha
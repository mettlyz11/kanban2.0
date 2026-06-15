# openclaw_deployment_config_guide

> 任务: 搭建OpenClaw子代理的控制框架 [04291956]
> 附件类型: 部署与配置手册
> 生成时间: 2026-05-04 17:26

# 搭建OpenClaw子代理的控制框架 [04291956] 部署与配置手册

**文档版本**: v1.0  
**发布日期**: 2025-01-15  
**适用对象**: 运维工程师、DevOps工程师、系统管理员  
**保密级别**: 内部公开  

---

## 1. 基础运行环境与依赖版本要求

### 1.1 硬件最低配置

| 组件 | 规格要求 |
|------|----------|
| CPU | 4核 x86_64（ARM64需额外编译适配） |
| 内存 | 16GB RAM（推荐32GB） |
| 磁盘 | 100GB SSD（生产环境建议300GB+） |
| 网络 | 1Gbps 内网带宽，外网需开放HTTPS(443)及gRPC(50051)端口 |

### 1.2 操作系统支持

| 操作系统 | 内核版本 | 已验证 |
|----------|----------|--------|
| Ubuntu 22.04 LTS | 5.15+ | ✅ |
| CentOS 7.9+ | 3.10+ | ✅ |
| Rocky Linux 9 | 5.14+ | ✅ |
| Debian 12 | 6.1+ | ✅ |

### 1.3 依赖软件版本

| 组件 | 版本 | 安装方式 |
|------|------|----------|
| Python | 3.10.12+ | pyenv / 系统包管理器 |
| Node.js | 20.11.0+ | nvm / 官方源 |
| Docker | 24.0.7+ | 官方安装脚本 |
| Docker Compose | 2.24.1+ | 独立二进制文件 |
| Kubernetes | 1.28.4+ | kubeadm / 托管集群 |
| OpenClaw Core | v0.4.2 | 容器镜像 (`openclaw/core:0.4.2`) |
| Prometheus | 2.50.1+ | 容器部署 |
| Grafana | 10.3.1+ | 容器部署 |
| PostgreSQL | 15.5+ | 容器或RDS |

### 1.4 Python依赖（用于子代理插件开发）

```txt
# requirements.txt
openclaw-sdk==0.4.2
pydantic==2.5.3
httpx==0.26.0
cryptography==41.0.7
grpcio==1.60.0
protobuf==4.25.1
psutil==5.9.8
pyyaml==6.0.1
```

---

## 2. 环境变量注入与API密钥安全存储

### 2.1 敏感凭证分类

| 凭证类型 | 示例变量名 | 来源 |
|----------|------------|------|
| 数据库密码 | `DB_PASSWORD` | 随机生成32位+ |
| API密钥 | `OPENCLAW_API_KEY` | 管理平台生成 |
| JWT签名密钥 | `JWT_SECRET` | 随机生成64字节hex |
| 云服务密钥 | `AWS_SECRET_ACCESS_KEY` | 云厂商控制台 |
| 监控认证 | `GRAFANA_ADMIN_PASSWORD` | 随机生成24位+ |

### 2.2 密钥生成示例

```bash
# 生成32字节随机密钥（hex格式）
openssl rand -hex 32 > /etc/openclaw/secrets/api_key.txt

# 生成JWT签名密钥（64字节）
openssl rand -hex 64 > /etc/openclaw/secrets/jwt_secret.txt

# 生成数据库密码（包含特殊字符）
python3 -c "import secrets;print(secrets.token_urlsafe(32))" > /etc/openclaw/secrets/db_password.txt
```

### 2.3 环境变量文件（`.env`模板）

```ini
# .env.production
# ===== 核心配置 =====
OPENCLAW_API_KEY_FILE=/run/secrets/openclaw_api_key
JWT_SECRET_FILE=/run/secrets/jwt_secret

# ===== 数据库 =====
DB_HOST=postgres-cluster.openclaw.svc
DB_PORT=5432
DB_NAME=openclaw_prod
DB_USER=openclaw_admin
DB_PASSWORD_FILE=/run/secrets/db_password

# ===== Redis（可选，用于缓存） =====
REDIS_HOST=redis.openclaw.svc
REDIS_PORT=6379
REDIS_DB=0

# ===== 监控 =====
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
GRAFANA_ADMIN_PASSWORD_FILE=/run/secrets/grafana_admin

# ===== 日志 =====
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_OUTPUT_DIR=/var/log/openclaw
```

### 2.4 Docker Secrets 使用规范

```yaml
# docker-compose.yml 片段
services:
  openclaw-core:
    image: openclaw/core:0.4.2
    secrets:
      - openclaw_api_key
      - jwt_secret
      - db_password
    environment:
      OPENCLAW_API_KEY_FILE: /run/secrets/openclaw_api_key
      JWT_SECRET_FILE: /run/secrets/jwt_secret
      DB_PASSWORD_FILE: /run/secrets/db_password

secrets:
  openclaw_api_key:
    file: ./secrets/openclaw_api_key.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  db_password:
    file: ./secrets/db_password.txt
```

### 2.5 Kubernetes Secret 创建

```bash
# 创建命名空间
kubectl create namespace openclaw-prod

# 创建Secrets
kubectl create secret generic openclaw-core-secrets \
  --namespace openclaw-prod \
  --from-file=openclaw_api_key=./secrets/openclaw_api_key.txt \
  --from-file=jwt_secret=./secrets/jwt_secret.txt \
  --from-file=db_password=./secrets/db_password.txt

# 验证
kubectl get secrets -n openclaw-prod
```

---

## 3. 容器化部署方案

### 3.1 Docker Compose 完整部署（单机测试环境）

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15.5
    container_name: openclaw-db
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    environment:
      POSTGRES_DB: openclaw
      POSTGRES_USER: openclaw_admin
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U openclaw_admin"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7.2-alpine
    container_name: openclaw-redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data

  openclaw-core:
    image: openclaw/core:0.4.2
    container_name: openclaw-core
    restart: unless-stopped
    ports:
      - "8080:8080"    # REST API
      - "50051:50051"  # gRPC
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./config:/etc/openclaw:ro
      - ./plugins:/opt/openclaw/plugins
      - openclaw_logs:/var/log/openclaw
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: openclaw
      DB_USER: openclaw_admin
      REDIS_HOST: redis
      REDIS_PORT: 6379
    secrets:
      - openclaw_api_key
      - jwt_secret
      - db_password
    env_file:
      - .env.production

  prometheus:
    image: prom/prometheus:v2.50.1
    container_name: openclaw-prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:10.3.1
    container_name: openclaw-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro
    environment:
      GF_SECURITY_ADMIN_PASSWORD__FILE: /run/secrets/grafana_admin
    secrets:
      - grafana_admin

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
  openclaw_logs:

secrets:
  openclaw_api_key:
    file: ./secrets/openclaw_api_key.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  db_password:
    file: ./secrets/db_password.txt
  grafana_admin:
    file: ./secrets/grafana_admin.txt
```

### 3.2 Kubernetes 部署（生产环境）

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openclaw-core
  namespace: openclaw-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: openclaw-core
  template:
    metadata:
      labels:
        app: openclaw-core
    spec:
      serviceAccountName: openclaw-sa
      containers:
      - name: core
        image: openclaw/core:0.4.2
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 50051
          name: grpc
        env:
        - name: DB_HOST
          value: "postgres-service.openclaw-prod.svc.cluster.local"
        - name: DB_PORT
          value: "5432"
        - name: DB_NAME
          value: "openclaw_prod"
        - name: DB_USER
          value: "openclaw_admin"
        - name: REDIS_HOST
          value: "redis-service.openclaw-prod.svc.cluster.local"
        - name: LOG_LEVEL
          value: "INFO"
        - name: PROMETHEUS_ENABLED
          value: "true"
        envFrom:
        - secretRef:
            name: openclaw-core-secrets
        volumeMounts:
        - name: config
          mountPath: /etc/openclaw
          readOnly: true
        - name: logs
          mountPath: /var/log/openclaw
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 15
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: openclaw-config
      - name: logs
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: openclaw-core-service
  namespace: openclaw-prod
spec:
  selector:
    app: openclaw-core
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: grpc
    port: 50051
    targetPort: 50051
  type: ClusterIP
```

### 3.3 部署验证脚本

```bash
#!/bin/bash
# deploy_verify.sh

echo "=== OpenClaw 部署验证脚本 ==="

# 检查容器状态
echo "[1/5] 检查Docker容器状态..."
docker ps --filter "name=openclaw" --format "table {{.Names}}\t{{.Status}}"

# 检查API健康状态
echo "[2/5] 验证API健康检查..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/healthz
if [ $? -eq 0 ]; then echo " - OK"; else echo " - FAILED"; fi

# 检查gRPC连接
echo "[3/5] 验证gRPC服务..."
grpcurl -plaintext localhost:50051 list 2>/dev/null | head -5

# 检查数据库连接
echo "[4/5] 验证数据库连接..."
docker exec openclaw-db pg_isready -U openclaw_admin

# 检查监控端点
echo "[5/5] 验证Prometheus指标..."
curl -s http://localhost:9090/api/v1/query?query=up | jq '.data.result[].metric'

echo "=== 验证完成 ==="
```

---

## 4. 日志采集与Prometheus/Grafana监控接入

### 4.1 日志采集配置

```yaml
# promtail-config.yml（用于Loki日志采集）
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
- job_name: openclaw-logs
  static_configs:
  - targets:
      - localhost
    labels:
      job: openclaw
      __path__: /var/log/openclaw/*.log
  pipeline_stages:
  - json:
      expressions:
        level: level
        module: module
        trace_id: trace_id
  - labels:
      level:
      module:
```

### 4.2 Prometheus 采集配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'openclaw-core'
    scrape_interval: 10s
    metrics_path: '/metrics'
    static_configs:
      - targets:
        - 'openclaw-core:8080'
        labels:
          service: 'openclaw-core'
          environment: 'production'

  - job_name: 'openclaw-agents'
    scrape_interval: 15s
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - openclaw-prod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        regex: openclaw-agent
        action: keep
      - source_labels: [__address__]
        action: replace
        regex: ([^:]+)(?::\d+)?
        replacement: $1:9100
        target_label: __address__
```

### 4.3 Grafana 仪表盘配置

```json
// grafana-dashboard.json (关键指标面板)
{
  "dashboard": {
    "title": "OpenClaw 子代理监控",
    "tags": ["openclaw", "agents"],
    "timezone": "browser",
    "panels": [
      {
        "title": "活跃子代理数量",
        "type": "stat",
        "datasource": "Prometheus",
        "targets": [{
          "expr": "count(openclaw_agent_uptime_seconds > 0)",
          "legendFormat": "活跃代理数"
        }]
      },
      {
        "title": "请求延迟 P99",
        "type": "timeseries",
        "datasource": "Prometheus",
        "targets": [{
          "expr": "histogram_quantile(0.99, sum(rate(openclaw_request_duration_seconds_bucket[5m])) by (le, agent_type))",
          "legendFormat": "{{agent_type}}"
        }]
      },
      {
        "title": "错误率",
        "type": "timeseries",
        "datasource": "Prometheus",
        "targets": [{
          "expr": "sum(rate(openclaw_errors_total[5m])) by (agent_type)",
          "legendFormat": "{{agent_type}}"
        }]
      }
    ]
  }
}
```

### 4.4 告警规则

```yaml
# alert_rules.yml
groups:
  - name: openclaw-alerts
    rules:
      - alert: AgentDown
        expr: up{job="openclaw-agents"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "子代理 {{ $labels.instance }} 已离线超过5分钟"

      - alert: HighErrorRate
        expr: rate(openclaw_errors_total[5m]) > 0.1
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "错误率超过10%（最近5分钟）"

      - alert: AgentMemoryHigh
        expr: process_resident_memory_bytes{job="openclaw-agents
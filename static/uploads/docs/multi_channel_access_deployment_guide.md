# multi_channel_access_deployment_guide

> 任务: 设计多channel信息接入模块 [04291942]
> 附件类型: 部署集成指南
> 生成时间: 2026-05-04 16:27

# 多Channel信息接入模块部署集成指南

**文档版本**: v1.0  
**文档编号**: DEPLOY-GUIDE-MULTI-CHANNEL-001  
**创建日期**: 2024-01-15  
**适用对象**: 开发人员、运维人员、系统集成工程师  

---

## 1. 环境要求

### 1.1 操作系统要求

| 操作系统 | 版本要求 | 备注 |
|---------|---------|------|
| Linux (推荐) | CentOS 7.9+/Ubuntu 20.04+/Debian 11+ | 生产环境首选 |
| Windows Server | 2019/2022 | 仅用于开发测试 |
| macOS | 12+ | 仅用于本地开发 |

### 1.2 运行时环境

| 组件 | 最低版本 | 推荐版本 | 说明 |
|------|---------|---------|------|
| JDK | 11 | 17 LTS | 必须为64位版本 |
| Maven | 3.6.3 | 3.9.6 | 构建工具 |
| Docker | 20.10+ | 24.0+ | 容器化部署 |
| Docker Compose | 1.29+ | 2.24+ | 多容器编排 |

### 1.3 依赖服务

| 服务 | 版本要求 | 端口 | 用途 |
|------|---------|------|------|
| Redis | 6.x+ | 6379 | 消息缓存与去重 |
| Kafka | 2.8+ | 9092 | 消息队列 |
| MySQL | 8.0+ | 3306 | 配置与状态存储 |
| Zookeeper | 3.7+ | 2181 | Kafka协调服务 |
| Prometheus | 2.45+ | 9090 | 指标监控 |
| Grafana | 9.5+ | 3000 | 可视化面板 |

### 1.4 硬件要求

| 部署规模 | CPU | 内存 | 磁盘 | 网络 |
|---------|-----|------|------|------|
| 单机测试 | 2核 | 4GB | 20GB SSD | 1Gbps |
| 生产最小 | 4核 | 8GB | 100GB SSD | 1Gbps |
| 生产推荐 | 8核+ | 16GB+ | 500GB SSD | 10Gbps |

---

## 2. 构建与打包步骤

### 2.1 源码获取

```bash
# 克隆代码仓库
git clone https://github.com/your-org/multi-channel-ingestion.git
cd multi-channel-ingestion

# 切换到稳定分支
git checkout release/v1.0.0

# 验证代码完整性
git verify-commit HEAD
```

### 2.2 Maven构建

```bash
# 构建前检查
mvn --version  # 确保版本 >= 3.6.3
java -version  # 确保版本 >= 11

# 清理并构建
mvn clean package -DskipTests=true

# 构建并运行单元测试
mvn clean package

# 构建并生成覆盖率报告
mvn clean package jacoco:report

# 构建产物位置
ls -la target/multi-channel-ingestion-*.jar
# 输出: target/multi-channel-ingestion-1.0.0.jar
```

### 2.3 Docker镜像构建

```dockerfile
# Dockerfile
FROM eclipse-temurin:17-jre-alpine

# 设置时区
RUN apk add --no-cache tzdata \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone

# 创建运行用户
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# 创建工作目录
WORKDIR /app

# 复制应用JAR
COPY target/multi-channel-ingestion-*.jar app.jar

# 复制配置文件模板
COPY src/main/resources/application.yml /app/config/

# 设置权限
RUN chown -R appuser:appgroup /app

# 暴露端口
EXPOSE 8080 8081 9090

# 切换用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://localhost:8080/actuator/health || exit 1

# 启动命令
ENTRYPOINT ["java", \
    "-Djava.security.egd=file:/dev/./urandom", \
    "-XX:+UseContainerSupport", \
    "-XX:MaxRAMPercentage=75.0", \
    "-jar", "app.jar", \
    "--spring.config.additional-location=/app/config/"]
```

```bash
# 构建Docker镜像
docker build -t multi-channel-ingestion:1.0.0 .

# 构建并指定仓库标签
docker build -t registry.example.com/multi-channel-ingestion:1.0.0 .

# 推送镜像到私有仓库
docker push registry.example.com/multi-channel-ingestion:1.0.0
```

### 2.4 Docker Compose编排

```yaml
# docker-compose.yml
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"
    volumes:
      - zookeeper-data:/var/lib/zookeeper/data
    networks:
      - channel-network

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"
    volumes:
      - kafka-data:/var/lib/kafka/data
    networks:
      - channel-network

  redis:
    image: redis:7.2-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD:-changeme} --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - channel-network

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-root123}
      MYSQL_DATABASE: multi_channel
      MYSQL_USER: channel_user
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-channel123}
    ports:
      - "3306:3306"
    volumes:
      - mysql-data:/var/lib/mysql
      - ./init-scripts:/docker-entrypoint-initdb.d
    networks:
      - channel-network

  app:
    image: multi-channel-ingestion:1.0.0
    depends_on:
      - kafka
      - redis
      - mysql
    environment:
      SPRING_PROFILES_ACTIVE: prod
      SPRING_DATASOURCE_URL: jdbc:mysql://mysql:3306/multi_channel?useSSL=false&allowPublicKeyRetrieval=true
      SPRING_DATASOURCE_USERNAME: channel_user
      SPRING_DATASOURCE_PASSWORD: ${MYSQL_PASSWORD:-channel123}
      SPRING_REDIS_HOST: redis
      SPRING_REDIS_PASSWORD: ${REDIS_PASSWORD:-changeme}
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
    ports:
      - "8080:8080"
      - "8081:8081"
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    networks:
      - channel-network

volumes:
  zookeeper-data:
  kafka-data:
  redis-data:
  mysql-data:

networks:
  channel-network:
    driver: bridge
```

---

## 3. 配置说明

### 3.1 核心配置文件

```yaml
# application-prod.yml
server:
  port: 8080
  shutdown: graceful
  tomcat:
    max-threads: 200
    max-connections: 1000
    accept-count: 100

spring:
  application:
    name: multi-channel-ingestion
  
  datasource:
    url: jdbc:mysql://${MYSQL_HOST:localhost}:3306/multi_channel?useSSL=false&serverTimezone=Asia/Shanghai
    username: ${MYSQL_USERNAME:channel_user}
    password: ${MYSQL_PASSWORD:channel123}
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      idle-timeout: 300000
      connection-timeout: 30000
      max-lifetime: 1800000
  
  redis:
    host: ${REDIS_HOST:localhost}
    port: 6379
    password: ${REDIS_PASSWORD:changeme}
    timeout: 5000
    lettuce:
      pool:
        max-active: 16
        max-idle: 8
        min-idle: 4

  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP_SERVERS:localhost:9092}
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer
      acks: all
      retries: 3
      batch-size: 16384
      linger-ms: 5
    consumer:
      group-id: multi-channel-consumer-group
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      auto-offset-reset: earliest
      enable-auto-commit: false
      max-poll-records: 500

# 多通道配置
channel:
  config:
    # 支持的通道类型: SMS, EMAIL, WECHAT, APP_PUSH, WEBHOOK
    types:
      - SMS
      - EMAIL
      - WECHAT
      - APP_PUSH
      - WEBHOOK
    
    # 各通道配置
    sms:
      enabled: true
      provider: aliyun  # 可选: aliyun, tencent, aws
      access-key: ${SMS_ACCESS_KEY}
      secret-key: ${SMS_SECRET_KEY}
      sign-name: 通知中心
      rate-limit: 100  # 每秒限制
      retry-count: 3
      timeout-ms: 5000
    
    email:
      enabled: true
      host: smtp.example.com
      port: 587
      username: ${EMAIL_USERNAME}
      password: ${EMAIL_PASSWORD}
      from-address: noreply@example.com
      ssl: true
      rate-limit: 50
    
    wechat:
      enabled: true
      app-id: ${WECHAT_APP_ID}
      app-secret: ${WECHAT_APP_SECRET}
      template-id: ${WECHAT_TEMPLATE_ID}
      rate-limit: 200
    
    app-push:
      enabled: true
      platform: jpush  # 可选: jpush, xiaomi, huawei
      app-key: ${APP_PUSH_KEY}
      master-secret: ${APP_PUSH_SECRET}
      rate-limit: 500
    
    webhook:
      enabled: true
      default-url: ${WEBHOOK_DEFAULT_URL}
      signature-key: ${WEBHOOK_SIGN_KEY}
      rate-limit: 300

# 消息路由配置
routing:
  rules:
    - priority: 1
      condition: "type == 'URGENT' && channel == 'ALL'"
      channels: ["SMS", "WECHAT", "APP_PUSH"]
    - priority: 2
      condition: "type == 'NOTIFICATION' && channel == 'ALL'"
      channels: ["WECHAT", "APP_PUSH"]
    - priority: 3
      condition: "type == 'MARKETING' && channel == 'ALL'"
      channels: ["EMAIL", "WEBHOOK"]
    - priority: 4
      condition: "channel == 'SMS'"
      channels: ["SMS"]
    - priority: 5
      condition: "channel == 'EMAIL'"
      channels: ["EMAIL"]

# 消息去重配置
deduplication:
  enabled: true
  strategy: message_id  # 可选: message_id, content_hash, both
  cache-duration: 3600  # 秒
  cache-type: redis  # 可选: redis, memory

# 重试配置
retry:
  max-attempts: 3
  initial-interval: 1000  # 毫秒
  multiplier: 2.0
  max-interval: 30000

# 监控配置
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
  metrics:
    export:
      prometheus:
        enabled: true
  endpoint:
    health:
      show-details: always
```

### 3.2 环境变量清单

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `MYSQL_HOST` | MySQL主机地址 | localhost | 是 |
| `MYSQL_PORT` | MySQL端口 | 3306 | 否 |
| `MYSQL_USERNAME` | MySQL用户名 | channel_user | 是 |
| `MYSQL_PASSWORD` | MySQL密码 | channel123 | 是 |
| `REDIS_HOST` | Redis主机地址 | localhost | 是 |
| `REDIS_PORT` | Redis端口 | 6379 | 否 |
| `REDIS_PASSWORD` | Redis密码 | changeme | 是 |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka连接地址 | localhost:9092 | 是 |
| `SMS_ACCESS_KEY` | 短信服务AccessKey | - | 条件 |
| `SMS_SECRET_KEY` | 短信服务SecretKey | - | 条件 |
| `EMAIL_USERNAME` | 邮箱用户名 | - | 条件 |
| `EMAIL_PASSWORD` | 邮箱密码 | - | 条件 |
| `WECHAT_APP_ID` | 微信AppID | - | 条件 |
| `WECHAT_APP_SECRET` | 微信AppSecret | - | 条件 |
| `APP_PUSH_KEY` | 推送服务Key | - | 条件 |
| `APP_PUSH_SECRET` | 推送服务Secret | - | 条件 |
| `WEBHOOK_DEFAULT_URL` | Webhook默认地址 | - | 条件 |
| `WEBHOOK_SIGN_KEY` | Webhook签名密钥 | - | 条件 |
| `LOG_LEVEL` | 日志级别 | INFO | 否 |
| `JAVA_OPTS` | JVM参数 | - | 否 |

---

## 4. 部署拓扑建议

### 4.1 单机部署（开发测试环境）

```
┌─────────────────────────────────────────────────────┐
│                    单台服务器                         │
│  ┌──────────────────────────────────────────────┐   │
│  │          Docker Compose 编排                  │   │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌──────┐  │   │
│  │  │ZooK │ │Kafka│ │Redis│ │MySQL│ │ App  │  │   │
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └──────┘  │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 4.2 生产集群部署

```
                          ┌─────────────┐
                          │  负载均衡器   │
                          │  Nginx/HA   │
                          └──────┬──────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
   ┌──────▼──────┐       ┌──────▼──────┐       ┌──────▼──────┐
   │ App实例 1    │       │ App实例 2    │       │ App实例 3    │
   │ 10.0.1.10   │       │ 10.0.1.11   │       │ 10.0.1.12   │
   │ port:8080   │       │ port:8080   │       │ port:8080   │
   └──────┬──────┘       └──────┬──────┘       └──────┬──────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                          ┌──────▼──────┐
                          │   Kafka集群  │
                          │  (3节点)     │
                          └──────┬──────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
   ┌──────▼──────┐       ┌──────▼──────┐       ┌──────▼──────┐
   │ Redis主从
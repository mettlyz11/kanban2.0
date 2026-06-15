# multi_channel_access_test_plan

> 任务: 设计多channel信息接入模块 [04291942]
> 附件类型: 测试方案
> 生成时间: 2026-05-04 16:26

# 多Channel信息接入模块测试方案

## 1. 测试范围与策略

### 1.1 测试目标
本测试方案旨在验证多Channel信息接入模块的功能正确性、性能稳定性和可靠性。模块核心能力包括：支持多种类型Channel（HTTP、WebSocket、gRPC、MQTT）的并发接入，提供统一的适配器接口，实现消息隔离与锁机制保障，确保数据不丢失、不重复。

### 1.2 测试范围
- **功能测试**：Channel适配器的创建、连接、断开、重连功能；消息的接收、转换、路由、分发功能；锁机制的并发控制正确性。
- **集成测试**：多Channel同时接入时的消息路由验证；消息隔离性验证（不同Channel消息互不干扰）；异常场景（网络断开、Channel超时、消息格式错误）下的恢复能力。
- **性能测试**：单Channel吞吐量；多Channel并发接入时的总体吞吐量；高并发下的消息延迟（P99、P95、P50）；资源消耗（CPU、内存、网络带宽）。
- **稳定性测试**：长时间运行（24小时）下的内存泄漏检测；消息丢失率；连接稳定性。

### 1.3 测试策略
采用分层测试策略：单元测试覆盖最小可测试单元，集成测试验证模块间交互，压测评估系统极限。测试环境使用Docker容器化部署，模拟真实生产环境。自动化测试框架选用JUnit 5 + Mockito进行单元测试，Testcontainers用于集成测试，JMeter + Locust用于压测。

## 2. 单元测试覆盖

### 2.1 Channel适配器测试
每个Channel类型（HTTP、WebSocket、gRPC、MQTT）需独立测试适配器接口实现。

#### 2.1.1 测试用例设计
| 测试ID | 测试名称 | 输入 | 预期输出 | 覆盖条件 |
|--------|----------|------|----------|----------|
| UT-001 | HTTP适配器连接成功 | 有效URL、超时5s | 返回Connection对象，状态CONNECTED | 正常连接 |
| UT-002 | HTTP适配器连接失败 | 无效URL | 抛出ConnectionException，状态FAILED | 连接失败 |
| UT-003 | WebSocket适配器重连 | 模拟第一次连接成功，第二次断开 | 自动重连3次，最终状态RECONNECTED | 重连机制 |
| UT-004 | gRPC适配器消息转换 | 输入Protobuf消息 | 输出统一内部消息格式 | 消息转换 |
| UT-005 | MQTT适配器订阅主题 | 主题名“sensor/temp” | 成功订阅，收到消息回调 | 订阅功能 |

#### 2.1.2 示例代码（JUnit 5 + Mockito）
```java
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class HttpChannelAdapterTest {
    @Mock
    private HttpClient httpClient;
    private HttpChannelAdapter adapter;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        adapter = new HttpChannelAdapter("http://example.com/api", 5000);
        adapter.setHttpClient(httpClient);
    }

    @Test
    void testConnectSuccess() {
        when(httpClient.connect(anyString(), anyInt())).thenReturn(new Connection(true));
        assertDoesNotThrow(() -> adapter.connect());
        assertEquals(ChannelState.CONNECTED, adapter.getState());
    }

    @Test
    void testConnectFailure() {
        when(httpClient.connect(anyString(), anyInt())).thenThrow(new ConnectionException("Timeout"));
        assertThrows(ConnectionException.class, () -> adapter.connect());
        assertEquals(ChannelState.FAILED, adapter.getState());
    }

    @Test
    void testReceiveMessage() {
        String rawMessage = "{\"id\":1,\"data\":\"test\"}";
        when(httpClient.receive()).thenReturn(rawMessage);
        InternalMessage msg = adapter.receive();
        assertEquals(1, msg.getId());
        assertEquals("test", msg.getData());
    }
}
```

### 2.2 锁机制测试
锁机制确保同一Channel的消息处理顺序正确，不同Channel间并行处理。

#### 2.2.1 锁粒度测试
| 测试ID | 测试名称 | 场景 | 预期结果 |
|--------|----------|------|----------|
| UT-010 | 同一Channel串行处理 | 100个消息并发提交到同一Channel | 消息按提交顺序处理 |
| UT-011 | 不同Channel并行处理 | 2个Channel各50个消息同时提交 | 总处理时间接近单Channel一半 |
| UT-012 | 锁超时释放 | 某消息处理超过5s | 锁自动释放，不阻塞后续消息 |

#### 2.2.2 示例代码
```java
@Test
void testChannelLockSerialization() throws InterruptedException {
    ChannelLockManager lockManager = new ChannelLockManager();
    String channelId = "ch1";
    List<Integer> processedOrder = Collections.synchronizedList(new ArrayList<>());
    CountDownLatch latch = new CountDownLatch(100);

    // 并发提交100个消息到同一Channel
    for (int i = 0; i < 100; i++) {
        final int msgId = i;
        new Thread(() -> {
            lockManager.lock(channelId);
            try {
                Thread.sleep(1); // 模拟处理
                processedOrder.add(msgId);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } finally {
                lockManager.unlock(channelId);
                latch.countDown();
            }
        }).start();
    }
    latch.await(10, TimeUnit.SECONDS);
    // 验证顺序递增
    for (int i = 0; i < processedOrder.size() - 1; i++) {
        assertTrue(processedOrder.get(i) < processedOrder.get(i + 1));
    }
}
```

### 2.3 消息隔离测试
验证不同Channel的消息不会互相影响。

| 测试ID | 测试名称 | 场景 | 预期结果 |
|--------|----------|------|----------|
| UT-020 | 消息隔离性 | Channel A发送消息M1，Channel B发送M2 | M1只路由到A的消费者，M2只路由到B的消费者 |
| UT-021 | 消息ID冲突 | 两个Channel使用相同消息ID | 系统通过Channel+ID复合键唯一标识 |

## 3. 集成测试方案

### 3.1 测试环境
- **硬件**：4核CPU、16GB内存、SSD硬盘
- **软件**：Docker 20.10+、Docker Compose
- **组件**：消息队列（RabbitMQ 3.9）、数据库（PostgreSQL 13）、测试服务（Java 17）
- **网络**：100Mbps内网，延迟<1ms

### 3.2 模拟多Channel并发接入

#### 3.2.1 测试场景
| 场景ID | 描述 | Channel数量 | 消息速率 | 持续时间 |
|--------|------|-------------|----------|----------|
| IT-001 | 基础并发 | 4（HTTP、WS、gRPC、MQTT各1） | 100 msg/s per channel | 5分钟 |
| IT-002 | 高并发 | 20（HTTP 10、WS 5、gRPC 3、MQTT 2） | 500 msg/s per channel | 10分钟 |
| IT-003 | 混合负载 | 10个Channel（随机类型） | 随机速率100-1000 msg/s | 30分钟 |

#### 3.2.2 消息路由验证
使用Testcontainers启动RabbitMQ和PostgreSQL，验证消息正确路由。
```java
@Testcontainers
class IntegrationTest {
    @Container
    static RabbitMQContainer rabbitMQ = new RabbitMQContainer("rabbitmq:3.9-management");
    @Container
    static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:13");

    @Test
    void testMessageRouting() throws Exception {
        // 启动多Channel接入模块
        MultiChannelModule module = new MultiChannelModule(rabbitMQ.getHost(), rabbitMQ.getPort());
        module.start();
        
        // 创建两个Channel
        ChannelConfig ch1 = new ChannelConfig("ch1", ChannelType.HTTP, "http://test1.com");
        ChannelConfig ch2 = new ChannelConfig("ch2", ChannelType.WEBSOCKET, "ws://test2.com");
        module.registerChannel(ch1);
        module.registerChannel(ch2);
        
        // 发送消息
        module.send("ch1", new InternalMessage(1, "data1"));
        module.send("ch2", new InternalMessage(2, "data2"));
        
        // 验证路由
        List<InternalMessage> ch1Messages = module.getMessages("ch1");
        List<InternalMessage> ch2Messages = module.getMessages("ch2");
        assertEquals(1, ch1Messages.size());
        assertEquals("data1", ch1Messages.get(0).getData());
        assertEquals(1, ch2Messages.size());
        assertEquals("data2", ch2Messages.get(0).getData());
    }
}
```

### 3.3 异常场景测试
| 场景ID | 异常类型 | 注入方式 | 预期行为 |
|--------|----------|----------|----------|
| IT-010 | Channel网络断开 | 使用iptables阻断端口 | 模块自动重连，消息缓存，重连后恢复 |
| IT-011 | 消息格式错误 | 发送非法JSON | 模块记录错误日志，返回错误码，不崩溃 |
| IT-012 | 锁死锁 | 模拟两个Channel互相等待 | 锁超时机制触发，释放资源 |

## 4. 并发压测方案

### 4.1 压测场景设计

#### 4.1.1 单Channel吞吐量测试
| 参数 | 值 |
|------|-----|
| Channel类型 | HTTP |
| 消息大小 | 1KB、10KB、100KB |
| 并发连接数 | 1、10、50、100 |
| 持续时间 | 60秒 |
| 目标 | 找到最大吞吐量（msg/s） |

#### 4.1.2 多Channel并发压测
| 场景 | Channel数量 | 每条消息大小 | 总并发数 | 目标 |
|------|-------------|-------------|---------|------|
| 轻量 | 10 | 1KB | 100 | 验证隔离性 |
| 中等 | 50 | 10KB | 500 | 验证资源消耗 |
| 重量 | 100 | 100KB | 1000 | 验证系统极限 |

### 4.2 性能指标定义

| 指标 | 定义 | 目标值 |
|------|------|--------|
| 吞吐量 | 每秒处理的消息数（msg/s） | ≥ 5000 msg/s（总） |
| P50延迟 | 50%消息的端到端延迟 | ≤ 10ms |
| P95延迟 | 95%消息的延迟 | ≤ 50ms |
| P99延迟 | 99%消息的延迟 | ≤ 100ms |
| 错误率 | 失败消息占比 | ≤ 0.1% |
| CPU使用率 | 平均CPU占用 | ≤ 80% |
| 内存使用 | 最大堆内存 | ≤ 4GB |

### 4.3 压测工具配置

#### 4.3.1 JMeter脚本示例
```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="MultiChannel Load Test">
      <elementProp name="TestPlan.user_defined_variables" elementType="Arguments">
        <collectionProp name="Arguments.arguments">
          <elementProp name="target_url" elementType="Argument">
            <stringProp name="Argument.name">target_url</stringProp>
            <stringProp name="Argument.value">http://localhost:8080/api/channel</stringProp>
          </elementProp>
        </collectionProp>
      </elementProp>
    </TestPlan>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="HTTP Channel Group">
        <intProp name="ThreadGroup.num_threads">100</intProp>
        <intProp name="ThreadGroup.ramp_time">10</intProp>
        <longProp name="ThreadGroup.duration">60</longProp>
      </ThreadGroup>
      <hashTree>
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="Send Message">
          <stringProp name="HTTPSampler.path">${target_url}/ch1/message</stringProp>
          <stringProp name="HTTPSampler.method">POST</stringProp>
          <stringProp name="HTTPSampler.postBodyRaw">true</stringProp>
          <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
            <collectionProp name="Arguments.arguments">
              <elementProp name="" elementType="HTTPArgument">
                <stringProp name="Argument.value">{"id":1,"data":"test payload"}</stringProp>
              </elementProp>
            </collectionProp>
          </elementProp>
        </HTTPSamplerProxy>
        <hashTree/>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
```

#### 4.3.2 Locust脚本示例
```python
from locust import HttpUser, task, between
import random

class MultiChannelUser(HttpUser):
    wait_time = between(0.1, 0.5)
    
    def on_start(self):
        self.channel_id = random.choice(['ch1', 'ch2', 'ch3'])
    
    @task(3)
    def send_message(self):
        payload = {"id": random.randint(1, 1000), "data": "test"}
        self.client.post(f"/api/channel/{self.channel_id}/message", json=payload)
    
    @task(1)
    def get_status(self):
        self.client.get(f"/api/channel/{self.channel_id}/status")
```

## 5. 测试数据准备与Mock策略

### 5.1 测试数据生成

#### 5.1.1 消息数据模板
| 字段 | 类型 | 示例值 | 说明 |
|------|------|--------|------|
| id | Integer | 1-100000 | 自增唯一ID |
| channelId | String | "ch_001" | 所属Channel |
| timestamp | Long | 1700000000000 | 毫秒时间戳 |
| payload | JSON | {"sensor":"temp","value":25.5} | 业务数据 |
| priority | Integer | 1-5 | 优先级1最高 |

#### 5.1.2 批量数据生成脚本（Python）
```python
import json
import random
import time

def generate_test_data(num_messages=1000):
    data = []
    for i in range(num_messages):
        msg = {
            "id": i,
            "channelId": f"ch_{random.randint(1, 10):03d}",
            "timestamp": int(time.time() * 1000),
            "payload": {
                "sensor": random.choice(["temp", "humidity", "pressure"]),
                "value": round(random.uniform(0, 100), 2)
            },
            "priority": random.randint(1, 5)
        }
        data.append(msg)
    return data

# 生成10000条消息，保存为JSON文件
with open("test_data.json", "w") as f:
    json.dump(generate_test_data(10000), f, indent=2)
```

### 5.2 Mock策略

#### 5.2.1 外部依赖Mock清单
| 依赖 | Mock方式 | 工具 |
|------|----------|------|
| 数据库 | 内存H2数据库 | H2 2.1 |
| 消息队列 | Mockito模拟RabbitMQ客户端 | Mockito 4.0 |
| 第三方API | WireMock模拟HTTP端点 | WireMock 3.0 |
| 时间服务 | Clock固定时间 | Java Clock Mock |

#### 5.2.2 Mock配置示例（WireMock）
```java
import com.github.tomakehurst.wiremock.junit5.WireMockExtension;
import static com.github.tomakehurst.wiremock.client.WireMock.*;

@RegisterExtension
static WireMockExtension wireMock = new WireMockExtension(8089);

@Test
void testExternalApiCall() {
    // 模拟第三方API
    stubFor(post(urlEqualTo("/external/api"))
        .withRequestBody(containing("test"))
        .willReturn(aResponse()
            .withStatus(200)
            .withHeader("Content-Type", "application/json")
            .withBody("{\"result\":\"success\"}")));
    
    // 执行测试
    ChannelAdapter adapter = new HttpChannelAdapter("http://localhost:8089/external/api");
    adapter.connect();
    InternalMessage response = adapter.send(new InternalMessage(1, "test"));
    assertEquals("success", response.getResult());
}
```

## 6. 验收标准与通过条件

### 6.1 功能验收标准
| 编号 | 标准 | 验证方式 |
|------|------|----------|
| F-01 | 支持至少4种Channel类型（HTTP、WS、gRPC、MQTT） | 单元测试通过 |
| F-02 | 同一Channel消息按顺序处理 | 锁机制测试通过 |
| F-03 | 不同Channel消息完全隔离 | 集成测试通过 |
| F-04 | 连接断开后自动重连（最多3次） | 异常场景测试通过 |
| F-05 | 消息格式错误时给出明确错误码 | 错误处理测试通过 |

###
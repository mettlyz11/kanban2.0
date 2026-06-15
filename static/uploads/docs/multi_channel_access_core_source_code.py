# multi_channel_access_core_source_code

> 任务: 设计多channel信息接入模块 [04291942]
> 附件类型: 代码文件
> 生成时间: 2026-05-04 16:22

# 多Channel信息接入模块设计文档

## 1. 目录结构说明

```
multi-channel-adapter/
├── src/
│   └── main/
│       ├── java/
│       │   └── com/
│       │       └── example/
│       │           └── channeladapter/
│       │               ├── core/
│       │               │   ├── ChannelAdapter.java          # 核心接口
│       │               │   ├── MessageDispatcher.java       # 消息分发器接口
│       │               │   ├── SessionLock.java             # 会话锁接口
│       │               │   ├── BaseChannelAdapter.java      # 基础适配器抽象类
│       │               │   ├── DefaultSessionLock.java      # 默认锁实现
│       │               │   └── DmScopeIsolator.java         # DM域隔离器
│       │               ├── channel/
│       │               │   ├── EmailChannelAdapter.java     # 邮件通道适配器
│       │               │   ├── WebhookChannelAdapter.java   # Webhook通道适配器
│       │               │   └── SmsChannelAdapter.java       # 短信通道适配器(预留)
│       │               ├── config/
│       │               │   ├── ChannelAdapterConfig.java    # 配置类
│       │               │   └── ThreadPoolConfig.java        # 线程池配置
│       │               ├── model/
│       │               │   ├── Message.java                 # 消息模型
│       │               │   ├── ChannelMessage.java          # 通道消息
│       │               │   └── SessionContext.java          # 会话上下文
│       │               └── Application.java                 # 启动入口
│       └── resources/
│           ├── application.yml                              # 主配置文件
│           └── channel-config.json                          # 通道配置模板
└── pom.xml                                                  # Maven依赖
```

## 2. 核心接口定义

### 2.1 ChannelAdapter 接口

```java
package com.example.channeladapter.core;

import com.example.channeladapter.model.ChannelMessage;
import com.example.channeladapter.model.SessionContext;

/**
 * 通道适配器核心接口
 * 所有具体通道实现必须实现此接口
 */
public interface ChannelAdapter {

    /**
     * 初始化通道连接
     * @param config 通道配置参数
     * @throws Exception 初始化失败时抛出
     */
    void initialize(Object config) throws Exception;

    /**
     * 发送消息到指定通道
     * @param message 通道消息对象
     * @return 发送结果标识 (true=成功, false=失败)
     */
    boolean send(ChannelMessage message);

    /**
     * 接收消息（阻塞方式，适用于需要主动拉取的通道）
     * @param timeout 超时时间(毫秒)
     * @return 接收到的消息，超时返回null
     */
    ChannelMessage receive(long timeout);

    /**
     * 注册消息监听器（异步方式，适用于推送型通道）
     * @param listener 消息回调监听器
     */
    void registerListener(MessageListener listener);

    /**
     * 关闭通道连接，释放资源
     */
    void shutdown();

    /**
     * 获取通道类型标识
     * @return 通道类型字符串，如"email", "webhook"
     */
    String getChannelType();

    /**
     * 检查通道是否处于活跃状态
     * @return true=活跃, false=断开
     */
    boolean isActive();

    /**
     * 消息监听器内部接口
     */
    @FunctionalInterface
    interface MessageListener {
        void onMessage(ChannelMessage message);
    }
}
```

### 2.2 MessageDispatcher 接口

```java
package com.example.channeladapter.core;

import com.example.channeladapter.model.ChannelMessage;
import com.example.channeladapter.model.Message;

/**
 * 消息分发器
 * 负责将统一消息格式分发到不同通道
 */
public interface MessageDispatcher {

    /**
     * 注册通道适配器
     * @param channelType 通道类型
     * @param adapter     通道适配器实例
     */
    void registerChannel(String channelType, ChannelAdapter adapter);

    /**
     * 注销通道适配器
     * @param channelType 通道类型
     */
    void unregisterChannel(String channelType);

    /**
     * 分发消息到指定通道
     * @param channelType 目标通道类型
     * @param message     待分发消息
     * @return 分发结果
     */
    DispatchResult dispatch(String channelType, Message message);

    /**
     * 广播消息到所有已注册通道
     * @param message 待广播消息
     * @return 各通道分发结果映射
     */
    java.util.Map<String, DispatchResult> broadcast(Message message);

    /**
     * 分发结果封装类
     */
    class DispatchResult {
        private final boolean success;
        private final String errorMessage;
        private final long timestamp;

        public DispatchResult(boolean success, String errorMessage) {
            this.success = success;
            this.errorMessage = errorMessage;
            this.timestamp = System.currentTimeMillis();
        }

        public boolean isSuccess() { return success; }
        public String getErrorMessage() { return errorMessage; }
        public long getTimestamp() { return timestamp; }

        public static DispatchResult ok() {
            return new DispatchResult(true, null);
        }

        public static DispatchResult fail(String errorMessage) {
            return new DispatchResult(false, errorMessage);
        }
    }
}
```

### 2.3 SessionLock 接口

```java
package com.example.channeladapter.core;

/**
 * 会话锁接口
 * 用于确保同一会话的消息顺序处理，防止并发冲突
 */
public interface SessionLock {

    /**
     * 尝试获取锁
     * @param sessionId 会话唯一标识
     * @param timeout   等待超时时间(毫秒)
     * @return 获取锁成功返回true，超时返回false
     */
    boolean tryLock(String sessionId, long timeout);

    /**
     * 释放锁
     * @param sessionId 会话唯一标识
     */
    void unlock(String sessionId);

    /**
     * 检查锁是否被当前线程持有
     * @param sessionId 会话唯一标识
     * @return true=当前线程持有锁
     */
    boolean isHeldByCurrentThread(String sessionId);

    /**
     * 获取锁的当前持有者信息
     * @param sessionId 会话唯一标识
     * @return 持有者标识，无锁时返回null
     */
    String getLockHolder(String sessionId);
}
```

## 3. 基础实现

### 3.1 BaseChannelAdapter 抽象类

```java
package com.example.channeladapter.core;

import com.example.channeladapter.model.ChannelMessage;
import com.example.channeladapter.model.SessionContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 通道适配器基础抽象类
 * 提供通用逻辑：状态管理、日志记录、生命周期控制
 */
public abstract class BaseChannelAdapter implements ChannelAdapter {

    protected final Logger logger = LoggerFactory.getLogger(getClass());

    /** 通道活跃状态 */
    protected final AtomicBoolean active = new AtomicBoolean(false);

    /** 通道配置 */
    protected Object config;

    /** 消息监听器 */
    protected MessageListener listener;

    /** 会话锁实例 */
    protected final SessionLock sessionLock;

    public BaseChannelAdapter(SessionLock sessionLock) {
        this.sessionLock = sessionLock;
    }

    @Override
    public void initialize(Object config) throws Exception {
        this.config = config;
        logger.info("Initializing channel adapter: {}", getChannelType());
        doInitialize(config);
        active.set(true);
        logger.info("Channel adapter initialized: {}", getChannelType());
    }

    /**
     * 子类实现具体的初始化逻辑
     */
    protected abstract void doInitialize(Object config) throws Exception;

    @Override
    public boolean send(ChannelMessage message) {
        if (!active.get()) {
            logger.warn("Channel {} is not active, message dropped", getChannelType());
            return false;
        }

        String sessionId = message.getSessionId();
        boolean locked = false;
        try {
            if (sessionId != null) {
                locked = sessionLock.tryLock(sessionId, 5000);
                if (!locked) {
                    logger.warn("Failed to acquire lock for session: {}", sessionId);
                    return false;
                }
            }
            return doSend(message);
        } finally {
            if (locked) {
                sessionLock.unlock(sessionId);
            }
        }
    }

    /**
     * 子类实现具体的发送逻辑
     */
    protected abstract boolean doSend(ChannelMessage message);

    @Override
    public void registerListener(MessageListener listener) {
        this.listener = listener;
        logger.info("Listener registered for channel: {}", getChannelType());
    }

    @Override
    public void shutdown() {
        logger.info("Shutting down channel adapter: {}", getChannelType());
        active.set(false);
        doShutdown();
        logger.info("Channel adapter shut down: {}", getChannelType());
    }

    /**
     * 子类实现具体的关闭逻辑
     */
    protected abstract void doShutdown();

    @Override
    public boolean isActive() {
        return active.get();
    }
}
```

### 3.2 DefaultSessionLock 实现

```java
package com.example.channeladapter.core;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantLock;

/**
 * 默认会话锁实现
 * 使用ReentrantLock保证线程安全，支持可重入
 */
public class DefaultSessionLock implements SessionLock {

    private final ConcurrentHashMap<String, ReentrantLock> lockMap = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Thread> holderMap = new ConcurrentHashMap<>();

    @Override
    public boolean tryLock(String sessionId, long timeout) {
        ReentrantLock lock = lockMap.computeIfAbsent(sessionId, k -> new ReentrantLock());
        try {
            boolean acquired = lock.tryLock(timeout, java.util.concurrent.TimeUnit.MILLISECONDS);
            if (acquired) {
                holderMap.put(sessionId, Thread.currentThread());
            }
            return acquired;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    @Override
    public void unlock(String sessionId) {
        ReentrantLock lock = lockMap.get(sessionId);
        if (lock != null && lock.isHeldByCurrentThread()) {
            holderMap.remove(sessionId);
            lock.unlock();
        }
    }

    @Override
    public boolean isHeldByCurrentThread(String sessionId) {
        ReentrantLock lock = lockMap.get(sessionId);
        return lock != null && lock.isHeldByCurrentThread();
    }

    @Override
    public String getLockHolder(String sessionId) {
        Thread holder = holderMap.get(sessionId);
        return holder != null ? holder.getName() : null;
    }

    /**
     * 清理不再使用的锁（可定期调用）
     */
    public void cleanUnusedLocks() {
        lockMap.entrySet().removeIf(entry -> !entry.getValue().isLocked());
    }
}
```

### 3.3 DmScopeIsolator 域隔离器

```java
package com.example.channeladapter.core;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * DM域隔离器
 * 用于隔离不同数据域(Domain)的消息处理，确保域间互不影响
 */
public class DmScopeIsolator {

    private final Map<String, DomainContext> domainContexts = new ConcurrentHashMap<>();

    /**
     * 注册域上下文
     * @param domainId 域标识
     * @param config   域配置
     */
    public void registerDomain(String domainId, DomainConfig config) {
        domainContexts.put(domainId, new DomainContext(domainId, config));
        System.out.println("Domain registered: " + domainId + " with config: " + config);
    }

    /**
     * 在指定域内执行操作
     * @param domainId 域标识
     * @param task     待执行任务
     * @param <T>      返回值类型
     * @return 执行结果
     * @throws IllegalArgumentException 域不存在时抛出
     */
    public <T> T executeInDomain(String domainId, DomainTask<T> task) {
        DomainContext context = domainContexts.get(domainId);
        if (context == null) {
            throw new IllegalArgumentException("Domain not found: " + domainId);
        }
        // 设置线程局部变量隔离域上下文
        DomainContextHolder.set(context);
        try {
            return task.execute();
        } finally {
            DomainContextHolder.clear();
        }
    }

    /**
     * 获取指定域的配置
     */
    public DomainConfig getDomainConfig(String domainId) {
        DomainContext context = domainContexts.get(domainId);
        return context != null ? context.getConfig() : null;
    }

    /**
     * 域上下文内部类
     */
    private static class DomainContext {
        private final String domainId;
        private final DomainConfig config;

        public DomainContext(String domainId, DomainConfig config) {
            this.domainId = domainId;
            this.config = config;
        }

        public String getDomainId() { return domainId; }
        public DomainConfig getConfig() { return config; }
    }

    /**
     * 域配置类
     */
    public static class DomainConfig {
        private final int maxConcurrency;
        private final long messageTimeout;
        private final boolean enableAudit;

        public DomainConfig(int maxConcurrency, long messageTimeout, boolean enableAudit) {
            this.maxConcurrency = maxConcurrency;
            this.messageTimeout = messageTimeout;
            this.enableAudit = enableAudit;
        }

        public int getMaxConcurrency() { return maxConcurrency; }
        public long getMessageTimeout() { return messageTimeout; }
        public boolean isEnableAudit() { return enableAudit; }

        @Override
        public String toString() {
            return String.format("DomainConfig{maxConcurrency=%d, messageTimeout=%d, enableAudit=%b}",
                    maxConcurrency, messageTimeout, enableAudit);
        }
    }

    /**
     * 域任务函数式接口
     */
    @FunctionalInterface
    public interface DomainTask<T> {
        T execute();
    }

    /**
     * 域上下文持有者（线程局部变量）
     */
    private static class DomainContextHolder {
        private static final ThreadLocal<DomainContext> holder = new ThreadLocal<>();

        public static void set(DomainContext context) {
            holder.set(context);
        }

        public static DomainContext get() {
            return holder.get();
        }

        public static void clear() {
            holder.remove();
        }
    }
}
```

## 4. 示例Channel适配器

### 4.1 EmailChannelAdapter

```java
package com.example.channeladapter.channel;

import com.example.channeladapter.core.BaseChannelAdapter;
import com.example.channeladapter.core.SessionLock;
import com.example.channeladapter.model.ChannelMessage;
import java.util.Properties;
import javax.mail.*;
import javax.mail.internet.*;

/**
 * 邮件通道适配器
 * 支持SMTP协议发送邮件，支持SSL/TLS加密
 */
public class EmailChannelAdapter extends BaseChannelAdapter {

    private String smtpHost;
    private int smtpPort;
    private String username;
    private String password;
    private boolean useSSL;
    private Session mailSession;

    public EmailChannelAdapter(SessionLock sessionLock) {
        super(sessionLock);
    }

    @Override
    public String getChannelType() {
        return "email";
    }

    @Override
    protected void doInitialize(Object config) throws Exception {
        if (config instanceof EmailConfig) {
            EmailConfig emailConfig = (EmailConfig) config;
            this.smtpHost = emailConfig.getHost();
            this.smtpPort = emailConfig.getPort();
            this.username = emailConfig.getUsername();
            this.password = emailConfig.getPassword();
            this.useSSL = emailConfig.isUseSSL();

            Properties props = new Properties();
            props.put("mail.smtp.host", smtpHost);
            props.put("mail.smtp.port", smtpPort);
            if (useSSL) {
                props.put("mail.smtp.socketFactory.port", smtpPort);
                props.put("mail.smtp.socketFactory.class", "javax.net.ssl.SSLSocketFactory");
            }
            props.put("mail.smtp.auth", "true");

            Authenticator auth = new Authenticator() {
                @Override
                protected PasswordAuthentication getPasswordAuthentication() {
                    return new PasswordAuthentication(username, password);
                }
            };
            mailSession = Session.getInstance(props, auth);
            logger.info("Email session created for host: {}", smtpHost);
        } else {
            throw new IllegalArgumentException("Invalid config type for EmailChannelAdapter");
        }
    }

    @Override
    protected boolean doSend(ChannelMessage message) {
        try {
            MimeMessage mimeMessage = new MimeMessage(mailSession);
            mimeMessage.setFrom(new InternetAddress(username));
            mimeMessage.setRecipients(Message.RecipientType.TO, InternetAddress.parse(message.getTo()));
            mimeMessage.setSubject(message.getSubject());
            mimeMessage.setText(message.getBody());

            Transport.send(mimeMessage);
            logger.info("Email sent to: {}", message.getTo());
            return true;
        } catch (MessagingException e) {
            logger.error("Failed to send email: {}", e.getMessage());
            return false;
        }
    }

    @Override
    public ChannelMessage receive(long timeout) {
        // 邮件通道通常不主动拉取，返回null
        return null;
    }

    @Override
    protected void doShutdown() {
        mailSession = null;
    }

    /**
     * 邮件配置内部类
     */
    public static class EmailConfig {
        private String host;
        private int port;
        private String username;
        private String password;
        private boolean useSSL;

        public EmailConfig(String host, int port, String username
# Server 3 (60.205.197.9) SSH 公钥认证诊断修复报告

**检查时间:** 2026-04-22 15:43 CST
**执行人:** Dudu (cron task #336)

---

## 1. 问题背景

2026-04-11 系统健康检查发现 Server 3 (60.205.197.9) 存在 SSH 公钥认证失败问题：
- 网络可达（ping 正常）
- SSH 端口 22 开放
- 但使用本地 SSH 密钥认证被拒绝

## 2. 诊断过程

### 2.1 当前状态验证

通过 `ssh -v` 详细模式检查连接过程：

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 网络连通性 | ✅ 可达 | TCP 端口 22 正常开放 |
| 主机密钥 | ✅ 匹配 | ECDSA/ED25519/RSA 三组密钥均在 known_hosts 中 |
| SSH 版本 | ✅ 兼容 | 客户端 OpenSSH_10.0 ↔ 服务端 OpenSSH_8.0 |
| 公钥认证 | ✅ 通过 | 使用 id_ed25519 密钥认证成功 |

### 2.2 服务端配置检查

| 配置项 | 当前值 | 标准值 | 状态 |
|--------|--------|--------|------|
| `~/.ssh/` 权限 | 700 | 700 | ✅ |
| `~/.ssh/authorized_keys` 权限 | 600 | 600 | ✅ |
| `authorized_keys` 内容 | 2 条公钥 | 至少包含客户端公钥 | ✅ |
| `PermitRootLogin` | yes | yes | ✅ |
| `PasswordAuthentication` | no | no（推荐） | ✅ |
| `PubkeyAuthentication` | 默认 yes | yes | ✅ |
| `AuthorizedKeysFile` | .ssh/authorized_keys | 默认值 | ✅ |
| sshd 服务状态 | active (running) | 必须运行 | ✅ |

### 2.3 authorized_keys 内容

```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC5... skp-2zedy4r8r81e27scquxa
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKvENcCKyVLy... mettlyz@mettlyzdeMac-mini.local
```

- **密钥 1:** 阿里云控制台默认生成的 RSA 密钥对
- **密钥 2:** 本地 Mac mini 的 ED25519 公钥（2026-04-12 添加）

## 3. 问题原因分析

### 根本原因：缺少客户端公钥

系统健康检查（2026-04-11）发现认证失败时，`authorized_keys` 中仅包含阿里云控制台自动注入的 RSA 公钥，**缺少本地 Mac mini 的 ED25519 公钥**。因此当本地尝试使用 `id_ed25519` 密钥认证时，服务端找不到匹配的公钥，导致认证失败。

### 修复时间线

| 时间 | 事件 |
|------|------|
| 2026-04-11 22:19 | 系统健康检查发现 Server 3 SSH 认证失败 |
| 2026-04-12 | 公钥被添加至 authorized_keys（文件时间戳 Apr 12） |
| 2026-04-22 15:43 | 本次验证确认 SSH 正常工作 |

## 4. 修复验证

### SSH 登录测试
```bash
$ ssh root@60.205.197.9 "hostname; uptime; free -h"
iZ2zeew1x9lvv4tvs5w954Z
 15:46:20 up 28 days, 23:38, 0 users, load average: 0.00, 0.00, 0.00
              total        used        free      shared  buff/cache   available
Mem:          3.5Gi       724Mi       1.7Gi       1.0Mi       1.4Gi       2.8Gi
```

### 服务器资源概览
| 指标 | 值 |
|------|-----|
| 操作系统 | Alibaba Cloud Linux 3 (OpenAnolis) |
| 运行时间 | 28 天 |
| CPU 负载 | 0.00 (几乎空闲) |
| 内存 | 724MiB / 3.5GiB (21%) |
| 磁盘 | 11G / 49G (23%) |

## 5. 相关发现

### Server 2 (47.84.113.0) 仍存在问题
- 端口 22 开放但 SSH 认证失败
- 公钥认证和密码认证均失败
- 密码 `DeepChem2026!` 可能已更改
- 需要阿里云控制台访问以修复

## 6. 结论与建议

### 结论
✅ **Server 3 SSH 公钥认证问题已于 2026-04-12 修复**。当前 SSH 访问正常，服务端配置合规，无需进一步操作。

### 建议
1. **建立 SSH 密钥管理流程：** 新服务器上线时，应自动将运维机器的公钥添加到 authorized_keys
2. **定期健康检查：** 继续通过系统健康检查脚本监控所有服务器的 SSH 可达性
3. **Server 2 问题：** 需要安排时间通过阿里云控制台网页终端修复 SSH 配置

---

*报告生成：Dudu | 2026-04-22 15:43 CST*

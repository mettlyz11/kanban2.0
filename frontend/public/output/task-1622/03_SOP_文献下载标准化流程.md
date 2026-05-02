# SOP: 文献下载标准化流程

> 适用场景: Helight 团队 / 和光智成日常文献获取
> 版本: v1.0 | 2026-04-23

---

## 1. 场景概述

研究人员需要从各大期刊数据库（ACS、RSC、Springer、Elsevier等）下载学术论文PDF。本SOP提供从DOI/标题到获取PDF的完整标准化流程。

**涉及技能：**
- ACS-paper-download (美国化学会)
- scihub-paper-downloader (Sci-Hub 备选)
- paper-fetcher (通用论文获取)
- zotero-local-pdf-import (Zotero 本地导入)

---

## 2. 前置条件

- [ ] OpenClaw 已安装并运行
- [ ] 网络可访问目标期刊网站
- [ ] 已安装相关技能（ACS-paper-download / paper-fetcher）
- [ ] (可选) Sci-Hub 可用作备选方案
- [ ] (可选) Zotero 已安装用于文献管理

---

## 3. 标准流程

### 3.1 通过DOI下载（推荐）

```
步骤:
1. 获得文献 DOI (如: 10.1021/jacs.5c01234)
2. 使用 ACS-paper-download 技能下载
   → openclaw: "下载 ACS 论文，DOI: 10.1021/jacs.5c01234"
3. 系统自动完成: 访问期刊 → 获取PDF → 保存到本地
4. PDF 自动保存到: ~/.openclaw/workspace/output/papers/
```

**替代命令格式：**
```
"帮我下载这篇论文: 10.1021/jacs.5c01234"
"下载文章 DOI: 10.1039/D5SC01234A (RSC)"
```

### 3.2 通过论文标题下载

```
步骤:
1. 提供完整论文标题
2. 使用 web_fetch + paper-fetcher 组合
3. 系统搜索 → 找到DOI → 下载PDF
```

**示例：**
```
"帮我下载论文《Machine Learning for Materials Discovery》"
```

### 3.3 批量下载

```
步骤:
1. 准备 DOI 列表文件 (每行一个DOI)
2. 提交给系统批量处理
3. 系统逐个遍历并下载
4. 下载完成后生成报告
```

**示例：**
```
"批量下载以下论文:
10.1021/jacs.5c01234
10.1021/jacs.5c05678
10.1039/D5SC01234A"
```

---

## 4. 备选方案

### 4.1 当直接下载失败时

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 付费墙 | 无订阅权限 | 切换到 Sci-Hub |
| 404 错误 | DOI 无效 | 检查 DOI 格式 |
| 超时 | 网络问题 | 重试或切换 VPN |
| 下载不完全 | 连接中断 | 检查网络稳定性 |

### 4.2 Sci-Hub 备选流程

```
1. 确认目标论文无法通过官方渠道获取
2. 发送指令: "用 Sci-Hub 下载 {DOI}"
3. 系统自动访问 Sci-Hub 获取 PDF
4. 下载完成后检查 PDF 质量
```

### 4.3 VPN 配置

```
# 北航 VPN (校园网访问)
技能: openclaw-buaa-vpn
使用:
  "连接北航 VPN"
  "通过 VPN 下载这篇论文: {DOI}"
```

---

## 5. 输出与归档

### 5.1 文件命名规范

```
格式: {year}_{journal_abbr}_{first_author}_{title_keywords}.pdf
示例: 2026_JACS_Liu_graphene_catalyst.pdf

默认保存路径: ~/.openclaw/workspace/output/papers/
```

### 5.2 Zotero 集成

```
下载完成后自动执行:
1. 提取元数据 (标题、作者、期刊、DOI)
2. 导入到 Zotero 文献库
3. 按项目标签分类
4. 关联到相应当前任务
```

---

## 6. 异常处理

### 6.1 下载失败处理

```yaml
failure_cases:
  - symptom: "无法访问期刊网站"
    action: "检查网络 → 切换 VPN → 重试"
  
  - symptom: "ACS 网站需要 IP 授权"
    action: "通过 BUAA VPN 接入 → 使用校园网 IP"
  
  - symptom: "Sci-Hub 返回空页面"
    action: "尝试其他 Sci-Hub 域名 → 等待一段时间后重试"
  
  - symptom: "PDF 文件损坏"
    action: "删除后重新下载 → 检查下载完整性"
```

### 6.2 日志与追溯

```bash
# 查看下载日志
tail -f ~/.openclaw/workspace/memory/jiuyuan_cron.log

# 检查下载目录
ls -la ~/.openclaw/workspace/output/papers/
```

---

## 7. 效率提示

1. **优先使用DOI**：比关键词搜索快3-5倍
2. **合理使用Sci-Hub**：仅用于无订阅权限的论文
3. **批量下载**：3篇以上时使用列表一次性提交
4. **检查PDF质量**：下载后检查是否有缺页、模糊等问题
5. **及时整理**：下载后立即导入Zotero，避免遗忘

---

## 8. 质量标准

- [ ] 下载PDF完整可读
- [ ] 元数据（DOI/标题/作者）正确
- [ ] 文件命名符合规范
- [ ] 已导入 Zotero 文献库
- [ ] 已关联当前研究任务

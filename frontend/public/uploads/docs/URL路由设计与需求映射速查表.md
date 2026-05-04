# URL路由设计与需求映射速查表

> 任务: 需求分析与URL结构调研 [04291803]
> 附件类型: 设计对照矩阵
> 生成时间: 2026-05-04 11:48

# 需求分析与URL结构调研 [04291803] — 设计对照矩阵

## 版本控制

| 版本号 | 修订日期 | 修订人 | 修订说明 |
|--------|----------|--------|----------|
| v1.0 | 2025-06-15 | 架构组 | 初始版本，基于调研报告提炼核心规范 |
| v1.1 | 2025-06-18 | 架构组 | 增加反模式示例及Lint规则 |

---

## 1. 路由层级划分与命名规范速查

### 1.1 路由层级结构标准

| 层级 | 名称 | 示例 | 说明 |
|------|------|------|------|
| L0 | 协议+域名 | `https://api.example.com` | 生产环境强制HTTPS |
| L1 | 版本前缀 | `/v1/`, `/v2/` | 主版本号，非向后兼容时递增 |
| L2 | 领域模块 | `/users/`, `/orders/` | 名词复数，对应业务核心实体 |
| L3 | 子资源 | `/users/{userId}/addresses/` | 嵌套资源，层级不超过3层 |
| L4 | 动作/视图 | `/search`, `/export` | 非CRUD操作，使用动词 |

### 1.2 命名规范速查表

| 元素 | 规范 | 正确示例 | 错误示例 |
|------|------|-----------|-----------|
| 资源名 | 全小写、复数、kebab-case | `/user-accounts/` | `/UserAccounts/`, `/user_accounts/` |
| 路径参数 | 驼峰命名，花括号包裹 | `/{orderId}/` | `/{order_id}/`, `/:orderId/` |
| 查询参数 | 全小写、snake_case | `?page_size=20` | `?pageSize=20`, `?page-size=20` |
| 筛选字段 | 使用标准前缀 | `?status=active` | `?filter_status=active` |
| 排序 | `sort=field:order` | `?sort=created_at:desc` | `?sort=created_at desc` |
| 分页 | `page_number`, `page_size` | `?page_number=1&page_size=20` | `?p=1&limit=20` |

### 1.3 版本策略决策矩阵

| 场景 | 推荐策略 | 说明 |
|------|----------|------|
| 内部微服务 | URI版本（/v1/） | 简单直观，易于调试 |
| 公开API | 请求头版本（Accept: application/vnd.api+json;version=1） | 避免URI污染，支持内容协商 |
| 移动端 | URI版本 | 客户端硬编码路径，版本切换明确 |
| Web前端 | 无版本（或单一版本覆盖） | 前后端同步部署，减少版本负担 |

---

## 2. 动态路径与查询参数设计模板

### 2.1 动态路径参数模板

#### 标准CRUD模板

```
# 集合资源
GET    /v1/{resources}/          # 列表查询（支持分页、筛选）
POST   /v1/{resources}/          # 创建资源
GET    /v1/{resources}/{id}/     # 获取单个资源
PUT    /v1/{resources}/{id}/     # 全量更新资源
PATCH  /v1/{resources}/{id}/     # 部分更新资源
DELETE /v1/{resources}/{id}/     # 删除资源
```

#### 嵌套资源模板（不超过3层）

```
# 用户地址管理
GET    /v1/users/{userId}/addresses/               # 用户地址列表
POST   /v1/users/{userId}/addresses/               # 添加用户地址
GET    /v1/users/{userId}/addresses/{addressId}/    # 获取单个地址
PUT    /v1/users/{userId}/addresses/{addressId}/    # 更新地址
DELETE /v1/users/{userId}/addresses/{addressId}/    # 删除地址
```

#### 动作/命令模板

```
# 非CRUD操作使用动词
POST   /v1/orders/{orderId}/cancel/       # 取消订单
POST   /v1/orders/{orderId}/refund/       # 发起退款
POST   /v1/users/{userId}/activate/       # 激活用户
POST   /v1/invoices/{invoiceId}/send/     # 发送发票邮件
```

### 2.2 查询参数设计模板

#### 标准查询参数集

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `page_number` | integer | 否 | 1 | 当前页码，从1开始 |
| `page_size` | integer | 否 | 20 | 每页记录数，最大100 |
| `sort` | string | 否 | `id:desc` | 排序字段和方向 |
| `fields` | string | 否 | 全部 | 返回字段白名单，逗号分隔 |
| `include` | string | 否 | 无 | 包含关联资源，逗号分隔 |
| `search` | string | 否 | 无 | 全文搜索关键词 |
| `status` | string | 否 | 无 | 状态筛选 |
| `created_after` | datetime | 否 | 无 | ISO 8601格式 |
| `created_before` | datetime | 否 | 无 | ISO 8601格式 |

#### 分页响应模板

```json
{
    "data": [...],
    "meta": {
        "page_number": 1,
        "page_size": 20,
        "total_count": 156,
        "total_pages": 8
    },
    "links": {
        "self": "https://api.example.com/v1/orders?page_number=1&page_size=20",
        "first": "https://api.example.com/v1/orders?page_number=1&page_size=20",
        "prev": null,
        "next": "https://api.example.com/v1/orders?page_number=2&page_size=20",
        "last": "https://api.example.com/v1/orders?page_number=8&page_size=20"
    }
}
```

---

## 3. 常见业务场景URL结构对照矩阵

### 3.1 电商系统场景矩阵

| 业务场景 | HTTP方法 | URL模式 | 说明 |
|----------|----------|---------|------|
| 用户注册 | POST | `/v1/users/` | 创建用户资源 |
| 用户登录 | POST | `/v1/auth/login/` | 认证端点，非资源 |
| 用户登出 | POST | `/v1/auth/logout/` | 销毁会话 |
| 获取用户资料 | GET | `/v1/users/{userId}/profile/` | 用户配置子资源 |
| 更新用户头像 | PATCH | `/v1/users/{userId}/avatar/` | 部分更新头像资源 |
| 商品列表 | GET | `/v1/products/?category=electronics&sort=price:asc` | 带筛选和排序 |
| 商品详情 | GET | `/v1/products/{productId}/` | 单个商品资源 |
| 添加购物车 | POST | `/v1/cart/items/` | 创建购物车条目 |
| 修改购物车数量 | PATCH | `/v1/cart/items/{itemId}/` | 部分更新条目 |
| 清空购物车 | DELETE | `/v1/cart/items/` | 删除集合资源 |
| 创建订单 | POST | `/v1/orders/` | 从购物车生成订单 |
| 取消订单 | POST | `/v1/orders/{orderId}/cancel/` | 命令式动作 |
| 支付回调 | POST | `/v1/payments/callback/` | 第三方回调端点 |
| 获取订单物流 | GET | `/v1/orders/{orderId}/tracking/` | 订单物流子资源 |
| 商品评价 | POST | `/v1/products/{productId}/reviews/` | 嵌套资源创建 |
| 收藏商品 | POST | `/v1/users/{userId}/favorites/` | 用户收藏子资源 |
| 取消收藏 | DELETE | `/v1/users/{userId}/favorites/{productId}/` | 删除收藏关系 |
| 优惠券列表 | GET | `/v1/coupons/?user_id={userId}&status=active` | 按用户筛选 |
| 领取优惠券 | POST | `/v1/users/{userId}/coupons/{couponId}/claim/` | 动作端点 |
| 搜索商品 | GET | `/v1/products/search/?q=iphone&page_number=1` | 搜索专用端点 |
| 导出订单 | GET | `/v1/orders/export/?status=paid&format=csv` | 导出动作 |

### 3.2 内容管理系统场景矩阵

| 业务场景 | HTTP方法 | URL模式 | 说明 |
|----------|----------|---------|------|
| 文章列表 | GET | `/v1/articles/?status=published&category=tech` | 发布状态筛选 |
| 创建文章 | POST | `/v1/articles/` | 创建内容资源 |
| 文章草稿 | GET | `/v1/articles/?status=draft&author_id={userId}` | 作者草稿列表 |
| 审核文章 | POST | `/v1/articles/{articleId}/review/` | 审核动作 |
| 发布文章 | POST | `/v1/articles/{articleId}/publish/` | 发布动作 |
| 撤回文章 | POST | `/v1/articles/{articleId}/unpublish/` | 撤回动作 |
| 文章标签 | GET | `/v1/tags/` | 标签资源集合 |
| 标签文章 | GET | `/v1/articles/?tags=tech,programming` | 多标签筛选 |
| 创建分类 | POST | `/v1/categories/` | 分类资源 |
| 分类树 | GET | `/v1/categories/tree/` | 树形结构视图 |
| 文章评论 | GET | `/v1/articles/{articleId}/comments/` | 嵌套评论列表 |
| 评论回复 | POST | `/v1/comments/{commentId}/replies/` | 回复嵌套 |
| 点赞文章 | POST | `/v1/articles/{articleId}/likes/` | 创建点赞记录 |
| 取消点赞 | DELETE | `/v1/articles/{articleId}/likes/` | 删除点赞记录 |
| 媒体上传 | POST | `/v1/media/` | 文件上传端点 |
| 媒体删除 | DELETE | `/v1/media/{mediaId}/` | 删除媒体资源 |
| 用户收藏夹 | GET | `/v1/users/{userId}/bookmarks/` | 收藏子资源 |
| 站点配置 | GET | `/v1/settings/` | 系统配置资源 |
| 更新配置 | PATCH | `/v1/settings/{settingKey}/` | 单项配置更新 |
| 操作日志 | GET | `/v1/audit-logs/?actor_id={userId}&action=delete` | 审计日志查询 |

### 3.3 SaaS多租户场景矩阵

| 业务场景 | HTTP方法 | URL模式 | 说明 |
|----------|----------|---------|------|
| 租户注册 | POST | `/v1/tenants/` | 创建租户资源 |
| 租户详情 | GET | `/v1/tenants/{tenantId}/` | 租户信息 |
| 租户用户 | GET | `/v1/tenants/{tenantId}/users/` | 租户下用户列表 |
| 邀请用户 | POST | `/v1/tenants/{tenantId}/invitations/` | 创建邀请 |
| 接受邀请 | POST | `/v1/invitations/{token}/accept/` | 令牌动作 |
| 租户角色 | GET | `/v1/tenants/{tenantId}/roles/` | 角色列表 |
| 分配角色 | POST | `/v1/tenants/{tenantId}/users/{userId}/roles/` | 角色分配 |
| 租户权限 | GET | `/v1/tenants/{tenantId}/permissions/` | 权限清单 |
| 租户配置 | GET | `/v1/tenants/{tenantId}/settings/` | 租户级配置 |
| 租户计费 | GET | `/v1/tenants/{tenantId}/billing/` | 计费信息 |
| 升级套餐 | POST | `/v1/tenants/{tenantId}/subscription/upgrade/` | 订阅动作 |
| 取消订阅 | POST | `/v1/tenants/{tenantId}/subscription/cancel/` | 取消动作 |
| 租户空间 | GET | `/v1/tenants/{tenantId}/storage/` | 存储使用量 |
| 导出租户数据 | GET | `/v1/tenants/{tenantId}/export/` | 数据导出 |
| 删除租户 | DELETE | `/v1/tenants/{tenantId}/` | 软删除资源 |
| 恢复租户 | POST | `/v1/tenants/{tenantId}/restore/` | 恢复动作 |
| API密钥管理 | GET | `/v1/tenants/{tenantId}/api-keys/` | 密钥列表 |
| 生成密钥 | POST | `/v1/tenants/{tenantId}/api-keys/generate/` | 生成动作 |
| 吊销密钥 | POST | `/v1/tenants/{tenantId}/api-keys/{keyId}/revoke/` | 吊销动作 |
| 操作审计 | GET | `/v1/tenants/{tenantId}/audit-logs/` | 租户级审计 |

---

## 4. 高频反模式识别与避坑指南

### 4.1 反模式速查表

| 序号 | 反模式 | 错误示例 | 正确做法 | 影响等级 |
|------|--------|----------|----------|----------|
| 1 | 动词化CRUD | `GET /users/getUserById/123` | `GET /users/123/` | 🔴 严重 |
| 2 | 单数资源名 | `GET /user/123` | `GET /users/123/` | 🟡 中等 |
| 3 | 下划线路径 | `GET /user_accounts/` | `GET /user-accounts/` | 🟡 中等 |
| 4 | 路径中带空格 | `GET /users/123 /profile` | `GET /users/123/profile/` | 🔴 严重 |
| 5 | 查询参数重复 | `?ids=1&ids=2&ids=3` | `?ids=1,2,3` | 🟢 轻微 |
| 6 | 状态码混淆 | 删除成功返回200 | 返回204 No Content | 🟡 中等 |
| 7 | 嵌套过深 | `/a/b/c/d/e/f/` | 扁平化或使用查询参数 | 🟡 中等 |
| 8 | 版本号放路径末尾 | `/users/v1/` | `/v1/users/` | 🔴 严重 |
| 9 | 混合大小写 | `GET /Users/123` | `GET /users/123/` | 🔴 严重 |
| 10 | 文件扩展名 | `GET /users/123.json` | 使用Accept头 | 🟡 中等 |
| 11 | 动作作为资源 | `GET /getUsers/` | `GET /users/` | 🔴 严重 |
| 12 | 查询参数做路径 | `GET /users/123/orders/active` | `GET /users/123/orders/?status=active` | 🟡 中等 |
| 13 | 无统一错误格式 | 各接口返回不同错误结构 | 统一错误响应格式 | 🔴 严重 |
| 14 | 忽略幂等性 | POST重复创建订单 | 使用Idempotency-Key头 | 🔴 严重 |
| 15 | 分页无默认值 | 不传参数返回全部数据 | 默认page_size=20 | 🟡 中等 |

### 4.2 典型反模式案例详解

#### 反模式1：动作路径化

```
❌ 错误：GET /v1/users/123/getOrders/
❌ 错误：GET /v1/users/123/getOrderHistory/
❌ 错误：GET /v1/users/123/getProfile/

✅ 正确：GET /v1/users/123/orders/
✅ 正确：GET /v1/users/123/orders/?history=true
✅ 正确：GET /v1/users/123/profile/
```

#### 反模式2：状态作为路径

```
❌ 错误：GET /v1/orders/active/
❌ 错误：GET /v1/orders/completed/
❌ 错误：GET /v1/orders/cancelled/

✅ 正确：GET /v1/orders/?status=active
✅ 正确：GET /v1/orders/?status=completed
✅ 正确：GET /v1/orders/?status=cancelled
```

#### 反模式3：非标准错误响应

```
❌ 错误格式（不一致）：
接口A: {"code": 400, "msg": "参数错误"}
接口B: {"error": "bad_request", "description": "缺少必要参数"}
接口C: {"status": "fail", "data": null, "message": "验证失败"}

✅ 正确格式（统一规范）：
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "请求参数验证失败",
        "details": [
            {
                "field": "email",
                "message": "邮箱格式不正确",
                "code": "INVALID_FORMAT"
            }
        ],
        "request_id": "req_abc123"
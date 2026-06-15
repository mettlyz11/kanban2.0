# Macmini_SMB配置操作手册

> 任务: 在Macmini上启用SMB文件共享 [04291941]
> 附件类型: 操作指南
> 生成时间: 2026-05-04 15:12

# 在Macmini上启用SMB文件共享操作指南

**文档编号：** SMB-MAC-04291941  
**版本号：** 1.0  
**适用平台：** macOS Ventura / Sonoma / Sequoia  
**最后更新：** 2025年4月29日  

---

## 1. 前置环境检查与网络连通性要求

在开始配置SMB文件共享之前，必须完成以下环境检查，避免因基础环境问题导致配置失败。

### 1.1 系统版本确认

打开终端执行以下命令，确认系统版本符合要求：

```bash
sw_vers
```

**预期输出示例：**
```
ProductName:        macOS
ProductVersion:     14.5
BuildVersion:       23F79
```

**要求：** macOS 10.13 (High Sierra) 及以上版本。较低版本可能存在SMB协议兼容性问题。

### 1.2 网络配置检查

#### 1.2.1 确认IP地址配置

```bash
ifconfig en0 | grep "inet "
# 有线网络使用 en0，无线网络使用 en1
```

**正确输出示例：**
```
inet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255
```

**配置要求：**
- 必须使用**静态IP地址**（推荐）或DHCP保留地址
- 子网掩码必须与局域网内其他设备一致（通常为255.255.255.0）
- 确保无IP地址冲突

#### 1.2.2 设置静态IP地址（推荐）

通过系统设置配置静态IP：

1. 打开 **系统设置 > 网络**
2. 选择当前活跃的网络接口（以太网或Wi-Fi）
3. 点击 **详细信息**
4. 在 **TCP/IP** 选项卡中，将 **配置IPv4** 改为 **手动**
5. 填写以下信息：
   - **IP地址：** 192.168.1.100（示例，请根据实际网络段调整）
   - **子网掩码：** 255.255.255.0
   - **路由器：** 192.168.1.1

#### 1.2.3 防火墙与端口检查

确保以下端口未被防火墙阻止：

| 端口 | 协议 | 用途 |
|------|------|------|
| 137 | UDP | NetBIOS名称服务 |
| 138 | UDP | NetBIOS数据报服务 |
| 139 | TCP | NetBIOS会话服务 |
| 445 | TCP | SMB直接连接 |

**检查防火墙状态：**
```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
```

**关闭防火墙（临时测试用）：**
```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off
```

### 1.3 网络连通性测试

在**客户端设备**（Windows/Linux/其他Mac）上执行：

```bash
ping 192.168.1.100
# 替换为Macmini的实际IP地址
```

**成功标准：** 连续5次ping测试，丢包率为0%，平均延迟<5ms（局域网内）。

---

## 2. GUI路径配置（系统设置-共享-文件共享与SMB协议）

### 2.1 启用文件共享服务

1. 打开 **系统设置**（点击屏幕左上角苹果图标 > 系统设置）
2. 在左侧边栏选择 **通用**
3. 向下滚动并点击 **共享**
4. 在右侧服务列表中，找到并开启 **文件共享** 开关

**验证：** 开关变为蓝色且状态显示为"文件共享：开"

### 2.2 配置SMB协议

1. 在文件共享服务右侧，点击 **信息** 按钮（i图标）
2. 在弹出的窗口中，点击 **选项...**
3. 在"Windows文件共享"区域，勾选 **使用SMB来共享文件和文件夹**
4. 在下方用户列表中，勾选需要授权访问的用户账户

**重要提示：** 
- 必须勾选至少一个用户账户，否则SMB共享将无法正常工作
- 被勾选的用户必须已设置登录密码（密码为空将导致连接失败）

### 2.3 添加共享文件夹

1. 在文件共享设置界面，点击 **共享文件夹** 列表下方的 **+** 按钮
2. 在Finder中选择要共享的文件夹（例如 `/Users/Shared/Public` 或自定义文件夹）
3. 点击 **添加**

### 2.4 配置权限

对每个共享文件夹，设置用户权限：

1. 在共享文件夹列表中选中目标文件夹
2. 在右侧 **用户** 列表下方，点击 **+** 添加用户
3. 选择用户或用户组：
   - **所有人：** 所有网络用户
   - **客人：** 无需密码访问（仅限访客共享）
   - **具体用户名：** 指定用户
4. 设置权限级别：
   - **只读：** 只能读取文件
   - **读写：** 可以读取和写入
   - **只写（投递箱）：** 只能写入，不能读取（适用于文件收集场景）

**权限配置示例：**

| 共享文件夹 | 用户 | 权限 |
|-----------|------|------|
| /Users/Shared/Public | 所有人 | 只读 |
| /Users/Shared/Public | user1 | 读写 |
| /Users/Shared/Projects | user1 | 读写 |
| /Users/Shared/Projects | user2 | 只读 |

### 2.5 验证配置

在文件共享设置主界面，确认以下信息正确显示：
- **文件共享：** 开
- **共享文件夹：** 显示已添加的文件夹列表
- **SMB：** 已启用

---

## 3. 终端命令行配置方案（高级/批量场景）

适用于需要批量配置或自动化部署的场景。

### 3.1 启用SMB共享服务

```bash
# 启用文件共享服务
sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.smbd.plist

# 设置为开机自启
sudo defaults write /System/Library/LaunchDaemons/com.apple.smbd Disabled -bool false
```

### 3.2 配置SMB共享参数

创建/编辑配置文件：

```bash
sudo nano /etc/nsmb.conf
```

**标准配置内容：**
```
[default]
protocol_vers_map=6
port445=yes
ntlmssp_auth=yes
signing_required=no
streams=no
```

**参数说明：**
- `protocol_vers_map=6`：启用SMB 2.0和3.0协议
- `port445=yes`：强制使用端口445
- `ntlmssp_auth=yes`：启用NTLMSSP认证
- `signing_required=no`：关闭签名要求（提高兼容性）
- `streams=no`：禁用资源分支流

### 3.3 创建共享文件夹并设置权限

```bash
# 创建共享文件夹
sudo mkdir -p /SharedData/Public
sudo mkdir -p /SharedData/Projects

# 设置文件夹权限
sudo chmod 755 /SharedData/Public
sudo chmod 770 /SharedData/Projects

# 更改所有者
sudo chown -R root:staff /SharedData/Public
sudo chown -R user1:staff /SharedData/Projects
```

### 3.4 配置SMB共享定义（高级）

编辑SMB配置文件：

```bash
sudo nano /etc/smb.conf
```

**完整配置示例：**
```ini
[global]
   workgroup = WORKGROUP
   server string = Macmini SMB Server
   security = user
   encrypt passwords = yes
   smb ports = 445
   max protocol = SMB3
   min protocol = SMB2_02
   unix charset = UTF-8
   dos charset = CP437
   log file = /var/log/samba/smbd.log
   max log size = 100
   load printers = no
   printing = bsd
   guest account = nobody

[Public]
   comment = Public Shared Folder
   path = /SharedData/Public
   browseable = yes
   writable = yes
   guest ok = yes
   read only = no
   create mask = 0644
   directory mask = 0755

[Projects]
   comment = Project Files
   path = /SharedData/Projects
   browseable = yes
   writable = yes
   guest ok = no
   valid users = user1, user2
   write list = user1
   read list = user2
   create mask = 0660
   directory mask = 0770
```

### 3.5 重启SMB服务

```bash
# 停止服务
sudo launchctl unload /System/Library/LaunchDaemons/com.apple.smbd.plist

# 启动服务
sudo launchctl load /System/Library/LaunchDaemons/com.apple.smbd.plist

# 检查服务状态
sudo launchctl list | grep smbd
```

**成功输出示例：**
```
PID     Status  Label
12345   0       com.apple.smbd
```

---

## 4. 用户授权与共享文件夹权限映射规则

### 4.1 用户账户要求

**必须条件：**
- 用户必须存在于Macmini的本地用户数据库中
- 用户必须设置登录密码
- 用户密码不能为空

**检查用户列表：**
```bash
dscl . list /Users | grep -v '^_'
```

**创建新用户（如需要）：**
```bash
sudo dscl . create /Users/smbuser
sudo dscl . create /Users/smbuser RealName "SMB User"
sudo dscl . create /Users/smbuser UniqueID 510
sudo dscl . create /Users/smbuser PrimaryGroupID 20
sudo dscl . create /Users/smbuser UserShell /bin/bash
sudo dscl . create /Users/smbuser NFSHomeDirectory /Users/smbuser
sudo dscl . passwd /Users/smbuser "StrongPassword123!"
sudo dscl . create /Users/smbuser IsHidden 1
sudo createhomedir -c -u smbuser
```

### 4.2 权限映射规则

SMB权限映射遵循以下优先级（从高到低）：

1. **明确拒绝（Deny）**：任何拒绝权限优先于允许权限
2. **用户特定权限**：针对特定用户设置的权限
3. **组权限**：用户所属组的权限
4. **所有人（Everyone）**：全局权限

**权限映射表：**

| macOS权限 | SMB权限 | 实际效果 |
|-----------|---------|----------|
| 读取（r） | 只读（Read） | 可查看文件列表、读取文件内容 |
| 写入（w） | 读写（Read/Write） | 可创建、修改、删除文件 |
| 执行（x） | 不直接映射 | 影响目录访问和脚本执行 |
| 无权限（-） | 拒绝访问（Deny） | 无法访问共享 |

### 4.3 权限配置示例

**场景1：部门共享文件夹**

| 用户/组 | 文件夹 | 权限 |
|---------|--------|------|
| user1 | /SharedData/Department | 读写 |
| user2 | /SharedData/Department | 读写 |
| 所有人 | /SharedData/Department | 只读 |

**命令配置：**
```bash
# 创建文件夹
sudo mkdir -p /SharedData/Department

# 设置组权限
sudo chown -R root:staff /SharedData/Department
sudo chmod 770 /SharedData/Department

# 设置ACL权限
sudo chmod +a "user:user1 allow list,add_file,search,add_subdirectory,delete_child,readattr,writeattr,readextattr,writeextattr,readsecurity,file_inherit,directory_inherit" /SharedData/Department
sudo chmod +a "user:user2 allow list,add_file,search,add_subdirectory,delete_child,readattr,writeattr,readextattr,writeextattr,readsecurity,file_inherit,directory_inherit" /SharedData/Department
sudo chmod +a "everyone deny delete_child,writeattr,writeextattr" /SharedData/Department
```

### 4.4 验证权限配置

```bash
# 查看ACL权限
ls -le /SharedData/Department

# 测试用户访问
sudo -u user1 ls /SharedData/Department
sudo -u user1 touch /SharedData/Department/test.txt
```

---

## 5. 局域网SMB连接测试与常见故障排查

### 5.1 连接测试方法

#### 5.1.1 从Windows客户端连接

**方法1：使用文件资源管理器**
1. 打开文件资源管理器
2. 在地址栏输入：`\\192.168.1.100`
3. 输入用户名和密码（Macmini上的用户凭据）
4. 确认可以访问共享文件夹

**方法2：使用命令行**
```cmd
net use Z: \\192.168.1.100\Public /user:smbuser StrongPassword123!
```

#### 5.1.2 从macOS客户端连接

```bash
# 使用Finder连接
open smb://192.168.1.100

# 使用命令行挂载
mkdir -p /tmp/smb_mount
mount_smbfs //smbuser:StrongPassword123!@192.168.1.100/Public /tmp/smb_mount
```

#### 5.1.3 从Linux客户端连接

```bash
# 安装SMB客户端
sudo apt-get install smbclient cifs-utils

# 列出共享
smbclient -L //192.168.1.100 -U smbuser

# 挂载共享
sudo mount -t cifs //192.168.1.100/Public /mnt/smb_share -o username=smbuser,password=StrongPassword123!,vers=3.0
```

### 5.2 性能测试

```bash
# 使用dd命令测试写入速度（在挂载目录中执行）
dd if=/dev/zero of=test_file bs=1M count=100 conv=fdatasync

# 测试读取速度
dd if=test_file of=/dev/null bs=1M count=100
```

**性能基准：**
- 千兆网络：读写速度应 > 80 MB/s
- 无线网络（802.11ac）：读写速度应 > 30 MB/s

### 5.3 常见故障排查

#### 故障1：无法发现Macmini

**症状：** 在Windows网络邻居中看不到Macmini

**排查步骤：**
1. 确认NetBIOS服务运行：
   ```bash
   sudo launchctl list | grep netbios
   ```
2. 重启NetBIOS服务：
   ```bash
   sudo launchctl unload /System/Library/LaunchDaemons/com.apple.netbiosd.plist
   sudo launchctl load /System/Library/LaunchDaemons/com.apple.netbiosd.plist
   ```
3. 检查工作组名称一致性：
   ```bash
   defaults read /Library/Preferences/SystemConfiguration/com.apple.smb.server NetBIOSName
   ```

#### 故障2：连接时提示"用户名或密码错误"

**排查步骤：**
1. 确认密码非空：
   ```bash
   sudo dscl . authonly smbuser "StrongPassword123!"
   # 返回0表示认证成功
   ```
2. 检查NTLMv2认证状态：
   ```bash
   defaults read /Library/Preferences/SystemConfiguration/com.apple.smb.server SigningRequired
   ```
3. 在客户端注册表（Windows）中添加：
   ```
   HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Lsa
   LMCompatibilityLevel = 2 (DWORD)
   ```

#### 故障3：连接成功但无法写入文件

**排查步骤：**
1. 检查文件夹权限：
   ```bash
   ls -ld /SharedData/Public
   ```
2. 检查SMB共享配置中的写入权限
3. 确认用户属于允许写入的组
4. 检查磁盘空间：
   ```bash
   df -h /SharedData
   ```

#### 故障4：传输速度慢

**排查步骤：**
1. 检查网络协商速度：
   ```bash
   networksetup -getMedia en0
   ```
2. 关闭SMB签名：
   ```bash
   defaults write /Library/Preferences/SystemConfiguration/com.apple.smb.server SigningRequired -bool false
   ```
3. 禁用IPv6（如果不需要）：
   ```bash
   networksetup -setv6off en0
   ```

### 5.4 日志查看

```bash
# SMB服务日志
sudo tail -f /var/log/samba/smbd.log

# 系统日志（过滤SMB相关）
sudo log stream --predicate 'subsystem contains "smb"' --info

# 连接日志
sudo tail -f /var/log/system.log | grep -i smb
```

### 5.5 自动恢复脚本

创建以下脚本用于自动恢复SMB服务：

```bash
#!/bin/bash
# /usr/local/bin/smb_health_check.sh

SMB_SERVICE="com.apple.smbd"
LOG_FILE="/var/log/smb_health.log"

check_smb() {
    if ! launchctl list | grep -q "$SMB_SERVICE"; then
        echo "$(date): SMB service not running, restarting..." >> $LOG_FILE
        sudo launchctl load -w /System/Library/LaunchDaemons/$SMB_SERVICE.plist
        return 1
    fi
    
    # 测试连接
    if ! smbutil status 192.168.
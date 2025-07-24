# Email MCP Server 设置指南

## 快速开始

### 1. 配置邮箱账户

要使用 Email MCP Server 的完整功能，您需要配置真实的邮箱账户。

#### 复制配置文件模板
```bash
cp email_accounts.json.example email_accounts.json
```

#### 编辑配置文件
编辑 `email_accounts.json` 文件，添加您的邮箱账户信息：

```json
{
  "accounts": {
    "your-email@gmail.com": {
      "email_address": "your-email@gmail.com",
      "password": "your_app_password_here",
      "display_name": "My Gmail Account",
      "protocol": "imap",
      "imap_host": "imap.gmail.com",
      "imap_port": 993,
      "imap_use_ssl": true,
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_use_tls": true,
      "enabled": true,
      "default_folder": "INBOX"
    }
  }
}
```

### 2. 获取应用密码

#### Gmail
1. 启用两步验证
2. 生成应用密码：https://myaccount.google.com/apppasswords
3. 使用生成的16位密码替换 `your_app_password_here`

#### Outlook/Hotmail
1. 启用两步验证
2. 生成应用密码：https://account.live.com/proofs/AppPassword
3. 使用生成的密码替换配置文件中的密码

#### QQ邮箱
1. 登录QQ邮箱设置
2. 账户 → POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
3. 开启IMAP/SMTP服务，获取授权码
4. 使用授权码作为密码

### 3. 启动服务器

```bash
# 启动 MCP 服务器
python src/email_mcp.py
```

服务器将在 `http://localhost:8000` 启动。

### 4. 测试功能

```bash
# 运行完整功能测试
python fastmcp_client_test.py
```

## 支持的邮箱提供商

### Gmail
- IMAP: imap.gmail.com:993 (SSL)
- SMTP: smtp.gmail.com:587 (TLS)
- 需要应用密码

### Outlook/Hotmail
- IMAP: outlook.office365.com:993 (SSL)
- POP3: outlook.office365.com:995 (SSL)
- SMTP: smtp.office365.com:587 (TLS)

### QQ邮箱
- IMAP: imap.qq.com:993 (SSL)
- POP3: pop.qq.com:995 (SSL)
- SMTP: smtp.qq.com:587 (TLS)

### 163邮箱
- IMAP: imap.163.com:993 (SSL)
- POP3: pop.163.com:995 (SSL)
- SMTP: smtp.163.com:587 (TLS)

## 可用的 MCP 工具

1. **fetch_emails** - 获取邮件列表
2. **search_emails** - 搜索邮件
3. **send_email** - 发送邮件
4. **get_attachment_info** - 获取附件信息
5. **read_attachment** - 读取附件内容
6. **list_attachments** - 列出邮件附件
7. **get_storage_stats** - 获取存储统计
8. **cleanup_old_attachments** - 清理旧附件
9. **extract_archives** - 提取压缩文件

## 故障排除

### 常见错误

1. **"No configuration found for email address"**
   - 确保在 `email_accounts.json` 中配置了对应的邮箱账户
   - 检查邮箱地址拼写是否正确

2. **"Authentication failed"**
   - 检查密码是否正确（应使用应用密码，不是登录密码）
   - 确认已启用IMAP/POP3服务

3. **"Connection failed"**
   - 检查网络连接
   - 确认服务器地址和端口正确
   - 检查防火墙设置

### 日志查看

服务器日志会显示详细的错误信息，帮助诊断问题：

```bash
# 查看服务器日志
tail -f server.log
```

## 安全注意事项

1. **不要提交配置文件到版本控制**
   - `email_accounts.json` 已在 `.gitignore` 中
   - 包含敏感的邮箱密码信息

2. **使用应用密码**
   - 不要使用主账户密码
   - 应用密码可以随时撤销

3. **定期更新密码**
   - 定期更换应用密码
   - 监控账户异常活动

## 高级配置

### 环境变量

```bash
# 自定义配置文件路径
export EMAIL_CONFIG_FILE="/path/to/your/config.json"

# 自定义附件存储目录
export ATTACHMENTS_DIR="/path/to/attachments"
```

### 多账户支持

可以在同一个配置文件中配置多个邮箱账户，服务器会自动管理所有账户。

### 协议选择

- **IMAP**: 推荐，支持文件夹同步
- **POP3**: 简单，适合单设备使用
- **SMTP**: 仅发送邮件
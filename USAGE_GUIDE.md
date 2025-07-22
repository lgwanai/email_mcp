# Email MCP Server 使用指南

## 🎉 配置成功！

您的邮箱配置已经测试成功，可以正常使用Email MCP Server了。

## 📧 当前配置

- **邮箱服务商**: QQ邮箱
- **邮箱地址**: 986007792@qq.com
- **IMAP服务器**: imap.qq.com:993 (SSL)
- **SMTP服务器**: smtp.qq.com:587 (TLS)
- **收件箱邮件数**: 12,050 封
- **测试状态**: ✅ 通过（收发邮件均正常）

## 🚀 启动MCP服务器

### 1. SSE模式（推荐用于Web客户端）
```bash
python main.py -t sse --port 8000
```

服务器将在 `http://localhost:8000/sse/` 启动

### 2. Stdio模式（用于命令行客户端）
```bash
python main.py -t stdio
```

## 🔧 在第三方客户端中使用

### Claude Desktop 配置

在 Claude Desktop 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "email-server": {
      "command": "python",
      "args": ["/path/to/email_mcp_server/main.py", "-t", "stdio"],
      "cwd": "/path/to/email_mcp_server"
    }
  }
}
```

### 其他MCP客户端

对于支持SSE的客户端，使用以下URL：
```
http://localhost:8000/sse/
```

## 🛠️ 可用的MCP工具

### 1. `fetch_emails` - 获取邮件
```json
{
  "folder": "INBOX",
  "limit": 10,
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "download_attachments": true
}
```

### 2. `get_attachment_info` - 获取附件信息
```json
{
  "email_uid": "12345"
}
```

### 3. `read_attachment` - 读取附件内容
```json
{
  "email_uid": "12345",
  "filename": "document.pdf"
}
```

### 4. `list_attachments` - 列出所有附件
```json
{
  "email_uid": "12345"
}
```

### 5. `get_storage_stats` - 获取存储统计
```json
{}
```

### 6. `cleanup_old_attachments` - 清理旧附件
```json
{
  "days": 30
}
```

### 7. `send_email` - 发送邮件
```json
{
  "smtp_host": "smtp.qq.com",
  "smtp_port": 587,
  "smtp_username": "986007792@qq.com",
  "smtp_password": "your_auth_code",
  "to_addresses": "recipient@example.com",
  "subject": "邮件主题",
  "body": "邮件正文内容",
  "smtp_use_tls": true,
  "cc_addresses": "cc@example.com",
  "bcc_addresses": "bcc@example.com",
  "html_body": "<h1>HTML格式邮件内容</h1>"
}
```

## 📝 使用示例

### 获取最近10封邮件
```
使用 fetch_emails 工具，参数：
{
  "folder": "INBOX",
  "limit": 10,
  "download_attachments": false
}
```

### 获取带附件的邮件
```
使用 fetch_emails 工具，参数：
{
  "folder": "INBOX",
  "limit": 5,
  "download_attachments": true
}
```

### 搜索特定日期范围的邮件
```
使用 fetch_emails 工具，参数：
{
  "folder": "INBOX",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "limit": 50
}
```

### 发送邮件
```
使用 send_email 工具，参数：
{
  "smtp_host": "smtp.qq.com",
  "smtp_port": 587,
  "smtp_username": "986007792@qq.com",
  "smtp_password": "rswihlruijvkbdad",
  "to_addresses": "recipient@example.com",
  "subject": "测试邮件",
  "body": "这是一封测试邮件",
  "smtp_use_tls": true
}
```

### 发送HTML格式邮件
```
使用 send_email 工具，参数：
{
  "smtp_host": "smtp.qq.com",
  "smtp_port": 587,
  "smtp_username": "986007792@qq.com",
  "smtp_password": "rswihlruijvkbdad",
  "to_addresses": "recipient@example.com",
  "subject": "HTML邮件测试",
  "body": "这是纯文本内容",
  "html_body": "<h1>这是HTML内容</h1><p>支持<strong>富文本</strong>格式</p>",
  "cc_addresses": "cc@example.com",
  "smtp_use_tls": true
}
```

## 🔒 安全注意事项

1. **授权码安全**: 当前使用的授权码 `rswihlruijvkbdad` 已保存在 `.env` 文件中
2. **文件权限**: 确保 `.env` 文件权限设置为 600 (仅所有者可读写)
3. **生产环境**: 在生产环境中建议使用环境变量或密钥管理服务
4. **网络安全**: 如果通过网络访问，建议使用HTTPS

## 📁 附件存储

- **存储位置**: `./attachments/`
- **文件结构**: `attachments/{email_uid}/{filename}`
- **元数据**: 每个邮件的附件信息保存在 `{email_uid}_attachments.json`
- **自动清理**: 可配置自动清理超过指定天数的附件

## 🐛 故障排除

### 连接问题
1. 检查网络连接
2. 验证邮箱地址和授权码
3. 确认IMAP服务已开启
4. 检查防火墙设置

### 权限问题
1. 确保有读写附件目录的权限
2. 检查 `.env` 文件是否存在且可读

### 性能优化
1. 限制邮件获取数量 (`limit` 参数)
2. 避免下载大量附件
3. 定期清理旧附件

## 📞 技术支持

如果遇到问题，请检查：
1. 服务器日志输出
2. `.env` 配置文件
3. 网络连接状态
4. 邮箱服务商设置

---

🎯 **现在您可以开始使用Email MCP Server了！**

启动命令：`python main.py -t sse --port 8000`
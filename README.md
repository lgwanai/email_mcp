# Email MCP Server

一个基于 FastMCP 框架的邮件收取 MCP (Model Context Protocol) 服务器，支持邮件获取和附件管理功能。

## 功能特性

- 🔗 **MCP 协议支持**: 基于 FastMCP 框架，支持 SSE 和 stdio 传输模式
- 📧 **邮件收取**: 支持 IMAP 协议连接各种邮件服务器
- 📎 **附件管理**: 自动下载邮件附件并按邮件 ID 组织存储
- 🔄 **智能附件解析**: 集成 MarkItDown 自动解析文档、表格、图片等多种格式附件，支持 PDF、Word、Excel、CSV、PowerPoint、图片等格式的内容提取和 Markdown 转换
- 🔍 **灵活查询**: 支持时间范围、文件夹、数量限制等多种过滤条件
- 📊 **标准化输出**: 统一的 JSON 格式响应
- 🛡️ **错误处理**: 完善的错误处理和重试机制
- 📝 **详细日志**: 结构化日志记录，便于调试和监控

## 安装依赖

### 基础依赖

```bash
pip install -r requirements.txt
```

### 推荐安装 MarkItDown（用于附件智能解析）

为了获得最佳的附件解析体验，强烈推荐安装 Microsoft 开源的 MarkItDown 工具：

```bash
# 安装完整功能版本（推荐）
pip install 'markitdown[all]'

# 或者根据需要安装特定格式支持
pip install 'markitdown[pdf,docx,xlsx,pptx]'
```

**MarkItDown 开源地址**: https://github.com/microsoft/markitdown.git

> MarkItDown 是微软开源的文档转换工具，支持将 PDF、Word、Excel、PowerPoint、图片等多种格式转换为 Markdown，非常适合与 LLM 应用集成。

## 快速开始

### 1. 启动 SSE 模式服务器（推荐）

```bash
python main.py -t sse --host localhost --port 8000
```

服务器将在 `http://localhost:8000/sse` 启动。

### 2. 启动 stdio 模式服务器

```bash
python main.py -t stdio
```

## MCP 工具说明

### 1. fetch_emails

获取邮件列表的主要工具。

**参数:**
- `email_address` (必需): 邮箱地址
- `password` (必需): 邮箱密码
- `folder` (可选): 邮件文件夹，默认 "INBOX"
- `start_date` (可选): 开始日期，格式 "YYYY-MM-DD" 或 "YYYY-MM-DD HH:MM:SS"
- `end_date` (可选): 结束日期，格式同上
- `limit` (可选): 邮件数量限制，默认 10，最大 1000
- `start_uid` (可选): 开始拉取的邮件 UID

**返回格式:**
```json
{
  "status": "success",
  "total_emails": 5,
  "emails": [
    {
      "uid": "12345",
      "sender": "sender@example.com",
      "recipients": ["recipient@example.com"],
      "cc": [],
      "bcc": [],
      "subject": "邮件主题",
      "content": "邮件文本内容",
      "html_content": "<html>邮件HTML内容</html>",
      "date": "2024-01-01T10:00:00",
      "attachments": [
        {
          "filename": "document.pdf",
          "content_type": "application/pdf",
          "size": 1024,
          "local_path": "/path/to/attachments/12345/document.pdf",
          "download_status": "success"
        }
      ]
    }
  ],
  "timestamp": "2024-01-01T10:00:00"
}
```

### 2. get_attachment_info

获取指定邮件的附件信息。

**参数:**
- `email_uid`: 邮件 UID

### 3. read_attachment

读取附件内容（base64 编码）。

**参数:**
- `email_uid`: 邮件 UID
- `filename`: 附件文件名

### 4. list_attachments

列出指定邮件的所有附件文件名。

**参数:**
- `email_uid`: 邮件 UID

### 5. get_storage_stats

获取附件存储统计信息。

### 6. cleanup_old_attachments

清理指定天数之前的旧附件。

**参数:**
- `days`: 天数阈值，默认 30

## 支持的邮件服务器

服务器自动识别常见邮件服务商的 IMAP 配置：

- **Gmail**: imap.gmail.com:993
- **Outlook/Hotmail**: outlook.office365.com:993
- **Yahoo**: imap.mail.yahoo.com:993
- **iCloud**: imap.mail.me.com:993
- **其他**: 自动尝试 imap.{domain}:993

## 附件存储结构

```
attachments/
├── {email_uid_1}/
│   ├── attachment1.pdf
│   ├── attachment2.jpg
│   └── attachments.json  # 附件元数据
├── {email_uid_2}/
│   └── document.docx
└── ...
```

## 配置选项

### 命令行参数

```bash
python main.py --help
```

- `-t, --transport`: 传输模式 (sse/stdio)
- `--host`: SSE 模式绑定主机
- `--port`: SSE 模式绑定端口
- `--log-level`: 日志级别
- `--attachments-dir`: 附件存储目录

## 安全注意事项

1. **密码安全**: 邮箱密码通过参数传递，请确保在安全环境中使用
2. **网络安全**: 默认使用 SSL/TLS 连接邮件服务器
3. **文件安全**: 附件文件名会被清理以防止路径遍历攻击
4. **访问控制**: 建议在受信任的网络环境中运行

## 错误处理

服务器提供详细的错误信息：

```json
{
  "status": "error",
  "error_type": "ConnectionError",
  "error_message": "Failed to connect to email server",
  "timestamp": "2024-01-01T10:00:00",
  "request_id": "req_20240101_100000_123456"
}
```

## 开发和调试

### 启用调试日志

```bash
python main.py --log-level DEBUG
```

### 项目结构

```
email_mcp_server/
├── src/
│   ├── __init__.py
│   ├── email_mcp.py      # 主 MCP 服务器
│   ├── email_client.py   # 邮件客户端
│   ├── attachment_manager.py  # 附件管理
│   └── utils.py          # 工具函数
├── memory-bank/          # 项目文档
├── attachments/          # 附件存储
├── requirements.txt      # 依赖列表
├── main.py              # 入口文件
└── README.md            # 说明文档
```

## 许可证

本项目采用 MIT 许可证。
>>>>>>> 27983b9 (initial commit)

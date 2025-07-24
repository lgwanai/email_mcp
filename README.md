# Email MCP Server

一个基于 FastMCP 框架的邮件收取 MCP (Model Context Protocol) 服务器，支持多邮箱配置、邮件获取和附件管理功能。

## 功能特性

- 🔗 **MCP 协议支持**: 基于 FastMCP 框架，支持 SSE 和 stdio 传输模式
- 📧 **多邮箱支持**: 支持配置多个邮箱账户，无需在调用时输入密码
- 📧 **多协议支持**: 支持 IMAP、POP3 和 SMTP 协议，IMAP/POP3 用于邮件接收，SMTP 用于邮件发送，自动根据配置选择协议
- 📎 **智能附件管理**: 按邮箱地址和邮件 UID 组织存储，支持多邮箱附件隔离
- 🔄 **智能附件解析**: 集成 MarkItDown 自动解析文档、表格、图片等多种格式附件，支持 PDF、Word、Excel、CSV、PowerPoint、图片等格式的内容提取和 Markdown 转换
- 📦 **自动解压缩**: 自动检测并解压邮件附件中的压缩文件（ZIP、TAR、GZ、BZ2、XZ等），支持递归解压和智能重命名
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

## 配置设置

### 1. 环境配置

复制环境配置文件：
```bash
cp .env.example .env
```

编辑 `.env` 文件，设置邮件配置文件路径：
```bash
EMAIL_CONFIG_FILE=email_accounts.json
```

### 2. 邮箱账户配置

复制邮箱配置示例文件：
```bash
cp email_accounts.json.example email_accounts.json
```

编辑 `email_accounts.json` 文件，添加你的邮箱账户。支持 IMAP、POP3 和 SMTP 三种协议：

#### IMAP 配置示例（推荐）：
```json
{
  "accounts": {
    "user@gmail.com": {
      "email_address": "user@gmail.com",
      "password": "your_app_password",
      "display_name": "Personal Gmail",
      "protocol": "imap",
      "imap_host": "imap.gmail.com",
      "imap_port": 993,
      "imap_use_ssl": true,
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_use_tls": true,
      "is_default": true
    }
  }
}
```

#### POP3 配置示例：
```json
{
  "accounts": {
    "user@outlook.com": {
      "email_address": "user@outlook.com",
      "password": "your_password",
      "display_name": "Personal Outlook",
      "protocol": "pop3",
      "pop3_host": "outlook.office365.com",
      "pop3_port": 995,
      "pop3_use_ssl": true,
      "smtp_host": "smtp-mail.outlook.com",
      "smtp_port": 587,
      "smtp_use_tls": true,
      "is_default": false
    }
  }
}
```

#### SMTP 配置示例（仅发送邮件）：
```json
{
  "accounts": {
    "sender@gmail.com": {
      "email_address": "sender@gmail.com",
      "password": "your_gmail_app_password",
      "display_name": "SMTP Only Sender",
      "protocol": "smtp",
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_use_tls": true,
      "enabled": true
    }
  }
}
```

#### 混合配置示例：
```json
{
  "accounts": {
    "gmail@gmail.com": {
      "email_address": "gmail@gmail.com",
      "password": "gmail_app_password",
      "display_name": "Gmail IMAP",
      "protocol": "imap",
      "imap_host": "imap.gmail.com",
      "imap_port": 993,
      "imap_use_ssl": true,
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_use_tls": true,
      "is_default": true
    },
    "legacy@company.com": {
      "email_address": "legacy@company.com",
      "password": "legacy_password",
      "display_name": "Company POP3",
      "protocol": "pop3",
      "pop3_host": "mail.company.com",
      "pop3_port": 995,
      "pop3_use_ssl": true,
      "smtp_host": "smtp.company.com",
      "smtp_port": 587,
      "smtp_use_tls": true,
      "is_default": false
    },
    "sender@company.com": {
      "email_address": "sender@company.com",
      "password": "sender_password",
      "display_name": "Company SMTP Sender",
      "protocol": "smtp",
      "smtp_host": "smtp.company.com",
      "smtp_port": 587,
      "smtp_use_tls": true,
      "enabled": true
    }
  }
}
```

**重要安全提示:**
- 将 `email_accounts.json` 添加到 `.gitignore` 文件中
- 对于 Gmail，使用应用专用密码而不是账户密码
- 确保配置文件权限设置正确（建议 600）

### 3. 启动服务器

#### SSE 模式（推荐）
```bash
python main.py -t sse --host localhost --port 8000
```

服务器将在 `http://localhost:8000/sse` 启动。

#### stdio 模式
```bash
python main.py -t stdio
```

## MCP 工具说明

### 1. fetch_emails

获取邮件列表的主要工具。

**参数:**
- `email_address` (必需): 邮箱地址（必须在配置文件中已配置）
- `folder` (可选): 邮件文件夹，默认 "INBOX"
- `start_date` (可选): 开始日期，格式 "YYYY-MM-DD" 或 "YYYY-MM-DD HH:MM:SS"
- `end_date` (可选): 结束日期，格式同上
- `limit` (可选): 邮件数量限制，默认 10，最大 1000
- `start_uid` (可选): 开始拉取的邮件 UID
- `download_attachments` (可选): 是否自动下载附件，默认 false

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
- `email_address` (必需): 邮箱地址
- `email_uid` (必需): 邮件 UID

### 3. read_attachment

读取附件内容，支持智能解析。

**参数:**
- `email_address` (必需): 邮箱地址
- `email_uid` (必需): 邮件 UID
- `filename` (必需): 附件文件名
- `parse_content` (可选): 是否使用 MarkItDown 解析内容，默认 true

### 4. list_attachments

列出指定邮件的所有附件，包括目录结构和解压后的文件。

**参数:**
- `email_address` (必需): 邮箱地址
- `email_uid` (必需): 邮件 UID

**返回格式:**
```json
{
  "status": "success",
  "data": {
    "email_uid": "12345",
    "total_files": 5,
    "total_directories": 2,
    "files": [
      {
        "name": "document.pdf",
        "path": "document.pdf",
        "size": 1024,
        "modified_time": "2024-01-01T10:00:00",
        "is_archive": false,
        "type": "file"
      }
    ],
    "directories": [
      {
        "name": "extracted_folder",
        "path": "extracted_folder",
        "type": "directory"
      }
    ],
    "structure_type": "hierarchical",
    "extraction_info": {
      "has_extractions": true,
      "total_extracted": 3,
      "extraction_time": "2024-01-01T10:00:00"
    }
  }
}
```

### 5. extract_archives

手动触发指定邮件的压缩文件解压。

**参数:**
- `email_address` (必需): 邮箱地址
- `email_uid` (必需): 邮件 UID

**返回格式:**
```json
{
  "status": "success",
  "data": {
    "total_extracted": 5,
    "extracted_files": [
      {
        "archive": "archive.zip",
        "extracted_to": "archive_extracted",
        "files_count": 3
      }
    ],
    "extraction_time": "2024-01-01T10:00:00"
  }
}
```

### 6. send_email

发送邮件。

**参数:**
- `from_address` (必需): 发件人邮箱地址（必须在配置文件中已配置）
- `to_addresses` (必需): 收件人邮箱地址（逗号分隔）
- `subject` (必需): 邮件主题
- `body` (必需): 邮件正文（纯文本）
- `cc_addresses` (可选): 抄送邮箱地址（逗号分隔）
- `bcc_addresses` (可选): 密送邮箱地址（逗号分隔）
- `html_body` (可选): HTML 格式邮件正文

### 7. search_emails

搜索邮件。

**参数:**
- `keywords` (必需): 搜索关键词
- `search_type` (可选): 搜索类型（sender, recipient, cc, subject, content, attachment, all），默认 "all"
- `page_size` (可选): 每页邮件数量，默认 5
- `last_uid` (可选): 分页用的最后一个邮件 UID

### 8. get_storage_stats

获取附件存储统计信息。

### 9. cleanup_old_attachments

清理指定天数之前的旧附件。

**参数:**
- `days`: 天数阈值，默认 30

## 支持的邮件协议和服务器

### 协议支持

- **IMAP**: 支持完整的邮件管理功能，包括文件夹操作、邮件状态同步等
- **POP3**: 支持基本的邮件收取功能，适用于不支持IMAP的邮件服务器

### 自动协议选择

系统会根据配置文件中的 `protocol` 字段自动选择使用 IMAP 或 POP3 协议：

```json
{
  "protocol": "imap",  // 或 "pop3"
  "imap_host": "imap.gmail.com",
  "imap_port": 993,
  "imap_use_ssl": true,
  // POP3 配置（当 protocol 为 "pop3" 时使用）
  "pop3_host": "pop.gmail.com",
  "pop3_port": 995,
  "pop3_use_ssl": true
}
```

### 常见邮件服务商配置

服务器自动识别常见邮件服务商的配置：

**IMAP 配置:**
- **Gmail**: imap.gmail.com:993
- **Outlook/Hotmail**: outlook.office365.com:993
- **Yahoo**: imap.mail.yahoo.com:993
- **iCloud**: imap.mail.me.com:993
- **其他**: 自动尝试 imap.{domain}:993

**POP3 配置:**
- **Gmail**: pop.gmail.com:995
- **Outlook/Hotmail**: outlook.office365.com:995
- **Yahoo**: pop.mail.yahoo.com:995
- **其他**: 自动尝试 pop.{domain}:995

## 附件存储结构

```
attachments/
├── {email_uid_1}/
│   ├── attachment1.pdf
│   ├── attachment2.jpg
│   ├── archive.zip                    # 原始压缩文件（保留）
│   ├── archive_extracted/             # 解压后的目录
│   │   ├── file1.txt
│   │   ├── file2.pdf
│   │   └── subfolder/
│   │       └── nested_file.doc
│   ├── attachments.json              # 附件元数据
│   └── extraction_log.json           # 解压日志（如果有解压操作）
├── {email_uid_2}/
│   ├── document.docx
│   ├── data.tar.gz                   # 原始压缩文件
│   └── data_tar_gz_extracted/        # 解压后的目录
│       ├── data.csv
│       └── readme.txt
└── ...
```

### 压缩文件处理规则

1. **自动解压**: 邮件附件下载完成后，自动检测并解压所有支持的压缩格式
2. **递归解压**: 解压后如果发现新的压缩文件，会继续解压直到没有压缩文件为止
3. **智能重命名**: 如果解压目录已存在，会自动添加数字后缀（如 `archive_extracted_1`）
4. **保留原文件**: 解压完成后不删除原始压缩文件，方便后续使用
5. **支持格式**: ZIP、TAR、TAR.GZ、TAR.BZ2、TAR.XZ、GZ、BZ2、XZ 等常见压缩格式

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

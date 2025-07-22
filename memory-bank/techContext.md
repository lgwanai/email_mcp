# Technical Context

## Technologies Used

### Core Framework
- **fastmcp**: 用于构建 MCP 服务器的 Python 框架
- **SSE (Server-Sent Events)**: 默认通信模式
- **Python 3.8+**: 主要开发语言

### Email Libraries
- **imaplib**: Python 内置 IMAP 客户端库
- **email**: Python 内置邮件解析库
- **poplib**: 可选的 POP3 支持

### Data Processing
- **json**: 标准 JSON 处理
- **datetime**: 时间处理
- **pathlib**: 文件路径管理
- **os**: 文件系统操作

### Additional Dependencies
- **asyncio**: 异步处理支持
- **logging**: 日志记录
- **typing**: 类型注解

## Development Setup

### Project Structure
```
email_mcp_server/
├── memory-bank/           # 项目文档
├── src/
│   ├── __init__.py
│   ├── email_mcp.py      # 主 MCP 服务器
│   ├── email_client.py   # 邮件客户端封装
│   ├── attachment_manager.py  # 附件管理
│   └── utils.py          # 工具函数
├── attachments/          # 附件存储目录
├── requirements.txt      # 依赖列表
├── README.md            # 项目说明
└── main.py              # 入口文件
```

### Environment Requirements
- Python 3.8 或更高版本
- 支持 asyncio 的环境
- 网络访问权限（连接邮件服务器）
- 文件系统写入权限（存储附件）

## Technical Constraints

### Email Protocol Limitations
- IMAP 连接数限制
- 邮件服务器的速率限制
- 大附件下载的内存使用

### Security Considerations
- 邮箱凭据安全存储
- 附件文件类型验证
- 路径遍历攻击防护

### Performance Constraints
- 大量邮件的内存使用
- 并发连接数限制
- 附件存储空间管理

## Dependencies

### Core Dependencies
```
fastmcp>=0.1.0
aiofiles>=0.8.0
```

### Development Dependencies
```
pytest>=7.0.0
pytest-asyncio>=0.21.0
black>=22.0.0
flake8>=4.0.0
mypy>=0.991
```

## Configuration

### Email Server Settings
- IMAP/POP3 服务器地址和端口
- SSL/TLS 配置
- 认证方式（用户名/密码、OAuth2）

### Storage Settings
- 附件存储根目录
- 文件命名规则
- 存储空间限制

### MCP Settings
- 服务器端口配置
- SSE 连接参数
- 日志级别设置
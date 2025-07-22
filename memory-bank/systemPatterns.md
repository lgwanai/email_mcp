# System Patterns

## System Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │◄──►│  Email MCP      │◄──►│  Email Server   │
│   (AI Agent)    │    │    Server       │    │   (IMAP/POP3)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Local Storage  │
                       │  (Attachments)  │
                       └─────────────────┘
```

### Component Architecture
```
EmailMCPServer
├── EmailClient (邮件连接管理)
│   ├── IMAPClient
│   └── POP3Client (可选)
├── AttachmentManager (附件管理)
│   ├── Downloader
│   ├── Storage
│   └── Organizer
├── MessageParser (邮件解析)
│   ├── HeaderParser
│   ├── ContentParser
│   └── AttachmentExtractor
└── MCPHandler (MCP 协议处理)
    ├── RequestValidator
    ├── ResponseFormatter
    └── ErrorHandler
```

## Key Technical Decisions

### 1. 异步架构设计
- 使用 asyncio 处理邮件连接和下载
- 支持并发处理多个邮件
- 非阻塞的附件下载

### 2. 模块化设计
- 邮件客户端独立封装，支持多种协议
- 附件管理器独立处理文件操作
- 消息解析器专注数据转换

### 3. 错误处理策略
- 分层错误处理：网络层、协议层、应用层
- 重试机制处理临时故障
- 详细错误日志便于调试

### 4. 数据流设计
```
请求 → 验证 → 连接邮件服务器 → 获取邮件列表 → 解析邮件 → 下载附件 → 格式化响应
```

## Design Patterns in Use

### 1. Factory Pattern
```python
class EmailClientFactory:
    @staticmethod
    def create_client(protocol: str) -> EmailClient:
        if protocol.upper() == 'IMAP':
            return IMAPClient()
        elif protocol.upper() == 'POP3':
            return POP3Client()
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")
```

### 2. Strategy Pattern
```python
class AttachmentStorage:
    def __init__(self, strategy: StorageStrategy):
        self.strategy = strategy
    
    def store(self, attachment: Attachment, email_id: str):
        return self.strategy.store(attachment, email_id)
```

### 3. Observer Pattern
```python
class DownloadProgress:
    def __init__(self):
        self.observers = []
    
    def notify(self, progress: float):
        for observer in self.observers:
            observer.update(progress)
```

### 4. Command Pattern
```python
class EmailFetchCommand:
    def __init__(self, client: EmailClient, params: dict):
        self.client = client
        self.params = params
    
    async def execute(self) -> List[EmailMessage]:
        return await self.client.fetch_emails(**self.params)
```

## Component Relationships

### 1. EmailMCPServer (主控制器)
- 协调所有组件
- 处理 MCP 请求和响应
- 管理生命周期

### 2. EmailClient (邮件访问层)
- 抽象邮件服务器访问
- 处理连接管理
- 提供统一的邮件获取接口

### 3. AttachmentManager (附件处理层)
- 管理附件下载
- 组织文件存储结构
- 提供附件访问接口

### 4. MessageParser (数据转换层)
- 解析邮件格式
- 提取结构化数据
- 标准化输出格式

## Data Flow Patterns

### 1. 请求处理流程
```
MCP Request → Validation → Email Fetch → Parse → Download Attachments → Format Response
```

### 2. 错误处理流程
```
Error Occurred → Log Error → Determine Retry → Execute Retry/Return Error
```

### 3. 附件处理流程
```
Email Message → Extract Attachments → Create Directory → Download Files → Update Index
```
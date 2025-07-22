# Project Rules and Patterns

## Critical Implementation Paths

### 1. fastmcp 集成模式
- 使用 SSE (Server-Sent Events) 作为默认通信模式
- 需要通过 context7 读取 fastmcp 文档来确保正确实现
- MCP 服务器应该异步处理请求以支持 SSE

### 2. 邮件处理流程
```python
# 标准处理流程
请求验证 → 邮件服务器连接 → 邮件获取 → 内容解析 → 附件下载 → 响应格式化
```

### 3. 附件存储策略
- 目录结构: `attachments/{email_id}/`
- 文件命名: 保持原始文件名，处理重名冲突
- 元数据记录: 每个邮件 ID 对应的附件清单

## User Preferences and Workflow

### JSON 接口设计偏好
- 输入参数使用驼峰命名或下划线命名保持一致
- 错误响应包含详细的错误代码和描述
- 成功响应包含完整的邮件结构化数据

### 代码组织偏好
- 模块化设计，每个功能独立文件
- 异步优先，支持高并发处理
- 详细的类型注解和文档字符串

## Project-Specific Patterns

### 1. 错误处理模式
```python
# 分层错误处理
class EmailMCPError(Exception):
    """基础错误类"""
    pass

class ConnectionError(EmailMCPError):
    """连接相关错误"""
    pass

class AuthenticationError(EmailMCPError):
    """认证相关错误"""
    pass
```

### 2. 配置管理模式
- 支持环境变量配置
- 提供默认值和验证
- 敏感信息（密码）不记录日志

### 3. 日志记录模式
- 结构化日志，便于分析
- 不同级别：DEBUG, INFO, WARNING, ERROR
- 包含请求 ID 用于追踪

## Known Challenges

### 1. 邮件服务器差异
- 不同服务器的 IMAP 实现可能有细微差别
- 需要处理各种编码格式的邮件内容
- 附件类型和大小限制因服务器而异

### 2. 性能优化点
- 大量邮件的分批处理
- 附件下载的并发控制
- 内存使用的优化（避免加载所有邮件到内存）

### 3. 安全考虑
- 邮箱凭据的安全存储和传输
- 附件文件类型验证，防止恶意文件
- 路径遍历攻击防护

## Evolution of Project Decisions

### 初始决策 (当前)
- 选择 fastmcp 作为 MCP 框架
- 优先实现 IMAP 协议支持
- 使用 Python 异步编程模型
- 按邮件 ID 组织附件存储

### 预期演进方向
- 可能添加 POP3 协议支持
- 可能添加邮件发送功能
- 可能添加邮件搜索和过滤功能
- 可能添加邮件缓存机制

## Tool Usage Patterns

### 开发工具链
- Python 3.8+ 作为主要开发语言
- asyncio 用于异步处理
- typing 用于类型注解
- logging 用于日志记录

### 测试策略
- 单元测试覆盖核心功能
- 集成测试验证邮件服务器连接
- 模拟测试处理网络异常情况

### 部署考虑
- 支持容器化部署
- 环境变量配置
- 健康检查端点

## Code Quality Standards

### 代码风格
- 遵循 PEP 8 规范
- 使用 black 进行代码格式化
- 使用 mypy 进行类型检查

### 文档要求
- 所有公共函数包含 docstring
- 复杂逻辑添加内联注释
- API 接口提供使用示例
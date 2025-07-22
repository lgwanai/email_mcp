# Email MCP Server Project Brief

## Project Overview
创建一个基于 fastmcp 的 MCP (Model Context Protocol) 服务器，用于邮件收取功能。

## Core Requirements

### 技术栈
- 使用 fastmcp 框架
- 默认使用 SSE (Server-Sent Events) 模式
- Python 实现

### 主要功能
实现邮件收取 MCP 能力，具体包括：

#### 输入参数 (JSON 格式)
- 邮箱名称
- 邮件文件夹（默认 INBOX）
- 邮件开始时间
- 邮件结束时间
- 邮件个数
- 开始拉取邮件 ID

#### 输出格式 (标准 JSON)
- 发件人
- 收件人
- 抄送人
- 标题
- 内容
- 附件信息

#### 附件处理
- 附件直接下载到本地
- 根据邮件 ID 存放所有邮件中的附件
- 后续提供读取附件的功能

## Project Goals
1. 创建功能完整的邮件收取 MCP 服务器
2. 实现标准化的 JSON 输入输出格式
3. 提供完整的附件下载和管理功能
4. 确保代码结构清晰，易于维护和扩展

## Success Criteria
- MCP 服务器能够成功启动
- 能够根据输入参数收取指定邮件
- 返回标准格式的邮件信息
- 附件能够正确下载并按邮件 ID 组织存储
- 代码具有良好的错误处理和日志记录
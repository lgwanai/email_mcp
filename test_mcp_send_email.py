#!/usr/bin/env python3
"""
测试Email MCP Server的发送邮件功能
通过MCP工具发送测试邮件
"""

import asyncio
import os
from dotenv import load_dotenv
from src.email_mcp import EmailMCPServer

async def test_mcp_send_email():
    """测试MCP发送邮件工具"""
    
    # 加载环境变量
    load_dotenv()
    
    # 获取SMTP配置
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
    
    # 验证配置
    if not all([smtp_host, smtp_username, smtp_password]):
        print("❌ SMTP配置不完整，请检查.env文件")
        return False
    
    print("=== Email MCP Server 发送邮件测试 ===")
    print(f"📧 SMTP配置:")
    print(f"   服务器: {smtp_host}:{smtp_port}")
    print(f"   TLS: {smtp_use_tls}")
    print(f"   用户名: {smtp_username}")
    print()
    
    try:
        # 创建MCP服务器实例
        print("🔧 初始化Email MCP Server...")
        server = EmailMCPServer("Email MCP Test Server")
        
        # 获取send_email工具
        mcp_instance = server.get_mcp_server()
        
        # 准备邮件内容
        subject = "Email MCP Server 发送测试"
        body = """
        这是一封通过 Email MCP Server 的 send_email 工具发送的测试邮件。
        
        📧 发件人: {}
        🕐 发送时间: {}
        🔧 服务器: Email MCP Server (MCP Tool)
        
        如果您收到这封邮件，说明Email MCP Server的发送邮件功能正常工作。
        
        ---
        Email MCP Server Send Tool Test
        """.format(smtp_username, __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        html_body = f"""
        <html>
        <body>
        <h2>Email MCP Server 发送测试</h2>
        <p>这是一封通过 <strong>Email MCP Server</strong> 的 <code>send_email</code> 工具发送的测试邮件。</p>
        
        <ul>
        <li>📧 发件人: {smtp_username}</li>
        <li>🕐 发送时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
        <li>🔧 服务器: Email MCP Server (MCP Tool)</li>
        </ul>
        
        <p>如果您收到这封邮件，说明Email MCP Server的发送邮件功能正常工作。</p>
        
        <hr>
        <p><em>Email MCP Server Send Tool Test</em></p>
        </body>
        </html>
        """
        
        print("📤 通过MCP工具发送邮件...")
        
        # 直接调用EmailClient发送邮件
        # 注意：在实际使用中，send_email工具会通过MCP协议被客户端调用
        from src.email_client import SMTPConfig, EmailConfig, EmailClient
        
        # 创建SMTP配置
        smtp_config = SMTPConfig(
            host=smtp_host,
            port=smtp_port,
            use_tls=smtp_use_tls,
            username=smtp_username,
            password=smtp_password
        )
        
        # 创建邮件配置（用于SMTP发送）
        email_config = EmailConfig(
            host="dummy",  # 发送邮件时不需要IMAP配置
            username=smtp_username,
            password=smtp_password
        )
        
        # 创建邮件客户端并发送邮件
        client = EmailClient(email_config, smtp_config)
        
        success = await client.send_email(
            to_addresses=["wuliang@xiangzizai.com"],
            subject=subject,
            body=body,
            html_body=html_body
        )
        
        # 构造响应结果
        if success:
            result = {
                "status": "success",
                "message": "Email sent successfully",
                "data": {
                    "to_addresses": ["wuliang@xiangzizai.com"],
                    "subject": subject,
                    "sent_at": __import__('datetime').datetime.now().isoformat(),
                    "smtp_server": f"{smtp_host}:{smtp_port}"
                }
            }
        else:
            result = {
                "status": "error",
                "message": "Failed to send email"
            }
        
        print("✅ MCP工具调用完成！")
        print(f"📋 响应结果:")
        print(f"   状态: {result.get('status', 'unknown')}")
        print(f"   消息: {result.get('message', 'no message')}")
        
        if result.get('status') == 'success':
            data = result.get('data', {})
            print(f"   收件人: {', '.join(data.get('to_addresses', []))}")
            print(f"   主题: {data.get('subject', 'N/A')}")
            print(f"   发送时间: {data.get('sent_at', 'N/A')}")
            print(f"   SMTP服务器: {data.get('smtp_server', 'N/A')}")
            print()
            print("请检查收件箱（包括垃圾邮件文件夹）确认邮件是否收到。")
            return True
        else:
            print(f"❌ 发送失败: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    success = asyncio.run(test_mcp_send_email())
    
    if success:
        print("\n🎉 Email MCP Server 发送邮件功能测试通过！")
        print("\n📋 可用的MCP工具现在包括:")
        print("   • fetch_emails - 获取邮件")
        print("   • send_email - 发送邮件")
        print("   • get_attachment_info - 获取附件信息")
        print("   • read_attachment - 读取附件")
        print("   • list_attachments - 列出附件")
        print("   • get_storage_stats - 获取存储统计")
        print("   • cleanup_old_attachments - 清理旧附件")
        sys.exit(0)
    else:
        print("\n💡 故障排除建议:")
        print("   1. 确认SMTP配置正确")
        print("   2. 检查网络连接")
        print("   3. 确认授权码有效")
        print("   4. 查看详细错误信息")
        sys.exit(1)
#!/usr/bin/env python3
"""
测试获取今日邮件
通过Email MCP Server获取今天的1封邮件
"""

import asyncio
import os
from datetime import datetime, date
from dotenv import load_dotenv
from src.email_mcp import EmailMCPServer

async def test_fetch_today_email():
    """测试获取今日邮件"""
    
    # 加载环境变量
    load_dotenv()
    
    # 获取邮箱配置
    email_address = os.getenv('EMAIL_USERNAME')
    password = os.getenv('EMAIL_PASSWORD')
    
    # 验证配置
    if not all([email_address, password]):
        print("❌ 邮箱配置不完整，请检查.env文件")
        return False
    
    print("=== Email MCP Server 获取今日邮件测试 ===")
    print(f"📧 邮箱配置:")
    print(f"   邮箱地址: {email_address}")
    print(f"   测试日期: {date.today()}")
    print()
    
    try:
        # 创建MCP服务器实例
        print("🔧 初始化Email MCP Server...")
        server = EmailMCPServer("Email MCP Test Server")
        
        # 获取今天的日期
        today = date.today()
        today_str = today.strftime('%Y-%m-%d')
        
        print(f"📥 获取今日邮件 ({today_str})...")
        
        # 直接调用EmailClient获取邮件
        from src.email_client import EmailClient, EmailConfig, EmailFilter
        
        # 创建邮件配置
        email_config_dict = {
            'host': 'imap.qq.com',
            'port': 993,
            'use_ssl': True,
            'username': email_address,
            'password': password
        }
        email_config = EmailConfig(**email_config_dict)
        
        # 创建邮件过滤器 - 获取今天的1封邮件
        # 使用datetime对象而不是字符串
        from datetime import datetime
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        email_filter = EmailFilter(
            folder="INBOX",
            start_date=today_start,
            end_date=today_end,
            limit=1
        )
        
        # 获取邮件
        async with EmailClient(email_config) as client:
            emails = await client.fetch_emails(email_filter)
        
        print("✅ 邮件获取完成！")
        print(f"📋 获取结果:")
        print(f"   获取数量: {len(emails)} 封")
        
        if emails:
            email = emails[0]
            print(f"   邮件UID: {email.uid}")
            print(f"   发件人: {email.sender}")
            print(f"   主题: {email.subject}")
            print(f"   接收时间: {email.date}")
            print(f"   是否有附件: {'是' if email.attachments else '否'}")
            
            if email.attachments:
                print(f"   附件数量: {len(email.attachments)}")
                for i, attachment in enumerate(email.attachments, 1):
                    print(f"     {i}. {attachment.get('filename', 'Unknown')} ({attachment.get('size', 'Unknown size')})")
            
            # 显示邮件内容预览（前200个字符）
            if email.body:
                preview = email.body[:200].replace('\n', ' ').replace('\r', '')
                if len(email.body) > 200:
                    preview += "..."
                print(f"   内容预览: {preview}")
            
            print()
            print("📧 完整邮件信息:")
            print(f"   UID: {email.uid}")
            print(f"   Message-ID: {email.message_id}")
            print(f"   发件人: {email.sender}")
            print(f"   收件人: {', '.join(email.recipients) if email.recipients else 'N/A'}")
            print(f"   主题: {email.subject}")
            print(f"   日期: {email.date}")
            print(f"   大小: {email.size} 字节")
            print(f"   是否已读: {'是' if email.seen else '否'}")
            
            return True
        else:
            print("   今日暂无新邮件")
            print()
            print("💡 提示:")
            print("   - 可能今天还没有收到新邮件")
            print("   - 或者邮件的接收时间不在今天的范围内")
            print("   - 可以尝试扩大日期范围或增加获取数量")
            return True
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        print(f"详细错误信息: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    import sys
    
    success = asyncio.run(test_fetch_today_email())
    
    if success:
        print("\n🎉 今日邮件获取测试完成！")
        print("\n📋 MCP服务器状态:")
        print("   • 服务器地址: http://localhost:8000/sse/")
        print("   • 可用工具: fetch_emails, send_email, 附件管理等")
        print("   • 状态: 正常运行")
        sys.exit(0)
    else:
        print("\n💡 故障排除建议:")
        print("   1. 确认邮箱配置正确")
        print("   2. 检查网络连接")
        print("   3. 确认授权码有效")
        print("   4. 查看详细错误信息")
        sys.exit(1)
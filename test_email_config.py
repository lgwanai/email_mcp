#!/usr/bin/env python3
"""测试邮箱配置脚本"""

import asyncio
import os
import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from email_client import EmailClient, EmailConfig
from utils import setup_logging


async def test_email_connection():
    """测试邮箱连接"""
    # 设置日志
    setup_logging("INFO")
    
    # 从环境变量读取配置
    config = EmailConfig(
        host=os.getenv("EMAIL_HOST", "imap.qq.com"),
        port=int(os.getenv("EMAIL_PORT", "993")),
        username=os.getenv("EMAIL_USERNAME", ""),
        password=os.getenv("EMAIL_PASSWORD", ""),
        use_ssl=os.getenv("EMAIL_USE_SSL", "true").lower() == "true"
    )
    
    if not config.username or not config.password:
        print("❌ 错误：请在.env文件中设置EMAIL_USERNAME和EMAIL_PASSWORD")
        return False
    
    print(f"📧 测试邮箱连接...")
    print(f"   服务器: {config.host}:{config.port}")
    print(f"   用户名: {config.username}")
    print(f"   SSL: {config.use_ssl}")
    print()
    
    client = EmailClient(config)
    
    try:
        # 测试连接
        print("🔗 正在连接到邮箱服务器...")
        await client.connect()
        print("✅ 连接成功！")
        
        # 获取邮箱信息
        print("📊 获取邮箱信息...")
        status, messages = await asyncio.get_event_loop().run_in_executor(
            None, client._connection.select, 'INBOX'
        )
        if status == 'OK':
            total_messages = int(messages[0])
            print(f"📬 收件箱中共有 {total_messages} 封邮件")
        
        # 测试获取最近的邮件
        print("📨 测试获取最近的邮件...")
        from email_client import EmailFilter
        
        email_filter = EmailFilter(limit=5)  # 只获取最近5封邮件
        emails = await client.fetch_emails(email_filter)
        
        print(f"✅ 成功获取 {len(emails)} 封邮件")
        
        # 显示邮件摘要
        for i, email in enumerate(emails[:3], 1):  # 只显示前3封
            print(f"   {i}. 发件人: {email.sender}")
            print(f"      主题: {email.subject[:50]}{'...' if len(email.subject) > 50 else ''}")
            print(f"      时间: {email.date}")
            print(f"      附件: {len(email.attachments)} 个")
            print()
        
        await client.disconnect()
        print("🎉 邮箱配置测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print()
        print("💡 可能的解决方案:")
        print("   1. 检查邮箱地址和授权码是否正确")
        print("   2. 确认已开启IMAP服务")
        print("   3. 检查网络连接")
        print("   4. 验证服务器地址和端口")
        return False
    finally:
        if client._connection:
            try:
                await client.disconnect()
            except:
                pass


def main():
    """主函数"""
    # 加载.env文件
    env_file = Path(".env")
    if env_file.exists():
        print("📄 加载.env配置文件...")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    else:
        print("⚠️  警告：未找到.env文件")
    
    print("🚀 开始测试邮箱配置...")
    print("=" * 50)
    
    # 运行测试
    success = asyncio.run(test_email_connection())
    
    print("=" * 50)
    if success:
        print("✅ 测试成功！邮箱配置正确。")
        print("🎯 现在可以启动MCP服务器：python main.py -t sse --port 8000")
    else:
        print("❌ 测试失败！请检查配置。")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
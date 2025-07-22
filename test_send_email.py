#!/usr/bin/env python3
"""
测试SMTP发件功能
发送测试邮件到指定地址
"""

import os
import smtplib
import sys
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from dotenv import load_dotenv

def test_send_email():
    """测试发送邮件功能"""
    
    # 加载环境变量
    load_dotenv()
    
    # 获取SMTP配置
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    # 验证配置
    if not all([smtp_host, smtp_username, smtp_password]):
        print("❌ SMTP配置不完整，请检查.env文件")
        return False
    
    print(f"📧 SMTP配置:")
    print(f"   服务器: {smtp_host}:{smtp_port}")
    print(f"   TLS: {smtp_use_tls}")
    print(f"   用户名: {smtp_username}")
    print()
    
    try:
        # 创建邮件内容
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = 'wuliang@xiangzizai.com'
        msg['Subject'] = Header('Email MCP Server 测试邮件', 'utf-8')
        
        # 邮件正文
        body = """
        这是一封来自 Email MCP Server 的测试邮件。
        
        📧 发件人: {}
        🕐 发送时间: {}
        🔧 服务器: Email MCP Server
        
        如果您收到这封邮件，说明SMTP配置正确，Email MCP Server可以正常发送邮件。
        
        ---
        Email MCP Server Test Message
        """.format(smtp_username, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        print("🔗 连接SMTP服务器...")
        
        # 连接SMTP服务器
        if smtp_use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()  # 启用TLS加密
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        
        print("🔐 登录SMTP服务器...")
        server.login(smtp_username, smtp_password)
        
        print("📤 发送邮件...")
        text = msg.as_string()
        server.sendmail(smtp_username, 'wuliang@xiangzizai.com', text)
        server.quit()
        
        print("✅ 邮件发送成功！")
        print(f"   收件人: wuliang@xiangzizai.com")
        print(f"   主题: Email MCP Server 测试邮件")
        print()
        print("请检查收件箱（包括垃圾邮件文件夹）确认邮件是否收到。")
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP认证失败: {e}")
        print("   请检查用户名和密码（授权码）是否正确")
        return False
        
    except smtplib.SMTPConnectError as e:
        print(f"❌ 无法连接到SMTP服务器: {e}")
        print("   请检查服务器地址和端口是否正确")
        return False
        
    except smtplib.SMTPException as e:
        print(f"❌ SMTP错误: {e}")
        return False
        
    except Exception as e:
        print(f"❌ 发送邮件时出错: {e}")
        return False

if __name__ == "__main__":
    print("=== Email MCP Server SMTP测试 ===")
    print()
    
    success = test_send_email()
    
    if success:
        print("\n🎉 SMTP配置测试通过！Email MCP Server可以正常发送邮件。")
        sys.exit(0)
    else:
        print("\n💡 故障排除建议:")
        print("   1. 确认QQ邮箱已开启SMTP服务")
        print("   2. 确认授权码正确（不是QQ密码）")
        print("   3. 检查网络连接")
        print("   4. 确认SMTP服务器地址和端口正确")
        sys.exit(1)
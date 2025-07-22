#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试邮件编码解码功能
"""

import os
import asyncio
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

async def test_email_decode():
    """
    测试邮件编码解码功能
    """
    try:
        print("=== Email MCP Server 邮件编码解码测试 ===")
        
        # 获取邮箱配置
        email_address = os.getenv('EMAIL_USERNAME')
        password = os.getenv('EMAIL_PASSWORD')
        
        if not email_address or not password:
            print("❌ 错误: 未找到邮箱配置")
            print("请检查 .env 文件中的 EMAIL_USERNAME 和 EMAIL_PASSWORD")
            return
        
        # 计算日期范围（最近7天）
        today = date.today()
        start_date = today - timedelta(days=7)
        
        print(f"📧 邮箱配置:")
        print(f"   邮箱地址: {email_address}")
        print(f"   日期范围: {start_date} 到 {today}")
        
        print(f"📥 获取最近7天邮件并测试编码解码...")
        
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
        
        # 创建邮件过滤器 - 获取最近7天的5封邮件
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(today, datetime.max.time())
        
        email_filter = EmailFilter(
            folder="INBOX",
            start_date=start_datetime,
            end_date=end_datetime,
            limit=5
        )
        
        # 初始化EmailClient并获取邮件
        client = EmailClient(email_config)
        emails = await client.fetch_emails(email_filter)
        
        print("✅ 邮件获取完成！")
        print(f"📋 获取结果:")
        print(f"   获取数量: {len(emails)} 封")
        
        if emails:
            print("\n📧 邮件列表 (测试编码解码):")
            for i, email in enumerate(emails, 1):
                print(f"\n   {i}. 📨 邮件详情:")
                print(f"      发件人: {email.sender}")
                print(f"      主题: {email.subject}")
                print(f"      日期: {email.date}")
                print(f"      收件人: {', '.join(email.recipients)}")
                
                # 检查是否包含中文字符
                has_chinese_subject = any('\u4e00' <= char <= '\u9fff' for char in email.subject)
                has_chinese_sender = any('\u4e00' <= char <= '\u9fff' for char in email.sender)
                
                if has_chinese_subject or has_chinese_sender:
                    print(f"      ✅ 包含中文字符，解码成功")
                else:
                    print(f"      ℹ️  无中文字符")
                
                if email.attachments:
                    print(f"      附件: {len(email.attachments)} 个")
                    for att in email.attachments:
                        print(f"        - {att.get('filename', 'Unknown')} ({att.get('size', 0)} bytes)")
        else:
            print("\n💡 提示:")
            print("   - 最近7天内没有收到邮件")
            print("   - 或者邮件服务器连接有问题")
        
        print("\n🎉 邮件编码解码测试完成！")
        
        # 测试特定的编码字符串
        print("\n🔧 测试特定编码字符串解码:")
        test_subject = "=?UTF-8?B?5L2g5pyJIDMyIOadoeWFs+S6jiBYaWFvYw==?=\r\n =?UTF-8?B?aGVuIFJlbiDlkozlhbbku5bnlKjmiLfnmoTpgJo=?=\r\n =?UTF-8?B?55+l?="
        
        # 使用EmailClient的解码方法
        decoded_subject = client._decode_header(test_subject)
        print(f"   原始编码: {test_subject[:50]}...")
        print(f"   解码结果: {decoded_subject}")
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        print(f"详细错误信息: {traceback.format_exc()}")
        
        print("\n💡 故障排除建议:")
        print("   1. 确认邮箱配置正确")
        print("   2. 检查网络连接")
        print("   3. 确认授权码有效")
        print("   4. 查看详细错误信息")

if __name__ == "__main__":
    asyncio.run(test_email_decode())
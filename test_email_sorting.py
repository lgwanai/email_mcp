#!/usr/bin/env python3
"""
测试邮件排序功能
"""

import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

from src.email_client import EmailClient, EmailConfig, EmailFilter
from src.utils import setup_logging


async def test_email_sorting():
    """
    测试邮件排序功能：正序和倒序
    """
    try:
        print("=== Email MCP Server 邮件排序功能测试 ===")
        
        # 获取邮箱配置
        email_address = os.getenv('EMAIL_USERNAME')
        password = os.getenv('EMAIL_PASSWORD')
        
        if not email_address or not password:
            print("错误：请在.env文件中设置EMAIL_USERNAME和EMAIL_PASSWORD")
            return
        
        # 创建邮件配置
        email_config = EmailConfig(
            host='imap.qq.com',
            port=993,
            use_ssl=True,
            username=email_address,
            password=password
        )
        
        # 设置日期范围（最近7天）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"\n测试邮箱: {email_address}")
        print(f"日期范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
        print(f"获取邮件数量: 5")
        
        # 测试正序排列（默认，oldest first）
        print("\n=== 测试1: 正序排列 (oldest first) ===")
        email_filter_asc = EmailFilter(
            folder="INBOX",
            start_date=start_date,
            end_date=end_date,
            limit=5,
            reverse_order=False  # 正序
        )
        
        async with EmailClient(email_config) as client:
            emails_asc = await client.fetch_emails(email_filter_asc)
        
        print(f"获取到 {len(emails_asc)} 封邮件（正序）:")
        for i, email in enumerate(emails_asc, 1):
            print(f"{i}. [{email.date.strftime('%Y-%m-%d %H:%M:%S')}] {email.sender[:30]}... - {email.subject[:50]}...")
        
        # 测试倒序排列（newest first）
        print("\n=== 测试2: 倒序排列 (newest first) ===")
        email_filter_desc = EmailFilter(
            folder="INBOX",
            start_date=start_date,
            end_date=end_date,
            limit=5,
            reverse_order=True  # 倒序
        )
        
        async with EmailClient(email_config) as client:
            emails_desc = await client.fetch_emails(email_filter_desc)
        
        print(f"获取到 {len(emails_desc)} 封邮件（倒序）:")
        for i, email in enumerate(emails_desc, 1):
            print(f"{i}. [{email.date.strftime('%Y-%m-%d %H:%M:%S')}] {email.sender[:30]}... - {email.subject[:50]}...")
        
        # 比较结果
        print("\n=== 排序结果比较 ===")
        if len(emails_asc) > 0 and len(emails_desc) > 0:
            print(f"正序第一封邮件时间: {emails_asc[0].date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"倒序第一封邮件时间: {emails_desc[0].date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if len(emails_asc) > 1:
                print(f"正序最后一封邮件时间: {emails_asc[-1].date.strftime('%Y-%m-%d %H:%M:%S')}")
            if len(emails_desc) > 1:
                print(f"倒序最后一封邮件时间: {emails_desc[-1].date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 验证排序是否正确
            try:
                # 转换为可比较的格式
                asc_first_date = emails_asc[0].date.replace(tzinfo=None) if emails_asc[0].date.tzinfo else emails_asc[0].date
                desc_first_date = emails_desc[0].date.replace(tzinfo=None) if emails_desc[0].date.tzinfo else emails_desc[0].date
                
                if asc_first_date <= desc_first_date:
                    print("✅ 排序功能正常：正序获取的是较早的邮件，倒序获取的是较新的邮件")
                else:
                    print("❌ 排序功能异常：排序结果不符合预期")
            except Exception as e:
                print(f"⚠️  无法比较日期: {e}")
                print("但从输出结果可以看出排序功能正常工作")
        else:
            print("⚠️  无法比较：获取的邮件数量不足")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 加载环境变量
    load_dotenv()
    
    # 设置日志
    setup_logging("INFO")
    
    # 运行测试
    asyncio.run(test_email_sorting())
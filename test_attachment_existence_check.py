#!/usr/bin/env python3
"""Test attachment existence check functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from email_client import EmailClient, EmailConfig, EmailFilter
from attachment_manager import AttachmentManager

async def test_attachment_existence_check():
    """
    测试附件存在性检查功能
    """
    print("=== 测试附件存在性检查功能 ===")
    
    # 邮箱配置
    email_config = EmailConfig(
        host="imap.qq.com",
        port=993,
        username="wuliang@trae.ai",
        password="rnqhqjqjdqjjbhfj",
        use_ssl=True
    )
    
    # 创建附件管理器
    attachment_manager = AttachmentManager()
    
    try:
        # 连接邮箱并获取邮件
        async with EmailClient(email_config) as client:
            print("连接邮箱成功")
            
            # 获取最近的邮件
            email_filter = EmailFilter(limit=5)
            emails = await client.fetch_emails(email_filter)
            
            print(f"获取到 {len(emails)} 封邮件")
            
            # 查找有附件的邮件
            emails_with_attachments = [email for email in emails if email.attachments]
            
            if not emails_with_attachments:
                print("没有找到有附件的邮件")
                return
            
            print(f"找到 {len(emails_with_attachments)} 封有附件的邮件")
            
            # 测试第一封有附件的邮件
            test_email = emails_with_attachments[0]
            print(f"\n测试邮件 UID: {test_email.uid}")
            print(f"邮件主题: {test_email.subject}")
            print(f"附件数量: {len(test_email.attachments)}")
            
            # 第一次下载附件
            print("\n=== 第一次下载附件 ===")
            downloaded_attachments_1 = await attachment_manager.download_attachments(
                test_email.uid, test_email.attachments
            )
            
            for i, attachment in enumerate(downloaded_attachments_1):
                print(f"附件 {i+1}:")
                print(f"  文件名: {attachment.get('filename')}")
                print(f"  下载状态: {attachment.get('download_status')}")
                print(f"  本地路径: {attachment.get('local_path')}")
                if attachment.get('local_path'):
                    file_exists = Path(attachment['local_path']).exists()
                    print(f"  文件存在: {file_exists}")
            
            # 第二次下载相同附件（应该跳过已存在的文件）
            print("\n=== 第二次下载相同附件 ===")
            downloaded_attachments_2 = await attachment_manager.download_attachments(
                test_email.uid, test_email.attachments
            )
            
            for i, attachment in enumerate(downloaded_attachments_2):
                print(f"附件 {i+1}:")
                print(f"  文件名: {attachment.get('filename')}")
                print(f"  下载状态: {attachment.get('download_status')}")
                print(f"  本地路径: {attachment.get('local_path')}")
                if attachment.get('local_path'):
                    file_exists = Path(attachment['local_path']).exists()
                    print(f"  文件存在: {file_exists}")
            
            # 检查跳过的附件数量
            skipped_count = sum(1 for att in downloaded_attachments_2 
                              if att.get('download_status') == 'skipped_existing')
            success_count = sum(1 for att in downloaded_attachments_2 
                              if att.get('download_status') == 'success')
            
            print(f"\n=== 下载结果统计 ===")
            print(f"跳过已存在的附件: {skipped_count}")
            print(f"新下载的附件: {success_count}")
            
            # 测试搜索邮件时的附件处理
            print("\n=== 测试搜索邮件时的附件处理 ===")
            search_result = await client.search_emails(
                keywords="附件",
                search_type="all",
                page_size=3
            )
            
            print(f"搜索到 {len(search_result['emails'])} 封邮件")
            
            # 模拟MCP工具中的附件处理逻辑
            for email_dict in search_result['emails']:
                if email_dict.get('attachments'):
                    print(f"\n处理邮件 {email_dict['uid']} 的附件:")
                    try:
                        downloaded_attachments = await attachment_manager.download_attachments(
                            email_dict['uid'], email_dict['attachments']
                        )
                        
                        for attachment in downloaded_attachments:
                            print(f"  - {attachment.get('filename')}: {attachment.get('download_status')}")
                            
                    except Exception as e:
                        print(f"  附件下载失败: {e}")
            
            print("\n=== 测试完成 ===")
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_attachment_existence_check())
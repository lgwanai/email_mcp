#!/usr/bin/env python3
"""Test attachment filename decoding functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from email_client import EmailClient, EmailConfig
from attachment_manager import AttachmentManager

async def test_attachment_decoding():
    """
    测试附件文件名解码功能
    """
    try:
        print("=== Email MCP Server 附件文件名解码测试 ===")
        
        # 获取邮箱配置
        email_address = os.getenv('EMAIL_USERNAME')
        password = os.getenv('EMAIL_PASSWORD')
        
        if not email_address or not password:
            print("错误: 请设置 EMAIL_USERNAME 和 EMAIL_PASSWORD 环境变量")
            return
        
        # 创建邮件客户端配置
        config = EmailConfig(
            host="imap.qq.com",
            port=993,
            username=email_address,
            password=password,
            use_ssl=True
        )
        
        # 创建附件管理器
        attachment_manager = AttachmentManager()
        
        print(f"连接到邮箱: {email_address}")
        
        # 使用邮件客户端
        async with EmailClient(config) as client:
            print("\n=== 获取最近的邮件（查找有附件的邮件）===")
            
            # 获取最近20封邮件，查找有附件的
            from email_client import EmailFilter
            filter_params = EmailFilter(
                folder="INBOX",
                limit=20,
                reverse_order=True
            )
            emails = await client.fetch_emails(filter_params)
            
            emails_with_attachments = [email for email in emails if email.attachments]
            
            if not emails_with_attachments:
                print("未找到有附件的邮件")
                return
            
            print(f"找到 {len(emails_with_attachments)} 封有附件的邮件")
            
            # 测试第一封有附件的邮件
            test_email = emails_with_attachments[0]
            print(f"\n=== 测试邮件 UID: {test_email.uid} ===")
            print(f"发件人: {test_email.sender}")
            print(f"主题: {test_email.subject}")
            print(f"附件数量: {len(test_email.attachments)}")
            
            print("\n=== 附件信息 ===")
            for i, attachment in enumerate(test_email.attachments):
                print(f"\n附件 {i+1}:")
                print(f"  原始文件名: {attachment.get('original_filename', 'N/A')}")
                print(f"  解码文件名: {attachment.get('filename', 'N/A')}")
                print(f"  内容类型: {attachment.get('content_type', 'N/A')}")
                print(f"  大小: {attachment.get('size', 0)} 字节")
            
            # 下载附件
            print("\n=== 下载附件 ===")
            downloaded_attachments = await attachment_manager.download_attachments(
                test_email.uid, test_email.attachments
            )
            
            print(f"成功下载 {len([a for a in downloaded_attachments if a.get('download_status') == 'success'])} 个附件")
            
            # 显示下载结果
            for i, att in enumerate(downloaded_attachments):
                print(f"\n下载结果 {i+1}:")
                print(f"  解码文件名: {att.get('filename', 'N/A')}")
                print(f"  原始文件名: {att.get('original_filename', 'N/A')}")
                print(f"  安全文件名: {att.get('safe_filename', 'N/A')}")
                print(f"  本地路径: {att.get('local_path', 'N/A')}")
                print(f"  下载状态: {att.get('download_status', 'N/A')}")
                
                # 检查文件是否存在
                local_path = att.get('local_path')
                if local_path and Path(local_path).exists():
                    print(f"  ✓ 文件存在于: {local_path}")
                else:
                    print(f"  ✗ 文件不存在: {local_path}")
            
            # 测试附件读取
            print("\n=== 测试附件读取 ===")
            for att in downloaded_attachments:
                if att.get('download_status') == 'success':
                    filename = att.get('filename')
                    print(f"\n尝试读取附件: {filename}")
                    
                    # 使用解码后的文件名读取
                    content = await attachment_manager.read_attachment(test_email.uid, filename)
                    if content:
                        print(f"  ✓ 成功读取，大小: {len(content)} 字节")
                    else:
                        print(f"  ✗ 读取失败")
                        
                        # 尝试使用原始文件名读取
                        original_filename = att.get('original_filename')
                        if original_filename != filename:
                            print(f"  尝试使用原始文件名: {original_filename}")
                            content = await attachment_manager.read_attachment(test_email.uid, original_filename)
                            if content:
                                print(f"  ✓ 使用原始文件名成功读取，大小: {len(content)} 字节")
                            else:
                                print(f"  ✗ 使用原始文件名也读取失败")
            
            # 获取附件元数据
            print("\n=== 附件元数据 ===")
            metadata = await attachment_manager.get_attachment_info(test_email.uid)
            if metadata:
                print(f"邮件 UID: {metadata.get('email_uid')}")
                print(f"下载时间: {metadata.get('download_time')}")
                print(f"总附件数: {metadata.get('total_attachments')}")
                print(f"成功下载数: {metadata.get('successful_downloads')}")
            else:
                print("未找到附件元数据")
            
            print("\n=== 测试完成 ===")
            
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_attachment_decoding())
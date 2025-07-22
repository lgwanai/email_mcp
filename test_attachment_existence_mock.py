#!/usr/bin/env python3
"""Mock test for attachment existence check functionality."""

import asyncio
import os
import sys
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from attachment_manager import AttachmentManager

async def test_attachment_existence_check_mock():
    """
    模拟测试附件存在性检查功能
    """
    print("=== 模拟测试附件存在性检查功能 ===")
    
    # 创建临时目录用于测试
    temp_dir = tempfile.mkdtemp(prefix="email_attachments_test_")
    print(f"测试目录: {temp_dir}")
    
    try:
        # 创建附件管理器，使用临时目录
        attachment_manager = AttachmentManager(base_path=temp_dir)
        
        # 模拟附件数据
        mock_attachments = [
            {
                'filename': '测试文档.pdf',
                'content_type': 'application/pdf',
                'size': 1024,
                'content_id': None,
                'part': Mock()  # 模拟邮件部分
            },
            {
                'filename': 'image.jpg',
                'content_type': 'image/jpeg',
                'size': 2048,
                'content_id': None,
                'part': Mock()
            }
        ]
        
        # 为模拟的邮件部分添加get_payload方法
        mock_attachments[0]['part'].get_payload.return_value = b'PDF content for testing'
        mock_attachments[1]['part'].get_payload.return_value = b'JPEG content for testing'
        
        email_uid = "test_email_123"
        
        print(f"\n模拟邮件 UID: {email_uid}")
        print(f"附件数量: {len(mock_attachments)}")
        
        # 第一次下载附件
        print("\n=== 第一次下载附件 ===")
        downloaded_attachments_1 = await attachment_manager.download_attachments(
            email_uid, mock_attachments
        )
        
        for i, attachment in enumerate(downloaded_attachments_1):
            print(f"附件 {i+1}:")
            print(f"  原始文件名: {attachment.get('original_filename')}")
            print(f"  安全文件名: {attachment.get('filename')}")
            print(f"  下载状态: {attachment.get('download_status')}")
            print(f"  本地路径: {attachment.get('local_path')}")
            if attachment.get('local_path'):
                file_exists = Path(attachment['local_path']).exists()
                file_size = Path(attachment['local_path']).stat().st_size if file_exists else 0
                print(f"  文件存在: {file_exists}")
                print(f"  文件大小: {file_size} bytes")
        
        # 验证文件确实被创建
        created_files = list(Path(temp_dir).rglob("*"))
        print(f"\n创建的文件: {len([f for f in created_files if f.is_file()])} 个")
        for file_path in created_files:
            if file_path.is_file():
                print(f"  - {file_path.name} ({file_path.stat().st_size} bytes)")
        
        # 第二次下载相同附件（应该跳过已存在的文件）
        print("\n=== 第二次下载相同附件（应该跳过） ===")
        downloaded_attachments_2 = await attachment_manager.download_attachments(
            email_uid, mock_attachments
        )
        
        for i, attachment in enumerate(downloaded_attachments_2):
            print(f"附件 {i+1}:")
            print(f"  原始文件名: {attachment.get('original_filename')}")
            print(f"  安全文件名: {attachment.get('filename')}")
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
        
        print(f"\n=== 第二次下载结果统计 ===")
        print(f"跳过已存在的附件: {skipped_count}")
        print(f"新下载的附件: {success_count}")
        
        # 测试内容不同的情况
        print("\n=== 测试内容不同的附件 ===")
        # 修改附件内容
        mock_attachments[0]['part'].get_payload.return_value = b'Modified PDF content for testing'
        
        downloaded_attachments_3 = await attachment_manager.download_attachments(
            email_uid, mock_attachments
        )
        
        for i, attachment in enumerate(downloaded_attachments_3):
            print(f"附件 {i+1}:")
            print(f"  原始文件名: {attachment.get('original_filename')}")
            print(f"  安全文件名: {attachment.get('filename')}")
            print(f"  下载状态: {attachment.get('download_status')}")
            print(f"  本地路径: {attachment.get('local_path')}")
        
        # 最终文件统计
        final_files = list(Path(temp_dir).rglob("*"))
        print(f"\n=== 最终文件统计 ===")
        print(f"总文件数: {len([f for f in final_files if f.is_file()])}")
        for file_path in final_files:
            if file_path.is_file():
                print(f"  - {file_path.name} ({file_path.stat().st_size} bytes)")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir)
            print(f"\n清理临时目录: {temp_dir}")
        except Exception as e:
            print(f"清理临时目录失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_attachment_existence_check_mock())
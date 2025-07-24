#!/usr/bin/env python3
"""Email MCP Server 真实账户演示脚本

这个脚本展示如何使用配置的真实邮箱账户来测试 Email MCP Server 的功能。
使用前请确保已经按照 SETUP_GUIDE.md 配置了邮箱账户。
"""

import asyncio
import json
from datetime import datetime, timedelta
from fastmcp import Client
from fastmcp.client.transports import SSETransport


class EmailMCPDemo:
    def __init__(self, server_url="http://127.0.0.1:8000/sse/"):
        self.server_url = server_url
        self.client = None
        
    def get_client(self):
        """获取MCP客户端"""
        transport = SSETransport(self.server_url)
        return Client(transport)
    
    async def list_available_tools(self, client):
        """列出可用的工具"""
        try:
            tools = await client.list_tools()
            print("\n=== 可用的 MCP 工具 ===")
            for i, tool in enumerate(tools, 1):
                print(f"{i}. {tool.name} - {tool.description}")
            return tools
        except Exception as e:
            print(f"❌ 获取工具列表失败: {e}")
            return []
    
    async def demo_fetch_emails(self, client, email_address, limit=50, specific_date=None):
        """演示获取邮件功能"""
        if specific_date:
            # 获取特定日期的邮件
            target_date = datetime.strptime(specific_date, '%Y-%m-%d')
            start_date = target_date
            end_date = target_date  # 只获取当天的邮件
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            print(f"\n=== 演示: 获取 {specific_date} 的邮件 ({email_address}) ===")
        else:
            # 计算最近7天的日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            print(f"\n=== 演示: 获取最近7天邮件 ({email_address}) ===")
        
        print(f"日期范围: {start_date_str} 到 {end_date_str}")
        try:
            result = await client.call_tool("fetch_emails", {
                "email_address": email_address,
                "folder": "INBOX",
                "limit": limit,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "reverse_order": True  # 最新邮件优先
            })
            
            # FastMCP CallToolResult 对象处理
            if hasattr(result, 'content') and result.content:
                content = result.content[0].text if result.content else '{}'
                try:
                    data = json.loads(content)
                    if data.get("status") == "success":
                        # fetch_emails直接返回emails数组，不是包装在data字段中
                        emails = data.get("emails", [])
                        if specific_date:
                            print(f"✅ 成功获取 {specific_date} 的 {len(emails)} 封邮件")
                        else:
                            print(f"✅ 成功获取最近7天 {len(emails)} 封邮件")
                        
                        # 显示所有邮件的详细信息
                        for i, email in enumerate(emails, 1):
                            print(f"\n邮件 {i}:")
                            print(f"  发件人: {email.get('sender', 'N/A')}")
                            print(f"  主题: {email.get('subject', 'N/A')}")
                            print(f"  日期: {email.get('date', 'N/A')}")
                            print(f"  附件数量: {len(email.get('attachments', []))}")
                            
                            # 如果有附件，显示附件信息
                            if email.get('attachments'):
                                print("  附件:")
                                for att in email['attachments']:  # 显示所有附件
                                    status = att.get('download_status', 'success')
                                    if status == 'failed':
                                        print(f"    - {att.get('filename', 'N/A')} ({att.get('size', 0)} bytes) [下载失败: {att.get('error', 'Unknown error')}]")
                                    else:
                                        print(f"    - {att.get('filename', 'N/A')} ({att.get('size', 0)} bytes)")
                    else:
                        print(f"❌ 获取邮件失败: {data.get('error_message', 'Unknown error')}")
                except json.JSONDecodeError:
                    print(f"❌ 响应格式错误: {content}")
            else:
                print(f"❌ 获取邮件失败: 无响应内容")
                
        except Exception as e:
            print(f"❌ 获取邮件异常: {e}")
    
    async def demo_search_emails(self, client, keywords="test"):
        """演示搜索邮件功能"""
        print(f"\n=== 演示: 搜索邮件 (关键词: '{keywords}') ===")
        try:
            result = await client.call_tool("search_emails", {
                "keywords": keywords,
                "search_type": "all",
                "page_size": 3
            })
            
            # FastMCP CallToolResult 对象处理
            if hasattr(result, 'content') and result.content:
                content = result.content[0].text if result.content else '{}'
                try:
                    data = json.loads(content)
                    if data.get("status") == "success":
                        search_data = data.get("data", {})
                        emails = search_data.get("emails", [])
                        total_found = search_data.get("total_found", 0)
                        
                        print(f"✅ 搜索完成，找到 {total_found} 封相关邮件")
                        
                        for i, email in enumerate(emails, 1):
                            print(f"\n搜索结果 {i}:")
                            print(f"  发件人: {email.get('sender', 'N/A')}")
                            print(f"  主题: {email.get('subject', 'N/A')}")
                            print(f"  日期: {email.get('date', 'N/A')}")
                    else:
                        print(f"❌ 搜索邮件失败: {data.get('error_message', 'Unknown error')}")
                except json.JSONDecodeError:
                    print(f"❌ 响应格式错误: {content}")
            else:
                print(f"❌ 搜索邮件失败: 无响应内容")
                
        except Exception as e:
            print(f"❌ 搜索邮件异常: {e}")
    
    async def demo_send_email(self, client, from_address, to_address):
        """演示发送邮件功能"""
        print(f"\n=== 演示: 发送邮件 ({from_address} -> {to_address}) ===")
        try:
            result = await client.call_tool("send_email", {
                "from_address": from_address,
                "to_addresses": to_address,
                "subject": "Email MCP Server 测试邮件",
                "body": "这是一封来自 Email MCP Server 的测试邮件。\n\n发送时间: " + 
                        str(asyncio.get_event_loop().time()),
                "is_html": False
            })
            
            # FastMCP CallToolResult 对象处理
            if hasattr(result, 'content') and result.content:
                content = result.content[0].text if result.content else '{}'
                try:
                    data = json.loads(content)
                    if data.get("status") == "success":
                        print("✅ 邮件发送成功!")
                        send_data = data.get("data", {})
                        print(f"  发送时间: {send_data.get('sent_at', 'N/A')}")
                        print(f"  SMTP服务器: {send_data.get('smtp_server', 'N/A')}")
                    else:
                        print(f"❌ 邮件发送失败: {data.get('error_message', 'Unknown error')}")
                except json.JSONDecodeError:
                    print(f"❌ 响应格式错误: {content}")
            else:
                print(f"❌ 邮件发送失败: 无响应内容")
                
        except Exception as e:
            print(f"❌ 发送邮件异常: {e}")
    
    async def demo_storage_stats(self, client):
        """演示存储统计功能"""
        print("\n=== 演示: 存储统计 ===")
        try:
            result = await client.call_tool("get_storage_stats", {})
            
            # FastMCP CallToolResult 对象处理
            if hasattr(result, 'content') and result.content:
                content = result.content[0].text if result.content else '{}'
                try:
                    data = json.loads(content)
                    if data.get("status") == "success":
                        stats = data.get("data", {})
                        print("✅ 存储统计:")
                        print(f"  总大小: {stats.get('total_size_mb', 0):.2f} MB")
                        print(f"  总文件数: {stats.get('total_files', 0)}")
                        print(f"  邮箱目录数: {stats.get('email_directories', 0)}")
                        print(f"  存储路径: {stats.get('base_path', 'N/A')}")
                    else:
                        print(f"❌ 获取存储统计失败: {data.get('error_message', 'Unknown error')}")
                except json.JSONDecodeError:
                    print(f"❌ 响应格式错误: {content}")
            else:
                print(f"❌ 获取存储统计失败: 无响应内容")
                
        except Exception as e:
            print(f"❌ 获取存储统计异常: {e}")


def load_default_email():
    """从配置文件加载默认邮箱地址"""
    try:
        with open('email_accounts.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            default_account = config.get('default_account')
            if default_account and default_account in config.get('accounts', {}):
                return default_account
            else:
                # 如果没有指定默认账户，使用第一个启用的账户
                accounts = config.get('accounts', {})
                for email, account_config in accounts.items():
                    if account_config.get('enabled', True):
                        return email
        return None
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None

async def main():
    """主演示函数"""
    print("🚀 Email MCP Server 功能演示")
    print("=" * 50)
    
    # 提示用户配置邮箱
    print("\n📧 请确保已按照 SETUP_GUIDE.md 配置了邮箱账户")
    print("配置文件: email_accounts.json")
    
    # 从配置文件加载默认邮箱
    default_email = load_default_email()
    if default_email:
        email_address = default_email
        print(f"\n✅ 使用配置文件中的默认邮箱: {email_address}")
    else:
        print("\n⚠️  未找到配置文件或默认邮箱配置")
        email_address = input("请输入要测试的邮箱地址: ").strip()
        if not email_address:
            email_address = "test@example.com"  # 最后的备用地址
    
    demo = EmailMCPDemo()
    
    try:
        # 使用 async with 管理客户端连接
        async with demo.get_client() as client:
            print(f"✅ 已连接到服务器: {demo.server_url}")
            
            # 列出可用工具
            await demo.list_available_tools(client)
            
            # 演示存储统计（不需要真实邮箱配置）
            await demo.demo_storage_stats(client)
            
            # 如果用户提供了真实邮箱地址，演示更多功能
            if email_address != "test@example.com":
                print(f"\n🔍 使用邮箱地址: {email_address}")
                
                # 演示获取7月21日邮件
                await demo.demo_fetch_emails(client, email_address, limit=50, specific_date="2025-07-21")
                
                # 暂时屏蔽其他测试用例，只测试fetch_emails
                print("\n📝 注意: 其他测试用例已暂时屏蔽，只测试fetch_emails功能")
                
                # # 演示搜索邮件
                # search_keywords = input("\n请输入搜索关键词 (或按回车使用 'test'): ").strip()
                # if not search_keywords:
                #     search_keywords = "test"
                # await demo.demo_search_emails(client, search_keywords)
                # 
                # # 询问是否发送测试邮件
                # send_test = input("\n是否发送测试邮件? (y/N): ").strip().lower()
                # if send_test == 'y':
                #     to_address = input("请输入收件人邮箱地址: ").strip()
                #     if to_address:
                #         await demo.demo_send_email(client, email_address, to_address)
                #     else:
                #         print("❌ 未提供收件人地址，跳过发送邮件演示")
            else:
                print("\n⚠️  使用默认测试地址，某些功能可能无法正常工作")
                print("   请配置真实邮箱账户以体验完整功能")
            
            print("\n🎉 演示完成!")
            print("✅ 已断开连接")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")


if __name__ == "__main__":
    print("Email MCP Server 演示脚本")
    print("使用前请确保:")
    print("1. MCP 服务器正在运行 (python src/email_mcp.py)")
    print("2. 已配置邮箱账户 (参考 SETUP_GUIDE.md)")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 演示已取消")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
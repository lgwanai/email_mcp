#!/usr/bin/env python3
"""
Proper MCP Client for Email MCP Server Testing

This script demonstrates how to properly test an MCP server
running with FastMCP SSE transport.
"""

import asyncio
import json
import logging
import aiohttp
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailMCPTester:
    """Test client for Email MCP Server via SSE/HTTP"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_server_health(self) -> bool:
        """Test if the MCP server is running and accessible."""
        try:
            async with self.session.get(f"{self.base_url}/") as response:
                if response.status in [200, 404]:  # 404 is OK, means server is running
                    logger.info(f"✅ MCP Server is running at {self.base_url}")
                    return True
                else:
                    logger.error(f"❌ Server responded with status {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to server: {e}")
            return False
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool via HTTP POST to SSE endpoint."""
        try:
            # Prepare the MCP request
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Send request to SSE endpoint
            async with self.session.post(
                f"{self.base_url}/sse/",
                json=mcp_request,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Tool call failed with status {response.status}: {error_text}")
                    return {"error": f"HTTP {response.status}: {error_text}"}
                    
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            return {"error": str(e)}
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools."""
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            async with self.session.post(
                f"{self.base_url}/sse/",
                json=mcp_request,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"List tools failed with status {response.status}: {error_text}")
                    return {"error": f"HTTP {response.status}: {error_text}"}
                    
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return {"error": str(e)}
    
    async def run_all_tests(self):
        """Run all MCP server tests"""
        logger.info("Starting comprehensive MCP server tests...")
        
        # Test 1: Check server health
        if not await self.test_server_health():
            logger.error("Server health check failed. Aborting tests.")
            return
        
        # Test 2: List available tools
        await self.test_list_tools()
        
        # Test 3: Test each tool
        await self.test_fetch_emails()
        await self.test_search_emails()
        await self.test_get_storage_stats()
        await self.test_send_email()
        await self.test_list_attachments()
        await self.test_cleanup_old_attachments()
        
        logger.info("All tests completed!")
    
    async def test_list_tools(self):
        """Test listing available tools"""
        try:
            logger.info("Testing: List available tools")
            result = await self.list_tools()
            
            if "error" in result:
                logger.error(f"Failed to list tools: {result['error']}")
            elif "result" in result and "tools" in result["result"]:
                tools = result["result"]["tools"]
                logger.info(f"Available tools: {len(tools)}")
                for tool in tools:
                    logger.info(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
            else:
                logger.info(f"List tools result: {result}")
                
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
    
    async def test_fetch_emails(self):
        """Test fetching emails"""
        try:
            logger.info("Testing: Fetch emails")
            
            result = await self.call_mcp_tool(
                "fetch_emails",
                {
                    "account_email": "986007792@qq.com",
                    "folder": "INBOX",
                    "limit": 5,
                    "download_attachments": False
                }
            )
            
            if "error" in result:
                logger.error(f"Fetch emails failed: {result['error']}")
            else:
                logger.info(f"✅ Fetch emails successful: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
            
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
    
    async def test_search_emails(self):
        """Test searching emails"""
        try:
            logger.info("Testing: Search emails")
            
            result = await self.call_mcp_tool(
                "search_emails",
                {
                    "account_email": "986007792@qq.com",
                    "query": "test",
                    "search_type": "subject",
                    "limit": 3
                }
            )
            
            if "error" in result:
                logger.error(f"Search emails failed: {result['error']}")
            else:
                logger.info(f"✅ Search emails successful: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
            
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
    
    async def test_get_storage_stats(self):
        """Test getting storage statistics"""
        try:
            logger.info("Testing: Get storage stats")
            
            result = await self.call_mcp_tool(
                "get_storage_stats",
                {}
            )
            
            if "error" in result:
                logger.error(f"Get storage stats failed: {result['error']}")
            else:
                logger.info(f"✅ Get storage stats successful: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
    
    async def test_send_email(self):
        """Test sending email"""
        try:
            logger.info("Testing: Send email")
            
            result = await self.call_mcp_tool(
                "send_email",
                {
                    "from_address": "986007792@qq.com",
                    "to_addresses": ["986007792@qq.com"],
                    "subject": "MCP Test Email",
                    "body": "This is a test email sent from MCP client.",
                    "is_html": False
                }
            )
            
            if "error" in result:
                logger.error(f"Send email failed: {result['error']}")
            else:
                logger.info(f"✅ Send email successful: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    async def test_list_attachments(self):
        """Test listing attachments"""
        try:
            logger.info("Testing: List attachments")
            
            # Try to list attachments (this might fail if no emails with attachments)
            result = await self.call_mcp_tool(
                "list_attachments",
                {
                    "account_email": "986007792@qq.com",
                    "message_id": "dummy_message_id"  # This will likely fail, but tests the tool
                }
            )
            
            if "error" in result:
                logger.warning(f"List attachments failed (expected): {result['error']}")
            else:
                logger.info(f"✅ List attachments successful: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
        except Exception as e:
            logger.error(f"Failed to list attachments: {e}")
    
    async def test_cleanup_old_attachments(self):
        """Test cleaning up old attachments"""
        try:
            logger.info("Testing: Cleanup old attachments")
            
            result = await self.call_mcp_tool(
                "cleanup_old_attachments",
                {
                    "days_old": 30
                }
            )
            
            if "error" in result:
                logger.error(f"Cleanup old attachments failed: {result['error']}")
            else:
                logger.info(f"✅ Cleanup old attachments successful: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old attachments: {e}")

async def main():
    """Main function to run the MCP client tests"""
    logger.info("Starting Email MCP Server Test Client")
    
    # Create tester instance and run tests
    async with EmailMCPTester() as tester:
        await tester.run_all_tests()
    
    logger.info("Test client finished!")

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""Main entry point for Email MCP Server."""

import argparse
import os
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.email_mcp import EmailMCPServer
from src.utils import setup_logging


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Email MCP Server - Fetch emails and manage attachments via MCP protocol"
    )
    
    parser.add_argument(
        "-t", "--transport",
        choices=["sse", "stdio"],
        default="sse",
        help="Transport type (default: sse)"
    )
    
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to for SSE transport (default: localhost)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to for SSE transport (default: 8000)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--attachments-dir",
        default="attachments",
        help="Directory to store attachments (default: attachments)"
    )
    
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Create attachments directory
    os.makedirs(args.attachments_dir, exist_ok=True)
    
    # Create and configure server
    server = EmailMCPServer("Email MCP Server")
    
    try:
        if args.transport == "sse":
            print(f"Starting Email MCP Server on {args.host}:{args.port} with SSE transport")
            print(f"Attachments will be stored in: {os.path.abspath(args.attachments_dir)}")
            print(f"Server URL: http://{args.host}:{args.port}/sse")
            print("Press Ctrl+C to stop the server")
            server.run_sse(args.host, args.port)
        else:
            print("Starting Email MCP Server with stdio transport")
            print(f"Attachments will be stored in: {os.path.abspath(args.attachments_dir)}")
            print("Server is ready for stdio communication")
            server.run_stdio()
            
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
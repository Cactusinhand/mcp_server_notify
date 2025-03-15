"""
MCP Notification Server Package

Exports the main server class and version information.
"""

import argparse
from .server import NotificationServer
from .sound import SoundPlayer
from .schemas import NotificationRequest, NotificationType
import asyncio
# 初始化日志配置（可选）
import logging

# Version should match pyproject.toml
__version__ = "0.1.0"

# 显式导出公共接口
__all__ = [
    "NotificationServer",
    "SoundPlayer",
    "NotificationRequest",
    "NotificationType",
    "__version__",
    "main",
]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
logger.info(f"Loaded mcp-server-notify version {__version__}")


def main():
    parser = argparse.ArgumentParser(description='MCP Notification Server')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    server = NotificationServer()
    if args.debug:
        print("Debug mode is enabled")
    asyncio.run(server.serve())

if __name__ == "__main__":
    main()


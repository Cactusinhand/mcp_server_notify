"""
MCP Notification Server Package

Exports the main server class and version information.
"""

import argparse
from .server import NotificationServer
from .sound import SoundPlayer
from .schemas import NotificationRequest
import asyncio
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
    # filename='path/to/your/logfile.log',
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
        logger.setLevel(logging.DEBUG)
        logger.info("Debug mode is enabled")

    # 确保服务器持续运行
    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise

if __name__ == "__main__":
    main()

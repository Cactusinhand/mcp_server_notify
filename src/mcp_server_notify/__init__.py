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

    asyncio.run(server.serve())

if __name__ == "__main__":
    main()

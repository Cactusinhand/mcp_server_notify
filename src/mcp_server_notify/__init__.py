"""
MCP Notification Server Package

Exports the main server class and version information.
"""

import argparse
import logging.config
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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
logger.info(f"Loaded mcp-server-notify version {__version__}")


def main():
    """
    MCP Notification Server
    Args:
        --debug: Enable debug mode
        --log-file: Specify log file path (works with --debug)
    Examples:
        python -m mcp_server_notify --debug
        python -m mcp_server_notify --debug --log-file=logfile.log
    """
    parser = argparse.ArgumentParser(description='MCP Notification Server')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--log-file', type=str, help='Specify log file path (works with --debug)')
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.debug else logging.INFO

    if args.debug and args.log_file:
        # 创建文件处理器
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        # 添加到根日志记录器
        logging.getLogger().addHandler(file_handler)
        logger.setLevel(log_level)
        logger.info(f"Debug mode enabled, logging to file: {args.log_file}")
    elif args.debug:
        logger.setLevel(log_level)
        logger.info("Debug mode is enabled")

    # 确保服务器持续运行
    server = NotificationServer()
    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise

if __name__ == "__main__":
    main()

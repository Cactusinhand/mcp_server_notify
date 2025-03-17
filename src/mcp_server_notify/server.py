from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from plyer import notification
from apprise import Apprise
from .schemas import NotificationRequest
from .sound import SoundPlayer
from pydantic import ValidationError
import os
import logging
import platform

logger = logging.getLogger(__name__)


class NotificationServer:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.sound_player = SoundPlayer()
        self.server = Server("mcp-notification")
        self.apprise = Apprise()
        self._setup_apprise_targets()

    def _get_linux_desktop_env(self):
        """检测当前 Linux 桌面环境"""
        desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "")
        if not desktop_env:
            desktop_env = os.environ.get("DESKTOP_SESSION", "")

        desktop_env = desktop_env.lower()
        logger.debug(f"检测到桌面环境: {desktop_env}")
        return desktop_env

    def _setup_apprise_targets(self):
        """设置多种 Apprise 通知目标，确保至少有一种可用"""
        system = platform.system().lower()
        logger.info(f"设置 Apprise 通知，系统：{system}")

        targets = []

        # 根据系统添加特定通知目标
        if system == "windows":
            targets.append("windows://")
        elif system == "darwin":  # macOS
            targets.append("macos://")
        elif system == "linux":
            desktop_env = self._get_linux_desktop_env()
            # 通用 D-Bus 作为首选
            targets.append("dbus://")
            # 桌面环境专属通知
            if desktop_env == "kde":
                targets.append("kde://")  # KDE Plasma 原生支持
            elif desktop_env == "gnome":
                targets.append("gnome://")  # GNOME 原生支持
            else:
                # 兼容 Qt/GLib 应用
                targets.extend(["qt://", "glib://"])

        # 添加所有目标，忽略错误
        success_count = 0
        for target in targets:
            try:
                result = self.apprise.add(target)
                if result:
                    success_count += 1
                    logger.info(f"成功添加通知目标: {target}")
                else:
                    logger.warning(f"无法添加通知目标: {target}")
            except Exception as e:
                logger.error(f"添加通知目标 {target} 时出错: {str(e)}")

        if success_count == 0:
            logger.warning("没有可用的 Apprise 通知目标，将回退到 plyer 或日志输出")

    async def serve(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools"""
            logger.debug("Listing tools.....")
            return [
                Tool(
                    name="send_notification",
                    description="Send system notification with optional sound",
                    inputSchema=NotificationRequest.model_json_schema(),
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Call a tool

            name: str - Tool name

            arguments: dict - Tool arguments
            """
            logger.info(f"Calling tool: {name} with arguments: {arguments}")
            if name != "send_notification":
                return [TextContent(type="text", text="Invalid tool name")]
            try:
                logger.debug("Validating request...")
                req = NotificationRequest(**arguments)
                logger.debug("Sending notification...")
                self._send_notification(req)
                logger.info("Notification sent successfully")
                return [TextContent(type="text", text="Notification sent successfully")]
            except ValidationError as e:
                logger.error(f"Validation error: {str(e)}")
                return [TextContent(type="text", text=f"Invalid request: {str(e)}")]
            except Exception as e:
                logger.error(f"Error: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        options = self.server.create_initialization_options()
        logger.info("Starting server...")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, options)

    def _send_notification(self, request: NotificationRequest):
        logger.debug("request: %s", request)
        notification_sent = False

        # 尝试使用 Apprise 发送
        if self.apprise and len(self.apprise) > 0:
            try:
                logger.debug("尝试使用 Apprise 发送通知...")
                result = self.apprise.notify(title=request.title, body=request.message)
                if result:
                    logger.info("Apprise 通知发送成功")
                    notification_sent = True
                else:
                    logger.warning("Apprise 通知发送失败")
            except Exception as e:
                logger.error(f"Apprise 通知异常: {str(e)}")

        # 如果 Apprise 失败，尝试 plyer
        if not notification_sent:
            try:
                logger.debug("尝试使用 plyer 发送通知...")
                notification.notify(
                    title=request.title,
                    message=request.message,
                    timeout=request.timeout,
                    app_name="mcp-notification",
                )
                logger.info("plyer 通知发送成功")
                notification_sent = True
            except Exception as e:
                logger.error(f"plyer 通知失败: {str(e)}")

        # 如果两种方法都失败或在容器环境中，使用日志输出
        if not notification_sent or os.path.exists("/.dockerenv"):
            logger.info(f"通知：{request.title} - {request.message}")
            print(f"Notification: {request.title} - {request.message}")

        # 播放声音
        if request.play_sound:
            logger.debug("播放通知声音...")
            self.sound_player.play()

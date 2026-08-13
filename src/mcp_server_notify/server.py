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
from importlib import resources

logger = logging.getLogger(__name__)


class NotificationServer:
    APP_ID = "com.qxzap.mcp_server_notify"
    APP_DISPLAY_NAME = "MCP Notify"
    DEFAULT_AGENT_ENV = "MCP_NOTIFY_DEFAULT_AGENT"

    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.sound_player = SoundPlayer()
        self.server = Server("mcp-notification")
        self.apprise = Apprise()
        # Register stable AUMID so Windows toast shows our name + icon instead of "Python"
        if platform.system().lower() == "windows":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.APP_ID)
            except Exception as e:
                logger.debug(f"Could not set AppUserModelID: {e}")
        self._setup_apprise_targets()

    @staticmethod
    def _resolve_asset(name: str) -> str | None:
        """Resolve a bundled asset path. Returns absolute path or None if missing."""
        try:
            asset_root = resources.files("mcp_server_notify").joinpath("assets")
            candidate = asset_root.joinpath(name)
            # importlib.resources >= 3.9 returns a Traversable; convert to real path
            with resources.as_file(candidate) as p:
                return str(p) if p.exists() else None
        except Exception:
            return None

    def _default_agent(self) -> str | None:
        val = os.environ.get(self.DEFAULT_AGENT_ENV, "").strip()
        return val or None

    def _resolve_title(self, request: NotificationRequest) -> str:
        agent = request.agent or self._default_agent()
        if agent:
            return f"[{agent}] {request.title}"
        return request.title

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

        title = self._resolve_title(request)
        icon_png = self._resolve_asset("icon.png")
        icon_ico = self._resolve_asset("icon.ico")

        # Apprise path — note: Apprise.notify() does not accept an image kwarg.
        # Custom icons are delivered by configuring AppriseAsset(image_path_mask=...)
        # at construction (see __init__). On Windows the AUMID + bundle ICO take effect;
        # on other platforms Apprise's default theme icon is used.
        if self.apprise and len(self.apprise) > 0:
            try:
                logger.debug("尝试使用 Apprise 发送通知...")
                result = self.apprise.notify(title=title, body=request.message)
                if result:
                    logger.info("Apprise 通知发送成功")
                    notification_sent = True
                else:
                    logger.warning("Apprise 通知发送失败")
            except Exception as e:
                logger.error(f"Apprise 通知异常: {str(e)}")

        # plyer fallback
        if not notification_sent:
            try:
                logger.debug("尝试使用 plyer 发送通知...")
                plyer_kwargs = {
                    "title": title,
                    "message": request.message,
                    "timeout": request.timeout,
                    "app_name": self.APP_DISPLAY_NAME,
                }
                if icon_ico:
                    plyer_kwargs["app_icon"] = icon_ico
                elif icon_png:
                    plyer_kwargs["app_icon"] = icon_png
                notification.notify(**plyer_kwargs)
                logger.info("plyer 通知发送成功")
                notification_sent = True
            except Exception as e:
                logger.error(f"plyer 通知失败: {str(e)}")

        # Last-resort log fallback (containers etc.)
        if not notification_sent or os.path.exists("/.dockerenv"):
            logger.info(f"通知：{title} - {request.message}")
            print(f"Notification: {title} - {request.message}")

        if request.play_sound:
            logger.debug("播放通知声音...")
            self.sound_player.play()

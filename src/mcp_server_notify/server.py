from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from plyer import notification
from .schemas import NotificationRequest
from .sound import SoundPlayer
from pydantic import ValidationError
import os
import logging

logger = logging.getLogger(__name__)

class NotificationServer:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.sound_player = SoundPlayer()
        self.server = Server("mcp-notification")
        
    async def serve(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools"""
            logger.debug("Listing tools.....")
            return [Tool(
                name="send_notification",
                description="Send system notification with optional sound",
                inputSchema=NotificationRequest.model_json_schema()
            )]

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
        # Plyer通知
        logger.debug("request: %s", request)
        try:
            # 显式指定通知图标（可选）
            notification.notify(
                title=request.title,
                message=request.message,
                timeout=request.timeout,
                app_name="mcp-notification"
            )
        except Exception as e:
            logger.error(f"Notification failed: {str(e)}")
            # 容器环境下降级处理
            if os.path.exists('/.dockerenv'):
                logger.debug("Docker environment detected, falling back to log output")
                print(f"Notification (Docker): {request.title} - {request.message}")
            else:
                raise
        
        # 播放声音
        if request.play_sound:
            logger.debug("Playing sound...")
            self.sound_player.play()

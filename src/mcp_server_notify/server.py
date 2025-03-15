from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from plyer import notification
from .schemas import NotificationRequest
from .sound import SoundPlayer
from pydantic import ValidationError
# 添加日志记录
import logging
logger = logging.getLogger(__name__)

class NotificationServer:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.sound_player = SoundPlayer()
        self.server = Server("mcp-notification")
        
    async def serve(self):
        @self.server.list_tools()
        async def list_tools():
            """List available tools"""
            return [Tool(
                name="send_notification",
                description="Send system notification with optional sound",
                inputSchema=NotificationRequest.model_json_schema()
            )]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            """Call a tool
            
            name: str - Tool name

            arguments: dict - Tool arguments
            """
            if name != "send_notification":
                return [TextContent(text="Invalid tool name")]
            try:
                req = NotificationRequest(**arguments)
                self._send_notification(req)
                return [TextContent(text="Notification sent successfully")]
            except ValidationError as e:
                logger.error(f"Validation error: {str(e)}")
                return [TextContent(text=f"Invalid request: {str(e)}")]
            except Exception as e:
                return [TextContent(text=f"Error: {str(e)}")]

        options = self.server.create_initialization_options()
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, options)

    def _send_notification(self, request: NotificationRequest):
        # Plyer通知
        notification.notify(
            title=request.title,
            message=request.message,
            timeout=request.timeout
        )
        
        # 播放声音
        if request.play_sound:
            self.sound_player.play()
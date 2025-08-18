import pytest
from mcp_server_notify import NotificationServer
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_notification_flow():
    server = NotificationServer()
    
    # 使用 AsyncMock 模拟异步调用
    mock_call_tool = AsyncMock(return_value=[{"text": "success"}])
    
    with patch.object(server.server, "call_tool", mock_call_tool):
        response = await server.server.call_tool(
            name="send_notification",
            arguments={
                "title": "Test",
                "message": "Test Message",
                "play_sound": True
            }
        )
        assert "success" in response[0]["text"]
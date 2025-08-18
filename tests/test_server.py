import asyncio
import time
from unittest.mock import AsyncMock

import pytest
from mcp_server_notify import NotificationServer, NotificationRequest


def test_send_notification_non_blocking(monkeypatch):
    server = NotificationServer()

    class FakeApprise:
        def __len__(self):
            return 1
        def notify(self, *args, **kwargs):
            time.sleep(0.05)
            return True
    server.apprise = FakeApprise()

    def blocking_play():
        time.sleep(0.05)
    server.sound_player.play = blocking_play

    ran = False
    async def background():
        nonlocal ran
        await asyncio.sleep(0)
        ran = True
    async def run_test():
        bg = asyncio.create_task(background())
        req = NotificationRequest(title="T", message="M", play_sound=True)
        await server._send_notification(req)
        assert ran
        await bg

    asyncio.run(run_test())


def test_send_notification_uses_to_thread(monkeypatch):
    server = NotificationServer()

    async_to_thread = AsyncMock()
    monkeypatch.setattr(asyncio, "to_thread", async_to_thread)

    async def run_test():
        server.apprise = None  # force plyer path
        req = NotificationRequest(title="T", message="M", play_sound=True)
        await server._send_notification(req)

        called_funcs = [c.args[0] for c in async_to_thread.call_args_list]
        assert server.sound_player.play in called_funcs
        assert any(getattr(f, "__name__", "") == "notify" for f in called_funcs)

    asyncio.run(run_test())

from pydantic import BaseModel
from typing import Optional

class NotificationRequest(BaseModel):
    """Request schema for sending a system notification.

    title: str - Notification title
    message: str - Notification message
    play_sound: bool - Whether to play a sound
    timeout: int - Notification timeout in seconds
    agent: Optional[str] - Optional agent name; when set, the title is prefixed
        with "[agent] " so the user can identify which agent triggered it.
    voice: bool - Whether to also speak the notification through the local
        TTS backend (Windows SAPI / macOS say / Linux espeak). Defaults to
        True. Can be overridden globally by setting MCP_NOTIFY_VOICE=false.
    speak: Optional[str] - Agent-supplied spoken line. When set, this wins
        over the server's auto-composed line. The agent should craft this
        so it sounds like a colleague, not a status page. Server still
        applies the readability filter as a defensive measure if the agent
        forgot.
    """
    title: str
    message: str
    play_sound: bool = True
    timeout: int = 60  # seconds
    agent: Optional[str] = None
    voice: bool = True
    speak: Optional[str] = None

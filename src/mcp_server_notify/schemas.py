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
    """
    title: str
    message: str
    play_sound: bool = True
    timeout: int = 60  # seconds
    agent: Optional[str] = None

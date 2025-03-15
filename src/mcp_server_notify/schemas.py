from enum import Enum
from pydantic import BaseModel

class NotificationType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class NotificationRequest(BaseModel):
    """Request schema for sending a system notification
    
    title: str - Notification title

    message: str - Notification message

    play_sound: bool - Whether to play a sound

    timeout: int - Notification timeout in seconds
    """
    title: str
    message: str
    # notification_type: NotificationType = NotificationType.INFO
    play_sound: bool = True
    timeout: int = 60  # seconds
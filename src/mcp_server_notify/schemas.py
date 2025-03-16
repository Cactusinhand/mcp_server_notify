from pydantic import BaseModel

class NotificationRequest(BaseModel):
    """Request schema for sending a system notification
    
    title: str - Notification title

    message: str - Notification message

    play_sound: bool - Whether to play a sound

    timeout: int - Notification timeout in seconds
    """
    title: str
    message: str
    play_sound: bool = True
    timeout: int = 60  # seconds
import base64
import platform
import tempfile
import os
import time
import io
import logging

logger = logging.getLogger(__name__)

class SoundPlayer:
    # 这是一个简短的WAV格式"叮"声音的base64编码
    _DEFAULT_SOUND = """
    UklGRnQFAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YVAFAACAjYyLhoWHioyQlZyp
    tcDJ0dbd5+rs7erm3tfRyMG5sKeekIeBfHNrW0g6KRoQBvLj1se1pJR/Z043GAT27OfgzLSLYkMl
    BuzPsotqUSIMx6V+VTYVAdy0ilcxEwLZsoRNKxAJ78ulcD4hFR7+4L+ATC0cKTcvGQT03MLAqYFU
    PUBOTzQQ58Sjg2VMWGpjSiYR++fo5NW7mXBVRDE0NyIL8efn29CuimRPOhwbJiUN8ebg1MazmX1r
    YVlORDcpGQkB/P/9+O7hyLamlYd5Z1hJNyYWCf7s28vAuLO0tLS1tLW4vcPK0NXZ2dnY1dPQz87P
    0dPW2Nzg4+Xp6+3u7/Dx8vLz8/T19fb19PPy8vLy8vP09fb3+Pn6+vv7+/v7+/v7+/v7+/v7+vr5
    +Pj39/f39/f3+Pn5+vr7+/z8/fz8/Pz8+/v7+/v7+/v7+/v7+/z8/Pz8/Pz8/Pz8/Pz8/Pz8/f39
    /f39/f7+/v///////////////////////////////////////wAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAA==
    """
    
    def __init__(self):
        self.system = platform.system()
        self.sound_data = base64.b64decode(self._DEFAULT_SOUND.strip())
        
    def play(self):
        """跨平台播放声音"""
        try:
            if self.system == 'Windows':
                logger.debug("Playing sound on Windows...")
                self._play_windows()
            elif self.system == 'Darwin':
                logger.debug("Playing sound on MacOS...")
                self._play_macos()
            elif self.system == 'Linux':
                logger.debug("Playing sound on Linux...")
                if os.path.exists('/.dockerenv'):
                    logger.debug("Playing sound on Linux in container...")
                    self._play_linux_simple()
                else:
                    logger.debug("Playing sound on Linux...")
                    self._play_linux()
            else:
                logger.debug("Playing sound on fallback...")
                self._play_fallback()
        except Exception as e:
            logger.error(f"Sound playback failed: {str(e)}")
            print(f"Sound playback failed: {str(e)}")

    def _play_windows(self):
        import winsound
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(self.sound_data)
            f.close()
            winsound.PlaySound(f.name, winsound.SND_FILENAME)
            os.unlink(f.name)

    def _play_macos(self):
        with tempfile.NamedTemporaryFile(suffix='.wav') as f:
            f.write(self.sound_data)
            f.flush()
            os.system(f'afplay "{f.name}"')

    def _play_linux(self):
        players = ['paplay', 'aplay', 'play']
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            try:
                f.write(self.sound_data)
                f.flush()
                for player in players:
                    if os.system(f'which {player} > /dev/null 2>&1') == 0:
                        logger.debug(f"Playing sound with {player}...")
                        os.system(f'{player} "{f.name}"')
                        break
            finally:
                try:
                    os.unlink(f.name)
                except:
                    pass
    def _play_linux_simple(self):
        with tempfile.NamedTemporaryFile(suffix='.wav') as f:
            f.write(self.sound_data)
            f.flush()
            os.system(f'aplay "{f.name}" 2>/dev/null')
    def _play_fallback(self):
        try:
            import pygame
            pygame.mixer.init()
            sound = pygame.mixer.Sound(io.BytesIO(self.sound_data))
            logger.debug("Playing sound with pygame...")
            sound.play()
            time.sleep(1)
        except ImportError:
            logger.error("No sound playback available")

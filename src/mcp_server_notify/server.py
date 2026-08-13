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
import re
import threading
from importlib import resources

logger = logging.getLogger(__name__)

# Kokoro model files live outside the wheel — 325MB has no business in a pip
# install. `notify-setup` downloads them here; env vars override per file.
MODEL_URL_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files"
MODEL_FILES = {"kokoro-v0_19.onnx": 325525180, "voices.bin": 5758648}


def default_model_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "kokoro")


class NotificationServer:
    APP_ID = "com.qxzap.mcp_server_notify"
    APP_DISPLAY_NAME = "MCP Notify"
    DEFAULT_AGENT_ENV = "MCP_NOTIFY_DEFAULT_AGENT"
    VOICE_ENV = "MCP_NOTIFY_VOICE"
    TTS_VOICE_ENV = "MCP_NOTIFY_TTS_VOICE"
    TTS_MODEL_PATH_ENV = "MCP_NOTIFY_TTS_MODEL"
    TTS_VOICES_PATH_ENV = "MCP_NOTIFY_TTS_VOICES"
    TTS_VOICE_DEFAULT = "af_bella"
    # Cap the spoken line so latency stays low. Kokoro re-rolls prosody on
    # very long inputs; a 4-second clip is plenty for a heads-up.
    SPOKEN_MAX_CHARS = 200
    # Above this fraction of "unreadable" tokens (hex hashes, base64, paths,
    # long digit runs) we drop the raw text and speak a placeholder instead.
    UNREADABLE_THRESHOLD = 0.5

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
            self._register_aumid_identity()
        self._setup_apprise_targets()

    def _register_aumid_identity(self) -> None:
        """Name the AUMID in the registry.

        SetCurrentProcessExplicitAppUserModelID alone makes Windows show the
        raw id ("com.qxzap.mcp_server_notify") as the toast source. Windows
        reads the friendly name and icon from
        HKCU\\Software\\Classes\\AppUserModelId\\<AUMID> — this is the
        shortcut-free way to register a desktop app for toasts.
        """
        try:
            import winreg
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Classes\AppUserModelId\{self.APP_ID}",
            ) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, self.APP_DISPLAY_NAME)
                icon = self._resolve_asset("icon.ico") or self._resolve_asset("icon.png")
                if icon:
                    winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, icon)
        except Exception as e:
            logger.debug(f"Could not register AUMID identity: {e}")

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

    def _voice_default_enabled(self) -> bool:
        raw = os.environ.get(self.VOICE_ENV, "true").strip().lower()
        return raw not in ("0", "false", "no", "off")

    def _voice_enabled(self, request: NotificationRequest) -> bool:
        """Per-request voice flag wins over the env default either way."""
        return bool(request.voice) and self._voice_default_enabled()

    @classmethod
    def tts_paths(cls) -> tuple[str, str]:
        """(model, voices) — env override wins, else the shared download dir."""
        d = default_model_dir()
        return (
            os.environ.get(cls.TTS_MODEL_PATH_ENV) or os.path.join(d, "kokoro-v0_19.onnx"),
            os.environ.get(cls.TTS_VOICES_PATH_ENV) or os.path.join(d, "voices.bin"),
        )

    @property
    def _tts(self):
        """Lazy-loaded Kokoro instance. Built once and reused for the lifetime
        of the server. Thread-safe enough for our use: Kokoro's create() is
        reentrant in practice, and if two notifications fire at the same
        instant the worst case is interleaved audio, not corruption.
        """
        cached = getattr(self, "_tts_cache", None)
        if cached is not None:
            return cached
        try:
            from kokoro_onnx import Kokoro  # local import — only pay the cost if voice is used
        except ImportError:
            logger.debug("kokoro_onnx not installed; voice layer disabled.")
            self._tts_cache = False
            return False
        model, voices = self.tts_paths()
        if not (os.path.isfile(model) and os.path.isfile(voices)):
            logger.debug(f"Kokoro model/voices missing at {model} / {voices}; run notify-setup.")
            self._tts_cache = False
            return False
        try:
            kokoro = Kokoro(model, voices)
        except Exception as e:
            logger.debug(f"Kokoro init failed: {e}")
            self._tts_cache = False
            return False
        self._tts_cache = kokoro
        return kokoro

    # Tokens TTS will mangle: long hex/hash runs, base64-ish blobs, file paths,
    # long digit runs, 0x-prefixed addresses, UUIDs, JSON braces.
    _UNREADABLE_RE = re.compile(
        r"(?:"
        r"\b[0-9a-fA-F]{16,}\b"          # hex hash (16+ hex chars)
        r"|\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"  # UUID
        r"|[A-Za-z0-9+/=]{24,}"          # base64-ish (also matches long letter runs)
        r"|\b0x[0-9a-fA-F]{6,}\b"        # 0x addresses
        r"|[A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s]+"  # windows path
        r"|/(?:usr|home|var|etc|opt|tmp)/[^\s]+"  # unix path
        r"|\b\d{8,}\b"                   # long digit run
        r")"
    )

    @classmethod
    def _unreadable_ratio(cls, text: str) -> float:
        """Fraction of non-space characters inside unreadable spans (0..1)."""
        if not text:
            return 0.0
        stripped = text.strip()
        if not stripped:
            return 0.0
        non_space = len(re.sub(r"\s+", "", stripped))
        if non_space == 0:
            return 0.0
        bad = sum(m.end() - m.start() for m in cls._UNREADABLE_RE.finditer(stripped))
        return bad / non_space

    @classmethod
    def _is_unreadable(cls, text: str) -> bool:
        return cls._unreadable_ratio(text) > cls.UNREADABLE_THRESHOLD

    @classmethod
    def _build_spoken(cls, request: NotificationRequest) -> str:
        """Compose the spoken line.

        If the agent passed `speak` explicitly, that wins (still filtered as a
        defensive guard). Otherwise compose from the agent-aware prefix and the
        title+message, with a hard length cap.
        """
        agent = request.agent  # don't fall back to env default for spoken line
        prefix = f"{agent} says" if agent else "Heads up"

        # Agent override wins — but still apply the filter so a malformed
        # line doesn't make the local TTS read out a hash.
        if request.speak:
            candidate = request.speak.strip()
            if cls._is_unreadable(candidate):
                return f"{prefix}: there's news, check your screen."
            if len(candidate) > cls.SPOKEN_MAX_CHARS:
                candidate = candidate[: cls.SPOKEN_MAX_CHARS - 1].rstrip() + "…"
            return candidate

        if cls._is_unreadable(request.message):
            return f"{prefix}: there's news, check your screen."
        body = f"{request.title}. {request.message}".strip()
        if len(body) > cls.SPOKEN_MAX_CHARS:
            body = body[: cls.SPOKEN_MAX_CHARS - 1].rstrip() + "…"
        return f"{prefix}: {body}"

    def _speak(self, request: NotificationRequest) -> None:
        """Speak the notification through the local Kokoro TTS. Never raises."""
        if not self._voice_enabled(request):
            return
        text = self._build_spoken(request)
        if not text:
            return
        voice = os.environ.get(self.TTS_VOICE_ENV, self.TTS_VOICE_DEFAULT)

        # Run on a daemon thread so the tool call returns immediately — the
        # first call also pays the ~2s model load in here, not in the caller.
        def _fire():
            try:
                kokoro = self._tts
                if not kokoro:
                    logger.debug("Kokoro unavailable; skipping speech.")
                    return
                import sounddevice as sd  # local import — only pay when we actually speak
                samples, sr = kokoro.create(text, voice=voice, speed=1.0)
                sd.play(samples, sr)
                sd.wait()
            except Exception as e:
                logger.debug(f"Kokoro speak failed: {e}")

        threading.Thread(target=_fire, daemon=True).start()

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

    @staticmethod
    def _backend_order(apprise_fn, plyer_fn) -> list:
        """Which delivery backend to try first.

        On Windows, Apprise's windows:// plugin uses the legacy pywin32 shell
        balloon, which Windows 10/11 accepts and then never renders — it
        reports success, plays the system sound, and shows nothing. plyer's
        toast does render (and carries our icon), so it goes first there.
        Everywhere else Apprise is the better path (terminal-notifier on
        macOS, dbus on Linux).
        """
        if platform.system().lower() == "windows":
            return [plyer_fn, apprise_fn]
        return [apprise_fn, plyer_fn]

    def _send_notification(self, request: NotificationRequest):
        logger.debug("request: %s", request)
        notification_sent = False

        title = self._resolve_title(request)
        icon_png = self._resolve_asset("icon.png")
        icon_ico = self._resolve_asset("icon.ico")

        def send_apprise() -> bool:
            # Apprise.notify() takes no image kwarg; icons come from the
            # AppriseAsset configured in __init__.
            if not (self.apprise and len(self.apprise) > 0):
                return False
            try:
                logger.debug("尝试使用 Apprise 发送通知...")
                if self.apprise.notify(title=title, body=request.message):
                    logger.info("Apprise 通知发送成功")
                    return True
                logger.warning("Apprise 通知发送失败")
            except Exception as e:
                logger.error(f"Apprise 通知异常: {str(e)}")
            return False

        def send_plyer() -> bool:
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
                return True
            except Exception as e:
                logger.error(f"plyer 通知失败: {str(e)}")
            return False

        for backend in self._backend_order(send_apprise, send_plyer):
            if backend():
                notification_sent = True
                break

        # Last-resort log fallback (containers etc.)
        if not notification_sent or os.path.exists("/.dockerenv"):
            logger.info(f"通知：{title} - {request.message}")
            print(f"Notification: {title} - {request.message}")

        if request.play_sound:
            logger.debug("播放通知声音...")
            self.sound_player.play()

        # Voice layer — fire-and-forget HTTP to the ai-calls TTS server.
        # Independent of sound: callers can have one without the other.
        self._speak(request)

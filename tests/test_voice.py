"""Tests for the voice layer (ai-calls TTS bridge)."""
from unittest.mock import patch, MagicMock
from mcp_server_notify.schemas import NotificationRequest
from mcp_server_notify.server import NotificationServer


def _bare_server():
    """Build a NotificationServer without running __init__ (skips AUMID + Apprise)."""
    return NotificationServer.__new__(NotificationServer)


# --- readability filter ----------------------------------------------------

def test_unreadable_pure_hex_hash():
    assert NotificationServer._is_unreadable(
        "compiled blob sha256 abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
    )


def test_unreadable_long_base64():
    assert NotificationServer._is_unreadable(
        "atob dGhlIHF1aWNrIGJyb3duIGZveCBqdW1wcyBvdmVyIDEzIGRvZ3M="
    )


def test_unreadable_windows_path():
    assert NotificationServer._is_unreadable(
        r"failed to read C:\Users\Milea\AppData\Local\Temp\build-output-7f3a9b2.log"
    )


def test_unreadable_uuid_with_minor_english():
    # one English word + a UUID is still mostly unreadable
    assert NotificationServer._is_unreadable("deployed 550e8400-e29b-41d4-a716-446655440000")


def test_readable_plain_prose():
    assert not NotificationServer._is_unreadable("All tests passed and the build is green.")


def test_readable_with_short_acronym():
    assert not NotificationServer._is_unreadable("Pushed v1.2.3 to the API server.")


def test_unreadable_empty_is_false():
    assert not NotificationServer._is_unreadable("")
    assert not NotificationServer._is_unreadable("   ")


# --- spoken line composition -----------------------------------------------

def test_spoken_with_agent_and_readable_message():
    req = NotificationRequest(title="Build done", message="All 42 tests passed.", agent="Sisyphus")
    assert NotificationServer._build_spoken(req) == "Sisyphus says: Build done. All 42 tests passed."


def test_spoken_without_agent_and_readable_message():
    req = NotificationRequest(title="Heads up", message="Something happened.")
    assert NotificationServer._build_spoken(req) == "Heads up: Heads up. Something happened."


def test_spoken_unreadable_uses_placeholder():
    req = NotificationRequest(
        title="done",
        message="sha256 deadbeefcafebabe0123456789abcdef0123456789abcdef0123456789abcdef",
        agent="Sisyphus",
    )
    line = NotificationServer._build_spoken(req)
    assert "Sisyphus says" in line
    assert "check your screen" in line
    assert "deadbeef" not in line  # raw blob must not be spoken


def test_spoken_truncates_long_body():
    req = NotificationRequest(title="t", message=("All clear. " * 100), agent="Sisyphus")
    line = NotificationServer._build_spoken(req)
    assert len(line) <= NotificationServer.SPOKEN_MAX_CHARS + 30  # headroom for "Sisyphus says: "
    assert line.endswith("…")


# --- voice enablement ------------------------------------------------------

def test_voice_enabled_per_request_true():
    server = _bare_server()
    req = NotificationRequest(title="x", message="y", voice=True)
    assert server._voice_enabled(req) is True


def test_voice_disabled_per_request_false_overrides_env(monkeypatch):
    monkeypatch.setenv("MCP_NOTIFY_VOICE", "true")
    server = _bare_server()
    req = NotificationRequest(title="x", message="y", voice=False)
    assert server._voice_enabled(req) is False


def test_voice_disabled_by_env(monkeypatch):
    monkeypatch.setenv("MCP_NOTIFY_VOICE", "false")
    server = _bare_server()
    req = NotificationRequest(title="x", message="y")
    assert server._voice_enabled(req) is False


def test_voice_env_accepts_common_falses(monkeypatch):
    server = _bare_server()
    req = NotificationRequest(title="x", message="y")
    for val in ("0", "no", "off", "FALSE", "  false  "):
        monkeypatch.setenv("MCP_NOTIFY_VOICE", val)
        assert server._voice_enabled(req) is False, val


def test_voice_env_defaults_to_true_when_unset(monkeypatch):
    monkeypatch.delenv("MCP_NOTIFY_VOICE", raising=False)
    server = _bare_server()
    req = NotificationRequest(title="x", message="y")
    assert server._voice_enabled(req) is True


def test_ai_calls_url_default(monkeypatch):
    monkeypatch.delenv("AI_CALLS_URL", raising=False)
    server = _bare_server()
    assert server._ai_calls_url() == "http://localhost:3414"


def test_ai_calls_url_override(monkeypatch):
    monkeypatch.setenv("AI_CALLS_URL", "http://voice.lan:9000/")
    server = _bare_server()
    assert server._ai_calls_url() == "http://voice.lan:9000"  # trailing slash stripped


# --- _speak does not block + never raises ----------------------------------

def test_speak_skips_when_voice_disabled(monkeypatch):
    import time as _time
    monkeypatch.setenv("MCP_NOTIFY_VOICE", "false")
    server = _bare_server()
    with patch("urllib.request.urlopen") as mock_open:
        server._speak(NotificationRequest(title="x", message="y"))
        # Give the daemon thread a tick to fail — urlopen must NOT have been called.
        _time.sleep(0.05)
        mock_open.assert_not_called()


def test_speak_fires_urlopen_when_enabled():
    import time as _time
    server = _bare_server()
    with patch("urllib.request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b""
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = lambda s, *a: False
        mock_open.return_value = mock_resp
        server._speak(NotificationRequest(title="Done", message="All tests passed.", agent="Sisyphus"))
        # Drain the daemon thread.
        _time.sleep(0.1)
        assert mock_open.called
        url_arg = mock_open.call_args[0][0]
        assert "/speak?" in url_arg
        assert "Sisyphus" in url_arg
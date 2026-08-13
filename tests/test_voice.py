"""Tests for the voice layer (local Kokoro TTS)."""
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
    assert "deadbeef" not in line


def test_spoken_truncates_long_body():
    req = NotificationRequest(title="t", message=("All clear. " * 100), agent="Sisyphus")
    line = NotificationServer._build_spoken(req)
    assert len(line) <= NotificationServer.SPOKEN_MAX_CHARS + 30
    assert line.endswith("…")


# --- speak override (agent-supplied line) -----------------------------------

def test_spoken_uses_explicit_speak_override():
    req = NotificationRequest(
        title="ignored",
        message="ignored",
        agent="Sisyphus",
        speak="Hey, I'm done — that was fast.",
    )
    assert NotificationServer._build_spoken(req) == "Hey, I'm done — that was fast."


def test_spoken_override_still_filtered_if_unreadable():
    req = NotificationRequest(
        title="x",
        message="y",
        agent="Sisyphus",
        speak="sha256 deadbeefcafebabe0123456789abcdef0123456789abcdef0123456789abcdef",
    )
    line = NotificationServer._build_spoken(req)
    assert "deadbeef" not in line
    assert "check your screen" in line


def test_spoken_override_truncated_if_too_long():
    long = "word " * 200
    req = NotificationRequest(title="x", message="y", speak=long.strip())
    line = NotificationServer._build_spoken(req)
    assert len(line) <= NotificationServer.SPOKEN_MAX_CHARS
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
    monkeypatch.setattr("mcp_server_notify.server.load_config", dict)
    server = _bare_server()
    req = NotificationRequest(title="x", message="y")
    assert server._voice_enabled(req) is True


def test_voice_falls_back_to_setup_choice(monkeypatch):
    """notify-setup writes {"voice": false}; that must silence speech."""
    monkeypatch.delenv("MCP_NOTIFY_VOICE", raising=False)
    monkeypatch.setattr("mcp_server_notify.server.load_config", lambda: {"voice": False})
    server = _bare_server()
    assert server._voice_enabled(NotificationRequest(title="x", message="y")) is False


def test_voice_env_overrides_setup_choice(monkeypatch):
    monkeypatch.setenv("MCP_NOTIFY_VOICE", "true")
    monkeypatch.setattr("mcp_server_notify.server.load_config", lambda: {"voice": False})
    server = _bare_server()
    assert server._voice_enabled(NotificationRequest(title="x", message="y")) is True


# --- Kokoro backend integration --------------------------------------------

def test_tts_lazy_load_returns_false_when_kokoro_missing(monkeypatch):
    """If kokoro_onnx isn't importable, _tts returns False instead of raising."""
    server = _bare_server()
    # Block the import by hiding the module.
    monkeypatch.setitem(__import__("sys").modules, "kokoro_onnx", None)
    assert server._tts is False


def test_tts_lazy_load_returns_false_when_models_missing(monkeypatch, tmp_path):
    """Model files not present at the configured path → _tts returns False."""
    monkeypatch.setenv("MCP_NOTIFY_TTS_MODEL", str(tmp_path / "missing.onnx"))
    monkeypatch.setenv("MCP_NOTIFY_TTS_VOICES", str(tmp_path / "missing.bin"))
    # Force a successful import of kokoro_onnx.
    fake_mod = MagicMock()
    fake_mod.Kokoro = MagicMock()
    monkeypatch.setitem(__import__("sys").modules, "kokoro_onnx", fake_mod)
    server = _bare_server()
    assert server._tts is False


def test_tts_paths_default_to_shared_dir(monkeypatch):
    monkeypatch.delenv("MCP_NOTIFY_TTS_MODEL", raising=False)
    monkeypatch.delenv("MCP_NOTIFY_TTS_VOICES", raising=False)
    model, voices = NotificationServer.tts_paths()
    assert model.endswith("kokoro-v0_19.onnx")
    assert voices.endswith("voices.bin")
    assert "kokoro" in model  # lands in the download dir, not the cwd


def test_tts_paths_env_overrides_each_file(monkeypatch):
    monkeypatch.setenv("MCP_NOTIFY_TTS_MODEL", "/custom/m.onnx")
    monkeypatch.delenv("MCP_NOTIFY_TTS_VOICES", raising=False)
    model, voices = NotificationServer.tts_paths()
    assert model == "/custom/m.onnx"
    assert voices.endswith("voices.bin")  # the other file still uses the default


def test_tts_loads_model_only_once(monkeypatch, tmp_path):
    """Regression: the cache attribute must actually be hit on the 2nd access.

    A private-name (__tts) cache silently never hit, so every notification
    re-loaded the 325MB ONNX model.
    """
    model = tmp_path / "m.onnx"
    voices = tmp_path / "v.bin"
    model.write_bytes(b"x")
    voices.write_bytes(b"x")
    monkeypatch.setenv("MCP_NOTIFY_TTS_MODEL", str(model))
    monkeypatch.setenv("MCP_NOTIFY_TTS_VOICES", str(voices))
    fake_mod = MagicMock()
    monkeypatch.setitem(__import__("sys").modules, "kokoro_onnx", fake_mod)
    server = _bare_server()
    first, second = server._tts, server._tts
    assert first is second
    assert fake_mod.Kokoro.call_count == 1


def test_speak_skips_when_voice_disabled(monkeypatch):
    import time as _time
    monkeypatch.setenv("MCP_NOTIFY_VOICE", "false")
    server = _bare_server()
    server._tts_cache = False  # pre-seed the lazy cache so no model load happens
    with patch("sounddevice.play") as mock_play:
        server._speak(NotificationRequest(title="x", message="y"))
        _time.sleep(0.05)
        mock_play.assert_not_called()


def test_speak_invokes_kokoro_when_enabled():
    import time as _time
    server = _bare_server()

    fake_kokoro = MagicMock()
    fake_kokoro.create.return_value = (b"\x00\x00" * 24000, 24000)
    server._tts_cache = fake_kokoro

    with patch("sounddevice.play") as mock_play, \
         patch("sounddevice.wait") as mock_wait:
        server._speak(NotificationRequest(
            title="Done",
            message="All tests passed.",
            agent="Sisyphus",
        ))
        _time.sleep(0.1)
        assert fake_kokoro.create.called
        text_arg = fake_kokoro.create.call_args[0][0]
        assert "Sisyphus" in text_arg
        assert "All tests passed" in text_arg
        assert mock_play.called
        assert mock_wait.called


def test_speak_uses_explicit_speak_param():
    import time as _time
    server = _bare_server()
    fake_kokoro = MagicMock()
    fake_kokoro.create.return_value = (b"\x00\x00" * 24000, 24000)
    server._tts_cache = fake_kokoro
    with patch("sounddevice.play"), patch("sounddevice.wait"):
        server._speak(NotificationRequest(
            title="ignored",
            message="ignored",
            speak="A custom crafted line from the agent.",
        ))
        _time.sleep(0.1)
        text_arg = fake_kokoro.create.call_args[0][0]
        assert text_arg == "A custom crafted line from the agent."
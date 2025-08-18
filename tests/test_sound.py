import pytest
from mcp_server_notify.sound import SoundPlayer
from unittest.mock import patch


@pytest.mark.parametrize("platform_name", ["Linux", "Windows", "Darwin"])
def test_sound_play(platform_name, monkeypatch):
    monkeypatch.setattr("platform.system", lambda: platform_name)

    player = SoundPlayer()

    with patch("os.system") as mock_system:
        mock_system.return_value = 0
        player.play()
        if platform_name == "Linux":
            assert any(
                "paplay" in str(call) or "aplay" in str(call) or "play" in str(call)
                for call in mock_system.call_args_list
            )
        elif platform_name == "Windows":
            mock_system.assert_not_called()
        elif platform_name == "Darwin":
            assert any("afplay" in str(call) for call in mock_system.call_args_list)

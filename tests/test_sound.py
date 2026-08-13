import pytest
from mcp_server_notify.sound import SoundPlayer
from unittest.mock import patch, MagicMock

@pytest.mark.parametrize("platform", ["Linux", "Windows", "Darwin"])
def test_sound_play(platform, monkeypatch):
    # 模拟平台
    monkeypatch.setattr("platform.system", lambda: platform)
    
    # 创建播放器
    player = SoundPlayer()
    
    with patch("os.system") as mock_system:
        # 模拟which命令成功
        mock_system.return_value = 0
        
        # 执行播放
        player.play()
        
        # 验证平台行为
        if platform == "Linux":
            # 检查最终播放命令
            assert any("paplay" in str(call) or "aplay" in str(call) for call in mock_system.call_args_list)
        elif platform == "Windows":
            # Windows不应调用os.system
            mock_system.assert_not_called()
        elif platform == "Darwin":
            # macOS应调用afplay
            mock_system.assert_called_once_with('afplay "{}"'.format(mock_system.call_args_list[0].args[0].split('"')[1]))

def test_windows_plays_from_memory_not_a_temp_file(monkeypatch):
    """A temp file costs ~1.4s (AV scan) to play 15ms of audio."""
    monkeypatch.setattr("platform.system", lambda: "Windows")
    player = SoundPlayer()
    winsound = MagicMock(SND_MEMORY=4)
    monkeypatch.setitem(__import__("sys").modules, "winsound", winsound)
    with patch("tempfile.NamedTemporaryFile") as mock_tmp:
        player.play()
        mock_tmp.assert_not_called()
    winsound.PlaySound.assert_called_once_with(player.sound_data, winsound.SND_MEMORY)

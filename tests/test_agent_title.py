from mcp_server_notify.schemas import NotificationRequest
from mcp_server_notify.server import NotificationServer


def test_resolve_title_no_agent():
    server = NotificationServer.__new__(NotificationServer)
    req = NotificationRequest(title="Hello", message="World")
    assert server._resolve_title(req) == "Hello"


def test_resolve_title_with_agent():
    server = NotificationServer.__new__(NotificationServer)
    req = NotificationRequest(title="Hello", message="World", agent="Sisyphus")
    assert server._resolve_title(req) == "[Sisyphus] Hello"


def test_resolve_title_with_default_agent_env(monkeypatch):
    monkeypatch.setenv("MCP_NOTIFY_DEFAULT_AGENT", "Cluster")
    server = NotificationServer.__new__(NotificationServer)
    req = NotificationRequest(title="Hello", message="World")
    assert server._resolve_title(req) == "[Cluster] Hello"


def test_resolve_title_agent_overrides_env(monkeypatch):
    monkeypatch.setenv("MCP_NOTIFY_DEFAULT_AGENT", "Cluster")
    server = NotificationServer.__new__(NotificationServer)
    req = NotificationRequest(title="Hello", message="World", agent="Sisyphus")
    assert server._resolve_title(req) == "[Sisyphus] Hello"


def test_schema_accepts_agent_field():
    req = NotificationRequest(title="x", message="y", agent="Zap")
    assert req.agent == "Zap"


def test_schema_agent_optional():
    req = NotificationRequest(title="x", message="y")
    assert req.agent is None


# --- delivery backend order -------------------------------------------------

def test_backend_order_prefers_plyer_on_windows(monkeypatch):
    """Apprise's windows:// reports success but renders nothing on Win10/11 —
    it must not shadow plyer, or the user only hears the sound."""
    monkeypatch.setattr("mcp_server_notify.server.platform.system", lambda: "Windows")
    assert NotificationServer._backend_order("apprise", "plyer") == ["plyer", "apprise"]


def test_backend_order_prefers_apprise_elsewhere(monkeypatch):
    monkeypatch.setattr("mcp_server_notify.server.platform.system", lambda: "Darwin")
    assert NotificationServer._backend_order("apprise", "plyer") == ["apprise", "plyer"]

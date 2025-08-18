import sys
import types
from contextlib import asynccontextmanager

# Create stub modules for the `mcp` package to satisfy imports during tests
mcp = types.ModuleType("mcp")
server_mod = types.ModuleType("mcp.server")
stdio_mod = types.ModuleType("mcp.server.stdio")
types_mod = types.ModuleType("mcp.types")

class Server:
    def __init__(self, name: str):
        self.name = name
    def list_tools(self):
        def decorator(func):
            return func
        return decorator
    def call_tool(self):
        def decorator(func):
            self._call_tool = func
            return func
        return decorator
    def create_initialization_options(self):
        return {}
    async def run(self, read_stream, write_stream, options):
        pass

@asynccontextmanager
async def stdio_server():
    yield (None, None)

class Tool:
    def __init__(self, name: str, description: str, inputSchema: dict):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema

class TextContent:
    def __init__(self, type: str, text: str):
        self.type = type
        self.text = text

server_mod.Server = Server
stdio_mod.stdio_server = stdio_server
types_mod.Tool = Tool
types_mod.TextContent = TextContent

sys.modules["mcp"] = mcp
sys.modules["mcp.server"] = server_mod
sys.modules["mcp.server.stdio"] = stdio_mod
sys.modules["mcp.types"] = types_mod

# Stub out external notification libraries used by NotificationServer
apprise_mod = types.ModuleType("apprise")

class Apprise:
    def __init__(self):
        self.targets: list[str] = []
    def add(self, target: str):
        self.targets.append(target)
        return True
    def notify(self, **kwargs):
        return True
    def __len__(self):
        return len(self.targets)

apprise_mod.Apprise = Apprise

plyer_mod = types.ModuleType("plyer")
notification_mod = types.ModuleType("plyer.notification")

def notify(**kwargs):
    return True

notification_mod.notify = notify
plyer_mod.notification = notification_mod

sys.modules["apprise"] = apprise_mod
sys.modules["plyer"] = plyer_mod
sys.modules["plyer.notification"] = notification_mod

# Minimal stub for pydantic used in schemas
pydantic_mod = types.ModuleType("pydantic")

class ValidationError(Exception):
    pass

class BaseModel:
    def __init__(self, **data):
        for field in self.__annotations__:
            if field in data:
                setattr(self, field, data[field])
            elif hasattr(self.__class__, field):
                setattr(self, field, getattr(self.__class__, field))
            else:
                raise ValidationError(f"Missing field: {field}")

    @classmethod
    def model_json_schema(cls):
        return {}

pydantic_mod.BaseModel = BaseModel
pydantic_mod.ValidationError = ValidationError

sys.modules["pydantic"] = pydantic_mod

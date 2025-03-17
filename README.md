# MCP Notify Server

[English](README.md) | [中文](README.zh.md)

An MCP (Model Context Protocol) service that provides system notification functionality for LLMs. Send desktop notifications when agent tasks are completed.

## Features

- Send system desktop notifications after agent tasks completion
- Play alert sounds to grab user attention
- Cross-platform support (Windows, macOS, Linux)
- Based on standard MCP protocol, integrates with various LLM clients

## Installation

### Install using [uv](https://docs.astral.sh/uv/) package manager

```bash
git clone https://github.com/Cactusinhand/mcp_server_notify.git
cd mcp_server_notify

uv venv
source .venv/Scripts/activate

uv pip install mcp-server-notify
# or
pip install mcp-server-notify
```

After installation, call the module directly to check if installation was successful:
```bash
python -m mcp_server_notify
```
This module accepts ` --debug ` or `--file ` option, we can use it like:
```shell
python -m mcp_server_notify --debug
python -m mcp_server_notify --debug --log-file=path/to/logfile.log
```

## Special requirements

We use [Apprise](https://github.com/caronc/apprise) API for our Desktop notification deliver，so we need to install some special requirements in our Desktop

**Windows**
```shell
# windows:// minimum requirements
pip install pywin32
```

**macOS**
```shell
# Make sure terminal-notifier is installed into your system
brew install terminal-notifier
```

## Usage

### Using with Claude Desktop:

Find the configuration file `claude_desktop_config.json`
```json
{
    "mcpServers": {
        "NotificationServer": {
            "command": "uv",
            "args": [
              "--directory",
              "path/to/your/mcp_server_notify project",
              "run",
              "mcp-server-notify",
            ]
        }
    }
}
```

If installed globally, you can also use the python command:
```json
{
    "mcpServers": {
        "NotificationServer": {
            "command": "python",
            "args": [
              "-m",
              "mcp_server_notify",
            ]
        }
    }
}
```

### Using with Cursor:
Find the configuration file `~/.cursor/mcp.json` or `your_project/.cursor/mcp.json`
```json
{
    "mcpServers": {
        "NotificationServer": {
            "command": "uv",
            "args": [
              "--directory",
              "path/to/your/mcp_server_notify project",
              "run",
              "mcp-server-notify",
            ]
        }
    }
}
```

After configuration, simply add a prompt like `finally, send me a notification when task finished.` at the end of your task input to the AI to trigger notifications.

In Cursor, you can add this prompt as a rule in `Cursor Settings` -> `Rules` so you don't have to type it manually each time.

### Running with Docker

Currently not available due to environment compatibility issues.
If Docker containers need to trigger host notifications regardless of whether the host OS is Windows, macOS, or Linux, the solution becomes much more complex, and direct use of native notifications is usually not feasible.

Main issues:
1. OS-specific notification systems
Each operating system (Windows, macOS, Linux) has its unique notification mechanism.

2. Docker isolation
The isolation of Docker containers limits their ability to access host operating system resources directly.

3. Dependency management
Need to handle different notification libraries and dependencies for each operating system.

## License

MIT

## Contributions

Issues and pull requests are welcome!

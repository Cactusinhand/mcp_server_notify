<a href="https://glama.ai/mcp/servers/@Cactusinhand/mcp_server_notify"> <img width="380" height="200" src="https://glama.ai/mcp/servers/@Cactusinhand/mcp_server_notify/badge" alt="Glama badge for Notify MCP server" /> </a> [![MseeP.ai Security Assessment Badge](https://mseep.net/pr/cactusinhand-mcp-server-notify-badge.png)](https://mseep.ai/app/cactusinhand-mcp-server-notify) 

[![PyPI version](https://badge.fury.io/py/mcp-server-notify.svg)](https://badge.fury.io/py/mcp-server-notify)

[![Trust Score](https://archestra.ai/mcp-catalog/api/badge/quality/Cactusinhand/mcp_server_notify)](https://archestra.ai/mcp-catalog/Cactusinhand__mcp_server_notify)


# 📢 MCP Notify Server (qxZap fork)



[English](README.md) | [中文](README.zh.md)

A MCP server that send desktop notifications with sound effect when agent tasks are completed.

> Fork notes (qxZap):
> - Windows toast now shows **"MCP Notify"** (not "Python") via a registered AppUserModelID.
> - Bundled notification-bot icon (SVG + PNG + ICO) shipped under `src/mcp_server_notify/assets/`.
> - Per-agent title prefix via the new `agent` parameter (see below).

## 🥩 Features

- Send system desktop notifications after agent tasks completion
- Play alert sounds to grab user attention, with sound file inside.
- Cross-platform support (Windows, macOS, Linux)
- Stable Windows AppUserModelID + bundled bot icon (Windows toast source shows "MCP Notify", not "Python")
- Per-agent title prefix to distinguish which agent triggered the notification
- Based on standard MCP protocol, integrates with various LLM clients

## 🆕 Per-agent title prefix

Pass an optional `agent` field on the request. When set, the title is rendered as `[agent] <title>` so you can tell at a glance which agent is calling for attention.

```json
{
  "title": "Build complete",
  "message": "All 42 tests passed",
  "agent": "Sisyphus"
}
```

Renders as: `[Sisyphus] Build complete`

You can also set a default agent for the server via the `MCP_NOTIFY_DEFAULT_AGENT` environment variable — every notification without an explicit `agent` will then use that prefix. Per-call `agent` overrides the env default.

## 🆕 Optional voice layer (local GPU TTS via Kokoro-82M)

Every notification can also be read out loud through [Kokoro-82M](https://github.com/thewh1teagle/kokoro-onnx) running locally on your GPU (ONNX runtime, ~200MB VRAM). Fully offline, no API keys, no network — once the model is on disk, speech is instant. A readability filter runs first — if more than half of the message is hex hashes, UUIDs, base64, paths, or long digit runs, the spoken line collapses to `"<agent> says: there's news, check your screen."` so TTS doesn't vocalize garbled blobs.

**Per-request fields:**

```json
{
  "title": "Build complete",
  "message": "All 42 tests passed.",
  "agent": "Sisyphus",
  "voice": true,
  "speak": "Hey, I'm done — that was fast."
}
```

- `voice: bool = True` — enable speech for this call. Per-request wins over env.
- `speak: str | None` — agent-supplied spoken line. Wins over auto-composed line. Server still filters and truncates it as a defensive guard.

**Voice defaults:**

- `voice: true` by default on every request.
- Override globally with `MCP_NOTIFY_VOICE=false` (also accepts `0`, `no`, `off`).
- Per-request `voice: false` overrides an enabled env default.
- Per-request `voice: true` re-enables speech even if the env disabled it.
- Voice picker: `MCP_NOTIFY_TTS_VOICE` env var (default `af_bella`). Available: `af_bella`, `af_nicole`, `af_sarah`, `af_sky`, `am_adam`, `am_michael`, `bf_emma`, `bf_isabella`, `bm_george`, `bm_lewis`, plus blends like `af`.
- Model paths (override with `MCP_NOTIFY_TTS_MODEL` / `MCP_NOTIFY_TTS_VOICES`):
  - Default model: `D:/Models/kokoro/kokoro-v0_19.onnx`
  - Default voices: `D:/Models/kokoro/voices.bin`

**One-time setup:**

```bash
mkdir -p D:/Models/kokoro
curl -L -o D:/Models/kokoro/kokoro-v0_19.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx
curl -L -o D:/Models/kokoro/voices.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin
pip install kokoro-onnx sounddevice
```

If the model files aren't present, speech silently no-ops (the toast still works). Failures during synth or playback are logged at debug level and never block or fail the toast itself.

## ⏬ Installation

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

## ⚠️❕ Special requirements

** We use [Apprise](https://github.com/caronc/apprise) API for our Desktop notification deliver，so we need to install some special requirements in our Desktop **

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

## 📚 Usage

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

### ⚡️ Using with Cursor:
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

### ⚡️ Using with VSCode + Copilot:
1.	Install the service manager [uv/uvx](https://docs.astral.sh/uv/):
`pip install uv`
2.	 Add the service to VSCode settings:

     Windows `%APPDATA%\Code\User\settings.json`  
macOS `$HOME/Library/Application\ Support/Code/User/settings.json`  
Linux `$HOME/.config/Code/User/settings.json`  

	 ```json
	 "mcp": {
         "servers": {
             "notifier": {
                 "command": "uvx",
                 "args": [
                     "mcp-server-notify"
                 ],
                 "env": {}
             }
         }
	 }
	 ```
3.	Make sure you are using the latest VSCode version — it automatically runs MCP services
4.	Open VSCode → enable Copilot → switch to agent mode.
5.	Type # → you will see the #send_notification option.
6.	Ask the agent: run #send_notification (it will handle the notification automatically).
7.	Now the Copilot in agent mode can send desktop notifications.



### 🐳 Running with Docker

Currently not available due to environment compatibility issues.
If Docker containers need to trigger host notifications regardless of whether the host OS is Windows, macOS, or Linux, the solution becomes much more complex, and direct use of native notifications is usually not feasible.

Main issues:
1. OS-specific notification systems
Each operating system (Windows, macOS, Linux) has its unique notification mechanism.

2. Docker isolation
The isolation of Docker containers limits their ability to access host operating system resources directly.

3. Dependency management
Need to handle different notification libraries and dependencies for each operating system.

## 🧾 License

MIT

## 💻 Contributions

Issues and pull requests are welcome!
